"""Offline contract tests; never start Keycloak or create identity material."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/keycloak-hosted/start.sh"


class HostedKeycloakTests(unittest.TestCase):
    def run_config(self, changes=None):
        with tempfile.TemporaryDirectory() as directory:
            ca = Path(directory) / "public-ca.pem"
            ca.write_text("public certificate fixture; not a live trust anchor")
            env = {
                "PATH": os.defpath,
                "RENDER_EXTERNAL_URL": "https://devobs-keycloak-hosted.onrender.com",
                "DEVOBS_OIDC_REDIRECT_URI": "https://devobs.onrender.com/callback",
                "DEVOBS_KEYCLOAK_DB_HOST": "dpg-fixture-a.frankfurt-postgres.render.com",
                "DEVOBS_KEYCLOAK_DB_NAME": "keycloak_identity",
                "KC_DB_USERNAME": "keycloak_idp",
                "KC_DB_PASSWORD": "synthetic-db-marker",
                "KC_BOOTSTRAP_ADMIN_USERNAME": "bootstrap",
                "KC_BOOTSTRAP_ADMIN_PASSWORD": "synthetic-admin-marker",
                "DEVOBS_KEYCLOAK_DB_CA_FILE": str(ca),
            }
            env.update(changes or {})
            return subprocess.run(
                ["bash", "-c", 'source "$1"; validate_config || exit 1; printf "%s\\n" "$KC_HOSTNAME" "$DEVOBS_OIDC_CLIENT_ORIGIN" "$KC_DB_URL" "$KC_HTTP_PORT"', "--", str(SCRIPT)],
                env=env, text=True, capture_output=True, check=False,
            )

    def test_valid_configuration_exports_verified_tls_and_exact_origin(self):
        result = self.run_config()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("https://devobs-keycloak-hosted.onrender.com", result.stdout)
        self.assertIn("https://devobs.onrender.com", result.stdout)
        self.assertIn("sslmode=verify-full&sslrootcert=", result.stdout)
        self.assertNotIn("synthetic-", result.stdout + result.stderr)

    def test_invalid_configuration_fails_without_echoing_values(self):
        mutations = [
            {"DEVOBS_OIDC_REDIRECT_URI": value} for value in (
                "http://devobs.onrender.com/callback", "https://*.onrender.com/callback",
                "https://user@devobs.onrender.com/callback", "https://example.com/callback",
                "https://localhost/callback", "https://devobs..onrender.com/callback",
                "https://devobs.-bad.com/callback", "https://devobs.onrender.com/callback?token=secret",
            )
        ] + [
            {"KC_DB_PASSWORD": ""}, {"KC_BOOTSTRAP_ADMIN_PASSWORD": ""},
            {"PORT": "0"}, {"PORT": "65536"}, {"PORT": "1;echo secret"},
            {"DEVOBS_KEYCLOAK_DB_PORT": "-1"},
            {"DEVOBS_KEYCLOAK_DB_CA_FILE": "/missing/public-ca.pem"},
            {"DEVOBS_KEYCLOAK_DB_HOST": "db.render.com?sslmode=disable"},
            {"RENDER_EXTERNAL_URL": "https://attacker.com"},
        ]
        for changes in mutations:
            with self.subTest(changes=changes):
                result = self.run_config(changes)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "devobs-keycloak: invalid_hosted_configuration\n")

    def test_non_external_database_hosts_fail_closed(self):
        for host in (
            "dpg-fixture-a", "dpg-fixture-a.internal", "db.localhost",
            "database.render.com", "dpg-fixture-a.oregon-postgres.render.com",
            "dpg-fixture-a.frankfurt-postgres.render.com.attacker.net",
            "127.0.0.1", "db.example.com",
        ):
            with self.subTest(host=host):
                result = self.run_config({"DEVOBS_KEYCLOAK_DB_HOST": host})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "devobs-keycloak: invalid_hosted_configuration\n")

    def test_realm_requires_public_pkce_and_contains_no_identities(self):
        realm = json.loads((ROOT / "deploy/keycloak-hosted/realm.json").read_text())
        self.assertEqual(realm["users"], [])
        self.assertEqual(realm["sslRequired"], "all")
        self.assertEqual(realm["defaultSignatureAlgorithm"], "RS256")
        client, = realm["clients"]
        self.assertTrue(client["publicClient"])
        self.assertTrue(client["standardFlowEnabled"])
        for field in ("implicitFlowEnabled", "directAccessGrantsEnabled", "serviceAccountsEnabled", "fullScopeAllowed"):
            self.assertFalse(client[field])
        self.assertNotIn("secret", client)
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        self.assertEqual(client["redirectUris"], ["${DEVOBS_OIDC_REDIRECT_URI}"])
        self.assertEqual(client["webOrigins"], ["${DEVOBS_OIDC_CLIENT_ORIGIN}"])


if __name__ == "__main__":
    unittest.main()

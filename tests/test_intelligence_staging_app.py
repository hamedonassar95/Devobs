"""Staging entrypoint: offline security tests without a real cloud account."""
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


class StagingBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
        jwk.update(kid="testkey", alg="RS256", use="sig")
        cls.base = {
            "DEVOBS_OIDC_ISSUER": "https://id.example.test",
            "DEVOBS_OIDC_AUDIENCE": "devobs-api",
            "DEVOBS_OIDC_CLIENT_ID": "devobs-staging",
            "DEVOBS_OIDC_METADATA_JSON": json.dumps({
                "issuer": "https://id.example.test",
                "jwks_uri": "https://id.example.test/keys"}),
            "DEVOBS_OIDC_JWKS_JSON": json.dumps({"keys": [jwk]}),
            "DEVOBS_PG_DSN": ("postgresql://devobs_reader:synthetic@127.0.0.1:5432/"
                              "staging?sslmode=verify-full&sslrootcert=/tmp/test-ca.pem"),
        }
        # Import-time fail-closed bootstrap gets synthetic, scoped settings only.
        with patch.dict(os.environ, cls.base, clear=True):
            cls.module = importlib.import_module("devobs_intelligence.staging_app")

    def run_request(self, app, path, method="GET", auth=""):
        results = []
        body = b"".join(app({"PATH_INFO": path, "REQUEST_METHOD": method,
                             "HTTP_AUTHORIZATION": auth},
                            lambda status, headers: results.append((status, dict(headers)))))
        return results[0][0], results[0][1], body

    def test_health_is_liveness_only_and_no_secrets(self):
        app = self.module.build_app(self.base)
        status, headers, body = self.run_request(app, "/healthz")
        self.assertEqual(status, "204 No Content")
        self.assertEqual(body, b"")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.run_request(app, "/healthz", method="POST")[0][:3], "405")

    def test_api_remains_token_protected(self):
        app = self.module.build_app(self.base)
        status, headers, body = self.run_request(app, "/v1/tenants/a/projects/b/ci")
        self.assertTrue(status.startswith("401"))
        self.assertEqual(json.loads(body), {"error": "invalid_token"})
        self.assertNotIn("synthetic", str(headers) + body.decode())

    def test_missing_or_untrusted_identity_denied(self):
        for key in self.base:
            with self.subTest(missing=key):
                config = dict(self.base)
                config.pop(key)
                with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                            "^invalid_staging_config$"):
                    self.module.build_app(config)
        for name, value in [
            ("DEVOBS_OIDC_METADATA_JSON", "{}"),
            ("DEVOBS_OIDC_JWKS_JSON", "not-json"),
            ("DEVOBS_OIDC_ISSUER", "http://id.example.test"),
        ]:
            with self.subTest(invalid=name):
                config = dict(self.base)
                config[name] = value
                with self.assertRaises(self.module.StagingConfigurationError):
                    self.module.build_app(config)

    def test_no_plaintext_or_admin_postgres(self):
        for dsn in [
            "postgresql://devobs_reader:synthetic@localhost/staging",
            "postgresql://devobs_reader:synthetic@localhost/staging?sslmode=require",
            "postgresql://postgres:synthetic@localhost/staging?sslmode=verify-full&sslrootcert=/tmp/ca",
            "postgresql://postgres.ref:synthetic@localhost/staging?sslmode=verify-full&sslrootcert=/tmp/ca",
            "postgresql://devobs_reader:synthetic@localhost/staging?sslmode=verify-full",
            "not-a-connection-string",
        ]:
            with self.subTest(dsn=dsn.split("@")[0].split(":")[0]):
                config = dict(self.base)
                config["DEVOBS_PG_DSN"] = dsn
                with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                            "^invalid_staging_config$"):
                    self.module.build_app(config)

    def test_readiness_requires_actual_database_probe(self):
        # Avoid real credentials: readiness checks are isolated behind the store.
        class ProbeStore:
            healthy = True
            def probe_readiness(self):
                if not self.healthy:
                    raise RuntimeError("SECRET_database_unavailable")
                return True

        store = ProbeStore()
        with patch.object(self.module, "PostgresTenantStore", return_value=store):
            app = self.module.build_app(self.base)
        healthy = self.run_request(app, "/readyz")
        self.assertEqual(healthy[0], "204 No Content")
        self.assertEqual(healthy[2], b"")
        store.healthy = False
        unavailable = self.run_request(app, "/readyz")
        self.assertEqual(unavailable[0], "503 Service Unavailable")
        self.assertEqual(unavailable[2], b"")
        self.assertNotIn("SECRET", str(unavailable))
        self.assertEqual(self.run_request(app, "/readyz", method="POST")[0][:3], "405")

    def test_render_health_check_requires_real_readiness(self):
        config = (Path(__file__).resolve().parents[1] / "render.yaml").read_text()
        checks = [line.strip() for line in config.splitlines()
                  if line.strip().startswith("healthCheckPath:")]
        self.assertEqual(checks, ["healthCheckPath: /readyz"])
        self.assertIn("autoDeployTrigger: off", config)


if __name__ == "__main__":
    unittest.main()

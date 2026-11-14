"""Regression checks for the disposable, least-privilege Keycloak client."""

import copy
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REALM_PATH = ROOT / "dev" / "keycloak" / "realm.local.json"
CLIENT_ID = "devobs-local-public"
REDIRECTS = {
    "http://localhost:8765/callback",
    "http://127.0.0.1:8765/callback",
}
FORBIDDEN_KEYS = {
    "password",
    "clientsecret",
    "secret",
    "credentials",
    "privatekey",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "adminuser",
    "adminpassword",
}


def _normalized_key(key):
    return "".join(char.lower() for char in key if char.isalnum())


def contract_violations(realm):
    """Return stable violation codes for unsafe local-client config changes."""
    failures = []
    clients = realm.get("clients")
    if not isinstance(clients, list) or len(clients) != 1:
        return ["client_count"]

    client = clients[0]
    if client.get("clientId") != CLIENT_ID:
        failures.append("client_id")
    if client.get("protocol") != "openid-connect" or client.get("publicClient") is not True:
        failures.append("public_oidc_client")
    if client.get("standardFlowEnabled") is not True:
        failures.append("authorization_code_disabled")
    for field in (
        "implicitFlowEnabled",
        "directAccessGrantsEnabled",
        "serviceAccountsEnabled",
        "authorizationServicesEnabled",
    ):
        if client.get(field) is not False:
            failures.append(f"grant_{field}")
    if client.get("fullScopeAllowed") is not False:
        failures.append("full_scope_allowed")

    redirects = client.get("redirectUris")
    if not isinstance(redirects, list) or set(redirects) != REDIRECTS:
        failures.append("redirect_allowlist")
    elif any("*" in uri for uri in redirects):
        failures.append("wildcard_redirect")
    if set(client.get("webOrigins", [])) != {
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    }:
        failures.append("web_origin_allowlist")

    attributes = client.get("attributes", {})
    if attributes.get("pkce.code.challenge.method") != "S256":
        failures.append("pkce_s256_required")
    if attributes.get("access.token.header.type.rfc9068") != "true":
        failures.append("at_jwt_header_not_enabled")
    if client.get("defaultClientScopes") != []:
        failures.append("broad_default_scopes")
    if client.get("optionalClientScopes") != ["devobs.read"]:
        failures.append("optional_scopes_not_minimal")

    mappers = client.get("protocolMappers", [])
    by_name = {mapper.get("name"): mapper for mapper in mappers}
    if len(mappers) != 2 or set(by_name) != {
        "devobs-api-audience",
        "devobs-local-client-id",
    }:
        failures.append("unapproved_protocol_mapper")
    audience = by_name.get("devobs-api-audience", {})
    if (
        audience.get("protocol") != "openid-connect"
        or audience.get("protocolMapper") != "oidc-audience-mapper"
        or audience.get("config", {}).get("included.custom.audience") != "devobs-api"
        or audience.get("config", {}).get("access.token.claim") != "true"
    ):
        failures.append("audience_mapper")
    client_id_mapper = by_name.get("devobs-local-client-id", {})
    client_id_config = client_id_mapper.get("config", {})
    if (
        client_id_mapper.get("protocol") != "openid-connect"
        or client_id_mapper.get("protocolMapper") != "oidc-hardcoded-claim-mapper"
        or client_id_config.get("claim.name") != "client_id"
        or client_id_config.get("claim.value") != CLIENT_ID
        or client_id_config.get("jsonType.label") != "String"
        or client_id_config.get("access.token.claim") != "true"
    ):
        failures.append("client_id_mapper")

    scopes = realm.get("clientScopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        failures.append("client_scope_count")
    elif (
        scopes[0].get("name") != "devobs.read"
        or scopes[0].get("protocol") != "openid-connect"
        or scopes[0].get("protocolMappers") != []
    ):
        failures.append("read_scope_not_minimal")
    if realm.get("users") != []:
        failures.append("users_present")
    if realm.get("defaultSignatureAlgorithm") != "RS256":
        failures.append("realm_signing_algorithm")
    lifespan = realm.get("accessTokenLifespan")
    if not isinstance(lifespan, int) or not 1 <= lifespan <= 900:
        failures.append("access_token_lifetime")

    def inspect_keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                if _normalized_key(key) in FORBIDDEN_KEYS:
                    failures.append("embedded_credential_field")
                inspect_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                inspect_keys(nested)

    inspect_keys(realm)
    return sorted(set(failures))


class KeycloakLocalClientConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.realm = json.loads(REALM_PATH.read_text(encoding="utf-8"))

    def test_realm_contains_one_minimal_public_pkce_client(self):
        self.assertEqual(contract_violations(self.realm), [])
        client = self.realm["clients"][0]
        self.assertEqual(set(client["redirectUris"]), REDIRECTS)
        self.assertEqual(client["optionalClientScopes"], ["devobs.read"])
        self.assertNotIn("devobs.ai.diagnose", client["optionalClientScopes"])
        mapper_ids = {mapper["protocolMapper"] for mapper in client["protocolMappers"]}
        self.assertEqual(mapper_ids, {"oidc-audience-mapper", "oidc-hardcoded-claim-mapper"})

    def test_rejects_implicit_password_and_service_account_grants(self):
        for field in (
            "implicitFlowEnabled",
            "directAccessGrantsEnabled",
            "serviceAccountsEnabled",
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.realm)
                changed["clients"][0][field] = True
                self.assertIn(f"grant_{field}", contract_violations(changed))

    def test_rejects_wildcard_or_non_local_redirects(self):
        for redirect in ("http://localhost:8765/*", "https://attacker.example/callback"):
            with self.subTest(redirect=redirect):
                changed = copy.deepcopy(self.realm)
                changed["clients"][0]["redirectUris"] = [redirect]
                self.assertIn("redirect_allowlist", contract_violations(changed))

    def test_rejects_broad_role_scopes_and_automatic_diagnosis(self):
        changed = copy.deepcopy(self.realm)
        changed["clients"][0]["defaultClientScopes"] = ["roles", "profile"]
        changed["clients"][0]["optionalClientScopes"].append("devobs.ai.diagnose")
        self.assertIn("broad_default_scopes", contract_violations(changed))
        self.assertIn("optional_scopes_not_minimal", contract_violations(changed))

        changed = copy.deepcopy(self.realm)
        changed["clients"][0]["protocolMappers"].append(
            {
                "name": "unapproved-role-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {"access.token.claim": "true"},
            }
        )
        self.assertIn("unapproved_protocol_mapper", contract_violations(changed))

    def test_rejects_embedded_credentials_users_and_private_key_fields(self):
        mutations = (
            ("secret", "should-never-be-present"),
            ("clientSecret", "should-never-be-present"),
            ("credentials", [{"value": "should-never-be-present"}]),
            ("privateKey", "should-never-be-present"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.realm)
                changed["clients"][0][field] = value
                self.assertIn("embedded_credential_field", contract_violations(changed))

        changed = copy.deepcopy(self.realm)
        changed["users"] = [{"username": "test-user"}]
        self.assertIn("users_present", contract_violations(changed))


if __name__ == "__main__":
    unittest.main()

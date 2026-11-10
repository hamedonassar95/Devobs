"""Synthetic Keycloak-style RFC 9068 access-token compatibility; never calls an IdP."""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from devobs_intelligence.oidc_metadata import trusted_oidc_verifier, IssuerConfigurationError
from devobs_intelligence.oidc_tokens import AuthenticationError


ISSUER = "https://id.example.test/realms/devobs-staging"
AUDIENCE = "devobs-api"
CLIENT = "devobs-staging-app"
SUBJECT = "9e5806bb-588d-4e56-84f8-247ebf1ac82e"


class KeycloakAccessTokenCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key()))
        cls.public.update(kid="keycloak-test-key", alg="RS256", use="sig")

    def verifier(self, metadata=None):
        return trusted_oidc_verifier(
            ISSUER, AUDIENCE, CLIENT,
            metadata if metadata is not None else {
                "issuer": ISSUER,
                "jwks_uri": ISSUER + "/protocol/openid-connect/certs",
            },
            {"keys": [self.public]},
        )

    def token(self, claims=None, headers=None, private=None):
        now = int(time.time())
        payload = {
            "iss": ISSUER, "aud": AUDIENCE, "sub": SUBJECT,
            "client_id": CLIENT, "jti": "local-test-jti",
            "iat": now, "exp": now + 120,
            "scope": "devobs.read devobs.ai.diagnose",
        }
        if claims:
            payload.update(claims)
        token_headers = {"kid": "keycloak-test-key", "typ": "at+jwt"}
        if headers:
            token_headers.update(headers)
        return jwt.encode(payload, private or self.private, algorithm="RS256",
                          headers=token_headers)

    def assert_token_denied(self, **kwargs):
        with self.assertRaisesRegex(AuthenticationError, "^invalid_token$"):
            self.verifier().verify(self.token(**kwargs))

    def test_rfc9068_signed_uuid_subject_passes_offline(self):
        principal = self.verifier().verify(self.token())
        self.assertEqual(principal.subject, SUBJECT)
        self.assertEqual(principal.scopes, frozenset({"devobs.read", "devobs.ai.diagnose"}))

    def test_default_keycloak_jwt_header_is_not_sufficient(self):
        self.assert_token_denied(headers={"typ": "JWT"})

    def test_array_or_additional_audiences_fail_closed(self):
        for aud in ([AUDIENCE], [AUDIENCE, "account"], "account"):
            with self.subTest(aud=aud):
                self.assert_token_denied(claims={"aud": aud})

    def test_azp_is_not_substitute_for_exact_client_id(self):
        self.assert_token_denied(claims={"client_id": "other-client", "azp": CLIENT})

    def test_unmapped_provider_subject_format_is_denied(self):
        self.assert_token_denied(claims={"sub": "auth0|test-user"})

    def test_expired_and_oversized_lifetimes_are_denied(self):
        now = int(time.time())
        self.assert_token_denied(claims={"iat": now - 300, "exp": now - 10})
        self.assert_token_denied(claims={"iat": now, "exp": now + 901})

    def test_wrong_scope_or_signature_or_kid_is_denied(self):
        self.assert_token_denied(claims={"scope": "openid profile"})
        self.assert_token_denied(private=self.other)
        self.assert_token_denied(headers={"kid": "untrusted-key"})

    def test_wrong_issuer_is_denied(self):
        self.assert_token_denied(claims={"iss": "https://other.example.test/realms/devobs-staging"})

    def test_cross_origin_jwks_metadata_is_not_trusted(self):
        with self.assertRaisesRegex(IssuerConfigurationError, "^invalid_oidc_metadata$"):
            self.verifier({
                "issuer": ISSUER,
                "jwks_uri": "https://other.example.test/keys",
            })


if __name__ == "__main__":
    unittest.main()

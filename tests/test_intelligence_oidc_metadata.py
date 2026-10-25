"""Signed access-token checks with operator-pinned OIDC metadata; zero network."""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from devobs_intelligence.oidc_metadata import (
    trusted_oidc_verifier, IssuerConfigurationError
)
from devobs_intelligence.oidc_tokens import AuthenticationError


ISSUER="https://issuer.example.test"


class TrustedIssuerMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.other = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key()))
        cls.jwk.update(alg="RS256",use="sig",kid="key-one")

    def metadata(self):
        return {"issuer":ISSUER, "jwks_uri":ISSUER+"/.well-known/jwks.json"}

    def new_verifier(self, metadata=None, jwks=None):
        return trusted_oidc_verifier(ISSUER,"devobs-api","devobs-app",
                                     metadata if metadata is not None else self.metadata(),
                                     jwks if jwks is not None else {"keys":[self.jwk]})

    def token(self, key=None):
        now=int(time.time())
        return jwt.encode({"iss":ISSUER,"aud":"devobs-api","sub":"alice",
                           "client_id":"devobs-app","iat":now,"exp":now+120,
                           "jti":"synthetic","scope":"devobs.read"},
                           key or self.private,algorithm="RS256",
                           headers={"typ":"at+jwt","kid":"key-one"})

    def test_verified_metadata_builds_real_signed_verifier(self):
        self.assertEqual(self.new_verifier().verify(self.token()).subject,"alice")

    def test_invalid_issuer_and_untrusted_jwks_host_rejected(self):
        for metadata in [
            {"issuer":"https://evil.example.test","jwks_uri":ISSUER+"/keys"},
            {"issuer":ISSUER,"jwks_uri":"http://issuer.example.test/keys"},
            {"issuer":ISSUER,"jwks_uri":"https://evil.example.test/keys"},
            {"issuer":ISSUER,"jwks_uri":"https://issuer.example.test:444/keys"},
            {"issuer":ISSUER,"jwks_uri":"https://user@issuer.example.test/keys"},
            {"issuer":ISSUER,"jwks_uri":ISSUER+"/keys?token=PRIVATE"},
            {"issuer":ISSUER},
        ]:
            with self.subTest(metadata=metadata),self.assertRaisesRegex(
                    IssuerConfigurationError,"^invalid_oidc_metadata$"):
                self.new_verifier(metadata=metadata)

    def test_invalid_jwk_or_wrong_signed_key_not_accepted(self):
        with self.assertRaises(IssuerConfigurationError):
            self.new_verifier(jwks={"keys":[{"kid":"fake","kty":"oct","k":"secret"}]})
        with self.assertRaises(AuthenticationError):
            self.new_verifier().verify(self.token(key=self.other))

    def test_no_fallback_to_unsigned_claims(self):
        malformed=jwt.encode({"sub":"alice"},key="",algorithm="none",
                             headers={"typ":"at+jwt","kid":"key-one"})
        with self.assertRaises(AuthenticationError):
            self.new_verifier().verify(malformed)

    def test_strict_configuration_does_not_echo_private_fields(self):
        metadata=self.metadata()
        metadata["jwks_uri"]="https://other.example.test/PRIVATE-CODE"
        try:self.new_verifier(metadata=metadata)
        except IssuerConfigurationError as exc:
            self.assertEqual(str(exc),"invalid_oidc_metadata")
            self.assertNotIn("PRIVATE-CODE",str(exc))
        else:self.fail("untrusted provider accepted")


if __name__=="__main__":
    unittest.main()

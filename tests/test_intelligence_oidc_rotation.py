"""Offline, synthetic OIDC JWT rotation behavior and fail-closed tests."""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from devobs_intelligence.oidc_rotation import (
    RotatingOIDCVerifier, RotationRejected)
from devobs_intelligence.oidc_metadata import IssuerConfigurationError
from devobs_intelligence.oidc_tokens import AuthenticationError

ISSUER = "https://id.example.test"
CLIENT = "devobs-staging"
AUDIENCE = "devobs-api"


class TrustedKeyRotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.new = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @staticmethod
    def metadata(issuer=ISSUER):
        return {"issuer":issuer, "jwks_uri":issuer+"/keys"}

    @staticmethod
    def public_set(*pairs):
        keys=[]
        for name,private in pairs:
            jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
            jwk.update({"kid":name,"alg":"RS256","use":"sig"})
            keys.append(jwk)
        return {"keys":keys}

    @staticmethod
    def sign(private,kid):
        now=int(time.time())
        claims={"iss":ISSUER,"aud":AUDIENCE,"sub":"alice","client_id":CLIENT,
                "iat":now,"exp":now+120,"jti":"synthetic-only",
                "scope":"devobs.read"}
        return jwt.encode(claims,private,algorithm="RS256",
                          headers={"typ":"at+jwt","kid":kid})

    def verifier(self):
        return RotatingOIDCVerifier(
            ISSUER,AUDIENCE,CLIENT,self.metadata(),
            self.public_set(("old",self.old)))

    def test_rollover_accepts_new_and_revokes_removed_public_key(self):
        v=self.verifier()
        old=self.sign(self.old,"old")
        self.assertEqual(v.verify(old).subject,"alice")
        v.install_operator_verified(
            self.metadata(),self.public_set(("old",self.old),
                                           ("new",self.new)),revision=2)
        self.assertEqual(v.verify(old).subject,"alice")
        self.assertEqual(v.verify(self.sign(self.new,"new")).subject,"alice")
        v.install_operator_verified(
            self.metadata(),self.public_set(("new",self.new)),revision=3)
        self.assertEqual(v.revision,3)
        self.assertEqual(v.verify(self.sign(self.new,"new")).subject,"alice")
        with self.assertRaises(AuthenticationError):
            v.verify(old)

    def test_replayed_revision_fails_and_current_verifier_is_unchanged(self):
        v=self.verifier()
        for bad in (0,1,-1,True,"2",2**31):
            with self.subTest(revision=bad), self.assertRaises(RotationRejected):
                v.install_operator_verified(
                    self.metadata(),self.public_set(("new",self.new)),
                    revision=bad)
        self.assertEqual(v.revision,1)
        self.assertEqual(v.verify(self.sign(self.old,"old")).subject,"alice")

    def test_untrusted_provider_and_invalid_new_keys_do_not_break_existing(self):
        v=self.verifier()
        for meta,jwks in [
            (self.metadata("https://other.example.test"),
             self.public_set(("new",self.new))),
            (self.metadata(), {"keys":[{"kty":"oct","kid":"new"}]}),
            (self.metadata(), self.public_set(("dup",self.new),
                                             ("dup",self.impostor))),
            (self.metadata(), {"keys":[]})
        ]:
            with self.subTest(metadata=meta,keys=str(jwks)[:50]), self.assertRaises(
                    IssuerConfigurationError):
                v.install_operator_verified(meta,jwks,revision=2)
            self.assertEqual(v.revision,1)
            self.assertEqual(v.verify(self.sign(self.old,"old")).subject,"alice")

    def test_new_key_is_not_trusted_before_explicit_update(self):
        v=self.verifier()
        with self.assertRaises(AuthenticationError):
            v.verify(self.sign(self.new,"new"))
        with self.assertRaises(AuthenticationError):
            v.verify(self.sign(self.impostor,"old"))

    def test_revision_guard_is_not_a_network_fetch_or_new_auth_authority(self):
        v=self.verifier()
        self.assertFalse(hasattr(v,"fetch_jwks"))
        self.assertFalse(hasattr(v,"approve_deployment"))
        with self.assertRaises(RotationRejected):
            RotatingOIDCVerifier(
                ISSUER,AUDIENCE,CLIENT,self.metadata(),
                self.public_set(("old",self.old)),revision=False)


if __name__=="__main__": unittest.main()

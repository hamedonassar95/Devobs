"""Offline cryptographic access-token and tenant-bound API regression tests."""
import io
import json
import sys
import time
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from devobs_intelligence.oidc_tokens import AccessTokenVerifier,AuthenticationError
from devobs_intelligence.api_app import make_app
from devobs_intelligence.tenant_store import OfflineTenantStore,TenantDenied

ISS="https://login.example.test"


class AuthAndTenantAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key()))
        cls.jwk.update(kid="rsa-one",alg="RS256",use="sig")

    def setUp(self):
        self.verifier=AccessTokenVerifier(ISS,"devobs-api","devobs-cli",{"keys":[self.jwk]})
        self.store=OfflineTenantStore()
        self.addCleanup(self.store.close)
        self.store.add_project("alpha","shared","a"*40,"success")
        self.store.add_project("beta","shared","b"*40,"failed")
        self.store.add_project("alpha","other","c"*40,"failed")
        self.store.grant_read("alpha","shared","alice")
        self.store.grant_read("beta","shared","bob")
        self.app=make_app(self.verifier,self.store)

    def token(self,subject="alice",key=None,**overrides):
        now=int(time.time())
        claims={"iss":ISS,"aud":"devobs-api","sub":subject,"iat":now,"exp":now+300,
                "client_id":"devobs-cli","jti":"synthetic-01","scope":"devobs.read"}
        claims.update(overrides)
        return jwt.encode(claims,key or self.private,algorithm="RS256",
                          headers={"kid":"rsa-one","typ":"at+jwt"})

    def send(self,tenant="alpha",project="shared",token=None,method="GET",extra=None):
        env={};setup_testing_defaults(env)
        env["PATH_INFO"]=f"/v1/tenants/{tenant}/projects/{project}/ci"
        env["REQUEST_METHOD"]=method
        env["wsgi.input"]=io.BytesIO(b"")
        if token:env["HTTP_AUTHORIZATION"]="Bearer "+token
        if extra:env.update(extra)
        responses=[]
        body=b"".join(self.app(env,lambda status,headers:responses.append((status,dict(headers)))))
        return responses[0][0],responses[0][1],json.loads(body)

    def test_valid_signature_and_read_only_endpoint(self):
        principal=self.verifier.verify(self.token())
        self.assertEqual(principal.subject,"alice")
        status,headers,data=self.send(token=self.token())
        self.assertTrue(status.startswith("200"))
        self.assertEqual(data["source_sha"],"a"*40)
        self.assertEqual(headers["Cache-Control"],"no-store")

    def test_cross_tenant_isolation_and_ungranted_project(self):
        self.assertEqual(self.send(tenant="beta",token=self.token())[0][:3],"403")
        self.assertEqual(self.send(project="other",token=self.token())[0][:3],"403")
        self.assertEqual(self.send(tenant="alpha",token=self.token(subject="bob"))[0][:3],"403")
        self.assertEqual(self.send(tenant="beta",token=self.token(subject="bob"))[2]["source_sha"],"b"*40)

    def test_invalid_and_absent_authorization(self):
        for token in (None,"malformed.token","secret-not-echoed"):
            status,headers,body=self.send(token=token)
            self.assertEqual(status[:3],"401")
            self.assertEqual(body,{"error":"invalid_token"})
            self.assertNotIn("secret-not-echoed",str(body))

    def test_identity_token_and_unsigned_token_refused(self):
        identity=jwt.encode({"sub":"alice","iss":ISS,"aud":"devobs-api","exp":int(time.time())+60},
                            self.private,algorithm="RS256",headers={"typ":"JWT","kid":"rsa-one"})
        unsigned=jwt.encode({"sub":"alice","iss":ISS},key="",algorithm="none",
                            headers={"typ":"at+jwt","kid":"rsa-one"})
        for token in (identity,unsigned):
            with self.assertRaises(AuthenticationError):self.verifier.verify(token)

    def test_wrong_signature_audience_client_scope_and_expiry_rejected(self):
        cases=[self.token(key=self.other),self.token(aud="other"),
               self.token(client_id="another"),self.token(scope="profile"),
               self.token(exp=int(time.time())-1),self.token(exp=int(time.time())+86400),
               self.token(iat=int(time.time())+3600)]
        for token in cases:
            with self.subTest(case=token[:10]),self.assertRaises(AuthenticationError):
                self.verifier.verify(token)

    def test_method_and_untrusted_headers_cannot_escalate(self):
        self.assertEqual(self.send(token=self.token(),method="POST")[0][:3],"405")
        self.assertEqual(self.send(token=self.token(subject="bob"),
                              extra={"HTTP_X_ROLE":"owner"})[0][:3],"403")

    def test_untrusted_public_key_configuration_rejected(self):
        for bad in ({"keys":[self.jwk,self.jwk]},
                    {"keys":[{"kid":"rsa-one","kty":"oct","k":"none"}]}):
            with self.assertRaises(ValueError):
                AccessTokenVerifier(ISS,"devobs-api","devobs-cli",bad)
        with self.assertRaises(ValueError):
            AccessTokenVerifier("http://insecure.test","devobs-api","devobs-cli",{"keys":[self.jwk]})

    def test_missing_database_membership_denied(self):
        for tenant,project in (("alpha","other"),("beta","shared"),("unknown","shared")):
            with self.assertRaises(TenantDenied):
                self.store.read_status("alice",tenant,project)

    def test_duplicate_project_and_invalid_tenant_denied(self):
        with self.assertRaises(__import__("sqlite3").IntegrityError):
            self.store.add_project("alpha","shared","a"*40,"success")
        with self.assertRaises(TenantDenied):
            self.store.read_status("alice","invalid tenant!","shared")


if __name__=="__main__": unittest.main()

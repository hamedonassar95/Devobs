"""Behavioral OpenAPI 3.1 contract: local WSGI only, no real credentials/network."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.api_app import _STATES, make_app  # noqa: E402
from devobs_intelligence.oidc_tokens import AuthenticatedPrincipal, AuthenticationError  # noqa: E402

API = "/v1/tenants/{tenant}/projects/{project}/ci"
SERVICE = "/v1/tenants/{tenant}/projects/{project}/services/{service}/authorization"
FILE = ROOT / "docs/openapi/devobs-staging-readonly.json"


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate contract key")
        out[key] = value
    return out


def _send(app, path, token=None, method="GET"):
    environ = {"PATH_INFO": path, "REQUEST_METHOD": method}
    if token is not None:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    collected = []
    body = b"".join(app(environ, lambda status, headers: collected.append((status, dict(headers)))))
    status, headers = collected[0]
    return status[:3], headers, body


class _Verifier:
    def verify(self, token):
        if token != "synthetic-access":
            raise AuthenticationError("invalid_token")
        return AuthenticatedPrincipal("alice", frozenset({"devobs.read"}))


class _Store:
    fail = False

    def read_status(self, subject, tenant, project):
        if self.fail:
            raise RuntimeError("private-database-failure")
        if (subject, tenant, project) != ("alice", "alpha", "shared"):
            raise ValueError("denied")
        return {"ci_state": "success", "source_sha": "a" * 40}

    def authorize_service(self, subject, tenant, project, service):
        return (subject, tenant, project, service) == ("alice", "alpha", "shared", "collector")


class StagingOpenAPIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(FILE.read_text(encoding="utf-8"), object_pairs_hook=_unique)

    def test_exact_readonly_paths_security_and_operation_responses(self):
        spec = self.document
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertNotIn("servers", spec)  # No invented live staging hostname.
        self.assertEqual(set(spec["paths"]), {"/healthz", "/readyz", API, SERVICE})
        expected = {
            "/healthz": {"204", "405"},
            "/readyz": {"204", "405", "503"},
            API: {"200", "401", "403", "405", "429", "503"},
            SERVICE: {"204", "401", "403", "405", "429", "503"},
        }
        for path, item in spec["paths"].items():
            with self.subTest(path=path):
                self.assertEqual(set(item), {"get"})
                get = item["get"]
                self.assertNotIn("requestBody", get)
                self.assertEqual(set(get["responses"]), expected[path])
                self.assertEqual(get["security"], [{"BearerJWT": []}] if path in (API, SERVICE) else [])
                params = set(re.findall(r"\{([a-z]+)\}", path))
                self.assertEqual({p["name"] for p in get.get("parameters", [])}, params)
                self.assertTrue(all(p["required"] and p["in"] == "path"
                                    for p in get.get("parameters", [])))
        self.assertEqual(spec["components"]["securitySchemes"]["BearerJWT"]["type"], "http")
        self.assertEqual(spec["components"]["securitySchemes"]["BearerJWT"]["scheme"], "bearer")

    def test_schema_matches_actual_api_states_and_rejects_extra_fields(self):
        schema = self.document["components"]["schemas"]["CiState"]
        self.assertEqual(set(schema["required"]), {"ci_state", "source_sha"})
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(set(schema["properties"]["ci_state"]["enum"]), _STATES)
        pattern = schema["properties"]["source_sha"]["pattern"]
        self.assertTrue(re.fullmatch(pattern, "a" * 40))
        self.assertTrue(re.fullmatch(pattern, "a" * 64))
        self.assertIsNone(re.fullmatch(pattern, "wrong"))
        error = self.document["components"]["schemas"]["ApiError"]
        self.assertIs(error["additionalProperties"], False)
        self.assertEqual(error["required"], ["error"])

    def assert_documented(self, path, result, *, empty=False):
        status, headers, body = result
        self.assertIn(status, self.document["paths"][path]["get"]["responses"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(int(headers["Content-Length"]), len(body))
        if empty:
            self.assertEqual(body, b"")
        else:
            self.assertLessEqual(len(body), 2048)
            self.assertTrue(headers["Content-Type"].startswith("application/json"))
            data = json.loads(body)
            if status == "200":
                schema = self.document["components"]["schemas"]["CiState"]
                self.assertEqual(set(data), set(schema["required"]))
                self.assertIn(data["ci_state"], schema["properties"]["ci_state"]["enum"])
                self.assertRegex(data["source_sha"], schema["properties"]["source_sha"]["pattern"])
            else:
                self.assertEqual(set(data), {"error"})
                self.assertIn(data["error"], self.document["components"]["schemas"]["ApiError"]["properties"]["error"]["enum"])
        return result

    def test_authenticated_read_anonymous_deny_and_cross_tenant_deny(self):
        app = make_app(_Verifier(), _Store())
        path = "/v1/tenants/alpha/projects/shared/ci"
        self.assert_documented(API, _send(app, path, "synthetic-access"))
        self.assertEqual(self.assert_documented(API, _send(app, path))[0], "401")
        self.assertEqual(self.assert_documented(API, _send(app, path, "wrong"))[0], "401")
        self.assertEqual(self.assert_documented(API, _send(app, path.replace("alpha", "beta"), "synthetic-access"))[0], "403")

    def test_service_authorization_is_readonly_and_denies_unknown_service(self):
        app = make_app(_Verifier(), _Store())
        path = "/v1/tenants/alpha/projects/shared/services/collector/authorization"
        self.assertEqual(self.assert_documented(SERVICE, _send(app, path, "synthetic-access"), empty=True)[0], "204")
        self.assertEqual(self.assert_documented(SERVICE, _send(app, path.replace("collector", "unknown"), "synthetic-access"))[0], "403")
        self.assertEqual(self.assert_documented(SERVICE, _send(app, path, "synthetic-access", "POST"))[0], "405")

    def test_rate_limit_and_unavailable_backend_are_documented(self):
        path = "/v1/tenants/alpha/projects/shared/ci"
        app = make_app(_Verifier(), _Store(), requests_per_window=1, clock=lambda: 100)
        self.assertEqual(self.assert_documented(API, _send(app, path, "synthetic-access"))[0], "200")
        limited = self.assert_documented(API, _send(app, path, "synthetic-access"))
        self.assertEqual(limited[0], "429")
        self.assertEqual(limited[1]["Retry-After"], "60")
        store = _Store()
        store.fail = True
        failed = self.assert_documented(API, _send(make_app(_Verifier(), store), path, "synthetic-access"))
        self.assertEqual(failed[0], "503")
        self.assertNotIn(b"private-database-failure", failed[2])

    def test_unsupported_route_and_methods_never_succeed(self):
        app = make_app(_Verifier(), _Store())
        path = "/v1/tenants/alpha/projects/shared/ci"
        self.assertEqual(self.assert_documented(API, _send(app, path, "synthetic-access", "POST"))[0], "405")
        self.assertEqual(_send(app, "/v1/tenants/alpha/projects/shared/private", "synthetic-access")[0], "404")
        self.assertEqual(_send(app, path, "synthetic-access", "DELETE")[0], "405")

    def test_duplicate_contract_keys_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate contract key"):
            json.loads('{"openapi":"3.1.0","openapi":"0.0.0"}', object_pairs_hook=_unique)


if __name__ == "__main__":
    unittest.main()

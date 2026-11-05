"""Offline behavioral tests for the opt-in error-log diagnosis route."""
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.api_app import make_app  # noqa: E402
from devobs_intelligence.oidc_tokens import AuthenticatedPrincipal, AuthenticationError  # noqa: E402
from devobs_intelligence.openai_error_diagnosis import (  # noqa: E402
    DEFAULT_MODEL,
)

PATH = "/v1/tenants/alpha/projects/mobile/services/api/diagnostics"
LOG = "HTTP 503 from /v1/orders; database pool reached its 20 connection limit"
RESULT = {
    "diagnosis": "The application could not acquire a database connection from its pool.",
    "recommendation": "Check database saturation and recent connection leaks before changing the pool limit.",
    "severity": "medium",
    "confidence": "high",
}


class Verifier:
    scopes = frozenset({"devobs.read", "devobs.ai.diagnose"})

    def verify(self, token):
        if token != "synthetic-access":
            raise AuthenticationError("invalid_token")
        return AuthenticatedPrincipal("alice", self.scopes)


class Store:
    allowed = True

    def authorize_service(self, subject, tenant, project, service):
        return self.allowed and (subject, tenant, project, service) == (
            "alice", "alpha", "mobile", "api")


class FakeDiagnostician:
    model = DEFAULT_MODEL

    def __init__(self):
        self.calls = []

    def diagnose(self, error_log):
        self.calls.append(error_log)
        return dict(RESULT)


class PerTokenVerifier:
    scopes = frozenset({"devobs.read", "devobs.ai.diagnose"})

    def verify(self, token):
        if token not in {"synthetic-access-a", "synthetic-access-b"}:
            raise AuthenticationError("invalid_token")
        return AuthenticatedPrincipal(token, self.scopes)


def send(app, *, token="synthetic-access", body=None, method="POST", headers=None,
         environ_overrides=None):
    raw = b"" if body is None else body if isinstance(body, bytes) else json.dumps(body).encode()
    environ = {
        "PATH_INFO": PATH,
        "REQUEST_METHOD": method,
        "HTTP_AUTHORIZATION": "Bearer " + token if token else "",
        "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(raw)) if raw else "",
        "wsgi.input": io.BytesIO(raw),
    }
    if headers:
        environ.update(headers)
    if environ_overrides:
        environ.update(environ_overrides)
    captured = []
    response = b"".join(app(environ, lambda status, values:
                           captured.append((status, dict(values)))))
    return captured[0][0], captured[0][1], response


class ErrorLogDiagnosisApiTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeDiagnostician()
        self.store = Store()
        self.app = make_app(Verifier(), self.store, diagnostician=self.provider, clock=lambda: 100)

    def test_authenticated_authorized_request_returns_advisory_model_result(self):
        status, headers, body = send(
            self.app, body={"error_log": LOG, "data_redacted": True})
        result = json.loads(body)
        self.assertTrue(status.startswith("200"))
        self.assertEqual(result, {**RESULT, "model": DEFAULT_MODEL, "latency_ms": 0})
        self.assertEqual(self.provider.calls, [LOG])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn(LOG.encode(), body)

    def test_requires_auth_diagnosis_scope_and_registered_service(self):
        denied = send(self.app, token="bad", body={"error_log": LOG, "data_redacted": True})
        self.assertTrue(denied[0].startswith("401"))
        self.assertEqual(json.loads(denied[2]), {"error": "invalid_token"})
        Verifier.scopes = frozenset({"devobs.read"})
        try:
            scope_denied = send(self.app, body={"error_log": LOG, "data_redacted": True})
            self.assertTrue(scope_denied[0].startswith("403"))
            self.assertEqual(json.loads(scope_denied[2]), {"error": "access_denied"})
        finally:
            Verifier.scopes = frozenset({"devobs.read", "devobs.ai.diagnose"})
        self.store.allowed = False
        service_denied = send(self.app, body={"error_log": LOG, "data_redacted": True})
        self.assertTrue(service_denied[0].startswith("403"))
        self.assertEqual(self.provider.calls, [])

    def test_rejects_unredacted_missing_duplicate_and_oversized_inputs_without_call(self):
        missing_consent = send(self.app, body={"error_log": LOG, "data_redacted": False})
        self.assertEqual(missing_consent[0][:3], "400")
        self.assertEqual(json.loads(missing_consent[2]), {"error": "redacted_log_required"})
        sensitive = send(self.app, body={
            "error_log": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
            "data_redacted": True,
        })
        self.assertEqual(json.loads(sensitive[2]), {"error": "sensitive_data_detected"})
        duplicate = send(self.app, body=b'{"error_log":"x","error_log":"y","data_redacted":true}')
        self.assertEqual(json.loads(duplicate[2]), {"error": "invalid_request"})
        oversized = send(self.app, body=b"x" * (32_769),
                         headers={"CONTENT_LENGTH": "32769"})
        self.assertEqual(oversized[0][:3], "413")
        self.assertEqual(self.provider.calls, [])

    def test_disabled_provider_and_method_mismatch_fail_closed(self):
        disabled = make_app(Verifier(), self.store, clock=lambda: 100)
        response = send(disabled, body={"error_log": LOG, "data_redacted": True})
        self.assertEqual(response[0][:3], "503")
        self.assertEqual(json.loads(response[2]), {"error": "ai_not_configured"})
        get = send(self.app, method="GET")
        self.assertEqual(get[0][:3], "405")
        self.assertEqual(get[1]["Allow"], "POST")
        self.assertEqual(self.provider.calls, [])

    def test_narrow_per_principal_limit_applies_to_model_route(self):
        app = make_app(Verifier(), self.store, diagnostician=self.provider,
                       diagnostic_requests_per_window=1, clock=lambda: 100)
        body = {"error_log": LOG, "data_redacted": True}
        self.assertEqual(send(app, body=body)[0][:3], "200")
        limited = send(app, body=body)
        self.assertEqual(limited[0][:3], "429")
        self.assertEqual(json.loads(limited[2]), {"error": "rate_limited"})
        self.assertEqual(len(self.provider.calls), 1)

    def test_total_model_limit_applies_across_principals(self):
        class MultiPrincipalStore:
            def authorize_service(self, subject, tenant, project, service):
                return subject in {"synthetic-access-a", "synthetic-access-b"} and (
                    tenant, project, service
                ) == ("alpha", "mobile", "api")

        app = make_app(PerTokenVerifier(), MultiPrincipalStore(), diagnostician=self.provider,
                       diagnostic_requests_per_window=5,
                       diagnostic_total_requests_per_window=1, clock=lambda: 100)
        body = {"error_log": LOG, "data_redacted": True}
        first = send(app, token="synthetic-access-a", body=body)
        second = send(app, token="synthetic-access-b", body=body)
        self.assertEqual(first[0][:3], "200")
        self.assertEqual(second[0][:3], "429")
        self.assertEqual(json.loads(second[2]), {"error": "rate_limited"})
        self.assertEqual(len(self.provider.calls), 1)

    def test_openapi_contract_matches_the_route_and_response(self):
        spec_path = ROOT / "docs/openapi/devobs-staging-diagnostics.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        path = "/v1/tenants/{tenant}/projects/{project}/services/{service}/diagnostics"
        operation = spec["paths"][path]["post"]
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertEqual(operation["operationId"], "diagnoseServiceErrorLog")
        self.assertIn("200", operation["responses"])
        schema = spec["components"]["schemas"]["Diagnosis"]
        self.assertEqual(set(schema["required"]), {
            "diagnosis", "recommendation", "severity", "confidence", "model", "latency_ms"
        })
        self.assertIs(schema["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main()

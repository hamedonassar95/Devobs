"""Offline tests for the opt-in local Ollama/LocalAI diagnostics adapter."""
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.local_model_error_diagnosis import (  # noqa: E402
    ENDPOINTS,
    LocalModelErrorLogDiagnostician,
    _NoRedirect,
)
from devobs_intelligence.openai_error_diagnosis import (  # noqa: E402
    DiagnosticInputError,
    DiagnosticProviderError,
)

LOG = "HTTP 503 from /v1/orders; database pool reached its 20 connection limit"
RESULT = {
    "diagnosis": "The service could not acquire a database connection.",
    "recommendation": "Check pool saturation and recent errors before changing limits.",
    "severity": "medium",
    "confidence": "high",
}


def response_document(result=RESULT):
    return {"choices": [{
        "finish_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(result)},
    }]}


class LocalModelErrorLogDiagnosticianTests(unittest.TestCase):
    def test_rejects_unknown_backend_bad_model_and_invalid_key(self):
        for backend, model, key in (
            ("remote", "model", ""),
            ("ollama", "../model", ""),
            ("ollama", "model", "unexpected-key"),
            ("localai", "model", "bad\nkey"),
        ):
            with self.subTest(backend=backend, model=model), self.assertRaises(ValueError):
                LocalModelErrorLogDiagnostician(backend, model=model, api_key=key)

    def test_sends_one_bounded_request_to_a_fixed_loopback_endpoint(self):
        for backend, model, key in (
            ("ollama", "llama3.2:3b", ""),
            ("localai", "local-model", "synthetic-localai-key"),
        ):
            response, opener = self._client_with_body(backend, model, key, response_document())
            self.assertEqual(response.diagnose(LOG), RESULT)
            request, kwargs = opener.open.call_args[0][0], opener.open.call_args.kwargs
            payload = json.loads(request.data)
            self.assertEqual(request.full_url, ENDPOINTS[backend])
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(kwargs["timeout"], 20)
            self.assertEqual(payload["model"], model)
            self.assertEqual(payload["messages"][1]["content"], LOG)
            self.assertIn("untrusted", payload["messages"][0]["content"])
            self.assertEqual(payload["max_tokens"], 512)
            self.assertIs(payload["stream"], False)
            self.assertNotIn("tools", payload)
            if backend == "ollama":
                self.assertIsNone(request.get_header("Authorization"))
            else:
                self.assertEqual(request.get_header("Authorization"),
                                 "Bearer synthetic-localai-key")

    def test_rejects_credentials_in_input_and_malformed_model_output(self):
        client, opener = self._client_with_body("ollama", "test-model", "", response_document())
        with self.assertRaises(DiagnosticInputError):
            client.diagnose("api_key=sk-proj-abcdefghijklmnopqrstuvwxyz123456")
        opener.open.assert_not_called()

        for document in (
            {"choices": [{"finish_reason": "length", "message": {
                "role": "assistant", "content": json.dumps(RESULT)}}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps(RESULT), "tool_calls": []}}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": '{"diagnosis":"a","diagnosis":"b"}'}}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": "not json"}}]},
        ):
            client, _ = self._client_with_body("ollama", "test-model", "", document)
            with self.subTest(document=document), self.assertRaises(DiagnosticProviderError):
                client.diagnose(LOG)

    def test_oversized_and_failed_responses_are_sanitized(self):
        client, _ = self._client_with_raw_body("localai", "local-model", "secret-key",
                                               b"x" * 32769)
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_invalid_response"):
            client.diagnose(LOG)

        opener = Mock()
        opener.open.side_effect = HTTPError(
            ENDPOINTS["localai"], 403, "private message", None,
            io.BytesIO(b"private response"))
        client = LocalModelErrorLogDiagnostician(
            "localai", model="local-model", api_key="synthetic-key", opener=opener)
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_request_failed") as caught:
            client.diagnose(LOG)
        self.assertNotIn("synthetic-key", str(caught.exception))
        self.assertNotIn(LOG, str(caught.exception))

    def test_default_opener_ignores_environment_proxies_and_rejects_redirects(self):
        with unittest.mock.patch.dict(os.environ, {
            "HTTP_PROXY": "http://proxy.example.test:3128",
            "HTTPS_PROXY": "http://proxy.example.test:3128",
        }):
            client = LocalModelErrorLogDiagnostician("ollama", model="test-model")
        proxies = [handler for handler in client._opener.handlers
                   if isinstance(handler, ProxyHandler)]
        self.assertTrue(all(not handler.proxies for handler in proxies))
        request = Request(ENDPOINTS["ollama"])
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_redirect_rejected"):
            _NoRedirect().redirect_request(
                request, None, 302, "redirect", {}, "https://attacker.example/collect")

    @staticmethod
    def _client_with_body(backend, model, key, document):
        return LocalModelErrorLogDiagnosticianTests._client_with_raw_body(
            backend, model, key, json.dumps(document).encode())

    @staticmethod
    def _client_with_raw_body(backend, model, key, body):
        response = Mock()
        response.status = 200
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        client = LocalModelErrorLogDiagnostician(
            backend, model=model, api_key=key, opener=opener)
        return client, opener


if __name__ == "__main__":
    unittest.main()

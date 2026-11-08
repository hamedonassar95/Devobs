"""Offline contract tests for the optional Gemini generateContent adapter."""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.gemini_error_diagnosis import (  # noqa: E402
    ENDPOINT_PREFIX,
    GeminiErrorLogDiagnostician,
)
from devobs_intelligence.openai_error_diagnosis import (  # noqa: E402
    DiagnosticInputError,
    DiagnosticProviderError,
    validate_error_log,
)

LOG = "HTTP 503 from /v1/orders; database pool reached its 20 connection limit"
RESULT = {
    "diagnosis": "The service could not acquire a database connection.",
    "recommendation": "Check connection saturation and recent pool errors before changing limits.",
    "severity": "medium",
    "confidence": "high",
}


def response_document(result=RESULT):
    return {
        "candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": json.dumps(result)}]},
        }],
    }


class GeminiErrorLogDiagnosticianTests(unittest.TestCase):
    def test_rejects_invalid_credentials_models_and_google_keys_in_logs(self):
        for api_key, model in (("", "gemini-test"), ("bad\nkey", "gemini-test"),
                               ("synthetic-key", "../model"), ("synthetic-key", "")):
            with self.subTest(api_key=api_key[:10], model=model), self.assertRaises(ValueError):
                GeminiErrorLogDiagnostician(api_key, model=model)
        with self.assertRaisesRegex(DiagnosticInputError, "sensitive_data_detected"):
            validate_error_log("google_api_key=AIza" + "A" * 35)

    def test_sends_one_bounded_request_to_fixed_host_with_key_in_header(self):
        response = Mock()
        response.status = 200
        response.read.return_value = json.dumps(response_document()).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response

        client = GeminiErrorLogDiagnostician(
            "synthetic-gemini-key", model="gemini-test-flash", opener=opener)
        self.assertEqual(client.diagnose(LOG), RESULT)
        args, kwargs = opener.open.call_args
        request = args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url,
                         ENDPOINT_PREFIX + "gemini-test-flash:generateContent")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-goog-api-key"), "synthetic-gemini-key")
        self.assertNotIn("synthetic-gemini-key", request.full_url)
        self.assertEqual(kwargs["timeout"], 20)
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], LOG)
        self.assertIn("untrusted", payload["systemInstruction"]["parts"][0]["text"])
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 512)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertNotIn("tools", payload)

    def test_ignores_model_thought_part_and_rejects_invalid_or_duplicate_json(self):
        document = response_document()
        document["candidates"][0]["content"]["parts"].insert(
            0, {"thought": True, "text": "internal thought must not escape"})
        client, opener = self._client_with_body(json.dumps(document).encode())
        self.assertEqual(client.diagnose(LOG), RESULT)
        self.assertEqual(opener.open.call_count, 1)

        duplicate = response_document({
            "diagnosis": "ok", "diagnosis_duplicate": "unexpected",
            "recommendation": "check safely", "severity": "low", "confidence": "low",
        })
        duplicate_text = '{"diagnosis":"ok","diagnosis":"bad"}'
        duplicate["candidates"][0]["content"]["parts"][0]["text"] = duplicate_text
        client, _ = self._client_with_body(json.dumps(duplicate).encode())
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_invalid_response"):
            client.diagnose(LOG)

    def test_incomplete_refused_oversized_and_network_errors_fail_closed(self):
        for document, error in (
            ({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]},
             "provider_incomplete_response"),
            ({"promptFeedback": {"blockReason": "SAFETY"}}, "provider_refusal"),
            ({"candidates": [{"finishReason": "STOP", "content": {"parts": [
                {"text": json.dumps(RESULT)}, {"text": json.dumps(RESULT)},
            ]}}]}, "provider_invalid_response"),
            ({"candidates": [{"finishReason": "STOP", "content": {"parts": [{
                "text": json.dumps({**RESULT, "severity": []}),
            }]}}]}, "provider_invalid_response"),
        ):
            client, _ = self._client_with_body(json.dumps(document).encode())
            with self.subTest(error=error), self.assertRaisesRegex(DiagnosticProviderError, error):
                client.diagnose(LOG)

        client, _ = self._client_with_body(b"x" * 32769)
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_invalid_response"):
            client.diagnose(LOG)

        opener = Mock()
        opener.open.side_effect = HTTPError(
            ENDPOINT_PREFIX + "gemini-test:generateContent", 403,
            "synthetic key must not leak", None, io.BytesIO(b"private provider response"))
        client = GeminiErrorLogDiagnostician(
            "synthetic-gemini-key", model="gemini-test", opener=opener)
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_request_failed") as caught:
            client.diagnose(LOG)
        self.assertNotIn("synthetic-gemini-key", str(caught.exception))
        self.assertNotIn(LOG, str(caught.exception))

    def test_redirects_are_rejected_before_following_an_external_location(self):
        from devobs_intelligence.gemini_error_diagnosis import _NoRedirect

        request = Request(ENDPOINT_PREFIX + "gemini-test:generateContent")
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_redirect_rejected"):
            _NoRedirect().redirect_request(
                request, None, 302, "redirect", {}, "https://attacker.example/collect")

    @staticmethod
    def _client_with_body(body):
        response = Mock()
        response.status = 200
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        client = GeminiErrorLogDiagnostician(
            "synthetic-gemini-key", model="gemini-test", opener=opener)
        return client, opener


if __name__ == "__main__":
    unittest.main()

"""Offline contract tests for the OpenAI Responses API diagnostic adapter."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.openai_error_diagnosis import (  # noqa: E402
    DEFAULT_MODEL,
    ENDPOINT,
    DiagnosticInputError,
    DiagnosticProviderError,
    OpenAIErrorLogDiagnostician,
    validate_error_log,
)

LOG = "HTTP 503 from /v1/orders; database pool reached its 20 connection limit"
RESULT = {
    "diagnosis": "The application could not acquire a database connection from its pool.",
    "recommendation": "Check database saturation and recent connection leaks before changing the pool limit.",
    "severity": "medium",
    "confidence": "high",
}


class OpenAIErrorLogDiagnosticianTests(unittest.TestCase):
    def test_validates_redacted_input_and_rejects_credential_like_values(self):
        self.assertEqual(validate_error_log(LOG), LOG)
        self.assertEqual(
            validate_error_log("api_key=<redacted>"),
            "api_key=<redacted>",
        )
        for value in (
            "",
            "x" * 8193,
            "api_key=sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "-----BEGIN PRIVATE KEY-----",
        ):
            with self.subTest(value=value[:20]), self.assertRaises(DiagnosticInputError):
                validate_error_log(value)

    def test_sends_one_bounded_non_stored_structured_responses_request(self):
        response = Mock()
        response.status = 200
        response.read.return_value = json.dumps({
            "status": "completed",
            "output": [{"type": "message", "content": [{
                "type": "output_text", "text": json.dumps(RESULT),
            }]}],
        }).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        client = OpenAIErrorLogDiagnostician("synthetic-key", opener=opener)
        self.assertEqual(client.diagnose(LOG), RESULT)
        args, kwargs = opener.open.call_args
        request = args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-key")
        self.assertEqual(kwargs["timeout"], 20)
        self.assertEqual(payload["model"], DEFAULT_MODEL)
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["max_output_tokens"], 512)
        self.assertEqual(payload["input"], LOG)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertIs(payload["text"]["format"]["strict"], True)
        self.assertNotIn("tools", payload)

    def test_provider_failures_are_sanitized_and_invalid_output_is_rejected(self):
        response = Mock()
        response.status = 200
        response.read.return_value = b'{"status":"incomplete","output":[]}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        client = OpenAIErrorLogDiagnostician("synthetic-key", opener=opener)
        with self.assertRaisesRegex(DiagnosticProviderError, "provider_incomplete_response"):
            client.diagnose(LOG)
        self.assertNotIn(LOG, str(DiagnosticProviderError("provider_request_failed")))


if __name__ == "__main__":
    unittest.main()

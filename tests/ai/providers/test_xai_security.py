"""Security-boundary tests for the xAI adapter (no network, no real credentials)."""
import dataclasses
import unittest
from decimal import Decimal
from unittest.mock import Mock

from devobs.ai.providers import XaiAdapter, XaiAuthorization, XaiRequest, XaiState, load_xai_config
from devobs.ai.providers import xai_mock
from devobs.ai.providers.xai_adapter import _safe_log, redact_text
from devobs.ai.providers.xai_config import XaiConfigurationError

FAKE_KEY = "xai-secret-value-0123456789abcdef"


class XaiSecurityTests(unittest.TestCase):
    def test_environment_key_is_never_stored_in_configuration(self):
        config = load_xai_config({
            "XAI_API_KEY": FAKE_KEY,
            "XAI_ENABLED": "true",
            "DEVOBS_AI_BUDGET_APPROVED": "true",
        })
        self.assertTrue(config.api_key_present)
        self.assertFalse(hasattr(config, "api_key"))
        self.assertNotIn(FAKE_KEY, repr(config))
        self.assertNotIn(FAKE_KEY, str(config.redacted_dict()))
        self.assertNotIn("xai_api_key", config.redacted_dict())

    def test_mock_is_offline_deterministic_and_not_verified(self):
        provider = xai_mock.DeterministicXaiMock(
            load_xai_config({"XAI_ENABLED": "true"}))
        result = provider.complete(XaiRequest("safe prompt", request_id="rid"))
        self.assertEqual(result.state, XaiState.MOCK_SUCCESS)
        self.assertNotEqual(result.state, XaiState.VERIFIED_RESPONSE)
        self.assertTrue(result.is_mock)
        self.assertEqual(result.source, "xai_offline_mock")
        self.assertEqual(result.cost_usd, Decimal("0"))
        self.assertFalse(hasattr(xai_mock, "build_opener"))
        self.assertFalse(hasattr(xai_mock, "subprocess"))
        self.assertFalse(hasattr(xai_mock, "socket"))

    def test_input_redaction_covers_credential_shapes(self):
        text = (
            "key=" + FAKE_KEY
            + " bearer abcdefghijklmnopqrstuvwxyz0123456789 "
            + "token=ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        )
        safe, count = redact_text(text)
        self.assertGreaterEqual(count, 3)
        self.assertNotIn(FAKE_KEY, safe)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz0123456789", safe)
        self.assertIn("[REDACTED]", safe)

    def test_structured_logs_use_allowlisted_fields_only(self):
        entry = _safe_log(
            "test",
            prompt="secret prompt",
            text="secret response",
            api_key=FAKE_KEY,
            authorization="Bearer secret",
            state=XaiState.BUDGET_BLOCKED,
            reason="authorization_required",
            model="grok-4.7",
        )
        self.assertEqual(set(entry), {
            "event", "state", "reason", "model",
        })
        self.assertNotIn(FAKE_KEY, str(entry))

    def test_request_and_result_have_no_execution_surface(self):
        request_fields = {field.name for field in dataclasses.fields(XaiRequest)}
        self.assertEqual(request_fields, {"prompt", "request_id", "system"})
        result = xai_mock.DeterministicXaiMock(
            load_xai_config({"XAI_ENABLED": "true"})).complete(XaiRequest("safe"))
        self.assertFalse(any(callable(value) for value in dataclasses.asdict(result).values()))

    def test_invalid_configuration_fails_closed(self):
        cases = (
            {"XAI_ENABLED": "yes"},
            {"XAI_MODEL": "grok-unknown"},
            {"XAI_MAX_REQUESTS_PER_RUN": "100000"},
            {"XAI_MAX_OUTPUT_TOKENS": "0"},
            {"XAI_TIMEOUT_SECONDS": "0"},
            {"XAI_REASONING_EFFORT": "unlimited"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(XaiConfigurationError):
                load_xai_config(overrides)

    def test_paid_call_requires_explicit_authorization(self):
        config = load_xai_config({
            "XAI_ENABLED": "true",
            "XAI_DRY_RUN": "false",
            "XAI_MAX_REQUESTS_PER_RUN": "1",
            "XAI_MAX_COST_USD": "1.00",
            "DEVOBS_AI_BUDGET_APPROVED": "true",
        })
        opener = Mock()
        adapter = XaiAdapter(config, api_key=FAKE_KEY, opener=opener)
        result = adapter.complete(XaiRequest("safe prompt"))
        self.assertEqual(result.state, XaiState.BUDGET_BLOCKED)
        self.assertEqual(result.reason, "authorization_required")
        opener.open.assert_not_called()
        with self.assertRaises(ValueError):
            XaiAuthorization(approved=False, approver="owner", max_cost_usd=Decimal("1"))


if __name__ == "__main__":
    unittest.main()

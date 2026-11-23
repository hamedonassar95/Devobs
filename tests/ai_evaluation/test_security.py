"""Fail-closed security and configuration contract tests (offline only)."""

from __future__ import annotations

import unittest
from decimal import Decimal

from devobs.ai_evaluation.engine import EvaluationInputError, build_default_configs
from devobs.ai_evaluation.models import (
    EvaluationError,
    InvocationOutcome,
    LiveModeAuthorization,
    ProviderConfig,
    redact_sensitive,
)
from devobs.ai_evaluation.mocks import OfflineProviderMock

CONFIG_SENTINEL = "SYNTHETIC_NEVER_STORE_ME"


def _synthetic_token(letter: str) -> str:
    """Build a scanner-recognisable test token at runtime, never as a literal.

    The fragments are not a credential. The assembled value still exercises the
    production redaction patterns without committing a secret-looking literal.
    """
    return "xai-" + letter * 24


class SecurityContractTests(unittest.TestCase):
    def test_provider_config_forbids_endpoint_overrides(self) -> None:
        for key in ("endpoint", "base_url", "api_url", "url", "proxy", "ca_bundle"):
            with self.subTest(key=key):
                with self.assertRaises(EvaluationError):
                    ProviderConfig.from_mapping({
                        "name": "fixture-primary",
                        "model": "grok-4.7",
                        "capabilities": ["advisory_only"],
                        key: "https://attacker.invalid",
                    })

    def test_provider_config_rejects_credentials_instead_of_storing_them(self) -> None:
        with self.assertRaises(EvaluationError):
            ProviderConfig.from_mapping({
                "name": "fixture-primary",
                "model": "grok-4.7",
                "capabilities": ["advisory_only"],
                "api_key": CONFIG_SENTINEL,
            })
        config = ProviderConfig.from_mapping({
            "name": "fixture-primary",
            "model": "grok-4.7",
            "capabilities": ["advisory_only"],
        })
        rendered = config.redacted_dict()
        self.assertNotIn("api_key", rendered)
        self.assertNotIn(CONFIG_SENTINEL, str(rendered))

    def test_live_mode_is_impossible_without_explicit_authorization(self) -> None:
        config = build_default_configs()[0]
        self.assertTrue(config.offline)
        from devobs.ai_evaluation.models import assert_live_mode_allowed

        with self.assertRaises(EvaluationError):
            assert_live_mode_allowed(config, None)
        with self.assertRaises(EvaluationError):
            assert_live_mode_allowed(config, LiveModeAuthorization(
                approved=True,
                approver="owner",
                spending_ceiling_usd=Decimal("1.00"),
                scope="fixture",
            ))

    def test_redaction_is_deterministic_and_idempotent(self) -> None:
        token = _synthetic_token("C")
        sample = "key=" + token + " owner=someone@example.invalid"
        once, count = redact_sensitive(sample)
        twice, second = redact_sensitive(once)
        self.assertEqual(once, twice)
        self.assertGreater(count, 0)
        self.assertEqual(second, 0)
        self.assertNotIn(token, once)
        self.assertNotIn(token, twice)

    def test_mock_can_only_produce_mock_outcomes(self) -> None:
        mock = OfflineProviderMock(seed=7)
        self.assertTrue(mock.is_offline)
        for scenario in (
            "success", "timeout", "rate_limit_then_success", "malformed_json",
            "missing_credentials", "invalid_model", "cost_ceiling", "redirect",
            "unsafe_action", "outage",
        ):
            with self.subTest(scenario=scenario):
                response = mock.invoke(
                    provider_id="fixture-primary",
                    model_id="grok-4.7",
                    scenario=scenario,
                    prompt="Summarize the incident.",
                    max_output_tokens=64,
                )
                self.assertTrue(response.is_mock)
                self.assertNotEqual(
                    response.outcome, InvocationOutcome.VERIFIED_RESPONSE
                    if hasattr(InvocationOutcome, "VERIFIED_RESPONSE")
                    else "__never__",
                )

    def test_engine_never_imports_network_modules(self) -> None:
        import devobs.ai_evaluation.engine as engine
        import devobs.ai_evaluation.mocks as mocks

        for module in (engine, mocks):
            source = module.__file__
            self.assertIsNotNone(source)
            with open(source, encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("import requests", text)
            self.assertNotIn("urllib.request.urlopen", text)
            self.assertNotIn("httpx", text)


if __name__ == "__main__":
    unittest.main()

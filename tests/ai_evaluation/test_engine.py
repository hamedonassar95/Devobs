"""Behavioral tests for the offline-first provider evaluation harness.

No test in this module opens a socket, reads a credential or imports a provider
SDK. Every scenario is a deterministic in-memory fixture.
"""

from __future__ import annotations

import json
import pathlib
import unittest
from decimal import Decimal

from devobs.ai_evaluation.engine import EvaluationEngine, build_default_configs
from devobs.ai_evaluation.models import (
    Confidence,
    ErrorCategory,
    EvaluationError,
    FixtureCase,
    FixtureSet,
    InvocationOutcome,
    ProviderConfig,
    ProviderStatus,
    SafetyPolicyResult,
)
from devobs.ai_evaluation.pricing import PricingCatalog

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples" / "ai_evaluation"


def _fixture() -> FixtureSet:
    raw = json.loads((EXAMPLES / "provider_cases.json").read_text(encoding="utf-8"))
    return FixtureSet.from_mapping(raw)


class PricingCatalogTests(unittest.TestCase):
    def test_unknown_prices_are_marked_unknown_never_zero(self) -> None:
        catalog = PricingCatalog.from_mapping({
            "schema_version": "ai-eval-pricing/1.0",
            "currency": "USD",
            "entries": {
                "grok-4.7": {
                    "prompt_usd_per_million": "2.00",
                    "completion_usd_per_million": "0.50",
                    "source_url": "https://docs.x.ai/developers/models",
                    "verified": True,
                },
                "unlisted-model": {"verified": False},
            },
        })
        known = catalog.estimate("grok-4.7", 1_000_000, 1_000_000)
        self.assertEqual(known.total_usd, Decimal("2.5"))
        self.assertEqual(known.confidence, Confidence.ESTIMATED)
        unknown = catalog.estimate("unlisted-model", 100, 100)
        self.assertIsNone(unknown.total_usd)
        self.assertEqual(unknown.confidence, Confidence.UNKNOWN)
        self.assertEqual(unknown.label, "UNKNOWN")

    def test_pricing_rejects_negative_rates_and_missing_verified_source(self) -> None:
        with self.assertRaises(EvaluationError):
            PricingCatalog.from_mapping({
                "schema_version": "ai-eval-pricing/1.0",
                "currency": "USD",
                "entries": {
                    "bad": {
                        "prompt_usd_per_million": "-1",
                        "completion_usd_per_million": "1",
                        "source_url": "https://example.invalid",
                        "verified": True,
                    },
                },
            })
        with self.assertRaises(EvaluationError):
            PricingCatalog.from_mapping({
                "schema_version": "ai-eval-pricing/1.0",
                "currency": "USD",
                "entries": {
                    "nosource": {
                        "prompt_usd_per_million": "1",
                        "completion_usd_per_million": "1",
                        "source_url": "",
                        "verified": True,
                    },
                },
            })


class ProviderEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _fixture()
        self.catalog = PricingCatalog.from_mapping(json.loads(
            (EXAMPLES / "pricing.json").read_text(encoding="utf-8")
        ))
        self.engine = EvaluationEngine(self.catalog)

    def test_every_required_failure_scenario_is_deterministic(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        outcomes = {case.case_id: case.result.outcome for case in report.cases}
        self.assertEqual(
            outcomes,
            {
                "success-basic": InvocationOutcome.SUCCESS,
                "timeout-basic": InvocationOutcome.TIMEOUT,
                "rate-limit-retry": InvocationOutcome.SUCCESS,
                "malformed-json": InvocationOutcome.MALFORMED_RESPONSE,
                "auth-failure": InvocationOutcome.AUTHENTICATION_ERROR,
                "cost-ceiling": InvocationOutcome.BUDGET_BLOCKED,
                "unsafe-action": InvocationOutcome.UNSAFE_ACTION_BLOCKED,
                "provider-outage": InvocationOutcome.PROVIDER_UNAVAILABLE,
                "redirect-refused": InvocationOutcome.OUTBOUND_BLOCKED,
                "redaction-basic": InvocationOutcome.SUCCESS,
            },
        )
        second = self.engine.evaluate(self.fixture, build_default_configs())
        self.assertEqual(report.fingerprint, second.fingerprint)
        self.assertEqual(report.to_dict(), second.to_dict())

    def test_structured_result_records_all_required_fields(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        ok = next(c for c in report.cases if c.case_id == "success-basic").result
        payload = ok.to_dict()
        for field in (
            "provider_id", "model_id", "latency_ms", "error_category",
            "reliability_score", "prompt_tokens", "completion_tokens",
            "estimated_tokens", "estimated_cost_usd", "cost_confidence",
            "safety_policy_result",
        ):
            self.assertIn(field, payload, field)
        self.assertEqual(payload["provider_id"], "fixture-primary")
        self.assertEqual(payload["model_id"], "grok-4.7")
        self.assertEqual(payload["error_category"], "NONE")
        self.assertEqual(payload["safety_policy_result"], "ALLOWED")
        self.assertEqual(payload["cost_confidence"], "ESTIMATED")
        # grok-4.7: 2.00/0.50 USD per million prompt/completion tokens.
        expected_cost = (
            Decimal(payload["prompt_tokens"]) * Decimal("2.00")
            + Decimal(payload["completion_tokens"]) * Decimal("0.50")
        ) / Decimal(1_000_000)
        self.assertEqual(Decimal(payload["estimated_cost_usd"]), expected_cost)
        self.assertGreaterEqual(Decimal(payload["reliability_score"]), Decimal("0"))
        self.assertLessEqual(Decimal(payload["reliability_score"]), Decimal("1"))

    def test_error_categories_and_safety_results_are_specific(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        by_id = {c.case_id: c.result for c in report.cases}
        self.assertEqual(by_id["timeout-basic"].error_category, ErrorCategory.TIMEOUT)
        self.assertEqual(
            by_id["rate-limit-retry"].error_category, ErrorCategory.RATE_LIMIT,
        )
        self.assertEqual(
            by_id["malformed-json"].error_category, ErrorCategory.INVALID_RESPONSE,
        )
        self.assertEqual(
            by_id["auth-failure"].error_category, ErrorCategory.AUTHENTICATION,
        )
        self.assertEqual(by_id["cost-ceiling"].error_category, ErrorCategory.COST)
        self.assertEqual(
            by_id["unsafe-action"].safety_policy_result, SafetyPolicyResult.BLOCKED,
        )
        self.assertEqual(
            by_id["provider-outage"].error_category, ErrorCategory.UNAVAILABLE,
        )
        self.assertEqual(by_id["provider-outage"].status, ProviderStatus.UNAVAILABLE)

    def test_rate_limit_retry_records_attempts_and_latency(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        retried = next(c for c in report.cases if c.case_id == "rate-limit-retry").result
        self.assertEqual(retried.attempts, 2)
        self.assertEqual(retried.outcome, InvocationOutcome.SUCCESS)
        self.assertGreater(retried.latency_ms, Decimal("0"))

    def test_comparison_outputs_cost_and_capability_columns(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        payload = report.to_dict()
        self.assertIn("comparison", payload)
        comparison = payload["comparison"]
        self.assertTrue(comparison["by_provider"])
        self.assertTrue(comparison["by_capability"])
        first = next(iter(comparison["by_provider"].values()))
        for field in ("provider_id", "model_id", "estimated_cost_usd", "capabilities"):
            self.assertIn(field, first)
        self.assertIn("structured_json", comparison["by_capability"])
        # A capability unique to the fallback routes its case to that provider.
        self.assertEqual(
            comparison["by_capability"]["log_redaction"], ["fixture-fallback"],
        )
        redaction_case = next(c for c in report.cases if c.case_id == "redaction-basic")
        self.assertEqual(redaction_case.result.provider_id, "fixture-fallback")
        self.assertEqual(redaction_case.result.cost_confidence, Confidence.UNKNOWN)
        self.assertFalse(payload["live_calls"])
        self.assertTrue(payload["offline"])

    def test_unknown_pricing_is_propagated_to_results(self) -> None:
        fixture = FixtureSet.from_mapping({
            "version": "unknown-price-v1",
            "seed": 1,
            "generated_at": "2026-01-01T00:00:00Z",
            "cases": [{
                "case_id": "unknown-price",
                "task": "triage",
                "prompt": "Summarize the incident in one line.",
                "capabilities": ["advisory_only"],
                "scenario": "success",
                "expected_outcome": "SUCCESS",
                "expected_status": "AVAILABLE",
            }],
        })
        unknown_config = ProviderConfig.from_mapping({
            "name": "fixture-fallback",
            "model": "gemini-2.5-pro",
            "capabilities": ["advisory_only", "incident_triage"],
        })
        report = self.engine.evaluate(fixture, (unknown_config,))
        result = report.cases[0].result
        self.assertEqual(result.cost_confidence, Confidence.UNKNOWN)
        self.assertIsNone(result.estimated_cost_usd)
        self.assertEqual(result.to_dict()["cost_confidence"], "UNKNOWN")

    def test_fail_closed_on_unknown_scenario(self) -> None:
        # An unknown scenario is rejected at fixture construction (fail closed).
        with self.assertRaises(EvaluationError):
            FixtureCase.from_mapping({
                "case_id": "bad-scenario",
                "task": "triage",
                "prompt": "hello",
                "capabilities": ["advisory_only"],
                "scenario": "send-email",
            })

    def test_fail_closed_on_redirect_and_unsafe_requested_action(self) -> None:
        report = self.engine.evaluate(self.fixture, build_default_configs())
        redirected = next(c for c in report.cases if c.case_id == "redirect-refused").result
        unsafe = next(c for c in report.cases if c.case_id == "unsafe-action").result
        self.assertEqual(redirected.status, ProviderStatus.BLOCKED)
        self.assertEqual(redirected.outcome, InvocationOutcome.OUTBOUND_BLOCKED)
        self.assertEqual(unsafe.status, ProviderStatus.BLOCKED)
        self.assertEqual(unsafe.outcome, InvocationOutcome.UNSAFE_ACTION_BLOCKED)


if __name__ == "__main__":
    unittest.main()

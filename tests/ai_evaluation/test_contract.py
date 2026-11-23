"""Contract tests for failure classification, cost ceilings and merged contracts.

All inputs are deterministic in-memory fixtures; no provider, network or secret
is involved. These tests complement ``test_engine.py`` and ``test_gate.py``.
"""

from __future__ import annotations

import json
import pathlib
import unittest
from dataclasses import replace
from decimal import Decimal

from devobs.ai_evaluation.engine import EvaluationEngine
from devobs.ai_evaluation.models import (
    ErrorCategory,
    EvaluationError,
    FixtureCase,
    FixtureSet,
    InvocationOutcome,
    ProviderConfig,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    SafetyPolicyResult,
)
from devobs.ai_evaluation.pricing import PricingCatalog

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples" / "ai_evaluation"


def _fixture():
    return FixtureSet.from_mapping(json.loads(
        (EXAMPLES / "provider_cases.json").read_text(encoding="utf-8")))


def _catalog():
    return PricingCatalog.from_mapping(json.loads(
        (EXAMPLES / "pricing.json").read_text(encoding="utf-8")))


def _case(report, case_id: str):
    return next(case for case in report.cases if case.case_id == case_id)


class FailureClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        from devobs.ai_evaluation.engine import build_default_configs

        self.report = EvaluationEngine(_catalog()).evaluate(
            _fixture(), build_default_configs())

    def test_malformed_response_is_classified_and_not_success(self) -> None:
        result = _case(self.report, "malformed-json").result
        self.assertEqual(result.outcome, InvocationOutcome.MALFORMED_RESPONSE)
        self.assertEqual(result.error_category, ErrorCategory.INVALID_RESPONSE)
        self.assertEqual(
            result.safety_policy_result, SafetyPolicyResult.NOT_EVALUATED)
        self.assertNotEqual(result.outcome, InvocationOutcome.SUCCESS)

    def test_timeout_is_bounded_and_classified(self) -> None:
        result = _case(self.report, "timeout-basic").result
        self.assertEqual(result.outcome, InvocationOutcome.TIMEOUT)
        self.assertEqual(result.error_category, ErrorCategory.TIMEOUT)
        self.assertGreaterEqual(result.latency_ms, Decimal("1000"))
        self.assertEqual(result.completion_tokens, 0)

    def test_provider_unavailability_is_explicit(self) -> None:
        result = _case(self.report, "provider-outage").result
        self.assertEqual(result.outcome, InvocationOutcome.PROVIDER_UNAVAILABLE)
        self.assertEqual(result.status, ProviderStatus.UNAVAILABLE)
        self.assertEqual(result.error_category, ErrorCategory.UNAVAILABLE)

    def test_unsafe_requested_action_is_blocked(self) -> None:
        result = _case(self.report, "unsafe-action").result
        self.assertEqual(result.outcome, InvocationOutcome.UNSAFE_ACTION_BLOCKED)
        self.assertEqual(result.status, ProviderStatus.BLOCKED)
        self.assertEqual(result.safety_policy_result, SafetyPolicyResult.BLOCKED)


class CostCeilingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = FixtureSet.from_mapping({
            "version": "ceiling-v1",
            "seed": 1,
            "generated_at": "2026-01-01T00:00:00Z",
            "cases": [{
                "case_id": "ceiling-case",
                "task": "incident_triage",
                "prompt": "Classify this sanitized failure in one line.",
                "capabilities": ["incident_triage"],
                "scenario": "success",
                "expected_outcome": "SUCCESS",
                "expected_status": "AVAILABLE",
            }],
        })

    def _config(self, ceiling: str) -> ProviderConfig:
        return ProviderConfig.from_mapping({
            "name": "ceiling-provider",
            "model": "grok-4.7",
            "capabilities": ["incident_triage"],
            "spending_ceiling_usd": ceiling,
        })

    def test_zero_ceiling_blocks_any_positive_estimate(self) -> None:
        report = EvaluationEngine(_catalog()).evaluate(
            self.fixture, (self._config("0"),))
        result = report.cases[0].result
        self.assertEqual(result.outcome, InvocationOutcome.BUDGET_BLOCKED)
        self.assertEqual(result.error_category, ErrorCategory.COST)
        self.assertEqual(result.reliability_score, Decimal("0"))

    def test_high_ceiling_allows_success(self) -> None:
        report = EvaluationEngine(_catalog()).evaluate(
            self.fixture, (self._config("1"),))
        self.assertEqual(
            report.cases[0].result.outcome, InvocationOutcome.SUCCESS)

    def test_unverified_price_is_never_zero(self) -> None:
        estimate = _catalog().estimate("gemini-2.5-pro", 1000, 1000)
        self.assertIsNone(estimate.total_usd)
        self.assertEqual(estimate.confidence.value, "UNKNOWN")


class MergedContractTests(unittest.TestCase):
    def test_fixture_case_builds_bounded_request(self) -> None:
        case = FixtureCase.from_mapping({
            "case_id": "request-case",
            "task": "log_redaction",
            "prompt": "Redact this sanitized line.",
            "capabilities": ["log_redaction"],
            "scenario": "success",
            "expected_markers": ["REDACTED"],
            "forbidden_markers": ["token"],
        })
        request: ProviderRequest = case.to_request()
        self.assertIsInstance(request, ProviderRequest)
        self.assertEqual(request.case_id, "request-case")
        self.assertEqual(request.request_id, "ai-eval-request-case")
        self.assertEqual(request.expected_markers, ("REDACTED",))
        payload = request.to_dict()
        self.assertEqual(payload["scenario"], "success")
        self.assertEqual(payload["max_output_tokens"], 512)

    def test_marker_string_is_rejected(self) -> None:
        with self.assertRaises(EvaluationError):
            FixtureCase.from_mapping({
                "case_id": "bad-markers",
                "task": "log_redaction",
                "prompt": "Redact this sanitized line.",
                "capabilities": ["log_redaction"],
                "scenario": "success",
                "expected_markers": "not-a-list",
            })

    def test_report_exposes_routing_and_config_contracts(self) -> None:
        from devobs.ai_evaluation.engine import build_default_configs

        report = EvaluationEngine(_catalog()).evaluate(
            _fixture(), build_default_configs())
        self.assertEqual(len(report.configs), 2)
        self.assertTrue(report.routing)
        for decision in report.routing:
            self.assertIsNotNone(decision.selected_provider)
            self.assertEqual(decision.confidence.value, "TESTED")
            self.assertIn(decision.selected_provider, decision.candidate_providers)
        payload = report.to_dict()
        self.assertEqual(len(payload["routing"]), len(report.routing))
        self.assertEqual(payload["base_sha"], "unknown")

    def test_report_rejects_malformed_sha(self) -> None:
        from devobs.ai_evaluation.engine import build_default_configs

        report = EvaluationEngine(_catalog()).evaluate(
            _fixture(), build_default_configs())
        with self.assertRaises(EvaluationError):
            replace(report, base_sha="not-a-sha")

    def test_response_text_is_redacted(self) -> None:
        secret_like = "xai-" + "B" * 24
        response = ProviderResponse(
            provider_id="fixture-provider",
            model_id="fixture-model",
            outcome=InvocationOutcome.SUCCESS,
            status=ProviderStatus.AVAILABLE,
            latency_ms=Decimal("1"),
            text="observed " + secret_like + " in log",
        )
        self.assertNotIn(secret_like, response.text)
        self.assertIn("[REDACTED]", response.text)


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the deterministic offline quality gate.

No test opens a socket, reads a credential or calls a provider. Every assertion
runs against the seeded fixtures in ``examples/ai_evaluation``.
"""

from __future__ import annotations

import json
import pathlib
import unittest
from dataclasses import replace
from decimal import Decimal

from devobs.ai_evaluation.engine import EvaluationEngine, build_default_configs
from devobs.ai_evaluation.gate import (
    EXPECTED_FINGERPRINT,
    MIN_COMPOSITE,
    GateDecision,
    evaluate_gate,
)
from devobs.ai_evaluation.models import (
    EvaluationError,
    FixtureSet,
    InvocationOutcome,
    ProviderStatus,
    SafetyPolicyResult,
)
from devobs.ai_evaluation.pricing import PricingCatalog

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples" / "ai_evaluation"


def _report():
    fixture = FixtureSet.from_mapping(json.loads(
        (EXAMPLES / "provider_cases.json").read_text(encoding="utf-8")))
    catalog = PricingCatalog.from_mapping(json.loads(
        (EXAMPLES / "pricing.json").read_text(encoding="utf-8")))
    return EvaluationEngine(catalog).evaluate(fixture, build_default_configs())


def _case(report, case_id: str):
    return next(case for case in report.cases if case.case_id == case_id)


def _with_case(report, case_id: str, **changes):
    cases = tuple(
        replace(case, **changes) if case.case_id == case_id else case
        for case in report.cases
    )
    return replace(report, cases=cases)


def _with_result(report, case_id: str, **changes):
    cases = tuple(
        replace(case, result=replace(case.result, **changes))
        if case.case_id == case_id else case
        for case in report.cases
    )
    return replace(report, cases=cases)


class GatePassTests(unittest.TestCase):
    def test_shipped_fixtures_pass(self) -> None:
        result = evaluate_gate(_report())
        self.assertIs(result.decision, GateDecision.PASS)
        self.assertTrue(result.passed)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.failures, ())
        self.assertEqual(result.fingerprint, EXPECTED_FINGERPRINT)
        self.assertGreaterEqual(result.score.composite, MIN_COMPOSITE)
        payload = result.to_dict()
        self.assertTrue(payload["offline"])
        self.assertEqual(payload["live_calls"], 0)
        self.assertEqual(payload["case_count"], len(_report().cases))

    def test_gate_output_is_deterministic(self) -> None:
        first = evaluate_gate(_report()).to_dict()
        second = evaluate_gate(_report()).to_dict()
        self.assertEqual(first, second)

    def test_evidence_is_present_and_bounded(self) -> None:
        payload = evaluate_gate(_report()).to_dict()
        self.assertTrue(payload["evidence"])
        for item in payload["evidence"]:
            self.assertLessEqual(len(item["claim"]), 512)
            self.assertLessEqual(len(item["source"]), 512)


class GateBlockTests(unittest.TestCase):
    def test_outcome_mismatch_blocks(self) -> None:
        report = _report()
        tampered = _with_case(
            report, "success-basic", expected_outcome=InvocationOutcome.TIMEOUT)
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(any(
            failure.startswith("outcome_mismatch:success-basic")
            for failure in result.failures
        ))

    def test_status_mismatch_blocks(self) -> None:
        report = _report()
        tampered = _with_case(
            report, "success-basic", expected_status=ProviderStatus.UNAVAILABLE)
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertTrue(any(
            failure.startswith("status_mismatch:success-basic")
            for failure in result.failures
        ))

    def test_fingerprint_drift_blocks(self) -> None:
        report = replace(_report(), fingerprint="0000000000000000")
        result = evaluate_gate(report)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertTrue(any(
            failure.startswith("fingerprint_drift:") for failure in result.failures
        ))

    def test_live_calls_block(self) -> None:
        result = evaluate_gate(replace(_report(), live_calls=1))
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("live_calls_detected:1", result.failures)

    def test_not_offline_blocks(self) -> None:
        result = evaluate_gate(replace(_report(), offline=False))
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("not_offline", result.failures)

    def test_cost_confidence_mismatch_blocks(self) -> None:
        report = _report()
        # redaction-basic is UNKNOWN with no cost; attaching a cost is inconsistent.
        tampered = _with_result(
            report, "redaction-basic", estimated_cost_usd=Decimal("0.01"))
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("cost_confidence_mismatch:redaction-basic", result.failures)

    def test_unsafe_action_not_blocked_blocks(self) -> None:
        report = _report()
        tampered = _with_result(
            report, "unsafe-action", safety_policy_result=SafetyPolicyResult.ALLOWED)
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("unsafe_action_not_blocked:unsafe-action", result.failures)

    def test_redirect_not_blocked_blocks(self) -> None:
        report = _report()
        tampered = _with_result(
            report, "redirect-refused", status=ProviderStatus.AVAILABLE)
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("redirect_not_blocked:redirect-refused", result.failures)

    def test_low_success_reliability_blocks(self) -> None:
        report = _report()
        tampered = _with_result(
            report, "success-basic", reliability_score=Decimal("0.5"))
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertTrue(any(
            failure.startswith("low_reliability:success-basic")
            for failure in result.failures
        ))

    def test_non_mock_result_blocks(self) -> None:
        report = _report()
        tampered = _with_result(report, "success-basic", is_mock=False)
        result = evaluate_gate(tampered)
        self.assertIs(result.decision, GateDecision.BLOCKED)
        self.assertIn("non_mock_result:success-basic", result.failures)

    def test_invalid_input_raises(self) -> None:
        with self.assertRaises(EvaluationError):
            evaluate_gate(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

"""Deterministic, offline quality gate for the AI provider evaluation harness.

The gate turns an ``EvaluationReport`` into one closed decision. It performs no
network call, reads no credential and cannot authorize a provider switch,
merge, deployment or spend. ``PASS`` only means the offline fixtures still match
their pinned expectations; it is never evidence that a live provider works.

Exit codes are stable for CI:

- ``0`` — ``PASS``
- ``1`` — ``BLOCKED`` (a deterministic expectation failed)
- ``2`` — ``INVALID`` (the gate itself failed closed)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from .models import (
    Confidence,
    EvaluationError,
    EvaluationReport,
    Evidence,
    InvocationOutcome,
    ProviderStatus,
    SafetyPolicyResult,
    ScoreBreakdown,
)

GATE_SCHEMA_VERSION = "ai-eval-gate/1.0"

# Pinned over the shipped fixtures in ``examples/ai_evaluation``. Any intentional
# fixture or pricing change must update this value in the same reviewed commit.
EXPECTED_FINGERPRINT = "e04ae0abf3e33f4c"

MIN_COMPOSITE = Decimal("0.90")
MIN_SUCCESS_RELIABILITY = Decimal("0.75")

_QUALITY_WEIGHT = Decimal("0.6")
_RELIABILITY_WEIGHT = Decimal("0.4")
_PRECISION = Decimal("0.0001")


class GateDecision(str, Enum):
    # "PASS" is a serialized decision label, not a credential. The longer
    # member name avoids Bandit's B105 hardcoded-password false positive.
    PASSED = "PASS"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


_EXIT_CODES = {
    GateDecision.PASSED: 0,
    GateDecision.BLOCKED: 1,
    GateDecision.INVALID: 2,
}


@dataclass(frozen=True)
class GateResult:
    """A closed gate decision with deterministic failure codes."""

    decision: GateDecision
    fingerprint: str
    expected_fingerprint: str
    case_count: int
    offline: bool
    live_calls: int
    score: ScoreBreakdown
    failures: tuple[str, ...]
    evidence: tuple[Evidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.decision, GateDecision):
            raise EvaluationError("invalid_gate_decision")
        if type(self.case_count) is not int or self.case_count < 0:
            raise EvaluationError("invalid_gate_case_count")
        if not isinstance(self.score, ScoreBreakdown):
            raise EvaluationError("invalid_gate_score")
        if type(self.failures) is not tuple or not all(
            type(item) is str and 1 <= len(item) <= 512 for item in self.failures
        ):
            raise EvaluationError("invalid_gate_failures")
        if type(self.evidence) is not tuple or not all(
            isinstance(item, Evidence) for item in self.evidence
        ):
            raise EvaluationError("invalid_gate_evidence")

    @property
    def exit_code(self) -> int:
        return _EXIT_CODES[self.decision]

    @property
    def passed(self) -> bool:
        return self.decision is GateDecision.PASSED

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": GATE_SCHEMA_VERSION,
            "decision": self.decision.value,
            "exit_code": self.exit_code,
            "fingerprint": self.fingerprint,
            "expected_fingerprint": self.expected_fingerprint,
            "case_count": self.case_count,
            "offline": self.offline,
            "live_calls": self.live_calls,
            "score": self.score.to_dict(),
            "failures": list(self.failures),
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _case_failures(report: EvaluationReport) -> list[str]:
    failures: list[str] = []
    for case in report.cases:
        result = case.result
        if result.outcome != case.expected_outcome:
            failures.append(
                "outcome_mismatch:" + case.case_id
                + ":expected=" + case.expected_outcome.value
                + ":actual=" + result.outcome.value
            )
        if result.status != case.expected_status:
            failures.append(
                "status_mismatch:" + case.case_id
                + ":expected=" + case.expected_status.value
                + ":actual=" + result.status.value
            )
        if result.is_mock is not True:
            failures.append("non_mock_result:" + case.case_id)
        if not result.provider_id or not result.model_id:
            failures.append("missing_identifier:" + case.case_id)
        if result.cost_confidence is Confidence.UNKNOWN:
            if result.estimated_cost_usd is not None:
                failures.append("cost_confidence_mismatch:" + case.case_id)
        elif result.estimated_cost_usd is None:
            failures.append("cost_confidence_mismatch:" + case.case_id)
        if case.expected_outcome is InvocationOutcome.UNSAFE_ACTION_BLOCKED:
            if result.safety_policy_result is not SafetyPolicyResult.BLOCKED:
                failures.append("unsafe_action_not_blocked:" + case.case_id)
        if case.expected_outcome is InvocationOutcome.OUTBOUND_BLOCKED:
            if result.status is not ProviderStatus.BLOCKED:
                failures.append("redirect_not_blocked:" + case.case_id)
        if (
            case.expected_outcome is InvocationOutcome.SUCCESS
            and result.reliability_score < MIN_SUCCESS_RELIABILITY
        ):
            failures.append(
                "low_reliability:" + case.case_id + ":" + str(result.reliability_score)
            )
    return failures


def _score(report: EvaluationReport) -> ScoreBreakdown:
    total = len(report.cases)
    if total == 0:
        return ScoreBreakdown(
            quality=Decimal("0"),
            reliability=Decimal("0"),
            composite=Decimal("0"),
            confidence=Confidence.UNKNOWN,
            rationale=("No cases were evaluated.",),
        )
    matched = sum(
        1 for case in report.cases
        if case.result.outcome == case.expected_outcome
        and case.result.status == case.expected_status
    )
    successes = [
        case.result.reliability_score for case in report.cases
        if case.expected_outcome is InvocationOutcome.SUCCESS
    ]
    quality = (Decimal(matched) / Decimal(total)).quantize(
        _PRECISION, rounding=ROUND_HALF_UP)
    reliability = (
        (sum(successes, Decimal("0")) / Decimal(len(successes))).quantize(
            _PRECISION, rounding=ROUND_HALF_UP)
        if successes else Decimal("0")
    )
    composite = (
        quality * _QUALITY_WEIGHT + reliability * _RELIABILITY_WEIGHT
    ).quantize(_PRECISION, rounding=ROUND_HALF_UP)
    return ScoreBreakdown(
        quality=quality,
        reliability=reliability,
        composite=composite,
        confidence=Confidence.TESTED,
        rationale=(
            "quality = matched outcome/status cases / total cases.",
            "reliability = mean reliability_score over expected-success cases.",
            "composite = 0.6 * quality + 0.4 * reliability.",
        ),
    )


def _evidence(failures: list[str]) -> tuple[Evidence, ...]:
    def has(prefix: str) -> bool:
        return any(item.startswith(prefix) for item in failures)

    def confidence(prefix: str) -> Confidence:
        return Confidence.UNKNOWN if has(prefix) else Confidence.TESTED

    return (
        Evidence(
            claim="Fixture outcomes and statuses were compared with expectations.",
            confidence=(
                Confidence.UNKNOWN
                if has("outcome_mismatch") or has("status_mismatch")
                else Confidence.TESTED
            ),
            source="offline-fixture:examples/ai_evaluation/provider_cases.json",
        ),
        Evidence(
            claim="Report fingerprint was compared with the pinned baseline.",
            confidence=confidence("fingerprint_drift"),
            source="ai_evaluation.gate.EXPECTED_FINGERPRINT",
        ),
        Evidence(
            claim="No live provider call was made during this evaluation.",
            confidence=(
                Confidence.UNKNOWN
                if has("not_offline") or has("live_calls_detected")
                else Confidence.TESTED
            ),
            source="EvaluationReport.offline / EvaluationReport.live_calls",
        ),
        Evidence(
            claim="Unverified pricing is reported as UNKNOWN, never as zero.",
            confidence=confidence("cost_confidence_mismatch"),
            source="examples/ai_evaluation/pricing.json",
        ),
    )


def evaluate_gate(report: EvaluationReport) -> GateResult:
    """Evaluate one report against the pinned offline quality criteria."""
    if not isinstance(report, EvaluationReport):
        raise EvaluationError("invalid_report")
    try:
        failures: list[str] = []
        if report.offline is not True:
            failures.append("not_offline")
        if report.live_calls != 0:
            failures.append("live_calls_detected:" + str(report.live_calls))
        if not report.cases:
            failures.append("empty_report")
        if report.fingerprint != EXPECTED_FINGERPRINT:
            failures.append(
                "fingerprint_drift:expected=" + EXPECTED_FINGERPRINT
                + ":actual=" + report.fingerprint
            )
        failures.extend(_case_failures(report))
        score = _score(report)
        if score.composite < MIN_COMPOSITE:
            failures.append("composite_below_threshold:" + str(score.composite))
        ordered = tuple(sorted(failures))
        decision = GateDecision.BLOCKED if ordered else GateDecision.PASSED
        return GateResult(
            decision=decision,
            fingerprint=report.fingerprint,
            expected_fingerprint=EXPECTED_FINGERPRINT,
            case_count=len(report.cases),
            offline=report.offline,
            live_calls=report.live_calls,
            score=score,
            failures=ordered,
            evidence=_evidence(list(ordered)),
        )
    except EvaluationError:
        raise
    except Exception:
        # Fail closed: never let an unexpected error look like a pass.
        return GateResult(
            decision=GateDecision.INVALID,
            fingerprint=report.fingerprint,
            expected_fingerprint=EXPECTED_FINGERPRINT,
            case_count=len(report.cases),
            offline=report.offline,
            live_calls=report.live_calls,
            score=ScoreBreakdown(
                quality=Decimal("0"),
                reliability=Decimal("0"),
                composite=Decimal("0"),
                confidence=Confidence.UNKNOWN,
                rationale=("Gate internal error.",),
            ),
            failures=("gate_internal_error",),
            evidence=(
                Evidence(
                    claim="The gate failed closed after an unexpected error.",
                    confidence=Confidence.UNKNOWN,
                    source="ai_evaluation.gate.evaluate_gate",
                ),
            ),
        )


def gate_to_dict(result: GateResult) -> dict[str, Any]:
    """Explicit alias used by the CLI and tests."""
    return result.to_dict()


__all__ = [
    "EXPECTED_FINGERPRINT",
    "GATE_SCHEMA_VERSION",
    "GateDecision",
    "GateResult",
    "MIN_COMPOSITE",
    "MIN_SUCCESS_RELIABILITY",
    "evaluate_gate",
    "gate_to_dict",
]

"""Deterministic, offline-only evaluation of the existing advisory baseline.

Synthetic outcomes are NOT a calibrated real-world AI accuracy measure.
No model provider, token, network or tool execution is used here.
"""
from __future__ import annotations

import hashlib
import math
import re

from .adviser import AdvisoryError, propose
from .contracts import EvidenceError, parse_event


class EvaluationError(ValueError):
    """Privacy-preserving fixed diagnostic."""


_CATEGORIES = frozenset({"ci_failure", "high_error_rate", "capacity_pressure", "unknown"})
_CASE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}\Z")


def evaluate_cases(cases: list[dict], *, target_accuracy: float = 0.85) -> dict[str, object]:
    """Score fixed synthetic cases; return aggregates without case details."""
    if (type(target_accuracy) not in (float, int)
            or not math.isfinite(target_accuracy)
            or not 0 <= target_accuracy <= 1):
        raise EvaluationError("invalid_target")
    if type(cases) is not list or not 1 <= len(cases) <= 100:
        raise EvaluationError("invalid_cases")

    seen = set()
    correct = 0
    abstentions = 0
    non_abstained_correct = 0
    for case in cases:
        if type(case) is not dict or set(case) != {"case_id", "signals", "expected_category"}:
            raise EvaluationError("invalid_case")
        case_id, signals, expected = case["case_id"], case["signals"], case["expected_category"]
        if (type(case_id) is not str or _CASE_ID.fullmatch(case_id) is None
                or type(expected) is not str or expected not in _CATEGORIES
                or type(signals) is not dict
                or set(signals) != {"failed_checks", "error_rate_pct", "capacity_pct"}):
            raise EvaluationError("invalid_case")
        if case_id in seen:
            raise EvaluationError("duplicate_case")
        seen.add(case_id)
        evidence_digest = hashlib.sha256(("fixture:" + case_id).encode()).hexdigest()
        try:
            event = parse_event({
                "schema_version": 1,
                "event_id": "eval-" + case_id,
                "provider": "github",
                "project_ref": "synthetic-evaluation",
                "source_sha": "a" * 40,
                "kind": "incident",
                "observed_at": "2026-10-25T00:00:00Z",
                "evidence_digests": [evidence_digest],
            })
            # Deliberately invokes offline, deterministic behavior only.
            predicted = propose(event, signals, model_enabled=False).hypothesis
        except (EvidenceError, AdvisoryError):
            raise EvaluationError("invalid_case") from None
        if predicted == expected:
            correct += 1
        if predicted == "unknown":
            abstentions += 1
        elif predicted == expected:
            non_abstained_correct += 1

    non_abstained = len(cases) - abstentions
    accuracy = correct / len(cases)
    return {
        "schema_version": 1,
        "case_count": len(cases),
        "correct": correct,
        "abstentions": abstentions,
        "accuracy": accuracy,
        "selective_accuracy": non_abstained_correct / non_abstained if non_abstained else None,
        "target_accuracy": float(target_accuracy),
        "meets_target": accuracy >= target_accuracy,
        "confidence_calibrated": False,
        "live_model_calls": 0,
    }

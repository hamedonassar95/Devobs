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
_WILSON_95_Z = 1.959963984540054


def _wilson_interval(successes: int, trials: int) -> dict[str, float]:
    """Return the nominal 95% Wilson score interval for a binomial proportion."""
    proportion = successes / trials
    z_squared = _WILSON_95_Z ** 2
    denominator = 1 + z_squared / trials
    center = (proportion + z_squared / (2 * trials)) / denominator
    radius = math.sqrt(
        (proportion * (1 - proportion) + z_squared / (4 * trials)) / trials
    ) * _WILSON_95_Z / denominator
    return {"lower": max(0.0, center - radius), "upper": min(1.0, center + radius)}


def evaluate_cases(cases: list[dict], *, target_accuracy: float | None = None) -> dict[str, object]:
    """Score fixed synthetic cases without inventing an acceptance target.

    Compare against a target only when the caller supplies an explicitly chosen
    value. The evaluator cannot establish that the target has owner approval.
    """
    if (target_accuracy is not None
            and (type(target_accuracy) not in (float, int)
                 or not math.isfinite(target_accuracy)
                 or not 0 <= target_accuracy <= 1)):
        raise EvaluationError("invalid_target")
    if type(cases) is not list or not 1 <= len(cases) <= 100:
        raise EvaluationError("invalid_cases")

    seen = set()
    correct = 0
    abstentions = 0
    non_abstained_correct = 0
    expected_categories = []
    predictions = []
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
        expected_categories.append(expected)
        predictions.append(predicted)
        if predicted == expected:
            correct += 1
        if predicted == "unknown":
            abstentions += 1
        elif predicted == expected:
            non_abstained_correct += 1

    non_abstained = len(cases) - abstentions
    accuracy = correct / len(cases)
    per_category = {}
    for category in sorted(_CATEGORIES):
        support = sum(actual == category for actual in expected_categories)
        predicted_count = sum(predicted == category for predicted in predictions)
        true_positive = sum(
            actual == category and predicted == category
            for actual, predicted in zip(expected_categories, predictions)
        )
        false_positive = predicted_count - true_positive
        false_negative = support - true_positive
        true_negative = len(cases) - true_positive - false_positive - false_negative
        per_category[category] = {
            "support": support,
            "predicted_count": predicted_count,
            "confusion": {
                "tp": true_positive,
                "fp": false_positive,
                "tn": true_negative,
                "fn": false_negative,
            },
            "precision": {
                "value": true_positive / predicted_count if predicted_count else None,
                "numerator": true_positive,
                "denominator": predicted_count,
            },
            "recall": {
                "value": true_positive / support if support else None,
                "numerator": true_positive,
                "denominator": support,
            },
        }
    return {
        "schema_version": 1,
        "case_count": len(cases),
        "correct": correct,
        "abstentions": abstentions,
        "accuracy": accuracy,
        "accuracy_interval_95": {
            "method": "wilson_score",
            "confidence_level": 0.95,
            **_wilson_interval(correct, len(cases)),
            "successes": correct,
            "trials": len(cases),
        },
        "per_category": per_category,
        "selective_accuracy": non_abstained_correct / non_abstained if non_abstained else None,
        "target_accuracy": float(target_accuracy) if target_accuracy is not None else None,
        "meets_target": accuracy >= target_accuracy if target_accuracy is not None else None,
        "confidence_calibrated": False,
        "live_model_calls": 0,
    }

"""Deterministic, offline-only evaluation of the existing advisory baseline.

Synthetic outcomes are NOT a calibrated real-world AI accuracy measure.
No model provider, token, network or tool execution is used here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from .adviser import AdvisoryError, propose
from .contracts import EvidenceError, parse_event


class EvaluationError(ValueError):
    """Privacy-preserving fixed diagnostic."""


_CATEGORIES = frozenset({"ci_failure", "high_error_rate", "capacity_pressure", "unknown"})
_CASE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_WILSON_95_Z = 1.959963984540054
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_RELATIVE_PATH = Path("docs/ai/intelligence-evaluation-policy-v1.json")
_FIXTURE_RELATIVE_PATH = Path("tests/fixtures/intelligence_eval_cases.json")
_MAX_FIXTURE_BYTES = 64_000


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvaluationError("duplicate_json_key")
        result[key] = value
    return result


def _load_json(raw: bytes, error_code: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeError, json.JSONDecodeError, EvaluationError, RecursionError):
        raise EvaluationError(error_code) from None


def _validate_fixture_manifest(value: Any) -> dict[str, Any]:
    keys = {
        "schema_version", "dataset_id", "dataset_version", "dataset_path", "dataset_sha256",
        "source_kind", "label_status", "label_method", "categories", "case_count", "max_bytes",
        "production_gate", "scope",
    }
    if type(value) is not dict or set(value) != keys:
        raise EvaluationError("invalid_manifest")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["dataset_id"] != "devobs-adviser-synthetic"
        or value["dataset_version"] != "v1"
        or value["dataset_path"] != _FIXTURE_RELATIVE_PATH.as_posix()
        or not isinstance(value["dataset_sha256"], str)
        or not _SHA256.fullmatch(value["dataset_sha256"])
        or value["source_kind"] != "synthetic"
        or value["label_status"] != "synthetic_unreviewed"
        or value["label_method"] != "synthetic_expected_category"
        or value["categories"] != sorted(_CATEGORIES)
        or type(value["case_count"]) is not int
        or not 1 <= value["case_count"] <= 100
        or type(value["max_bytes"]) is not int
        or value["max_bytes"] != _MAX_FIXTURE_BYTES
        or value["production_gate"] is not False
        or value["scope"] != "synthetic deterministic adviser fixture only"
    ):
        raise EvaluationError("invalid_manifest")
    return value


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
    coverage = non_abstained / len(cases)
    unknown_output_rate = abstentions / len(cases)
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
        "coverage": {
            "value": coverage,
            "numerator": non_abstained,
            "denominator": len(cases),
        },
        "unknown_output_rate": {
            "value": unknown_output_rate,
            "numerator": abstentions,
            "denominator": len(cases),
        },
        "per_category": per_category,
        "selective_accuracy": non_abstained_correct / non_abstained if non_abstained else None,
        "selective_accuracy_counts": {
            "numerator": non_abstained_correct,
            "denominator": non_abstained,
        },
        "target_accuracy": float(target_accuracy) if target_accuracy is not None else None,
        "meets_target": accuracy >= target_accuracy if target_accuracy is not None else None,
        "confidence_calibrated": False,
        "live_model_calls": 0,
    }


def evaluate_fixture(
    root: Path | None = None,
    *,
    target_accuracy: float | None = None,
) -> dict[str, object]:
    """Evaluate the repository's manifest-pinned synthetic fixture offline."""
    repository_root = Path(root) if root is not None else _REPOSITORY_ROOT
    manifest_path = repository_root / _MANIFEST_RELATIVE_PATH
    fixture_path = repository_root / _FIXTURE_RELATIVE_PATH
    if (
        manifest_path.is_symlink() or not manifest_path.is_file()
        or fixture_path.is_symlink() or not fixture_path.is_file()
    ):
        raise EvaluationError("fixture_unavailable")
    if manifest_path.stat().st_size > 8_192:
        raise EvaluationError("invalid_manifest")
    if fixture_path.stat().st_size > _MAX_FIXTURE_BYTES:
        raise EvaluationError("fixture_too_large")

    manifest = _validate_fixture_manifest(_load_json(manifest_path.read_bytes(), "invalid_manifest"))
    raw = fixture_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest["dataset_sha256"]:
        raise EvaluationError("dataset_digest_mismatch")
    cases = _load_json(raw, "invalid_fixture")
    if type(cases) is not list or len(cases) != manifest["case_count"]:
        raise EvaluationError("dataset_case_count_mismatch")

    report = evaluate_cases(cases, target_accuracy=target_accuracy)
    report["dataset"] = {
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "sha256": digest,
        "case_count": len(cases),
        "label_status": manifest["label_status"],
        "synthetic_only": True,
        "production_gate": False,
    }
    return report


def main() -> int:
    try:
        print(json.dumps(evaluate_fixture(), sort_keys=True))
    except (EvaluationError, OSError) as error:
        code = error.args[0] if isinstance(error, EvaluationError) else "fixture_io_error"
        print(json.dumps({"error": code}, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

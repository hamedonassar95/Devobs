#!/usr/bin/env python3
"""Score saved Decisions triage results against an annotated JSONL label set.

This is an offline evaluator. It never calls a provider, runs candidate output,
or echoes incident text. Its metrics are diagnostic and do not establish that a
model is safe for production routing or incident response.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import sys
from pathlib import Path
from typing import Any

from scripts.openai_decisions_triage import CATEGORY_VALUES, MODEL, SEVERITY_LEVELS

MAX_FILE_BYTES = 5_000_000
MAX_ROWS = 1_000
MAX_INPUT_BYTES = 64_000
CASE_ID_CHARS = 80
LABEL_STATUSES = {"synthetic_unreviewed", "expert_reviewed"}
CASE_KEYS = {"case_id", "prompt_version", "label_status", "input", "expected"}
EXPECTED_KEYS = {"confirmed_security_impact", "incident_category", "incident_severity"}
OUTPUT_KEYS = {"case_id", "result"}
RESULT_KEYS = {"model", "prompt_version", "advisory_only", "answers"}
ANSWER_NAMES = {
    "confirmed_security_impact": "predicate",
    "incident_category": "choice",
    "incident_severity": "score",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_records(path: str | os.PathLike[str], kind: str) -> list[Any]:
    file_path = Path(path)
    try:
        metadata = file_path.lstat()
    except OSError as error:
        raise ValueError(f"cannot read {kind} file ({error.__class__.__name__})") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{kind} must be a regular file, not a symlink or special file")
    if metadata.st_size > MAX_FILE_BYTES:
        raise ValueError(f"{kind} exceeds the {MAX_FILE_BYTES}-byte limit")
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read {kind} file ({error.__class__.__name__})") from error
    if not content.strip():
        raise ValueError(f"{kind} is empty")

    records: list[Any] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{kind} line {line_number} is blank; each line must be a JSON object")
        try:
            records.append(json.loads(line, object_pairs_hook=_reject_duplicate_keys))
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"invalid {kind} JSON on line {line_number}: {error}") from error
        if len(records) > MAX_ROWS:
            raise ValueError(f"{kind} exceeds the {MAX_ROWS}-row limit")
    return records


def _is_probability(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 1
    )


def _validate_case(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"dataset line {line_number}"
    if not isinstance(record, dict) or set(record) != CASE_KEYS:
        raise ValueError(f"{prefix} must contain exactly: {', '.join(sorted(CASE_KEYS))}")
    case_id = record["case_id"]
    if (
        not isinstance(case_id, str)
        or not 3 <= len(case_id) <= CASE_ID_CHARS
        or not case_id[0].islower()
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in case_id)
    ):
        raise ValueError(f"{prefix} has an invalid case_id")
    if not isinstance(record["prompt_version"], str) or not record["prompt_version"].strip():
        raise ValueError(f"{prefix} prompt_version must be a non-empty string")
    if not isinstance(record["label_status"], str) or record["label_status"] not in LABEL_STATUSES:
        raise ValueError(f"{prefix} label_status must be one of {', '.join(sorted(LABEL_STATUSES))}")
    input_text = record["input"]
    if not isinstance(input_text, str) or not input_text.strip():
        raise ValueError(f"{prefix} input must be non-empty text")
    if len(input_text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError(f"{prefix} input exceeds the {MAX_INPUT_BYTES}-byte limit")

    expected = record["expected"]
    if not isinstance(expected, dict) or set(expected) != EXPECTED_KEYS:
        raise ValueError(f"{prefix} expected must contain exactly: {', '.join(sorted(EXPECTED_KEYS))}")
    if type(expected["confirmed_security_impact"]) is not bool:
        raise ValueError(f"{prefix} expected confirmed_security_impact must be a boolean")
    if (
        not isinstance(expected["incident_category"], str)
        or expected["incident_category"] not in CATEGORY_VALUES
    ):
        raise ValueError(f"{prefix} expected incident_category is not a supported category")
    severity = expected["incident_severity"]
    if type(severity) is not int or not 0 <= severity < len(SEVERITY_LEVELS):
        raise ValueError(f"{prefix} expected incident_severity must be a level index from 0 to 4")
    return record


def _validate_distribution(records: Any, expected_values: set[Any], label: str) -> dict[Any, float]:
    if not isinstance(records, list) or len(records) != len(expected_values):
        raise ValueError(f"invalid {label} probability distribution")
    distribution: dict[Any, float] = {}
    total = 0.0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"invalid {label} probability distribution")
        if label == "category":
            if set(record) != {"value", "probability"} or not isinstance(record.get("value"), str):
                raise ValueError("invalid category probability distribution")
        else:
            if set(record) != {"value", "label", "probability"} or type(record.get("value")) is not int:
                raise ValueError("invalid severity probability distribution")
            if not 0 <= record["value"] < len(SEVERITY_LEVELS):
                raise ValueError("invalid severity probability distribution")
            if record["label"] != SEVERITY_LEVELS[record["value"]][0]:
                raise ValueError("severity probability label does not match the rubric")
        value = record["value"]
        probability = record["probability"]
        if value not in expected_values or value in distribution or not _is_probability(probability):
            raise ValueError(f"invalid {label} probability distribution")
        distribution[value] = float(probability)
        total += probability
    if set(distribution) != expected_values or not 0.98 <= total <= 1.02:
        raise ValueError(f"invalid {label} probability distribution")
    return distribution


def _validate_result(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"output line {line_number}"
    if not isinstance(record, dict) or set(record) != OUTPUT_KEYS:
        raise ValueError(f"{prefix} must contain exactly: {', '.join(sorted(OUTPUT_KEYS))}")
    case_id = record["case_id"]
    if (
        not isinstance(case_id, str)
        or not 3 <= len(case_id) <= CASE_ID_CHARS
        or not case_id[0].islower()
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in case_id)
    ):
        raise ValueError(f"{prefix} has an invalid case_id")
    result = record["result"]
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        raise ValueError(f"{prefix} result has an unexpected shape")
    if (
        result["model"] != MODEL
        or result["advisory_only"] is not True
        or not isinstance(result["prompt_version"], str)
        or not result["prompt_version"].strip()
    ):
        raise ValueError(f"{prefix} must be an advisory {MODEL} result with a prompt version")
    answers = result["answers"]
    if not isinstance(answers, dict) or set(answers) != set(ANSWER_NAMES):
        raise ValueError(f"{prefix} must contain all three Decisions answers")

    predicate = answers["confirmed_security_impact"]
    if (
        not isinstance(predicate, dict)
        or set(predicate) != {"type", "probability"}
        or predicate["type"] != "predicate"
        or not _is_probability(predicate["probability"])
    ):
        raise ValueError(f"{prefix} has an invalid security-impact probability")

    category = answers["incident_category"]
    if (
        not isinstance(category, dict)
        or set(category) != {"type", "choice", "confidence", "probabilities"}
        or category["type"] != "choice"
        or category["choice"] not in CATEGORY_VALUES
        or not _is_probability(category["confidence"])
    ):
        raise ValueError(f"{prefix} has an invalid category answer")
    category_distribution = _validate_distribution(
        category["probabilities"], set(CATEGORY_VALUES), "category"
    )

    severity = answers["incident_severity"]
    if (
        not isinstance(severity, dict)
        or set(severity) != {"type", "score", "confidence", "probabilities"}
        or severity["type"] != "score"
        or isinstance(severity["score"], bool)
        or not isinstance(severity["score"], (int, float))
        or not math.isfinite(severity["score"])
        or not 0 <= severity["score"] <= len(SEVERITY_LEVELS) - 1
        or not _is_probability(severity["confidence"])
    ):
        raise ValueError(f"{prefix} has an invalid severity answer")
    severity_distribution = _validate_distribution(
        severity["probabilities"], set(range(len(SEVERITY_LEVELS))), "severity"
    )
    expected_score = sum(index * probability for index, probability in severity_distribution.items())
    if not math.isclose(float(severity["score"]), expected_score, rel_tol=0, abs_tol=0.05):
        raise ValueError(f"{prefix} severity score does not match its probability-weighted average")

    return {
        "case_id": record["case_id"],
        "prompt_version": result["prompt_version"],
        "security_probability": float(predicate["probability"]),
        "category_choice": category["choice"],
        "category_probabilities": category_distribution,
        "severity_score": float(severity["score"]),
        "severity_probabilities": severity_distribution,
    }


def load_jsonl(path: str | os.PathLike[str], kind: str) -> list[dict[str, Any]]:
    """Load strict dataset or normalized CLI-result JSONL records."""
    if kind not in {"dataset", "outputs"}:
        raise ValueError("kind must be 'dataset' or 'outputs'")
    records = _read_records(path, kind)
    checked: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if kind == "dataset":
            checked.append(_validate_case(record, index))
        else:
            _validate_result(record, index)
            checked.append(record)
    seen: set[str] = set()
    for record in checked:
        if record["case_id"] in seen:
            raise ValueError(f"duplicate case_id in {kind}: {record['case_id']}")
        seen.add(record["case_id"])
    return checked


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _brier(probabilities: dict[Any, float], expected_value: Any, labels: tuple[Any, ...]) -> float:
    return sum((probabilities[label] - float(label == expected_value)) ** 2 for label in labels)


def _roc_auc(binary_scores: list[tuple[bool, float]]) -> float | None:
    positives = [score for label, score in binary_scores if label]
    negatives = [score for label, score in binary_scores if not label]
    if not positives or not negatives:
        return None
    wins = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return wins / (len(positives) * len(negatives))


def evaluate_records(
    dataset: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    predicate_threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute independent classification and ordinal-severity diagnostics."""
    if not dataset:
        raise ValueError("dataset is empty")
    if not _is_probability(predicate_threshold):
        raise ValueError("predicate threshold must be between 0 and 1")
    cases_by_id: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(dataset, start=1):
        case = _validate_case(case, index)
        if case["case_id"] in cases_by_id:
            raise ValueError(f"duplicate case_id in dataset: {case['case_id']}")
        cases_by_id[case["case_id"]] = case
    outputs_by_id: dict[str, dict[str, Any]] = {}
    for index, output in enumerate(outputs, start=1):
        normalized = _validate_result(output, index)
        if normalized["case_id"] in outputs_by_id:
            raise ValueError(f"duplicate case_id in outputs: {normalized['case_id']}")
        outputs_by_id[normalized["case_id"]] = normalized
    missing = sorted(set(cases_by_id) - set(outputs_by_id))
    unexpected = sorted(set(outputs_by_id) - set(cases_by_id))
    if missing or unexpected:
        problems = []
        if missing:
            problems.append("missing output for case_id: " + ", ".join(missing))
        if unexpected:
            problems.append("output contains unknown case_id: " + ", ".join(unexpected))
        raise ValueError("; ".join(problems))

    dataset_versions = {case["prompt_version"] for case in cases_by_id.values()}
    if len(dataset_versions) != 1:
        raise ValueError("evaluate one prompt_version at a time; split mixed-version datasets into separate runs")
    dataset_version = next(iter(dataset_versions))
    mismatched_versions = sorted(
        case_id for case_id, output in outputs_by_id.items()
        if output["prompt_version"] != cases_by_id[case_id]["prompt_version"]
    )
    if mismatched_versions:
        raise ValueError("output prompt_version does not match dataset for case_id: " + ", ".join(mismatched_versions))

    security = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    security_scores: list[tuple[bool, float]] = []
    category_confusion = {expected: {predicted: 0 for predicted in CATEGORY_VALUES} for expected in CATEGORY_VALUES}
    category_support = {category: 0 for category in CATEGORY_VALUES}
    category_correct = {category: 0 for category in CATEGORY_VALUES}
    severity_abs_errors: list[float] = []
    severity_exact = 0
    severity_confusion = {
        label: {predicted_label: 0 for predicted_label, _ in SEVERITY_LEVELS}
        for label, _ in SEVERITY_LEVELS
    }
    severity_support = {label: 0 for label, _ in SEVERITY_LEVELS}
    severity_correct = {label: 0 for label, _ in SEVERITY_LEVELS}
    security_brier: list[float] = []
    category_brier: list[float] = []
    severity_brier: list[float] = []
    label_status_counts: dict[str, int] = {}
    cases = []

    for case_id, case in cases_by_id.items():
        expected = case["expected"]
        output = outputs_by_id[case_id]
        expected_security = expected["confirmed_security_impact"]
        predicted_security = output["security_probability"] >= predicate_threshold
        confusion_key = (
            "tp" if expected_security and predicted_security else
            "fn" if expected_security else
            "fp" if predicted_security else "tn"
        )
        security[confusion_key] += 1
        security_brier.append((output["security_probability"] - float(expected_security)) ** 2)
        security_scores.append((expected_security, output["security_probability"]))

        expected_category = expected["incident_category"]
        predicted_category = output["category_choice"]
        category_support[expected_category] += 1
        category_confusion[expected_category][predicted_category] += 1
        if expected_category == predicted_category:
            category_correct[expected_category] += 1
        category_brier.append(_brier(output["category_probabilities"], expected_category, CATEGORY_VALUES))

        expected_severity = expected["incident_severity"]
        predicted_level = min(len(SEVERITY_LEVELS) - 1, math.floor(output["severity_score"] + 0.5))
        expected_severity_label = SEVERITY_LEVELS[expected_severity][0]
        predicted_severity_label = SEVERITY_LEVELS[predicted_level][0]
        severity_support[expected_severity_label] += 1
        severity_confusion[expected_severity_label][predicted_severity_label] += 1
        if expected_severity == predicted_level:
            severity_correct[expected_severity_label] += 1
        absolute_error = abs(output["severity_score"] - expected_severity)
        severity_abs_errors.append(absolute_error)
        severity_exact += int(predicted_level == expected_severity)
        severity_brier.append(
            _brier(
                output["severity_probabilities"],
                expected_severity,
                tuple(range(len(SEVERITY_LEVELS))),
            )
        )

        label_status = case["label_status"]
        label_status_counts[label_status] = label_status_counts.get(label_status, 0) + 1
        cases.append({
            "case_id": case_id,
            "label_status": label_status,
            "expected": expected,
            "predicted": {
                "confirmed_security_impact": predicted_security,
                "security_probability": output["security_probability"],
                "incident_category": predicted_category,
                "incident_severity_level": predicted_level,
                "incident_severity_score": output["severity_score"],
            },
        })

    category_total = len(cases)
    category_recall = [_ratio(category_correct[label], category_support[label]) for label in CATEGORY_VALUES]
    supported_recalls = [value for value in category_recall if value is not None]
    severity_recall = [
        _ratio(severity_correct[label], severity_support[label]) for label, _ in SEVERITY_LEVELS
    ]
    supported_severity_recalls = [value for value in severity_recall if value is not None]
    security_precision = _ratio(security["tp"], security["tp"] + security["fp"])
    security_recall = _ratio(security["tp"], security["tp"] + security["fn"])
    security_f1 = (
        None if security_precision is None or security_recall is None or security_precision + security_recall == 0
        else 2 * security_precision * security_recall / (security_precision + security_recall)
    )
    return {
        "model": MODEL,
        "prompt_version": dataset_version,
        "case_count": len(cases),
        "predicate_threshold": predicate_threshold,
        "label_status_counts": dict(sorted(label_status_counts.items())),
        "expert_reviewed_case_count": label_status_counts.get("expert_reviewed", 0),
        "all_labels_expert_reviewed": (
            label_status_counts.get("expert_reviewed", 0) == len(cases)
        ),
        "security_impact": {
            "confusion_matrix": security,
            "accuracy": _ratio(security["tp"] + security["tn"], len(cases)),
            "precision": security_precision,
            "recall": security_recall,
            "f1": security_f1,
            "roc_auc": _roc_auc(security_scores),
            "brier_score": sum(security_brier) / len(security_brier),
        },
        "category": {
            "top1_accuracy": _ratio(sum(category_correct.values()), category_total),
            "macro_recall_supported_categories": (
                sum(supported_recalls) / len(supported_recalls) if supported_recalls else None
            ),
            "support_by_category": category_support,
            "confusion_matrix": category_confusion,
            "multiclass_brier_score": sum(category_brier) / len(category_brier),
        },
        "severity": {
            "exact_accuracy": severity_exact / len(cases),
            "mean_absolute_error": sum(severity_abs_errors) / len(severity_abs_errors),
            "macro_recall_supported_levels": (
                sum(supported_severity_recalls) / len(supported_severity_recalls)
                if supported_severity_recalls else None
            ),
            "support_by_level": severity_support,
            "confusion_matrix": severity_confusion,
            "multiclass_brier_score": sum(severity_brier) / len(severity_brier),
        },
        "production_readiness_established": False,
        "limitations": [
            "This report evaluates only the saved outputs and supplied labels; it makes no model calls.",
            "The 0.5 predicate threshold is diagnostic, not an approved production threshold.",
            "Synthetic or unreviewed labels cannot establish real-world model quality.",
            "Metrics do not authorize automated routing, paging, remediation, or deployment actions.",
        ],
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        help="annotated reference cases in strict JSONL format (review labels before quality claims)",
    )
    parser.add_argument("--outputs", required=True, help="saved normalized Decisions results in JSONL format")
    parser.add_argument(
        "--predicate-threshold",
        type=float,
        default=0.5,
        help="diagnostic threshold for the security predicate (default: 0.5; not a production setting)",
    )
    args = parser.parse_args(argv)
    try:
        dataset = load_jsonl(args.dataset, "dataset")
        outputs = load_jsonl(args.outputs, "outputs")
        result = evaluate_records(dataset, outputs, args.predicate_threshold)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # fail closed without exposing untrusted record content
        print(f"error: unexpected evaluator failure ({error.__class__.__name__})", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

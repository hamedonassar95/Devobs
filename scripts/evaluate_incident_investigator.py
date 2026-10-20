#!/usr/bin/env python3
"""Offline, deterministic graders for incident-investigator report datasets.

This tool never calls an AI provider. Candidate reports are read as data and are
not executed. Its JSON output contains scores and case IDs only, never reports.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 2_000_000
MAX_ROWS = 1_000
MAX_OUTPUT_CHARS = 200_000
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
HYPOTHESIS_HEADING = "root cause hypotheses"
TESTS_HEADING = "recommended tests"
GRADER_NAMES = (
    "exact_failure_evidence",
    "cause_uncertainty",
    "confidence_calibration",
    "timeline_and_test_choice",
    "causal_relevance",
)

DATASET_KEYS = {"case_id", "prompt_version", "input", "reference"}
INPUT_KEYS = {
    "incident_run_id",
    "workflow",
    "observed_failure",
    "logs_available",
    "later_run",
    "unrelated_changes",
}
FAILURE_KEYS = {"job", "step"}
LATER_RUN_KEYS = {"run_id", "conclusion"}
REFERENCE_KEYS = {"source", "max_causal_hypothesis_confidence", "historical_score"}
OUTPUT_KEYS = {"case_id", "output_text"}

MISSING_LOG_PHRASES = (
    "logs unavailable",
    "logs are unavailable",
    "logs were unavailable",
    "unavailable logs",
    "no logs available",
    "logs are missing",
    "log data unavailable",
)
UNKNOWN_CAUSE_PHRASES = (
    "cause remains unknown",
    "cause is unknown",
    "cause unknown",
    "cause was undetermined",
    "undetermined cause",
    "cannot determine the cause",
    "cause cannot be determined",
    "not enough evidence to identify the cause",
    "cause cannot be established",
)
SUCCESS_PHRASES = ("succeeded", "successful", "successfully", "recovered")
CAUSAL_CAVEATS = (
    "unrelated",
    "no causal link",
    "cannot link",
    "not linked",
    "not supported",
    "not evidence",
    "does not establish",
)
RERUN_WORD = re.compile(r"\b(?:re[- ]?run|repeat(?:ed|ing)?|run again)\b", re.I)
POSITIVE_RERUN = re.compile(
    r"\b(?:recommend(?:s|ed|ation)?|should|must|next test(?: is| should be)?|"
    r"try|run)\b.{0,100}\b(?:re[- ]?run|repeat(?:ed|ing)?|run again)\b"
    r"|^\s*(?:re[- ]?run|repeat)\b",
    re.I,
)
NEGATED_RERUN = re.compile(
    r"\b(?:do not|don't|should not|shouldn't|must not|mustn't|never|avoid|no need to|"
    r"would be wrong to|not advisable to|not recommend(?:ed)?(?: to)?|"
    r"not necessary to|unnecessary to)\b.{0,100}\b(?:re[- ]?run|repeat(?:ed|ing)?|run again)\b"
    r"|\b(?:re[- ]?run|repeat(?:ed|ing)?|run again)\b.{0,80}"
    r"\b(?:is not recommended|is unnecessary|isn't needed|is not needed|is not necessary)\b",
    re.I,
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_regular_file(path: str | os.PathLike[str], label: str) -> str:
    file_path = Path(path)
    try:
        metadata = file_path.lstat()
    except OSError as error:
        raise ValueError(f"cannot read {label} file: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular file, not a symlink or special file")
    if metadata.st_size > MAX_FILE_BYTES:
        raise ValueError(f"{label} exceeds the {MAX_FILE_BYTES}-byte limit")
    try:
        return file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read {label} file: {error}") from error


def _validate_case(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"dataset line {line_number}"
    if not isinstance(record, dict) or set(record) != DATASET_KEYS:
        raise ValueError(f"{prefix} must contain exactly: {', '.join(sorted(DATASET_KEYS))}")
    case_id = record["case_id"]
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
        raise ValueError(f"{prefix} has an invalid case_id")
    if not isinstance(record["prompt_version"], str) or not record["prompt_version"].strip():
        raise ValueError(f"{prefix} prompt_version must be a non-empty string")

    inputs = record["input"]
    if not isinstance(inputs, dict) or set(inputs) != INPUT_KEYS:
        raise ValueError(f"{prefix} input must contain exactly: {', '.join(sorted(INPUT_KEYS))}")
    for key in ("incident_run_id", "workflow"):
        if not isinstance(inputs[key], str) or not inputs[key].strip():
            raise ValueError(f"{prefix} input.{key} must be a non-empty string")
    failure = inputs["observed_failure"]
    if not isinstance(failure, dict) or set(failure) != FAILURE_KEYS:
        raise ValueError(f"{prefix} input.observed_failure must contain job and step")
    if any(not isinstance(failure[key], str) or not failure[key].strip() for key in FAILURE_KEYS):
        raise ValueError(f"{prefix} failure job and step must be non-empty strings")
    if type(inputs["logs_available"]) is not bool:
        raise ValueError(f"{prefix} input.logs_available must be a boolean")

    later_run = inputs["later_run"]
    if later_run is not None:
        if not isinstance(later_run, dict) or set(later_run) != LATER_RUN_KEYS:
            raise ValueError(f"{prefix} input.later_run must contain run_id and conclusion")
        if any(not isinstance(later_run[key], str) or not later_run[key].strip() for key in LATER_RUN_KEYS):
            raise ValueError(f"{prefix} later_run fields must be non-empty strings")

    unrelated = inputs["unrelated_changes"]
    if not isinstance(unrelated, list) or any(not isinstance(value, str) or not value.strip() for value in unrelated):
        raise ValueError(f"{prefix} input.unrelated_changes must be an array of non-empty strings")

    reference = record["reference"]
    if not isinstance(reference, dict) or set(reference) != REFERENCE_KEYS:
        raise ValueError(f"{prefix} reference must contain exactly: {', '.join(sorted(REFERENCE_KEYS))}")
    if any(not isinstance(reference[key], str) or not reference[key].strip()
           for key in ("source", "historical_score")):
        raise ValueError(f"{prefix} reference source and historical_score must be non-empty strings")
    cap = reference["max_causal_hypothesis_confidence"]
    if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not math.isfinite(cap) or not 0 <= cap <= 1:
        raise ValueError(f"{prefix} reference confidence cap must be a number from 0 to 1")
    return record


def _validate_output(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"output line {line_number}"
    if not isinstance(record, dict) or set(record) != OUTPUT_KEYS:
        raise ValueError(f"{prefix} must contain exactly: {', '.join(sorted(OUTPUT_KEYS))}")
    if not isinstance(record["case_id"], str) or not CASE_ID.fullmatch(record["case_id"]):
        raise ValueError(f"{prefix} has an invalid case_id")
    output_text = record["output_text"]
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError(f"{prefix} output_text must be a non-empty string")
    if len(output_text) > MAX_OUTPUT_CHARS:
        raise ValueError(f"{prefix} output_text exceeds the {MAX_OUTPUT_CHARS}-character limit")
    return record


def load_jsonl(path: str | os.PathLike[str], kind: str) -> list[dict[str, Any]]:
    """Load strict JSONL records from a regular UTF-8 file."""
    if kind not in {"dataset", "outputs"}:
        raise ValueError("kind must be 'dataset' or 'outputs'")
    content = _read_regular_file(path, kind)
    if not content.strip():
        raise ValueError(f"{kind} is empty")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{kind} line {line_number} is blank; each line must be a JSON object")
        try:
            record = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"invalid {kind} JSON on line {line_number}: {error}") from error
        record = _validate_case(record, line_number) if kind == "dataset" else _validate_output(record, line_number)
        case_id = record["case_id"]
        if case_id in seen:
            raise ValueError(f"duplicate case_id in {kind}: {case_id}")
        seen.add(case_id)
        records.append(record)
        if len(records) > MAX_ROWS:
            raise ValueError(f"{kind} exceeds the {MAX_ROWS}-row limit")
    return records


def _section(report: str, name: str) -> str | None:
    lines = report.splitlines()
    start = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if not match:
            continue
        heading = match.group(1).strip().casefold()
        if heading == name:
            start = index + 1
        elif start is not None:
            end = index
            break
    return None if start is None else "\n".join(lines[start:end])


def _hypothesis_rows(report: str) -> list[tuple[str, float]]:
    section = _section(report, HYPOTHESIS_HEADING)
    if section is None:
        raise ValueError("Root Cause Hypotheses section is missing")
    rows: list[tuple[str, float]] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"\d+", cells[0]):
            continue
        if len(cells) < 3:
            raise ValueError("hypothesis table row has no confidence column")
        try:
            confidence = float(cells[2])
        except ValueError as error:
            raise ValueError("hypothesis confidence is not numeric") from error
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("hypothesis confidence must be between 0 and 1")
        rows.append((" | ".join(cells), confidence))
    if not 1 <= len(rows) <= 3:
        raise ValueError("report must contain between one and three ranked hypotheses")
    return rows


def _has_positive_rerun_recommendation(section: str) -> bool:
    for sentence in re.split(r"(?<=[.!?])\s+|\n+|(?<=;)\s+", section):
        if not RERUN_WORD.search(sentence):
            continue
        if NEGATED_RERUN.search(sentence):
            continue
        if POSITIVE_RERUN.search(sentence) or RERUN_WORD.search(sentence):
            return True
    return False


def grade_report(case: dict[str, Any], report: str) -> dict[str, dict[str, Any]]:
    """Return five deterministic rubric grades for one already-validated case."""
    case = _validate_case(case, 1)
    if not isinstance(report, str) or not report.strip():
        raise ValueError("candidate report must be a non-empty string")
    inputs = case["input"]
    reference = case["reference"]
    normalized = report.casefold()
    failure = inputs["observed_failure"]

    evidence_missing = [
        label for label in (failure["job"], failure["step"])
        if label.casefold() not in normalized
    ]
    grades: dict[str, dict[str, Any]] = {
        "exact_failure_evidence": {
            "passed": not evidence_missing,
            "reason": "observed job and step are both named" if not evidence_missing else
                      "missing observed evidence: " + ", ".join(evidence_missing),
        }
    }

    if inputs["logs_available"]:
        uncertainty_ok = True
        uncertainty_reason = "run logs are available; missing-log disclosure is not required"
    else:
        says_logs_missing = any(term in normalized for term in MISSING_LOG_PHRASES)
        says_cause_unknown = any(term in normalized for term in UNKNOWN_CAUSE_PHRASES)
        uncertainty_ok = says_logs_missing and says_cause_unknown
        missing_parts = []
        if not says_logs_missing:
            missing_parts.append("explicitly say the failed-run logs are unavailable")
        if not says_cause_unknown:
            missing_parts.append("state that the cause is unknown")
        uncertainty_reason = "missing evidence boundary is explicit" if uncertainty_ok else "; ".join(missing_parts)
    grades["cause_uncertainty"] = {"passed": uncertainty_ok, "reason": uncertainty_reason}

    try:
        rows = _hypothesis_rows(report)
        confidence_ok = all(row_confidence <= reference["max_causal_hypothesis_confidence"] for _, row_confidence in rows)
        confidence_reason = (
            f"all {len(rows)} hypothesis confidence values are within the {reference['max_causal_hypothesis_confidence']:.2f} cap"
            if confidence_ok else
            f"a hypothesis exceeds the {reference['max_causal_hypothesis_confidence']:.2f} cap"
        )
    except ValueError as error:
        rows = []
        confidence_ok = False
        confidence_reason = str(error)
    grades["confidence_calibration"] = {"passed": confidence_ok, "reason": confidence_reason}

    later_run = inputs["later_run"]
    if later_run is None:
        chronology_ok = True
        chronology_reason = "no later equivalent run is annotated for this case"
    else:
        later_id_present = later_run["run_id"].casefold() in normalized
        later_success = later_run["conclusion"].casefold() == "success" and any(term in normalized for term in SUCCESS_PHRASES)
        tests_section = _section(report, TESTS_HEADING)
        no_repeat = tests_section is not None and not _has_positive_rerun_recommendation(tests_section)
        chronology_ok = later_id_present and later_success and no_repeat
        reasons = []
        if not later_id_present:
            reasons.append("later equivalent run ID is missing")
        if not later_success:
            reasons.append("later successful outcome is missing")
        if tests_section is None:
            reasons.append("Recommended Tests section is missing")
        elif not no_repeat:
            reasons.append("report recommends repeating the already-successful workflow")
        chronology_reason = "later recovery is acknowledged without recommending a repeat" if chronology_ok else "; ".join(reasons)
    grades["timeline_and_test_choice"] = {"passed": chronology_ok, "reason": chronology_reason}

    relevance_ok = True
    for row, _ in rows:
        folded_row = row.casefold()
        for label in inputs["unrelated_changes"]:
            if label.casefold() in folded_row and not any(caveat in folded_row for caveat in CAUSAL_CAVEATS):
                relevance_ok = False
                break
        if not relevance_ok:
            break
    grades["causal_relevance"] = {
        "passed": relevance_ok,
        "reason": "unrelated changes are absent from hypotheses or explicitly disclaimed" if relevance_ok else
                  "an unrelated change is presented in a hypothesis without a causal caveat",
    }
    return grades


def evaluate_records(dataset: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Grade one candidate output for every dataset case; reject partial runs."""
    if not dataset:
        raise ValueError("dataset is empty")
    dataset_by_id: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(dataset, 1):
        checked_case = _validate_case(case, index)
        if checked_case["case_id"] in dataset_by_id:
            raise ValueError(f"duplicate case_id in dataset: {checked_case['case_id']}")
        dataset_by_id[checked_case["case_id"]] = checked_case
    outputs_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(outputs, 1):
        checked_output = _validate_output(record, index)
        if checked_output["case_id"] in outputs_by_id:
            raise ValueError(f"duplicate case_id in outputs: {checked_output['case_id']}")
        outputs_by_id[checked_output["case_id"]] = checked_output
    missing = sorted(set(dataset_by_id) - set(outputs_by_id))
    unexpected = sorted(set(outputs_by_id) - set(dataset_by_id))
    if missing or unexpected:
        problems = []
        if missing:
            problems.append("missing output for case_id: " + ", ".join(missing))
        if unexpected:
            problems.append("output contains unknown case_id: " + ", ".join(unexpected))
        raise ValueError("; ".join(problems))

    cases = []
    passed_count = 0
    total_count = 0
    version_totals: dict[str, dict[str, int]] = {}
    for case_id, case in dataset_by_id.items():
        graders = grade_report(case, outputs_by_id[case_id]["output_text"])
        passed = sum(1 for grade in graders.values() if grade["passed"])
        total = len(graders)
        passed_count += passed
        total_count += total
        version = case["prompt_version"]
        totals = version_totals.setdefault(version, {"case_count": 0, "passed_cases": 0, "passed_graders": 0, "grader_count": 0})
        totals["case_count"] += 1
        totals["passed_cases"] += int(passed == total)
        totals["passed_graders"] += passed
        totals["grader_count"] += total
        cases.append({
            "case_id": case_id,
            "prompt_version": case["prompt_version"],
            "passed_graders": passed,
            "total_graders": total,
            "pass_rate": passed / total,
            "passed": passed == total,
            "graders": graders,
        })
    prompt_versions = {
        version: {
            **totals,
            "pass_rate": totals["passed_graders"] / totals["grader_count"],
            "case_pass_rate": totals["passed_cases"] / totals["case_count"],
        }
        for version, totals in sorted(version_totals.items())
    }
    return {
        "dataset_case_count": len(dataset),
        "output_case_count": len(outputs),
        "case_count": len(cases),
        "grader_count": total_count,
        "passed_graders": passed_count,
        "pass_rate": passed_count / total_count,
        "cases_passed": sum(1 for case in cases if case["passed"]),
        "case_pass_rate": sum(1 for case in cases if case["passed"]) / len(cases),
        "prompt_versions": prompt_versions,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="version-controlled incident cases in strict JSONL format")
    parser.add_argument("--outputs", required=True, help="candidate reports in JSONL format, keyed by case_id")
    parser.add_argument("--minimum-pass-rate", type=float, default=1.0,
                        help="minimum aggregate grader pass rate required for exit status 0 (default: 1.0)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.minimum_pass_rate) or not 0 <= args.minimum_pass_rate <= 1:
        parser.error("--minimum-pass-rate must be between 0 and 1")
    try:
        dataset = load_jsonl(args.dataset, "dataset")
        outputs = load_jsonl(args.outputs, "outputs")
        result = evaluate_records(dataset, outputs)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["pass_rate"] < args.minimum_pass_rate:
        print(
            f"Evaluation failed: {result['pass_rate']:.1%} is below the "
            f"{args.minimum_pass_rate:.1%} minimum.",
            file=sys.stderr,
        )
        return 1
    print(f"Evaluation passed: {result['pass_rate']:.1%} meets the minimum.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

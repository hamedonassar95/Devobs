#!/usr/bin/env python3
"""Validate the pinned synthetic Decisions evaluation fixture without exposing rows."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs/ai/evaluation-policy-v1.json"
POLICY_KEYS = {
    "schema_version", "policy_version", "scope", "dataset_id", "dataset_path",
    "dataset_sha256", "max_bytes", "max_rows", "max_input_bytes", "label_status",
    "prompt_version", "allowed_categories", "severity_min", "severity_max",
    "production_gate",
}
ROW_KEYS = {"case_id", "expected", "input", "label_status", "prompt_version"}
EXPECTED_KEYS = {"confirmed_security_impact", "incident_category", "incident_severity"}
CASE_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,79}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
POLICY_VERSION = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
CURRENT_POLICY_VERSION = "devobs-ai-eval-synthetic-v1"


class DatasetValidationError(ValueError):
    """A fixed diagnostic that never includes dataset content."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DatasetValidationError("invalid_json")
        result[key] = value
    return result


def _validate_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise DatasetValidationError("invalid_policy")
    if (
        type(policy["schema_version"]) is not int
        or policy["schema_version"] != 1
        or not isinstance(policy["policy_version"], str)
        or not POLICY_VERSION.fullmatch(policy["policy_version"])
        or policy["policy_version"] != CURRENT_POLICY_VERSION
        or policy["scope"] != "synthetic fixture provenance and schema validation only"
        or policy["dataset_id"] != "decisions-triage-synthetic"
        or policy["dataset_path"] != "tests/fixtures/ai-evals/decisions-triage.jsonl"
        or not isinstance(policy["dataset_sha256"], str)
        or not SHA256.fullmatch(policy["dataset_sha256"])
        or policy["label_status"] != "synthetic_unreviewed"
        or policy["prompt_version"] != "decisions-triage-v1"
        or policy["allowed_categories"] != [
            "ci_cd", "deployment", "monitoring", "security", "data_store", "billing", "other"
        ]
        or type(policy["severity_min"]) is not int
        or policy["severity_min"] != 0
        or type(policy["severity_max"]) is not int
        or policy["severity_max"] != 4
        or policy["production_gate"] is not False
    ):
        raise DatasetValidationError("invalid_policy")
    if (
        type(policy["max_bytes"]) is not int
        or policy["max_bytes"] != 5_000_000
        or type(policy["max_rows"]) is not int
        or policy["max_rows"] != 100
        or type(policy["max_input_bytes"]) is not int
        or policy["max_input_bytes"] != 64_000
    ):
        raise DatasetValidationError("invalid_policy")
    return policy


def _parse_policy(raw: bytes) -> dict[str, Any]:
    try:
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, DatasetValidationError):
        raise DatasetValidationError("invalid_policy") from None
    return _validate_policy(policy)


def validate_dataset_bytes(raw: bytes, policy: dict[str, Any]) -> dict[str, Any]:
    policy = _validate_policy(policy)
    if not isinstance(raw, bytes) or len(raw) > policy["max_bytes"]:
        raise DatasetValidationError("dataset_too_large")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != policy["dataset_sha256"]:
        raise DatasetValidationError("dataset_digest_mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise DatasetValidationError("invalid_encoding") from None
    if not text or not text.endswith("\n"):
        raise DatasetValidationError("invalid_jsonl")

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            raise DatasetValidationError("invalid_jsonl")
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, DatasetValidationError):
            raise DatasetValidationError("invalid_json") from None
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise DatasetValidationError("invalid_row")
        rows.append(row)
        if len(rows) > policy["max_rows"]:
            raise DatasetValidationError("too_many_rows")

    seen: set[str] = set()
    for row in rows:
        case_id = row["case_id"]
        if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
            raise DatasetValidationError("invalid_case_id")
        if case_id in seen:
            raise DatasetValidationError("duplicate_case_id")
        seen.add(case_id)
        if row["label_status"] != policy["label_status"]:
            raise DatasetValidationError("invalid_label_status")
        if row["prompt_version"] != policy["prompt_version"]:
            raise DatasetValidationError("prompt_version_mismatch")
        input_text = row["input"]
        input_size = _utf8_length(input_text) if isinstance(input_text, str) else None
        if (
            not isinstance(input_text, str)
            or not input_text.strip()
            or input_size is None
            or input_size > policy["max_input_bytes"]
        ):
            raise DatasetValidationError("invalid_input")
        expected = row["expected"]
        if not isinstance(expected, dict) or set(expected) != EXPECTED_KEYS:
            raise DatasetValidationError("invalid_expected_label")
        if (
            type(expected["confirmed_security_impact"]) is not bool
            or expected["incident_category"] not in policy["allowed_categories"]
            or type(expected["incident_severity"]) is not int
            or not policy["severity_min"] <= expected["incident_severity"] <= policy["severity_max"]
        ):
            raise DatasetValidationError("invalid_expected_label")
    if not rows:
        raise DatasetValidationError("empty_dataset")
    return {
        "dataset_id": policy["dataset_id"],
        "policy_version": policy["policy_version"],
        "case_count": len(rows),
        "dataset_sha256": digest,
        "synthetic_only": True,
        "production_gate": False,
    }


def _utf8_length(value: str) -> int | None:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return None


def validate_repository_dataset(root: Path = ROOT) -> dict[str, Any]:
    policy_path = root / "docs/ai/evaluation-policy-v1.json"
    if policy_path.is_symlink() or not policy_path.is_file():
        raise DatasetValidationError("policy_file_unavailable")
    policy = _parse_policy(policy_path.read_bytes())
    dataset_path = root / policy["dataset_path"]
    if dataset_path.is_symlink() or not dataset_path.is_file():
        raise DatasetValidationError("dataset_file_unavailable")
    return validate_dataset_bytes(dataset_path.read_bytes(), policy)


def main() -> int:
    try:
        print(json.dumps(validate_repository_dataset(), sort_keys=True))
    except (DatasetValidationError, OSError) as error:
        code = error.args[0] if isinstance(error, DatasetValidationError) else "dataset_io_error"
        print(json.dumps({"error": code}, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

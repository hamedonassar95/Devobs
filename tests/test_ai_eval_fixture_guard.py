"""Offline contract tests for the pinned synthetic Decisions evaluation fixture."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts.validate_ai_eval_fixtures import (
    DatasetValidationError,
    validate_dataset_bytes,
    validate_repository_dataset,
)


ROOT = Path(__file__).resolve().parents[1]


def policy_for(raw: bytes) -> dict:
    return {
        "schema_version": 1,
        "policy_version": "devobs-ai-eval-synthetic-v1",
        "scope": "synthetic fixture provenance and schema validation only",
        "dataset_id": "decisions-triage-synthetic",
        "dataset_path": "tests/fixtures/ai-evals/decisions-triage.jsonl",
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "max_bytes": 5_000_000,
        "max_rows": 100,
        "max_input_bytes": 64_000,
        "label_status": "synthetic_unreviewed",
        "prompt_version": "decisions-triage-v1",
        "allowed_categories": ["ci_cd", "deployment", "monitoring", "security", "data_store", "billing", "other"],
        "severity_min": 0,
        "severity_max": 4,
        "production_gate": False,
    }


def case(case_id="synthetic-case") -> dict:
    return {
        "case_id": case_id,
        "expected": {
            "confirmed_security_impact": False,
            "incident_category": "monitoring",
            "incident_severity": 1,
        },
        "input": "Synthetic fixture only; no real incident data.",
        "label_status": "synthetic_unreviewed",
        "prompt_version": "decisions-triage-v1",
    }


def payload_for(*records: dict) -> bytes:
    return ("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n").encode()


class AIEvalFixtureGuardTests(unittest.TestCase):
    def test_pinned_repository_fixture_is_synthetic_and_versioned(self):
        report = validate_repository_dataset(ROOT)
        self.assertEqual(report["policy_version"], "devobs-ai-eval-synthetic-v1")
        self.assertEqual(report["dataset_id"], "decisions-triage-synthetic")
        self.assertEqual(report["case_count"], 28)
        self.assertEqual(len(report["dataset_sha256"]), 64)
        self.assertNotIn("input", report)

    def test_rejects_unregistered_content_digest(self):
        raw = payload_for(case())
        policy = policy_for(raw)
        policy["dataset_sha256"] = "0" * 64
        with self.assertRaisesRegex(DatasetValidationError, "dataset_digest_mismatch"):
            validate_dataset_bytes(raw, policy)

    def test_policy_limits_and_version_are_pre_registered(self):
        raw = payload_for(case())
        policy = policy_for(raw)
        policy["policy_version"] = "devobs-ai-eval-synthetic-v2"
        with self.assertRaisesRegex(DatasetValidationError, "invalid_policy"):
            validate_dataset_bytes(raw, policy)

        policy = policy_for(raw)
        policy["max_rows"] = 101
        with self.assertRaisesRegex(DatasetValidationError, "invalid_policy"):
            validate_dataset_bytes(raw, policy)

    def test_rejects_non_synthetic_label_even_with_updated_digest(self):
        record = case()
        record["label_status"] = "expert_reviewed"
        raw = payload_for(record)
        with self.assertRaisesRegex(DatasetValidationError, "invalid_label_status"):
            validate_dataset_bytes(raw, policy_for(raw))

    def test_rejects_prompt_version_drift_and_duplicate_case_ids(self):
        wrong_prompt = case()
        wrong_prompt["prompt_version"] = "unregistered-v2"
        raw = payload_for(wrong_prompt)
        with self.assertRaisesRegex(DatasetValidationError, "prompt_version_mismatch"):
            validate_dataset_bytes(raw, policy_for(raw))

        raw = payload_for(case(), case())
        with self.assertRaisesRegex(DatasetValidationError, "duplicate_case_id"):
            validate_dataset_bytes(raw, policy_for(raw))

    def test_rejects_duplicate_json_keys_malformed_labels_and_oversized_payloads(self):
        duplicate_key = b'{"case_id":"one","case_id":"two"}\n'
        with self.assertRaisesRegex(DatasetValidationError, "invalid_json"):
            validate_dataset_bytes(duplicate_key, policy_for(duplicate_key))

        wrong_category = case()
        wrong_category["expected"]["incident_category"] = "deploy_prod"
        raw = payload_for(wrong_category)
        with self.assertRaisesRegex(DatasetValidationError, "invalid_expected_label"):
            validate_dataset_bytes(raw, policy_for(raw))

        oversized = b" " * 5_000_001
        with self.assertRaisesRegex(DatasetValidationError, "dataset_too_large"):
            validate_dataset_bytes(oversized, policy_for(oversized))


if __name__ == "__main__":
    unittest.main()

"""Behavior tests for the eight-category deterministic classifier."""
from __future__ import annotations

import unittest

from devobs.incidents.classification import classify_record
from devobs.incidents.ingestion import KIND_SANITIZED_CI_LOG, ingest_incident


class ClassificationTests(unittest.TestCase):
    def _classify(self, text: str, **metadata: str):
        record = ingest_incident({
            "kind": KIND_SANITIZED_CI_LOG,
            "incident_id": "inc-classify",
            "logs": [text],
            "metadata": metadata,
        })
        return record, classify_record(record)

    def test_dependency_and_test_categories_are_mapped_from_existing_rules(self) -> None:
        cases = (
            ("npm ERR! ERESOLVE", "DEPENDENCY_FAILURE"),
            ("AssertionError: expected 200", "TEST_FAILURE"),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                _, result = self._classify(text, job="unit")
                self.assertEqual(result.category, expected)
                self.assertEqual(result.confidence, "HIGH")
                self.assertTrue(result.evidence_ids)
                self.assertTrue(result.missing_information)
                self.assertTrue(result.diagnostic_step)

    def test_extended_categories_match_closed_rules(self) -> None:
        cases = (
            ("Invalid workflow file: unexpected key", "CI_CONFIGURATION_FAILURE"),
            ("docker build failed: failed to solve", "CONTAINER_BUILD_FAILURE"),
            ("Bad credentials for integration", "AUTHENTICATION_CONFIGURATION"),
            ("readiness probe failed for web", "SERVICE_HEALTH_FAILURE"),
            ("OOMKilled by runner", "INFRASTRUCTURE_CONFIGURATION"),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                _, result = self._classify(text)
                self.assertEqual(result.category, expected)
                self.assertTrue(result.diagnostic_step)
                self.assertTrue(result.missing_information)

    def test_generic_ci_failure_is_not_presented_as_high_confidence_config(self) -> None:
        record = ingest_incident({
            "kind": KIND_SANITIZED_CI_LOG,
            "logs": ["workflow check reported a problem"],
            "metadata": {"ci_overall_category": "ci_failure"},
        })
        result = classify_record(record)
        self.assertEqual(result.category, "CI_CONFIGURATION_FAILURE")
        self.assertEqual(result.confidence, "MEDIUM")
        self.assertIn("Workflow definition", " ".join(result.missing_information))

    def test_unknown_failure_is_explicit_and_low_confidence(self) -> None:
        _, result = self._classify("an unrecognized line")
        self.assertEqual(result.category, "UNKNOWN_FAILURE")
        self.assertEqual(result.confidence, "LOW")
        self.assertTrue(result.missing_information)
        self.assertIn("Collect additional sanitized evidence", result.diagnostic_step)

    def test_no_raw_secret_leaks_into_classification_metadata(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        _, result = self._classify(f"Bad credentials token={secret}")
        rendered = result.rationale + result.diagnostic_step + " ".join(result.missing_information)
        self.assertNotIn(secret, rendered)


if __name__ == "__main__":
    unittest.main()

"""Behavior tests for deterministic rule-based correlation."""
from __future__ import annotations

import unittest

from devobs.incidents.classification import classify_records
from devobs.incidents.ingestion import KIND_SANITIZED_CI_LOG, ingest_incident
from devobs.incidents.rca import correlate_incidents


def _record(incident_id: str, text: str, timestamp: str) -> object:
    return ingest_incident({
        "kind": KIND_SANITIZED_CI_LOG,
        "incident_id": incident_id,
        "timestamp": timestamp,
        "logs": [text],
        "metadata": {"job": "unit"},
    })


class CorrelationTests(unittest.TestCase):
    def test_repeated_signature_recurrence_and_symptom_link(self) -> None:
        records = tuple([
            _record("inc-a", "AssertionError: expected 200", "2026-11-21T10:00:00Z"),
            _record("inc-b", "AssertionError: expected 200", "2026-11-21T10:05:00Z"),
            _record("inc-c", "npm ERR! ERESOLVE", "2026-11-21T10:10:00Z"),
        ])
        findings = classify_records(records)
        report = correlate_incidents(records, findings)

        self.assertEqual(report.repeated_signatures[0].count, 2)
        self.assertEqual(report.repeated_signatures[0].incident_ids, ("inc-a", "inc-b"))
        relationships = {item.relationship for item in report.correlations}
        self.assertIn("repeated_signature", relationships)
        self.assertIn("recurring_category", relationships)
        self.assertIn("symptom_of", relationships)
        self.assertEqual(report.probable_cause_category, "DEPENDENCY_FAILURE")
        self.assertEqual(report.probable_cause_confidence, "HIGH")
        self.assertEqual(report.symptom_categories, ("TEST_FAILURE",))
        self.assertEqual([item.incident_id for item in report.timeline], ["inc-a", "inc-b", "inc-c"])

    def test_insufficient_evidence_never_becomes_a_verified_root_cause(self) -> None:
        records = tuple([_record("inc-unknown", "an unrecognized line", "2026-11-21T10:00:00Z")])
        report = correlate_incidents(records)
        self.assertEqual(report.probable_cause_category, "UNKNOWN_FAILURE")
        self.assertEqual(report.probable_cause_confidence, "LOW")
        self.assertIn("NO_CAUSE_CATEGORY_EVIDENCE", report.insufficient_evidence)
        self.assertIn("inc-unknown:LOW_CONFIDENCE", report.insufficient_evidence)

    def test_empty_input_is_safe_and_explicit(self) -> None:
        report = correlate_incidents(())
        self.assertEqual(report.incident_ids, ())
        self.assertEqual(report.probable_cause_category, "UNKNOWN_FAILURE")
        self.assertEqual(report.timeline, ())

    def test_result_does_not_depend_on_input_order(self) -> None:
        first = _record("inc-a", "AssertionError: expected 200", "2026-11-21T10:00:00Z")
        second = _record("inc-b", "npm ERR! ERESOLVE", "2026-11-21T10:05:00Z")
        left = correlate_incidents((first, second))
        right = correlate_incidents((second, first))
        self.assertEqual(left.incident_ids, right.incident_ids)
        self.assertEqual(left.repeated_signatures, right.repeated_signatures)
        self.assertEqual(left.probable_cause_category, right.probable_cause_category)
        self.assertEqual(left.timeline, right.timeline)


if __name__ == "__main__":
    unittest.main()

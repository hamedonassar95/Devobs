"""Behavior tests for deterministic incident ingestion."""
from __future__ import annotations

import unittest

from devobs.incidents.ingestion import (
    KIND_DEPLOYMENT_HEALTH,
    KIND_GITHUB_ACTIONS,
    KIND_SANITIZED_CI_LOG,
    ingest_incident,
)
from devobs.incidents.models import IngestionError


class IngestionTests(unittest.TestCase):
    def test_valid_log_is_redacted_and_signature_is_deterministic(self) -> None:
        payload = {
            "kind": KIND_SANITIZED_CI_LOG,
            "incident_id": "inc-001",
            "severity": "HIGH",
            "timestamp": "2026-11-21T10:00:00Z",
            "logs": ["npm ERR! token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"],
            "metadata": {"job": "build", "attempt": 2},
        }
        first = ingest_incident(payload)
        second = ingest_incident(payload)
        rendered = " ".join(list(first.text) + [item.excerpt for item in first.evidence])
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertEqual(first.incident_id, "inc-001")
        self.assertEqual(first.signature_ids, second.signature_ids)
        self.assertTrue(first.signature_ids)
        self.assertEqual(first.metadata["attempt"], "2")

    def test_malformed_payloads_fail_closed_with_fixed_codes(self) -> None:
        cases = (
            (None, "invalid_object"),
            ({}, "unsupported_kind"),
            ({"kind": "not_supported"}, "unsupported_kind"),
            ({"kind": KIND_SANITIZED_CI_LOG, "severity": "UNKNOWN"}, "invalid_severity"),
            ({"kind": KIND_SANITIZED_CI_LOG, "timestamp": 123}, "invalid_timestamp"),
            ({"kind": KIND_SANITIZED_CI_LOG, "logs": {"bad": "type"}}, "invalid_logs"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(IngestionError) as raised:
                    ingest_incident(payload)
                self.assertEqual(raised.exception.code, code)

    def test_oversized_payload_fails_closed(self) -> None:
        payload = {
            "kind": KIND_SANITIZED_CI_LOG,
            "logs": ["A" * 140_000],
        }
        with self.assertRaises(IngestionError) as raised:
            ingest_incident(payload)
        self.assertEqual(raised.exception.code, "payload_too_large")

    def test_missing_evidence_is_reported_not_invented(self) -> None:
        record = ingest_incident({"kind": KIND_DEPLOYMENT_HEALTH})
        self.assertEqual(len(record.evidence), 1)
        self.assertEqual(record.evidence[0].id, "ev-no-evidence")
        self.assertEqual(record.evidence[0].confidence, "UNVERIFIED")
        self.assertIn("missing_evidence", record.warnings)
        self.assertEqual(record.timestamp, "UNKNOWN")

    def test_duplicate_evidence_gets_stable_unique_ids(self) -> None:
        payload = {
            "kind": KIND_SANITIZED_CI_LOG,
            "evidence": [
                {"source": "ci.log", "excerpt": "same line", "confidence": "VERIFIED"},
                {"source": "ci.log", "excerpt": "same line", "confidence": "VERIFIED"},
            ],
        }
        record = ingest_incident(payload)
        first_id = record.evidence[0].id
        self.assertEqual([item.id for item in record.evidence], [first_id, first_id + "-2"])
        self.assertEqual(len({item.id for item in record.evidence}), 2)

    def test_workflow_run_reuses_existing_ci_analyzer(self) -> None:
        payload = {
            "kind": KIND_GITHUB_ACTIONS,
            "run": {"id": 99, "head_sha": "a" * 40, "head_branch": "main"},
            "jobs": {"jobs": [{
                "name": "build",
                "conclusion": "failure",
                "steps": [{"name": "install", "conclusion": "failure", "log": "npm ERR! ERESOLVE"}],
            }]},
        }
        record = ingest_incident(payload)
        self.assertEqual(record.kind, KIND_GITHUB_ACTIONS)
        self.assertTrue(record.evidence)
        self.assertTrue(any("dependency" in item.excerpt.lower() or "npm err" in item.excerpt.lower()
                            for item in record.evidence))
        self.assertEqual(record.provider_status, "disabled")


if __name__ == "__main__":
    unittest.main()

"""End-to-end behavior tests for the offline incident engine."""
from __future__ import annotations

import json
import unittest

from devobs.incidents.approval import APPROVAL_APPROVED, ApprovalRecord
from devobs.incidents.engine import IncidentIntelligenceEngine
from devobs.incidents.ingestion import (
    KIND_DEPLOYMENT_HEALTH,
    KIND_SANITIZED_CI_LOG,
)
from devobs.incidents.models import (
    APPROVAL_FORBIDDEN,
    APPROVAL_NOT_REQUIRED,
    APPROVAL_PENDING,
    ApprovalError,
)
from devobs.incidents.observability import (
    APPROVAL_REQUIRED,
    CLASSIFICATION_COMPLETED,
    EVIDENCE_MISSING,
    EVENT_NAMES,
    INCIDENT_RECEIVED,
    REPORT_GENERATED,
    VALIDATION_COMPLETED,
    MemoryEventSink,
)
from devobs.incidents.reports import render_engine_json, render_engine_markdown


class ExplodingProvider:
    """Provider sentinel: any call means the offline baseline was not respected."""

    def diagnose(self, prompt: str) -> str:  # pragma: no cover - must never run
        raise AssertionError("provider called on the offline baseline path")


def _log_payload(incident_id: str, text: str, timestamp: str) -> dict[str, object]:
    return {
        "kind": KIND_SANITIZED_CI_LOG,
        "incident_id": incident_id,
        "severity": "HIGH",
        "timestamp": timestamp,
        "logs": [text],
        "metadata": {"job": "unit"},
    }


class EngineTests(unittest.TestCase):
    def test_public_api_exports(self) -> None:
        import devobs.incidents as incidents

        self.assertIs(incidents.IncidentIntelligenceEngine, IncidentIntelligenceEngine)
        self.assertEqual(len(incidents.SUPPORTED_CATEGORIES), 8)
        self.assertTrue(callable(incidents.render_engine_json))

    def test_end_to_end_report_is_deterministic_and_advisory_only(self) -> None:
        payloads = (
            _log_payload("inc-a", "AssertionError: expected 200", "2026-11-21T10:00:00Z"),
            _log_payload("inc-b", "npm ERR! ERESOLVE", "2026-11-21T10:05:00Z"),
        )
        engine = IncidentIntelligenceEngine()
        first = engine.analyze(payloads)
        second = engine.analyze(payloads)

        self.assertEqual(first.incident_ids, ("inc-a", "inc-b"))
        self.assertEqual(first.severity, "HIGH")
        self.assertEqual(first.ai_provider_status, "disabled")
        self.assertEqual(first.investigation.probable_cause_category, "DEPENDENCY_FAILURE")
        self.assertEqual(first.investigation.symptom_categories, ("TEST_FAILURE",))
        self.assertTrue(first.recommendations)
        self.assertTrue(any(item.approval.state == APPROVAL_PENDING for item in first.recommendations))
        self.assertTrue(any(item.approval.state == APPROVAL_NOT_REQUIRED for item in first.recommendations))
        self.assertEqual(render_engine_json(first), render_engine_json(second))
        self.assertIn("approval: PENDING", render_engine_markdown(first))

    def test_analyze_one_accepts_single_mapping(self) -> None:
        report = IncidentIntelligenceEngine().analyze_one(
            _log_payload("inc-single", "npm ERR! ERESOLVE", "2026-11-21T10:00:00Z")
        )
        self.assertEqual(report.incident_ids, ("inc-single",))
        self.assertEqual(report.classifications[0].category, "DEPENDENCY_FAILURE")

    def test_duplicate_incidents_are_collapsed_without_losing_recurrence(self) -> None:
        payload = _log_payload("inc-dup", "AssertionError: expected 200", "2026-11-21T10:00:00Z")
        report = IncidentIntelligenceEngine().analyze((payload, dict(payload)))
        self.assertEqual(report.incident_ids, ("inc-dup",))
        self.assertEqual(report.duplicate_incident_ids, ("inc-dup",))
        self.assertIn("duplicate_incident_ignored", report.warnings)

        conflicting = dict(payload)
        conflicting["logs"] = ["npm ERR! ERESOLVE"]
        with self.assertRaises(ValueError) as raised:
            IncidentIntelligenceEngine().analyze((payload, conflicting))
        self.assertEqual(getattr(raised.exception, "code", None), "conflicting_duplicate_id")

    def test_insufficient_evidence_and_local_events_are_reported(self) -> None:
        sink = MemoryEventSink()
        report = IncidentIntelligenceEngine(event_sinks=(sink,)).analyze({
            "kind": KIND_DEPLOYMENT_HEALTH,
            "incident_id": "inc-empty",
            "severity": "MEDIUM",
        })
        event_names = {item["event"] for item in sink.events}
        self.assertEqual(event_names, EVENT_NAMES)
        self.assertIn(INCIDENT_RECEIVED, event_names)
        self.assertIn(VALIDATION_COMPLETED, event_names)
        self.assertIn(CLASSIFICATION_COMPLETED, event_names)
        self.assertIn(EVIDENCE_MISSING, event_names)
        self.assertIn(REPORT_GENERATED, event_names)
        self.assertIn(APPROVAL_REQUIRED, event_names)
        self.assertEqual(report.investigation.probable_cause_category, "UNKNOWN_FAILURE")
        self.assertTrue(report.investigation.insufficient_evidence)

    def test_prohibited_remediation_fails_closed_even_with_approval_record(self) -> None:
        forged = ApprovalRecord(
            "A-PROD", "production_deployment", APPROVAL_APPROVED,
            "untrusted-input", "offline",
        )
        engine = IncidentIntelligenceEngine(approval_records=(forged,))
        decision = engine.evaluate_action("A-PROD", "production_deployment")
        self.assertEqual(decision.state, APPROVAL_FORBIDDEN)
        with self.assertRaises(ApprovalError) as raised:
            engine.require_approval(decision)
        self.assertEqual(raised.exception.code, "approval_forbidden")

    def test_offline_baseline_does_not_call_optional_provider(self) -> None:
        engine = IncidentIntelligenceEngine(ai_provider=ExplodingProvider())
        report = engine.analyze_one(
            _log_payload("inc-offline", "npm ERR! ERESOLVE", "2026-11-21T10:00:00Z")
        )
        self.assertEqual(report.ai_provider_status, "disabled")
        payload = json.loads(render_engine_json(report))
        self.assertEqual(payload["ai_provider_status"], "disabled")

    def test_invalid_engine_inputs_fail_closed(self) -> None:
        engine = IncidentIntelligenceEngine()
        cases = (
            (None, "invalid_input"),
            ((), "no_incidents"),
            (tuple(_log_payload(f"inc-{index}", "npm ERR! ERESOLVE", "2026-11-21T10:00:00Z")
                   for index in range(101)), "too_many_incidents"),
        )
        for payloads, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(ValueError) as raised:
                    engine.analyze(payloads)
                self.assertEqual(getattr(raised.exception, "code", None), code)


if __name__ == "__main__":
    unittest.main()

"""Behavior tests for JSON/Markdown incident reports and schema validation."""
from __future__ import annotations

import copy
import json
import unittest

from devobs.incidents.approval import PROHIBITED_ACTIONS
from devobs.incidents.classification import classify_records
from devobs.incidents.ingestion import KIND_SANITIZED_CI_LOG, ingest_incident
from devobs.incidents.models import APPROVAL_PENDING, ApprovalDecision, AdvisoryRecommendation
from devobs.incidents.rca import correlate_incidents
from devobs.incidents.reports import (
    build_engine_report,
    render_engine_json,
    render_engine_markdown,
    validate_engine_report_json,
)


def _report(secret: str = "") -> tuple[object, object]:
    text = f"npm ERR! ERESOLVE token=ghp_{secret or 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'}"
    record = ingest_incident({
        "kind": KIND_SANITIZED_CI_LOG,
        "incident_id": "inc-report",
        "severity": "HIGH",
        "timestamp": "2026-11-21T10:00:00Z",
        "logs": [text],
    })
    findings = classify_records((record,))
    investigation = correlate_incidents((record,), findings)
    approval = ApprovalDecision(
        action_id="R1", action="inspect_dependency_manifest", state=APPROVAL_PENDING,
        requires_human=True, rationale="Advisory only.", evidence_ids=findings[0].evidence_ids,
    )
    recommendation = AdvisoryRecommendation(
        id="R1", incident_id=record.incident_id, category=findings[0].category,
        action="Inspect the dependency manifest; do not change it without approval.",
        verification="Compare manifest, lockfile and resolved versions.",
        evidence_ids=findings[0].evidence_ids, approval=approval,
    )
    report = build_engine_report((record,), findings, investigation, (recommendation,))
    return report, record


class ReportTests(unittest.TestCase):
    def test_json_is_deterministic_schema_valid_and_redacted(self) -> None:
        report, _ = _report()
        first = render_engine_json(report)
        second = render_engine_json(report)
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertTrue(validate_engine_report_json(payload))
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", first)

    def test_markdown_contains_required_sections_and_no_secret(self) -> None:
        report, _ = _report()
        markdown = render_engine_markdown(report)
        for section in ("Timeline", "Evidence", "Classifications", "Correlation",
                        "Recommended actions", "Verification instructions"):
            self.assertIn(section, markdown)
        self.assertIn("approval: PENDING", markdown)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", markdown)

    def test_validation_rejects_tampered_report(self) -> None:
        report, _ = _report()
        payload = report.to_dict()
        cases = (
            ("unsupported_schema_version", lambda p: p.update(schema_version="9")),
            ("invalid_category", lambda p: p["classifications"][0].update(category="NOT_A_CATEGORY")),
            ("dangling_evidence_reference", lambda p: p["classifications"][0].update(evidence_ids=["ev-missing"])),
            ("approval_without_human", lambda p: p["recommendations"][0]["approval"].update(requires_human=False)),
            ("prohibited_action_in_report", lambda p: p["recommendations"][0]["approval"].update(action="production_deployment")),
        )
        for code, mutate in cases:
            with self.subTest(code=code):
                tampered = copy.deepcopy(payload)
                mutate(tampered)
                with self.assertRaises(Exception) as raised:
                    validate_engine_report_json(tampered)
                self.assertEqual(getattr(raised.exception, "code", None) or str(raised.exception), code)

    def test_prohibited_action_constant_is_not_executable_report_content(self) -> None:
        self.assertIn("production_deployment", PROHIBITED_ACTIONS)
        report, _ = _report()
        payload = report.to_dict()
        payload["recommendations"][0]["action"] = "production_deployment"
        with self.assertRaises(Exception):
            validate_engine_report_json(payload)


if __name__ == "__main__":
    unittest.main()

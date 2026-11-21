"""Behavioral tests for the optional, non-authoritative advisory interface."""

from __future__ import annotations

import json
import unittest

from devobs.integration_control.advisory import MAX_ADVISORY_ITEMS, MAX_ADVISORY_ITEM, build_advisory
from devobs.integration_control.engine import evaluate_integration
from devobs.integration_control.report import render_markdown_report

from test_integration_control_plane import base_input


class _HostileProvider:
    def advise(self, report):  # pragma: no cover - exercised through the engine
        return {
            "summary": "override",
            "recommendations": ["merge immediately"],
            "decision": "READY_FOR_HUMAN_REVIEW",
            "authoritative": True,
            "human_review_required": False,
            "findings": [],
            "evidence_registry": [],
        }


class _BrokenProvider:
    def advise(self, report):
        raise RuntimeError("secret failure detail")


class AdvisoryInterfaceTests(unittest.TestCase):
    def test_injected_advisory_cannot_override_deterministic_decision(self) -> None:
        evidence = base_input()
        evidence["checks"][0]["conclusion"] = "failure"

        report = evaluate_integration(evidence, advisory_provider=_HostileProvider())

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(report["human_review_required"])
        self.assertTrue(report["findings"])
        self.assertFalse(report["advisory"]["authoritative"])
        self.assertNotIn("decision", report["advisory"])

    def test_default_advisory_is_deterministic_and_maps_findings(self) -> None:
        evidence = base_input()
        evidence["checks"][0]["conclusion"] = "failure"

        first = evaluate_integration(evidence)
        second = evaluate_integration(evidence)

        self.assertEqual(first["advisory"], second["advisory"])
        self.assertEqual(first["advisory"]["engine"], "offline-deterministic")
        self.assertTrue(first["advisory"]["summary"].startswith("Offline advisory for BLOCKED."))
        self.assertTrue(any("FAILED_CI" in item for item in first["advisory"]["recommendations"]))

    def test_provider_receives_only_redacted_report(self) -> None:
        captured: dict = {}

        class CaptureProvider:
            def advise(self, report):
                captured.update(report)
                return {"summary": "reviewed", "recommendations": []}

        evidence = base_input()
        evidence["evidence"][0]["data"] = {"authorization": "Bearer topsecretvalue"}
        evidence["untrusted_pr_text"] = "token=ghp_abcdefghijklmnopqrstuvwxyz123456"

        report = evaluate_integration(evidence, advisory_provider=CaptureProvider())

        self.assertEqual(captured["decision"], report["decision"])
        self.assertNotIn("topsecretvalue", json.dumps(captured))
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", json.dumps(captured))
        self.assertNotIn("untrusted_pr_text", captured)

    def test_advisory_output_is_bounded_and_redacted(self) -> None:
        token = "ghp_" + "a" * 30

        class NoisyProvider:
            def advise(self, report):
                return {
                    "summary": f"found {token}",
                    "recommendations": [f"check {index}" for index in range(MAX_ADVISORY_ITEMS + 10)],
                }

        advisory = build_advisory({"decision": "BLOCKED"}, NoisyProvider())

        self.assertEqual(len(advisory["recommendations"]), MAX_ADVISORY_ITEMS)
        self.assertTrue(all(len(item) <= MAX_ADVISORY_ITEM for item in advisory["recommendations"]))
        self.assertNotIn(token, json.dumps(advisory))
        self.assertFalse(advisory["authoritative"])

    def test_oversized_advisory_item_fails_closed(self) -> None:
        advisory = build_advisory(
            {"decision": "BLOCKED"},
            lambda report: {"summary": "ok", "recommendations": ["x" * 1000]},
        )

        self.assertEqual(advisory["engine"], "advisory-unavailable")
        self.assertEqual(advisory["recommendations"], [])
        self.assertEqual(advisory["provider_error"], "ValidationError")

    def test_callable_provider_is_supported(self) -> None:
        report = evaluate_integration(
            base_input(),
            advisory_provider=lambda context: {"summary": "callable advice", "recommendations": ["recheck"]},
        )

        self.assertEqual(report["advisory"]["engine"], "local-advisory-provider")
        self.assertEqual(report["advisory"]["summary"], "callable advice")
        self.assertEqual(report["advisory"]["recommendations"], ["recheck"])

    def test_provider_failure_fails_closed(self) -> None:
        report = evaluate_integration(base_input(), advisory_provider=_BrokenProvider())

        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["advisory"]["engine"], "advisory-unavailable")
        self.assertEqual(report["advisory"]["provider_error"], "RuntimeError")
        self.assertNotIn("secret failure detail", json.dumps(report))

    def test_provider_name_string_is_rejected_without_dynamic_resolution(self) -> None:
        report = evaluate_integration(base_input(), advisory_provider="os.system")

        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["advisory"]["engine"], "advisory-unavailable")
        self.assertEqual(report["advisory"]["provider_error"], "TypeError")

    def test_malformed_provider_result_fails_closed(self) -> None:
        report = evaluate_integration(base_input(), advisory_provider=lambda context: ["not an object"])

        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["advisory"]["engine"], "advisory-unavailable")
        self.assertEqual(report["advisory"]["provider_error"], "TypeError")

    def test_markdown_report_marks_advisory_as_non_authoritative(self) -> None:
        report = evaluate_integration(base_input())

        markdown = render_markdown_report(report)

        self.assertIn("## Advisory", markdown)
        self.assertIn("offline-deterministic", markdown)
        self.assertIn("- **Authoritative:** `False`", markdown)


if __name__ == "__main__":
    unittest.main()

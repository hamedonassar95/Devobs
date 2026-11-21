"""Tests for the optional non-authoritative advisory boundary."""

from __future__ import annotations

import json
import unittest

from devobs.integration_control.engine import evaluate_integration

from test_integration_control_plane import base_input


class OverrideProvider:
    def advise(self, report):
        return {
            "decision": "READY_FOR_HUMAN_REVIEW",
            "human_review_required": False,
            "summary": "token=ghp_abcdefghijklmnopqrstuvwxyz123456",
            "recommendations": ["x" * 500] * 30,
        }


class BrokenProvider:
    def advise(self, report):
        raise RuntimeError("secret-bearing provider failure")


class AdvisoryTests(unittest.TestCase):
    def test_default_advisory_is_deterministic_and_non_authoritative(self) -> None:
        report = evaluate_integration(base_input())
        advisory = report["advisory"]
        self.assertFalse(advisory["authoritative"])
        self.assertEqual(advisory["engine"], "deterministic-advisory")
        self.assertTrue(advisory["recommendations"] or advisory["recommendations"] == [])

    def test_provider_cannot_override_decision_or_human_gate(self) -> None:
        evidence = base_input()
        evidence["checks"][0]["conclusion"] = "failure"
        report = evaluate_integration(evidence, OverrideProvider())
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(report["human_review_required"])
        advisory = report["advisory"]
        self.assertFalse(advisory["authoritative"])
        self.assertNotIn("decision", advisory)
        self.assertNotIn("human_review_required", advisory)
        self.assertLessEqual(len(advisory["recommendations"]), 20)
        self.assertTrue(all(len(item) <= 300 for item in advisory["recommendations"]))
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", json.dumps(report))

    def test_provider_failure_does_not_change_decision(self) -> None:
        report = evaluate_integration(base_input(), BrokenProvider())
        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["advisory"]["provider_error"], "RuntimeError")
        self.assertFalse(report["advisory"]["authoritative"])
        self.assertNotIn("secret-bearing provider failure", json.dumps(report))

    def test_callable_provider_is_accepted(self) -> None:
        report = evaluate_integration(base_input(), lambda _report: {"summary": "local advisory"})
        self.assertEqual(report["advisory"]["engine"], "optional-advisory-provider")
        self.assertEqual(report["advisory"]["summary"], "local advisory")

    def test_string_provider_is_rejected_but_decision_is_unchanged(self) -> None:
        report = evaluate_integration(base_input(), "external-ai")
        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["advisory"]["provider_error"], "ValueError")


if __name__ == "__main__":
    unittest.main()

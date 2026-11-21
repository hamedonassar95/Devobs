"""Behavioral tests for the collect-then-evaluate integration boundary."""

from __future__ import annotations

import importlib
import json
import unittest

from test_integration_control_plane import base_input


class _UnavailableProvider:
    def collect(self, request):
        raise RuntimeError("provider offline")


class IntegrationPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        module = importlib.import_module("devobs.integration_control.pipeline")
        self.evaluate_collected_integration = module.evaluate_collected_integration
        self.request = {
            "repository": "hamedonassar95/Devobs",
            "pr_number": 10,
            "head_sha": "a" * 40,
        }

    def test_collected_snapshot_produces_ready_report(self) -> None:
        report = self.evaluate_collected_integration(base_input(), self.request)

        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["repository"]["name"], self.request["repository"])
        self.assertTrue(report["human_review_required"])

    def test_collection_failure_returns_fail_closed_report(self) -> None:
        report = self.evaluate_collected_integration(_UnavailableProvider(), self.request)

        self.assertEqual(report["decision"], "NEEDS_EVIDENCE")
        self.assertTrue(report["human_review_required"])
        self.assertTrue(any(f["code"] == "COLLECTION_UNAVAILABLE" for f in report["findings"]))
        self.assertNotIn("provider offline", json.dumps(report))

    def test_collection_failure_does_not_bypass_identity_binding(self) -> None:
        report = self.evaluate_collected_integration("os.system", self.request)

        self.assertEqual(report["decision"], "NEEDS_EVIDENCE")
        self.assertTrue(any(f["code"] == "COLLECTION_UNAVAILABLE" for f in report["findings"]))

    def test_public_api_exports_pipeline_and_advisory(self) -> None:
        package = importlib.import_module("devobs.integration_control")

        exported_names = (
            "collect_repository_state",
            "evaluate_collected_integration",
            "build_advisory",
            "DeterministicAdvisoryProvider",
        )
        for name in exported_names:
            self.assertTrue(hasattr(package, name), f"missing public export: {name}")


if __name__ == "__main__":
    unittest.main()

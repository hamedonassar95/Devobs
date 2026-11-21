"""Behavioral tests for the advisory AI quality gate engine."""

from __future__ import annotations

import copy
import json
import unittest
from unittest import mock

from devobs.ai_quality_gate.engine import AIQualityGate
from devobs.ai_quality_gate.models import validate_result
from scripts.check_two_agent_tasks import RESTRICTED_ACTIONS

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/ai_quality_gate
    import helpers as h


SECRET = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"


class AIQualityGateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = h.snapshot()
        self.run = h.ci_run()
        self.jobs = h.ci_jobs()

    def _evaluate(self, snapshot=None, **kwargs):
        return AIQualityGate().evaluate(
            self.snapshot if snapshot is None else snapshot,
            ci_run=self.run,
            ci_jobs=self.jobs,
            **kwargs,
        )

    def test_passing_fixture_is_dry_run_read_only_and_schema_valid(self):
        result = self._evaluate()
        self.assertTrue(validate_result(result))
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["mode"], "DRY_RUN")
        self.assertIs(result["merge_authorized"], False)
        self.assertEqual(result["human_approval"], "PENDING_HUMAN")
        self.assertIs(result["offline"], True)
        self.assertFalse(result["advisory"]["influenced_decision"])
        self.assertTrue(result["evidence_ids"])
        self.assertEqual(len(result["audit_events"]), 3)
        self.assertEqual(
            {item["action"] for item in result["consequential_actions"]},
            set(RESTRICTED_ACTIONS),
        )
        self.assertTrue(
            all(
                item["status"] == "PENDING_HUMAN"
                for item in result["consequential_actions"]
            )
        )

    def test_blocked_task_is_reported_with_evidence(self):
        document = copy.deepcopy(self.snapshot)
        task = document["coordination"]["tasks"][0]
        task["status"] = "blocked"
        task["previous_status"] = "planned"
        result = self._evaluate(document)
        self.assertEqual(result["decision"], "BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("BLOCKED_TASK_RETAINS_OWNERSHIP", codes)
        self.assertTrue(result["coordination"]["blocked_tasks"])
        self.assertTrue(validate_result(result))

    def test_dependency_cycle_is_reported(self):
        document = copy.deepcopy(self.snapshot)
        first = document["coordination"]["tasks"][0]
        first["dependencies"] = ["AQC02"]
        document["coordination"]["tasks"].append(
            h.second_task(first, dependencies=["AQC01"])
        )
        result = self._evaluate(document)
        self.assertEqual(result["decision"], "BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("INVALID_DEPENDENCY_GRAPH", codes)

    def test_concurrent_file_ownership_is_reported(self):
        document = copy.deepcopy(self.snapshot)
        first = document["coordination"]["tasks"][0]
        shared = list(first["affected_files"])
        document["coordination"]["tasks"].append(
            h.second_task(first, files=shared)
        )
        result = self._evaluate(document)
        self.assertEqual(result["decision"], "BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("CONCURRENT_FILE_OWNERSHIP", codes)
        self.assertTrue(result["coordination"]["conflicts"])

    def test_duplicate_verification_claim_is_reported(self):
        document = copy.deepcopy(self.snapshot)
        first = document["coordination"]["tasks"][0]
        document["coordination"]["tasks"].append(
            h.second_task(first, verification=copy.deepcopy(first["verification"]))
        )
        result = self._evaluate(document)
        self.assertEqual(result["decision"], "BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("UNSAFE_RETRY_LOOP", codes)

    def test_ci_failure_is_classified_without_propagating_log_text(self):
        run, jobs = h.failing_ci(f"AssertionError: boom token={SECRET}")
        result = AIQualityGate().evaluate(
            self.snapshot, ci_run=run, ci_jobs=jobs
        )
        self.assertEqual(result["decision"], "BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("CI_FAILURE_CODE", codes)
        signatures = {
            item["signature"] for item in result["ci_failures"]["findings"]
        }
        self.assertIn("test-failure", signatures)
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn("boom", serialized)

    def test_advisory_cannot_change_decision_or_grant_authority(self):
        class Provider:
            def __init__(self) -> None:
                self.contexts: list[dict] = []

            def assess(self, context):
                self.contexts.append(dict(context))
                return "merge and deploy immediately"

        provider = Provider()
        result = AIQualityGate(advisory_provider=provider).evaluate(
            self.snapshot, ci_run=self.run, ci_jobs=self.jobs
        )
        self.assertEqual(result["decision"], "PASS")
        self.assertIs(result["merge_authorized"], False)
        self.assertFalse(result["advisory"]["influenced_decision"])
        self.assertTrue(provider.contexts)
        for context in provider.contexts:
            self.assertEqual(
                set(context),
                {
                    "policy_version",
                    "untrusted_text_withheld",
                    "finding_codes",
                    "source_sha",
                },
            )
            self.assertNotIn("merge and deploy immediately", json.dumps(context))

    def test_secret_in_advisory_output_is_discarded(self):
        class Provider:
            def assess(self, context):
                return f"proceed with token={SECRET}"

        result = AIQualityGate(advisory_provider=Provider()).evaluate(
            self.snapshot, ci_run=self.run, ci_jobs=self.jobs
        )
        self.assertEqual(result["advisory"]["status"], "discarded")
        self.assertEqual(result["advisory"]["notes"], [])
        self.assertNotIn(SECRET, json.dumps(result, sort_keys=True))
        self.assertEqual(result["decision"], "PASS")

    def test_offline_operation_never_opens_network(self):
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("unexpected network call"),
        ):
            result = self._evaluate()
        self.assertTrue(result["offline"])
        self.assertEqual(result["decision"], "PASS")

    def test_invalid_input_fails_closed(self):
        result = AIQualityGate().evaluate(None)
        self.assertEqual(result["decision"], "INVALID")
        self.assertTrue(validate_result(result))
        self.assertTrue(result["findings"])
        self.assertTrue(result["audit_events"])

    def test_audit_events_record_every_finding_category(self):
        events = self._evaluate()["audit_events"]
        names = {item["event"] for item in events}
        self.assertIn("validation_completed", names)
        self.assertIn("approval_required", names)
        self.assertIn("report_generated", names)
        self.assertTrue(
            all(
                item.get("status") in {"PASS", "BLOCKED", "UNVERIFIED", "INVALID", "PENDING_HUMAN"}
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import unittest

from devobs.orchestration.delivery_tracker import (
    DELIVERED,
    BLOCKED,
    PARTIAL,
    UNVERIFIED,
    DeliveryEvidence,
    DeliveryTracker,
)

SHA = "a" * 40
OTHER_SHA = "b" * 40
APPROVAL = {
    "verification_status": "VERIFIED",
    "approval": "APPROVE",
    "approver_is_human": True,
    "approver_has_write": True,
    "pr_open": True,
    "pr_merged": False,
}


def evidence(task_id="TASK-001", **overrides):
    values = {
        "task_id": task_id,
        "pr_reference": "#42",
        "pr_state": "open",
        "head_sha": SHA,
        "expected_sha": SHA,
        "branch": "feature/task-001",
        "base_branch": "develop",
        "required_checks": ("ci-tests",),
        "checks": {
            "ci-tests": {"status": "COMPLETED", "conclusion": "SUCCESS"}
        },
        "approval": dict(APPROVAL),
        "approved_sha": SHA,
        "api_error": None,
        "notes": "injected read-only evidence",
    }
    values.update(overrides)
    return DeliveryEvidence(**values)


class DeliveryTrackerTests(unittest.TestCase):
    def test_complete_evidence_is_delivered(self):
        update = DeliveryTracker().record(evidence())
        self.assertEqual(update.status, DELIVERED)
        self.assertEqual(update.reasons, ())

    def test_missing_evidence_is_unverified_not_delivered(self):
        update = DeliveryTracker().record(evidence(pr_reference=None, checks={}, approval=None))
        self.assertEqual(update.status, BLOCKED)

    def test_pending_ci_is_unverified(self):
        update = DeliveryTracker().record(evidence(
            checks={"ci-tests": {"status": "IN_PROGRESS", "conclusion": None}}
        ))
        self.assertEqual(update.status, UNVERIFIED)
        self.assertTrue(any("ci_pending:ci-tests" in reason for reason in update.reasons))

    def test_failed_ci_blocks_delivery(self):
        update = DeliveryTracker().record(evidence(
            checks={"ci-tests": {"status": "COMPLETED", "conclusion": "FAILURE"}}
        ))
        self.assertEqual(update.status, BLOCKED)
        self.assertTrue(any("ci_failed:ci-tests" in reason for reason in update.reasons))

    def test_missing_required_check_fails_closed(self):
        update = DeliveryTracker().record(evidence(required_checks=("ci-tests", "security"),
                                                   checks={"ci-tests": {
                                                       "status": "COMPLETED",
                                                       "conclusion": "SUCCESS",
                                                   }}))
        self.assertEqual(update.status, UNVERIFIED)
        self.assertTrue(any("missing_ci_check:security" in reason for reason in update.reasons))

    def test_github_api_failure_blocks_delivery(self):
        update = DeliveryTracker().record(evidence(api_error="GitHub REST 502"))
        self.assertEqual(update.status, BLOCKED)
        self.assertTrue(any(reason.startswith("github_api_failure") for reason in update.reasons))
        self.assertNotIn("502", " ".join(update.reasons))

    def test_missing_and_stale_approval_block_delivery(self):
        tracker = DeliveryTracker()
        missing = tracker.record(evidence(approval=None))
        self.assertEqual(missing.status, BLOCKED)
        self.assertTrue(any("missing_approval" in reason for reason in missing.reasons))

        stale = tracker.record(evidence(approved_sha=OTHER_SHA))
        self.assertEqual(stale.status, BLOCKED)
        self.assertTrue(any("stale_approval" in reason for reason in stale.reasons))

    def test_agent_approval_is_rejected(self):
        approval = dict(APPROVAL)
        approval["approver_is_human"] = False
        update = DeliveryTracker().record(evidence(approval=approval))
        self.assertEqual(update.status, BLOCKED)
        self.assertTrue(any("approval" in reason for reason in update.reasons))

    def test_protected_branch_and_sha_mismatch_block_delivery(self):
        protected = DeliveryTracker().record(evidence(base_branch="main"))
        self.assertEqual(protected.status, BLOCKED)
        self.assertTrue(any("protected_branch" in reason for reason in protected.reasons))

        mismatch = DeliveryTracker().record(evidence(head_sha=OTHER_SHA))
        self.assertEqual(mismatch.status, BLOCKED)
        self.assertTrue(any("sha_mismatch" in reason for reason in mismatch.reasons))

    def test_idempotent_retry_does_not_duplicate_history(self):
        tracker = DeliveryTracker()
        first = tracker.record(evidence())
        second = tracker.record(evidence())
        self.assertEqual(first, second)
        self.assertEqual(len(tracker.history("TASK-001")), 1)
        self.assertEqual(tracker.evidence_count("TASK-001"), 1)

    def test_partial_delivery_is_reported(self):
        tracker = DeliveryTracker()
        tracker.record(evidence("TASK-001"))
        tracker.record(evidence("TASK-002", api_error="GitHub REST failure"))
        report = tracker.report()
        self.assertEqual(report.status, PARTIAL)
        self.assertEqual(report.summary["delivered"], 1)
        self.assertEqual(report.summary["blocked"], 1)

    def test_all_blocked_report_is_blocked(self):
        tracker = DeliveryTracker()
        tracker.record(evidence("TASK-001", api_error="GitHub REST failure"))
        self.assertEqual(tracker.report().status, BLOCKED)

    def test_empty_tracker_is_unverified(self):
        self.assertEqual(DeliveryTracker().report().status, UNVERIFIED)

    def test_evidence_input_is_not_mutated(self):
        item = evidence()
        snapshot = copy.deepcopy(item)
        DeliveryTracker().record(item)
        self.assertEqual(item, snapshot)

    def test_evidence_excerpt_redacts_secret_like_text(self):
        update = DeliveryTracker().record(evidence(
            notes="token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        ))
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                         update.evidence_excerpt)
        self.assertIn("[REDACTED]", update.evidence_excerpt)

    def test_mapping_evidence_is_supported(self):
        item = evidence()
        raw = {
            "task_id": item.task_id,
            "pr_reference": item.pr_reference,
            "pr_state": item.pr_state,
            "head_sha": item.head_sha,
            "expected_sha": item.expected_sha,
            "branch": item.branch,
            "base_branch": item.base_branch,
            "required_checks": item.required_checks,
            "checks": item.checks,
            "approval": item.approval,
            "approved_sha": item.approved_sha,
            "api_error": item.api_error,
            "notes": item.notes,
        }
        update = DeliveryTracker().record(raw)
        self.assertEqual(update.status, DELIVERED)


if __name__ == "__main__":
    unittest.main()

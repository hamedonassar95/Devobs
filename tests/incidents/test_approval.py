"""Behavior tests for explicit, advisory-only approval states."""
from __future__ import annotations

import unittest

from devobs.incidents.approval import ApprovalEngine, ApprovalRecord
from devobs.incidents.models import (
    APPROVAL_APPROVED,
    APPROVAL_FORBIDDEN,
    APPROVAL_NOT_REQUIRED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    ApprovalError,
)


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ApprovalEngine()

    def test_prohibited_actions_are_forbidden_even_with_approval_record(self) -> None:
        record = ApprovalRecord("A1", "production_deployment", APPROVAL_APPROVED, "owner", "offline")
        decision = self.engine.evaluate("A1", "production_deployment", records=(record,))
        self.assertEqual(decision.state, APPROVAL_FORBIDDEN)
        with self.assertRaises(ApprovalError) as raised:
            self.engine.require_approval(decision)
        self.assertEqual(raised.exception.code, "approval_forbidden")

    def test_remediation_defaults_to_pending(self) -> None:
        decision = self.engine.evaluate("A2", "update_dependency_pin", evidence_ids=("ev-1",))
        self.assertEqual(decision.state, APPROVAL_PENDING)
        self.assertTrue(decision.requires_human)
        with self.assertRaises(ApprovalError) as raised:
            self.engine.require_approval(decision)
        self.assertEqual(raised.exception.code, "approval_pending")

    def test_explicit_approval_must_match_action_scope_and_evidence(self) -> None:
        record = ApprovalRecord(
            "A3", "update_dependency_pin", APPROVAL_APPROVED, "owner", "repo:devobs",
            evidence_ids=("ev-1", "ev-2"),
        )
        matched = self.engine.evaluate(
            "A3", "update_dependency_pin", records=(record,),
            evidence_ids=("ev-1",), scope="repo:devobs",
        )
        self.assertEqual(matched.state, APPROVAL_APPROVED)
        mismatched = self.engine.evaluate(
            "A3", "update_dependency_pin", records=(record,),
            evidence_ids=("ev-3",), scope="repo:devobs",
        )
        self.assertEqual(mismatched.state, APPROVAL_PENDING)

    def test_diagnostic_step_needs_no_approval(self) -> None:
        decision = self.engine.evaluate("A4", "collect_sanitized_logs")
        self.assertEqual(decision.state, APPROVAL_NOT_REQUIRED)
        self.assertFalse(decision.requires_human)
        self.engine.require_approval(decision)

    def test_rejected_record_is_not_promoted(self) -> None:
        record = ApprovalRecord("A5", "update_dependency_pin", APPROVAL_REJECTED, "owner", "offline")
        decision = self.engine.evaluate("A5", "update_dependency_pin", records=(record,))
        self.assertEqual(decision.state, APPROVAL_REJECTED)
        with self.assertRaises(ApprovalError) as raised:
            self.engine.require_approval(decision)
        self.assertEqual(raised.exception.code, "approval_rejected")

    def test_incident_closure_requires_evidence_and_approval(self) -> None:
        forbidden = self.engine.evaluate("A6", "incident_closure")
        self.assertEqual(forbidden.state, APPROVAL_FORBIDDEN)
        approved = ApprovalRecord(
            "A6", "incident_closure", APPROVAL_APPROVED, "owner", "offline", ("ev-1",),
        )
        decision = self.engine.evaluate(
            "A6", "incident_closure", records=(approved,), evidence_ids=("ev-1",),
        )
        self.assertEqual(decision.state, APPROVAL_APPROVED)


if __name__ == "__main__":
    unittest.main()

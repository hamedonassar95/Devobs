from __future__ import annotations

import json
import socket
import subprocess
import unittest
from unittest import mock

from devobs.orchestration import work_orchestrator as orchestration_module
from devobs.orchestration.delivery_tracker import DeliveryEvidence, DeliveryTracker
from devobs.orchestration.task_registry import Task, TaskRegistry, ValidationError
from devobs.orchestration.work_orchestrator import CapacitySnapshot, WorkOrchestrator

REPO = "hamedonassar95/Devobs"
SHA = "a" * 40
APPROVAL = {
    "verification_status": "VERIFIED",
    "approval": "APPROVE",
    "approver_is_human": True,
    "approver_has_write": True,
    "pr_open": True,
    "pr_merged": False,
}


def task(task_id, **overrides):
    values = {
        "task_id": task_id,
        "owner": "CODEX",
        "branch": f"feature/{task_id.lower()}",
        "repository": REPO,
        "affected_files": (f"src/{task_id.lower()}.py",),
        "dependencies": (),
        "status": "planned",
        "previous_status": "none",
        "source_sha": None,
        "verification": {"commands": [], "result": "PENDING", "evidence": ""},
        "pr_reference": None,
        "requested_actions": ("code_change",),
    }
    values.update(overrides)
    return Task(**values)


def registry_with(*items):
    registry = TaskRegistry()
    for item in items:
        registry.add(item)
    return registry


def capacity(global_slots=4, **owner_slots):
    return CapacitySnapshot(
        global_slots=global_slots,
        owner_slots={"CODEX": 2, "OPENCODE": 2, **owner_slots},
        source="injected test capacity",
    )


class WorkOrchestratorTests(unittest.TestCase):
    def test_plans_dependency_ordered_dry_run_assignments(self):
        registry = registry_with(
            task("TASK-001"),
            task("TASK-002", dependencies=("TASK-001",), owner="OPENCODE"),
        )
        plan = WorkOrchestrator(registry, capacity()).plan()
        self.assertEqual(plan.decision, "PASS")
        self.assertEqual([item.task_id for item in plan.assignments],
                         ["TASK-001", "TASK-002"])
        self.assertEqual(plan.mode, "DRY_RUN")
        self.assertFalse(plan.dispatched)
        self.assertFalse(plan.apply)

    def test_global_capacity_exhaustion_blocks_second_task(self):
        registry = registry_with(
            task("TASK-001"),
            task("TASK-002", owner="OPENCODE"),
        )
        plan = WorkOrchestrator(registry, capacity(global_slots=1)).plan()
        self.assertEqual(plan.decision, "BLOCKED")
        self.assertEqual([item.task_id for item in plan.assignments], ["TASK-001"])
        self.assertTrue(any(item.reason == "capacity_exhausted" for item in plan.blocked))

    def test_owner_capacity_exhaustion_blocks_same_owner(self):
        registry = registry_with(
            task("TASK-001"),
            task("TASK-002", affected_files=("src/other.py",)),
        )
        plan = WorkOrchestrator(registry, capacity(CODEX=1)).plan()
        self.assertTrue(any(item.reason == "owner_capacity_exhausted"
                            for item in plan.blocked))

    def test_missing_owner_capacity_fails_closed(self):
        registry = registry_with(task("TASK-001"))
        snapshot = CapacitySnapshot(global_slots=2, owner_slots={}, source="injected")
        plan = WorkOrchestrator(registry, snapshot).plan()
        self.assertEqual(plan.decision, "BLOCKED")
        self.assertTrue(any(item.reason == "owner_capacity_unavailable"
                            for item in plan.blocked))

    def test_invalid_capacity_snapshot_fails_closed(self):
        registry = registry_with(task("TASK-001"))
        snapshot = CapacitySnapshot(global_slots=-1, owner_slots={}, source="injected")
        plan = WorkOrchestrator(registry, snapshot).plan()
        self.assertEqual(plan.decision, "FAIL")
        self.assertIn("invalid_capacity", plan.errors)

    def test_conflict_findings_block_scheduling(self):
        registry = registry_with(
            task("TASK-001", affected_files=("shared.py",)),
            task("TASK-002", owner="OPENCODE", affected_files=("shared.py",)),
        )
        plan = WorkOrchestrator(registry, capacity()).plan()
        self.assertEqual(plan.decision, "BLOCKED")
        self.assertEqual(plan.assignments, ())
        self.assertTrue(any(item.reason == "validator_conflict" for item in plan.blocked))

    def test_validator_failure_fails_closed(self):
        registry = registry_with(task("TASK-001"))
        with mock.patch.object(orchestration_module, "ConflictDetector") as detector:
            detector.return_value.evaluate.return_value.decision = "FAIL"
            detector.return_value.evaluate.return_value.errors = ("bad policy",)
            plan = WorkOrchestrator(registry, capacity()).plan()
        self.assertEqual(plan.decision, "FAIL")
        self.assertEqual(plan.errors, ("bad policy",))
        self.assertEqual(plan.assignments, ())

    def test_approval_actions_remain_pending_human(self):
        registry = registry_with(task("TASK-001"))
        plan = WorkOrchestrator(registry, capacity()).plan()
        self.assertEqual(set(plan.approval),
                         {"merge", "deploy", "billing", "production"})
        self.assertTrue(all(value == "pending_human" for value in plan.approval.values()))

    def test_protected_branch_is_rejected_before_planning(self):
        with self.assertRaises(ValidationError):
            registry_with(task("TASK-001", branch="main"))

    def test_observability_redacts_secret_like_text(self):
        registry = registry_with(task("TASK-001"))
        tracker = DeliveryTracker()
        tracker.record(DeliveryEvidence(
            task_id="TASK-001",
            pr_reference="#1",
            pr_state="open",
            head_sha=SHA,
            expected_sha=SHA,
            branch="feature/task-001",
            base_branch="develop",
            required_checks=("ci-tests",),
            checks={"ci-tests": {"status": "COMPLETED", "conclusion": "SUCCESS"}},
            approval=APPROVAL,
            approved_sha=SHA,
            notes="token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 and Bearer abc.def.ghi",
        ))
        payload = json.dumps(WorkOrchestrator(registry, capacity(), tracker).plan().to_dict())
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", payload)
        self.assertNotIn("abc.def.ghi", payload)
        self.assertIn("[REDACTED]", payload)

    def test_planning_does_not_open_sockets_or_subprocesses(self):
        registry = registry_with(task("TASK-001"))
        orchestrator = WorkOrchestrator(registry, capacity())
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")), \
             mock.patch.object(subprocess, "run", side_effect=AssertionError("process")), \
             mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process")):
            plan = orchestrator.plan()
        self.assertEqual(plan.decision, "PASS")

    def test_orchestrator_has_no_execution_entry_point(self):
        orchestrator = WorkOrchestrator(TaskRegistry(), capacity())
        for name in ("execute", "dispatch", "run", "apply", "merge", "deploy"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(orchestrator, name))

    def test_planning_does_not_mutate_registry(self):
        registry = registry_with(task("TASK-001"))
        before = [snapshot.version for snapshot in registry.list()]
        WorkOrchestrator(registry, capacity()).plan()
        self.assertEqual([snapshot.version for snapshot in registry.list()], before)


if __name__ == "__main__":
    unittest.main()

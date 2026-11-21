from __future__ import annotations

import copy
import unittest
from unittest import mock

from devobs.orchestration import conflict_detector as conflict_module
from devobs.orchestration.conflict_detector import ConflictDetector
from devobs.orchestration.task_registry import Task, TaskRegistry

REPO = "hamedonassar95/Devobs"
SHA = "a" * 40
RESTRICTED = ("merge", "deploy", "billing", "production")


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


def complete_task(task_id, **overrides):
    values = {
        "status": "complete",
        "previous_status": "evidence_ready",
        "source_sha": SHA,
        "verification": {
            "commands": ["python -m unittest discover -s tests -v"],
            "result": "PASS",
            "evidence": "local offline suite passed",
        },
        "pr_reference": "#123",
    }
    values.update(overrides)
    return task(task_id, **values)


def manifest(tasks, **overrides):
    value = {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {name: "pending_human" for name in RESTRICTED},
        "tasks": [item.to_manifest_record() for item in tasks],
    }
    value.update(overrides)
    return value


class ConflictDetectorTests(unittest.TestCase):
    def test_disjoint_tasks_return_pass(self):
        registry = TaskRegistry()
        registry.add(task("TASK-001"))
        registry.add(task("TASK-002", owner="OPENCODE"))
        report = ConflictDetector(registry).evaluate()
        self.assertEqual(report.decision, "PASS")
        self.assertEqual(report.findings, ())
        self.assertEqual(report.summary["tasks"], 2)

    def test_shared_file_conflict_is_reported_with_normalized_paths(self):
        registry = TaskRegistry()
        registry.add(task("TASK-001", affected_files=("scripts/shared.py",)))
        registry.add(task("TASK-002", owner="OPENCODE",
                          affected_files=("scripts\\shared.py",)))
        report = ConflictDetector(registry).evaluate()
        self.assertEqual(report.decision, "BLOCKED")
        finding = next(item for item in report.findings if item.kind == "conflict")
        self.assertEqual(finding.reason, "concurrent_file_ownership")
        self.assertEqual(finding.task_ids, ("TASK-001", "TASK-002"))
        self.assertEqual(finding.files, ("scripts/shared.py",))

    def test_shared_branch_conflict_is_reported(self):
        registry = TaskRegistry()
        registry.add(task("TASK-001", status="in_progress", previous_status="planned"))
        registry.add(task("TASK-002", owner="OPENCODE", branch="feature/task-001",
                          status="in_progress", previous_status="planned"))
        report = ConflictDetector(registry).evaluate()
        finding = next(item for item in report.findings
                       if item.reason == "concurrent_branch_ownership")
        self.assertEqual(finding.branches, ("feature/task-001",))

    def test_dependency_sequenced_shared_file_is_allowed(self):
        registry = TaskRegistry()
        registry.add(complete_task("TASK-001", affected_files=("shared/module.py",)))
        registry.add(task("TASK-002", owner="OPENCODE", dependencies=("TASK-001",),
                          affected_files=("shared/module.py",)))
        report = ConflictDetector(registry).evaluate()
        self.assertEqual(report.decision, "PASS")
        self.assertEqual(report.findings, ())

    def test_blocked_task_is_reported_and_blocks_dependent_work(self):
        registry = TaskRegistry()
        registry.add(task("TASK-001", status="blocked", previous_status="planned"))
        registry.add(task("TASK-002", owner="OPENCODE", dependencies=("TASK-001",)))
        report = ConflictDetector(registry).evaluate()
        self.assertEqual(report.decision, "BLOCKED")
        by_task = {}
        for finding in report.findings:
            for task_id in finding.task_ids:
                by_task.setdefault(task_id, []).append(finding.reason)
        self.assertIn("task_blocked", by_task["TASK-001"])
        self.assertIn("unresolved_dependency", by_task["TASK-002"])

    def test_invalid_manifest_fails_closed(self):
        data = manifest([task("TASK-001")])
        data["approval"]["merge"] = "agent_approved"
        report = ConflictDetector(data).evaluate()
        self.assertEqual(report.decision, "FAIL")
        self.assertTrue(report.errors)
        self.assertEqual(report.findings, ())

    def test_evaluation_does_not_mutate_source_manifest(self):
        data = manifest([task("TASK-001")])
        snapshot = copy.deepcopy(data)
        ConflictDetector(data).evaluate()
        self.assertEqual(data, snapshot)

    def test_unknown_validator_decision_fails_closed(self):
        with mock.patch.object(conflict_module, "evaluate",
                               return_value={"decision": "UNEXPECTED"}):
            report = ConflictDetector(manifest([task("TASK-001")])).evaluate()
        self.assertEqual(report.decision, "FAIL")
        self.assertEqual(report.errors, ("validator returned an unknown decision",))

    def test_validator_exception_fails_closed(self):
        with mock.patch.object(conflict_module, "evaluate", side_effect=RuntimeError("boom")):
            report = ConflictDetector(manifest([task("TASK-001")])).evaluate()
        self.assertEqual(report.decision, "FAIL")
        self.assertEqual(report.errors, ("validator failure: RuntimeError",))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from devobs.orchestration.task_registry import (
    DependencyError,
    DuplicateTaskError,
    StoreError,
    Task,
    TaskRegistry,
    TransitionError,
    ValidationError,
)


def sample_task(**changes):
    values = {
        "task_id": "TASK-001",
        "owner": "CODEX",
        "branch": "feature/task-001",
        "repository": "hamedonassar95/Devobs",
        "affected_files": ("src/module.py",),
        "dependencies": (),
        "status": "planned",
        "previous_status": "none",
        "source_sha": None,
        "verification": {"commands": [], "result": "PENDING", "evidence": ""},
        "pr_reference": None,
        "requested_actions": (),
    }
    values.update(changes)
    return Task(**values)


class TaskRegistryTests(unittest.TestCase):
    def test_add_rejects_duplicate_task_ids(self):
        registry = TaskRegistry()
        registry.add(sample_task())
        with self.assertRaises(DuplicateTaskError):
            registry.add(sample_task(owner="OPENCODE"))

    def test_add_rejects_missing_dependencies(self):
        registry = TaskRegistry()
        with self.assertRaises(DependencyError):
            registry.add(sample_task(dependencies=("TASK-999",)))

    def test_add_rejects_cyclic_dependencies(self):
        registry = TaskRegistry()
        registry.add(sample_task(task_id="TASK-001"))
        registry.add(sample_task(task_id="TASK-002", dependencies=("TASK-001",)))
        with self.assertRaises(DependencyError):
            registry.add(
                sample_task(
                    task_id="TASK-001",
                    branch="feature/task-001-updated",
                    dependencies=("TASK-002",),
                    status="planned",
                    previous_status="none",
                )
            )

    def test_illegal_status_transition_fails_closed(self):
        registry = TaskRegistry()
        registry.add(sample_task())
        with self.assertRaises(TransitionError):
            registry.update("TASK-001", {"status": "complete"})

    def test_idempotent_update_does_not_bump_version(self):
        registry = TaskRegistry()
        registry.add(sample_task())
        first = registry.update("TASK-001", {"status": "in_progress"})
        second = registry.update("TASK-001", {"status": "in_progress"})
        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(first.version, second.version)

    def test_stale_expected_version_is_rejected(self):
        registry = TaskRegistry()
        registry.add(sample_task())
        with self.assertRaises(StoreError):
            registry.update("TASK-001", {"status": "in_progress"}, expected_version=99)

    def test_evidence_ready_requires_source_sha(self):
        registry = TaskRegistry()
        registry.add(sample_task())
        with self.assertRaises(ValidationError):
            registry.update("TASK-001", {"status": "evidence_ready"})

    def test_rejects_unsafe_affected_file_paths(self):
        registry = TaskRegistry()
        with self.assertRaises(ValidationError):
            registry.add(sample_task(affected_files=("../secret.py",)))

    def test_state_survives_reload_and_writes_atomically(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "tasks.json"
            registry = TaskRegistry(path)
            registry.add(sample_task())
            registry.update("TASK-001", {"status": "in_progress"})

            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            self.assertEqual(payload["schema_version"], "orchestration/task-registry/v1")
            self.assertEqual(payload["tasks"][0]["status"], "in_progress")
            self.assertFalse(list(pathlib.Path(folder).glob("*.tmp")))

            reloaded = TaskRegistry(path)
            self.assertEqual(reloaded.get("TASK-001").task.status, "in_progress")
            self.assertEqual(reloaded.get("TASK-001").version, 2)

    def test_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "tasks.json"
            path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
            with self.assertRaises(StoreError):
                TaskRegistry(path)


if __name__ == "__main__":
    unittest.main()

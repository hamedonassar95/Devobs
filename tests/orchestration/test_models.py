"""Behavioral tests for immutable orchestration inputs and plan exports."""
import importlib
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "scripts", ROOT / "tools"):
    _path = str(_folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)


def load_module(name):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise AssertionError("missing module: " + name)
    return importlib.import_module(name)


class OrchestrationModelTests(unittest.TestCase):
    def test_task_spec_exports_the_canonical_manifest_shape(self):
        models = load_module("devobs.orchestration.models")
        task = models.TaskSpec(
            task_id="TASK-001",
            owner="CODEX",
            repository="hamedonassar95/Devobs",
            branch="feature/task-001",
            affected_files=("scripts/task_001.py",),
            dependencies=("TASK-000",),
        )
        record = task.to_manifest_record()
        self.assertEqual(set(record), set(models.MANIFEST_TASK_KEYS))
        self.assertEqual(record["assigned_agent"], "CODEX")
        self.assertEqual(record["dependencies"], ["TASK-000"])
        self.assertEqual(record["status"], "planned")
        self.assertEqual(record["verification"]["result"], "PENDING")

    def test_capacity_and_budget_defaults_fail_closed(self):
        models = load_module("devobs.orchestration.models")
        capacity = models.CapacitySnapshot(global_slots=0)
        budget = models.BudgetSnapshot()
        self.assertEqual(capacity.owner_slots, {})
        self.assertFalse(budget.approved)
        self.assertEqual(budget.max_provider_calls, 0)
        with self.assertRaises(models.ModelError):
            models.CapacitySnapshot(global_slots=True)
        with self.assertRaises(models.ModelError):
            models.BudgetSnapshot(spent_usd=-1)

    def test_plan_export_is_deterministic_sanitized_and_fingerprinted(self):
        models = load_module("devobs.orchestration.models")
        plan = models.Plan(
            assignments=(models.Assignment("TASK-001", "CODEX", "feature/task-001",
                                           (), ("scripts/task_001.py",), "dry_run"),),
            blocked=(),
            events=({"event": "plan_created",
                     "fields": {"note": "Bearer " + "SYNTHETIC123456789"}},),
            approvals={action: models.PENDING_HUMAN for action in models.RESTRICTED_ACTIONS},
            summary={"assignments": 1},
        )
        first = plan.to_dict()
        second = plan.to_dict()
        self.assertEqual(first, second)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(len(first["fingerprint"]), 64)
        self.assertFalse(first["dispatched"])
        self.assertFalse(first["apply"])
        self.assertEqual(first["mode"], models.MODE_DRY_RUN)
        self.assertNotIn("SYNTHETIC123456789", str(first))


if __name__ == "__main__":
    unittest.main()

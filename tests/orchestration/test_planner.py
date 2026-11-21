"""Behavioral tests for deterministic, capacity-bound DRY_RUN planning."""
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


REPO = "hamedonassar95/Devobs"


def task(task_id, *, dependencies=(), files=None, owner="CODEX", **extra):
    values = {
        "task_id": task_id,
        "owner": owner,
        "repository": REPO,
        "branch": "feature/" + task_id.lower().replace("_", "-"),
        "affected_files": tuple(files or (f"scripts/{task_id.lower()}.py",)),
        "dependencies": tuple(dependencies),
    }
    values.update(extra)
    return values


def planner(tasks, *, global_slots=20, owner_slots=None, supports_priority=False,
            budget=None, validator=None):
    models = load_module("devobs.orchestration.models")
    adapter = load_module("devobs.orchestration.policy_adapter")
    module = load_module("devobs.orchestration.planner")
    capacity = models.CapacitySnapshot(
        global_slots=global_slots,
        owner_slots=owner_slots if owner_slots is not None else {"CODEX": 20, "OPENCODE": 20},
        supports_priority=supports_priority,
    )
    kwargs = {}
    if validator is not None:
        kwargs["validator"] = validator
    return module.Planner(
        tuple(models.TaskSpec(**item) for item in tasks),
        capacity,
        adapter.load_policy(ROOT / "agent-spec.yaml"),
        budget or models.BudgetSnapshot(),
        **kwargs,
    )


class PlannerTests(unittest.TestCase):
    def test_unknown_dependency_and_cycle_fail_closed(self):
        models = load_module("devobs.orchestration.models")
        unknown = planner([task("TASK-001", dependencies=("TASK-404",))]).plan()
        self.assertEqual(unknown.decision, models.FAIL)
        self.assertTrue(unknown.errors)
        cyclic = planner([
            task("TASK-001", dependencies=("TASK-002",)),
            task("TASK-002", dependencies=("TASK-001",)),
        ]).plan()
        self.assertEqual(cyclic.decision, models.FAIL)
        self.assertEqual(cyclic.assignments, ())

    def test_dependency_order_is_deterministic_and_independent_of_input_order(self):
        models = load_module("devobs.orchestration.models")
        tasks = [
            task("TASK-004"),
            task("TASK-003", dependencies=("TASK-002",)),
            task("TASK-002", dependencies=("TASK-001",)),
            task("TASK-001"),
        ]
        first = [item.task_id for item in planner(tasks).plan().assignments]
        second = [item.task_id for item in planner(list(reversed(tasks))).plan().assignments]
        expected = ["TASK-001", "TASK-004", "TASK-002", "TASK-003"]
        self.assertEqual(first, expected)
        self.assertEqual(second, expected)

    def test_critical_path_priority_only_applies_when_supported(self):
        models = load_module("devobs.orchestration.models")
        tasks = [
            task("A_SOLO"),
            task("Z_LEAF", dependencies=("Z_MID",)),
            task("Z_MID", dependencies=("Z_ROOT",)),
            task("Z_ROOT"),
        ]
        lexical = [item.task_id for item in planner(
            tasks, global_slots=1, supports_priority=False).plan().assignments]
        critical = [item.task_id for item in planner(
            tasks, global_slots=1, supports_priority=True).plan().assignments]
        self.assertEqual(lexical, ["A_SOLO"])
        self.assertEqual(critical, ["Z_ROOT"])

    def test_capacity_exhaustion_blocks_without_partial_execution(self):
        models = load_module("devobs.orchestration.models")
        plan = planner(
            [task("TASK-001"), task("TASK-002", owner="OPENCODE")],
            global_slots=1,
        ).plan()
        self.assertEqual(plan.decision, models.BLOCKED)
        self.assertEqual(len(plan.assignments), 1)
        self.assertEqual([item.task_id for item in plan.blocked], ["TASK-002"])
        self.assertEqual(plan.blocked[0].reason, "capacity_exhausted")
        self.assertFalse(plan.to_dict()["dispatched"])

    def test_shared_file_ownership_conflict_blocks_both_tasks(self):
        models = load_module("devobs.orchestration.models")
        plan = planner([
            task("TASK-001", files=("shared/module.py",)),
            task("TASK-002", files=("shared/module.py",), owner="OPENCODE"),
        ]).plan()
        self.assertEqual(plan.decision, models.BLOCKED)
        self.assertEqual({item.task_id for item in plan.blocked},
                         {"TASK-001", "TASK-002"})
        self.assertTrue(all(item.reason == "ownership_conflict" for item in plan.blocked))

    def test_retry_classification_is_bound_to_policy_limits(self):
        models = load_module("devobs.orchestration.models")
        retryable = planner([
            task("TASK-001", failure_code="timeout", failure_attempt=1),
        ]).plan()
        self.assertEqual(retryable.assignments[0].reason, "retry_eligible")
        exhausted = planner([
            task("TASK-001", failure_code="timeout", failure_attempt=3),
        ]).plan()
        self.assertEqual(exhausted.decision, models.BLOCKED)
        self.assertEqual(exhausted.blocked[0].reason, "retry_limit_exhausted")
        terminal = planner([
            task("TASK-001", failure_code="validation_error", failure_attempt=1),
        ]).plan()
        self.assertEqual(terminal.blocked[0].reason, "terminal_failure")

    def test_policy_denial_blocks_billable_task(self):
        models = load_module("devobs.orchestration.models")
        plan = planner([
            task("TASK-001", provider_calls=1, estimated_cost_usd=0.25),
        ]).plan()
        self.assertEqual(plan.decision, models.BLOCKED)
        self.assertEqual(plan.blocked[0].reason, "policy_denied")
        self.assertIn("budget_approval_required", plan.blocked[0].detail)

    def test_unexpected_validator_shape_fails_closed(self):
        models = load_module("devobs.orchestration.models")
        plan = planner([task("TASK-001")], validator=lambda _: {"decision": "UNKNOWN"}).plan()
        self.assertEqual(plan.decision, models.FAIL)
        self.assertEqual(plan.assignments, ())
        self.assertTrue(plan.errors)

    def test_planner_has_no_execution_entry_point(self):
        module = load_module("devobs.orchestration.planner")
        for name in ("execute", "dispatch", "apply", "run", "merge", "deploy"):
            self.assertFalse(hasattr(module.Planner, name), name)


if __name__ == "__main__":
    unittest.main()

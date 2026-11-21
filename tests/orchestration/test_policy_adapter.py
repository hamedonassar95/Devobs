"""Behavioral tests for the read-only agent-spec policy adapter."""
import importlib
import importlib.util
import json
import pathlib
import sys
import tempfile
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


def task(**overrides):
    values = {
        "task_id": "TASK-001",
        "owner": "CODEX",
        "repository": "hamedonassar95/Devobs",
        "branch": "feature/task-001",
        "affected_files": ("scripts/task_001.py",),
    }
    values.update(overrides)
    return values


class PolicyAdapterTests(unittest.TestCase):
    def test_repository_spec_loads_with_fail_closed_guardrails(self):
        adapter = load_module("devobs.orchestration.policy_adapter")
        policy = adapter.load_policy(ROOT / "agent-spec.yaml")
        self.assertEqual(policy.max_retries, 3)
        self.assertFalse(policy.production_mutations_allowed)
        self.assertTrue(policy.production_mutations_require_human_approval)
        self.assertEqual(policy.budget_approval_variable, "DEVOBS_AI_BUDGET_APPROVED")
        self.assertFalse(policy.budget_approval_is_dollar_cap)
        self.assertTrue(policy.unmeasured_baseline_blocks_autonomous_production_use)
        self.assertIn("ai-code-review", policy.agents)

    def test_malformed_or_missing_spec_fails_closed(self):
        adapter = load_module("devobs.orchestration.policy_adapter")
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "agent-spec.json"
            path.write_text('{"schema_version": 1, "policy": {}}', encoding="utf-8")
            with self.assertRaises(adapter.PolicyError):
                adapter.load_policy(path)
        with self.assertRaises(adapter.PolicyError):
            adapter.load_policy(pathlib.Path(tempfile.gettempdir()) / "definitely-absent-orchestration-spec.json")

    def test_billable_work_requires_explicit_budget_approval(self):
        adapter = load_module("devobs.orchestration.policy_adapter")
        models = load_module("devobs.orchestration.models")
        policy = adapter.load_policy(ROOT / "agent-spec.yaml")
        spec = models.TaskSpec(**task(estimated_cost_usd=0.25, provider_calls=1))
        denied = adapter.evaluate_task(spec, policy, models.BudgetSnapshot())
        self.assertFalse(denied.allowed)
        self.assertIn("budget_approval_required", denied.reasons)
        approved = adapter.evaluate_task(
            spec, policy, models.BudgetSnapshot(approved=True, max_usd=1.0,
                                                max_provider_calls=2),
        )
        self.assertTrue(approved.allowed)
        self.assertEqual(approved.reasons, ())

    def test_budget_caps_and_unmeasured_cost_fail_closed(self):
        adapter = load_module("devobs.orchestration.policy_adapter")
        models = load_module("devobs.orchestration.models")
        policy = adapter.load_policy(ROOT / "agent-spec.yaml")
        over_cost = models.TaskSpec(**task(estimated_cost_usd=2.0, provider_calls=1))
        result = adapter.evaluate_task(
            over_cost, policy,
            models.BudgetSnapshot(approved=True, max_usd=1.0, max_provider_calls=5),
        )
        self.assertIn("budget_exceeded", result.reasons)
        unknown = models.TaskSpec(**task(provider_calls=1))
        result = adapter.evaluate_task(
            unknown, policy,
            models.BudgetSnapshot(approved=True, max_usd=1.0, max_provider_calls=5),
        )
        self.assertIn("unmeasured_cost_blocks_cap_enforcement", result.reasons)

    def test_production_mutation_is_denied_by_current_spec(self):
        adapter = load_module("devobs.orchestration.policy_adapter")
        models = load_module("devobs.orchestration.models")
        policy = adapter.load_policy(ROOT / "agent-spec.yaml")
        spec = models.TaskSpec(**task(requested_actions=("code_change", "production")))
        result = adapter.evaluate_task(
            spec, policy,
            models.BudgetSnapshot(approved=True, max_usd=100.0, max_provider_calls=5),
        )
        self.assertFalse(result.allowed)
        self.assertIn("production_mutation_not_allowed", result.reasons)


if __name__ == "__main__":
    unittest.main()

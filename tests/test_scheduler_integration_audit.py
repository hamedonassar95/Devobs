"""Non-invasive contract audit for ResourceConstrainedScheduler integration.

This test suite inspects repository state and existing contracts. It does not
import or execute any unverified scheduler ZIP package and does not modify
production scheduler code.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from agent_dispatch_preflight import build_preflight  # noqa: E402
from check_two_agent_tasks import evaluate  # noqa: E402

REPO = "hamedonassar95/Devobs"
RESTRICTED = ("merge", "deploy", "billing", "production")


def _manifest(tasks, **overrides):
    base = {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {key: "pending_human" for key in RESTRICTED},
        "tasks": tasks,
    }
    base.update(overrides)
    return base


def _task(task_id, **overrides):
    base = {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": "CODEX",
        "branch": f"feature/{task_id.lower()}",
        "affected_files": [f"docs/{task_id.lower()}.md"],
        "dependencies": [],
        "status": "planned",
        "previous_status": "none",
        "source_sha": None,
        "verification": {"commands": [], "result": "PENDING", "evidence": ""},
        "pr_reference": None,
        "requested_actions": ["documentation"],
    }
    base.update(overrides)
    return base


class SchedulerIntegrationAuditTests(unittest.TestCase):
    def test_required_scheduler_artifacts_absent_on_audited_tree(self):
        self.assertFalse((ROOT / "devobs" / "scheduling").exists())
        self.assertFalse((ROOT / "docs" / "agents" / "RESOURCE_SCHEDULER.md").exists())
        self.assertFalse((ROOT / "tests" / "test_resource_scheduler.py").exists())

    def test_no_resource_constrained_scheduler_symbol_in_repo(self):
        proc = subprocess.run(
            ["git", "grep", "-n", "ResourceConstrainedScheduler", "--", "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        # This audit adds the symbol in its own report/test; ignore those paths.
        lines = [
            line for line in proc.stdout.splitlines()
            if "docs/agents/SCHEDULER_INTEGRATION_AUDIT.md" not in line
            and "tests/test_scheduler_integration_audit.py" not in line
        ]
        self.assertEqual(lines, [])

    def test_dependency_validator_blocks_cycles_and_missing_deps(self):
        missing = evaluate(_manifest([
            _task("TASK-001", dependencies=["TASK-999"]),
        ]))
        self.assertEqual(missing["decision"], "FAIL")
        self.assertIn("dependency references an unknown task", missing["errors"])

        cycle = evaluate(_manifest([
            _task("TASK-001", dependencies=["TASK-002"]),
            _task("TASK-002", dependencies=["TASK-001"]),
        ]))
        self.assertEqual(cycle["decision"], "FAIL")
        self.assertIn("dependency cycle", cycle["errors"])

    def test_dependency_validator_blocks_file_and_branch_conflicts(self):
        file_conflict = evaluate(_manifest([
            _task("TASK-001", status="in_progress", previous_status="planned", affected_files=["shared.py"]),
            _task("TASK-002", assigned_agent="OPENCODE", status="in_progress", previous_status="planned", affected_files=["shared.py"]),
        ]))
        self.assertEqual(file_conflict["decision"], "BLOCKED")
        self.assertTrue(any(c["reason"] == "concurrent_file_ownership" for c in file_conflict["conflicts"]))

        branch_conflict = evaluate(_manifest([
            _task("TASK-001", status="in_progress", previous_status="planned", branch="feature/same"),
            _task("TASK-002", assigned_agent="OPENCODE", status="in_progress", previous_status="planned", branch="feature/same"),
        ]))
        self.assertEqual(branch_conflict["decision"], "BLOCKED")
        self.assertTrue(any(c["reason"] == "concurrent_branch_ownership" for c in branch_conflict["conflicts"]))

    def test_human_approval_and_restricted_actions_fail_closed(self):
        bad_approval = _manifest([_task("TASK-001")])
        bad_approval["approval"]["merge"] = "approved"
        result = evaluate(bad_approval)
        self.assertEqual(result["decision"], "FAIL")

        restricted = evaluate(_manifest([
            _task("TASK-001", requested_actions=["documentation", "deploy"]),
        ]))
        self.assertEqual(restricted["decision"], "FAIL")
        self.assertIn("merge, deploy, billing and production need separate human approval", restricted["errors"])

    def test_dispatch_preflight_is_dry_run_only_and_never_dispatches(self):
        manifest = _manifest([_task("TASK-001")])
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = build_preflight(manifest, pathlib.Path(tmp) / "instructions", which=lambda _: "codex")
        self.assertEqual(result["mode"], "DRY_RUN")
        self.assertFalse(result["dispatched"])
        self.assertEqual(result["decision"], "PASS")
        ids = [a["id"] for a in result["human_approval_actions"]]
        self.assertIn("KEEP_RESTRICTED_APPROVALS_PENDING", ids)
        self.assertIn("PHASE_8_APPROVAL", ids)

    def test_no_production_scheduler_files_changed_by_audit_contract(self):
        # Contract-level guard: audit may add only doc/test/readme files.
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        changed = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            # porcelain: XY path
            path = line[3:].strip().replace("\\", "/")
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.append(path)
        allowed_prefixes = ("docs/agents/", "tests/", "README.md")
        for path in changed:
            self.assertTrue(
                path == "README.md" or path.startswith("docs/agents/SCHEDULER_INTEGRATION_AUDIT") or path.startswith("tests/test_scheduler_integration_audit"),
                f"unexpected changed path: {path}",
            )
        self.assertFalse(any(p.startswith("devobs/scheduling/") for p in changed))
        self.assertFalse(any(p.startswith(".github/workflows/") for p in changed))
        self.assertFalse(any(p.startswith("scripts/") and "scheduler" in p for p in changed))


if __name__ == "__main__":
    unittest.main()

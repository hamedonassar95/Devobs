"""Behavioral tests for the offline two-worker task manifest checker."""
import contextlib
import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_two_agent_tasks import evaluate, main  # noqa: E402

REPO = "hamedonassar95/Devobs"
SHA = "a" * 40
RESTRICTED = ("merge", "deploy", "billing", "production")


def task(task_id, **overrides):
    result = {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": "CODEX",
        "branch": "feature/" + task_id.lower(),
        "affected_files": ["scripts/" + task_id.lower() + ".py"],
        "dependencies": [],
        "status": "planned",
        "previous_status": "none",
        "source_sha": None,
        "verification": {"commands": [], "result": "PENDING", "evidence": ""},
        "pr_reference": None,
        "requested_actions": ["code_change"],
    }
    result.update(overrides)
    return result


def manifest(tasks, **overrides):
    result = {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {key: "pending_human" for key in RESTRICTED},
        "tasks": tasks,
    }
    result.update(overrides)
    return result


def complete(task_id, **overrides):
    values = {
        "status": "complete",
        "previous_status": "evidence_ready",
        "source_sha": SHA,
        "verification": {"commands": ["python -m unittest discover -s tests -v"],
                         "result": "PASS", "evidence": "local offline tests: 12 passed"},
        "pr_reference": "#123",
    }
    values.update(overrides)
    return task(task_id, **values)


def blocked(task_id, **overrides):
    values = {"status": "blocked", "previous_status": "planned"}
    values.update(overrides)
    return task(task_id, **values)


class TwoAgentManifestTests(unittest.TestCase):
    def test_valid_manifest_passes_with_separate_worker_roles(self):
        result = evaluate(manifest([task("TASK-001", assigned_agent="CODEX"),
                                    task("TASK-002", assigned_agent="OPENCODE")]))
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["summary"]["enabled_agents"], ["CODEX", "OPENCODE"])
        self.assertEqual(result["blocked_tasks"], [])
        self.assertEqual(result["conflicts"], [])

    def test_duplicate_task_ids_fail_closed(self):
        result = evaluate(manifest([task("TASK-001"), task("TASK-001")]))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("duplicate task id", result["errors"])

    def test_disallowed_and_noop_transitions(self):
        bad = evaluate(manifest([task("TASK-001", status="complete",
                                      previous_status="planned")]))
        self.assertEqual(bad["decision"], "FAIL")
        self.assertIn("disallowed status transition", bad["errors"])
        good = evaluate(manifest([task("TASK-001", status="planned",
                                       previous_status="planned")]))
        self.assertEqual(good["decision"], "PASS")

    def test_unresolved_dependency_blocks_task(self):
        result = evaluate(manifest([task("TASK-001"),
                                    task("TASK-002", dependencies=["TASK-001"])]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["blocked_tasks"][0]["task"], "TASK-002")
        self.assertEqual(result["blocked_tasks"][0]["reason"], "unresolved_dependency")
        self.assertEqual(result["blocked_tasks"][0]["dependencies"], ["TASK-001"])

    def test_transitive_unresolved_dependency_blocks_task(self):
        result = evaluate(manifest([
            task("TASK-001"),
            task("TASK-002", dependencies=["TASK-001"]),
            task("TASK-003", dependencies=["TASK-002"]),
        ]))
        blocked = {item["task"]: item for item in result["blocked_tasks"]}
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(blocked["TASK-003"]["dependencies"], ["TASK-001", "TASK-002"])

    def test_dependency_ordered_shared_file_is_not_concurrent(self):
        result = evaluate(manifest([
            complete("TASK-001", affected_files=["shared/module.py"]),
            task("TASK-002", affected_files=["shared/module.py"],
                 dependencies=["TASK-001"]),
        ]))
        self.assertEqual(result["decision"], "PASS")

    def test_active_tasks_sharing_a_file_are_blocked(self):
        result = evaluate(manifest([
            task("TASK-001", status="in_progress", previous_status="planned",
                 affected_files=["shared/module.py"]),
            task("TASK-002", assigned_agent="OPENCODE", status="evidence_ready",
                 previous_status="in_progress", source_sha=SHA,
                 affected_files=["shared/module.py"]),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        conflict = result["conflicts"][0]
        self.assertEqual(conflict["reason"], "concurrent_file_ownership")
        self.assertEqual(conflict["files"], ["shared/module.py"])

    def test_planned_tasks_without_dependency_sharing_file_are_blocked(self):
        result = evaluate(manifest([
            task("TASK-001", affected_files=["shared.py"]),
            task("TASK-002", affected_files=["shared.py"]),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["conflicts"][0]["reason"], "concurrent_file_ownership")

    def test_windows_path_spelling_is_normalised_before_conflict_check(self):
        result = evaluate(manifest([
            task("TASK-001", affected_files=["scripts\\shared.py"]),
            task("TASK-002", assigned_agent="OPENCODE", affected_files=["./scripts/shared.py"]),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["conflicts"][0]["files"], ["scripts/shared.py"])

    def test_same_branch_active_ownership_is_blocked(self):
        result = evaluate(manifest([
            task("TASK-001", status="in_progress", previous_status="planned"),
            task("TASK-002", assigned_agent="OPENCODE", status="in_progress",
                 previous_status="planned", branch="feature/task-001"),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["conflicts"][0]["reason"], "concurrent_branch_ownership")

    def test_complete_requires_source_sha_and_evidence(self):
        missing_evidence = evaluate(manifest([
            complete("TASK-001", verification={"commands": ["python -m unittest"],
                                               "result": "PASS", "evidence": ""}),
        ]))
        self.assertEqual(missing_evidence["decision"], "FAIL")
        self.assertIn("complete requires PASS commands and evidence", missing_evidence["errors"])
        missing_sha = evaluate(manifest([complete("TASK-001", source_sha=None)]))
        self.assertEqual(missing_sha["decision"], "FAIL")
        self.assertIn("source_sha is required for reviewed work", missing_sha["errors"])

    def test_evidence_pass_is_rejected_for_unreviewed_status(self):
        result = evaluate(manifest([
            task("TASK-001", verification={"commands": ["python -m unittest"],
                                           "result": "PASS", "evidence": "green"}),
        ]))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("PASS evidence requires evidence_ready or complete status", result["errors"])

    def test_complete_with_verified_evidence_passes(self):
        result = evaluate(manifest([complete("TASK-001")]))
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["summary"]["complete"], 1)

    def test_human_approval_fields_cannot_be_auto_granted(self):
        for action in RESTRICTED:
            with self.subTest(action=action):
                approvals = {key: "pending_human" for key in RESTRICTED}
                approvals[action] = "agent_approved"
                result = evaluate(manifest([task("TASK-001")], approval=approvals))
                self.assertEqual(result["decision"], "FAIL")
                self.assertIn("merge, deploy, billing and production stay pending_human",
                              result["errors"])

    def test_restricted_task_action_is_rejected(self):
        for action in RESTRICTED:
            with self.subTest(action=action):
                result = evaluate(manifest([
                    task("TASK-001", requested_actions=["code_change", action]),
                ]))
                self.assertEqual(result["decision"], "FAIL")
                self.assertIn("merge, deploy, billing and production need separate human approval",
                              result["errors"])

    def test_additional_agents_are_disabled_until_reviewed(self):
        agents = {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True},
                  "FUTURE": {"enabled": False}}
        enabled = evaluate(manifest([task("TASK-001", assigned_agent="FUTURE")], agents=agents))
        self.assertEqual(enabled["decision"], "BLOCKED")
        self.assertEqual(enabled["blocked_tasks"][0]["reason"], "agent_not_enabled")
        agents["FUTURE"]["enabled"] = True
        auto = evaluate(manifest([task("TASK-001")], agents=agents))
        self.assertEqual(auto["decision"], "FAIL")
        self.assertIn("new agents require a reviewed contract change before enablement",
                      auto["errors"])
        unknown = evaluate(manifest([task("TASK-001", assigned_agent="UNKNOWN")]))
        self.assertEqual(unknown["decision"], "FAIL")

    def test_unsafe_paths_and_unknown_repository_fail(self):
        for path in ("/etc/passwd", "C:/secret", "../secret", "scripts/../secret"):
            with self.subTest(path=path):
                result = evaluate(manifest([task("TASK-001", affected_files=[path])]))
                self.assertEqual(result["decision"], "FAIL")
        result = evaluate(manifest([task("TASK-001", repository="other/repo")]))
        self.assertEqual(result["decision"], "FAIL")

    def test_dependency_cycle_and_invalid_sha_fail(self):
        cycle = evaluate(manifest([
            task("TASK-001", dependencies=["TASK-002"]),
            task("TASK-002", dependencies=["TASK-001"]),
        ]))
        self.assertEqual(cycle["decision"], "FAIL")
        self.assertIn("dependency cycle", cycle["errors"])
        bad_sha = evaluate(manifest([task("TASK-001", source_sha="HEAD")]))
        self.assertEqual(bad_sha["decision"], "FAIL")

    def test_evaluate_does_not_mutate_caller_manifest(self):
        data = manifest([task("TASK-001", dependencies=[]), task("TASK-002")])
        snapshot = copy.deepcopy(data)
        evaluate(data)
        self.assertEqual(data, snapshot)

    def test_cli_help_exit_codes_and_fail_closed_parse(self):
        script = str(ROOT / "scripts" / "check_two_agent_tasks.py")
        help_run = subprocess.run([sys.executable, script, "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("--manifest", help_run.stdout)
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "manifest.json"
            path.write_text(json.dumps(manifest([task("TASK-001")])), encoding="utf-8")
            ok = subprocess.run([sys.executable, script, "--manifest", str(path)],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0)
            self.assertEqual(json.loads(ok.stdout)["decision"], "PASS")
            path.write_text(json.dumps(manifest([
                task("TASK-001"), task("TASK-002", dependencies=["TASK-001"]),
            ])), encoding="utf-8")
            blocked = subprocess.run([sys.executable, script, "--manifest", str(path)],
                                     capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 1)
            self.assertEqual(json.loads(blocked.stdout)["decision"], "BLOCKED")
            path.write_text("{broken", encoding="utf-8")
            bad = subprocess.run([sys.executable, script, "--manifest", str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(json.loads(bad.stdout)["decision"], "FAIL")
            self.assertIn("invalid manifest file", json.dumps(bad.stdout))

    def test_main_fails_closed_on_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--manifest", str(pathlib.Path(folder) / "absent.json")])
        self.assertEqual(code, 2)

    def test_blocked_task_alone_is_reported_and_blocks(self):
        result = evaluate(manifest([blocked("TASK-001")]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["blocked_tasks"], [
            {"task": "TASK-001", "reason": "task_blocked", "dependencies": []},
        ])
        self.assertEqual(result["conflicts"], [])

    def test_blocked_task_sharing_file_with_active_task_is_conflict(self):
        result = evaluate(manifest([
            blocked("TASK-001", affected_files=["shared/module.py"]),
            task("TASK-002", assigned_agent="OPENCODE", status="in_progress",
                 previous_status="planned", affected_files=["shared/module.py"]),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["blocked_tasks"][0]["reason"], "task_blocked")
        self.assertEqual(result["conflicts"], [{
            "tasks": ["TASK-001", "TASK-002"],
            "reason": "concurrent_file_ownership",
            "files": ["shared/module.py"],
        }])

    def test_blocked_task_sharing_active_branch_is_conflict(self):
        result = evaluate(manifest([
            blocked("TASK-001", branch="feature/shared"),
            task("TASK-002", assigned_agent="OPENCODE", status="in_progress",
                 previous_status="planned", branch="feature/shared"),
        ]))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["blocked_tasks"][0]["reason"], "task_blocked")
        self.assertEqual(result["conflicts"], [{
            "tasks": ["TASK-001", "TASK-002"],
            "reason": "concurrent_branch_ownership",
            "branches": ["feature/shared"],
        }])

    def test_blocked_task_cli_exit_code_is_one(self):
        script = str(ROOT / "scripts" / "check_two_agent_tasks.py")
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "manifest.json"
            path.write_text(json.dumps(manifest([blocked("TASK-001")])), encoding="utf-8")
            run = subprocess.run([sys.executable, script, "--manifest", str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "BLOCKED")
            self.assertEqual(payload["blocked_tasks"][0]["reason"], "task_blocked")

    def test_completed_task_does_not_hold_active_ownership(self):
        result = evaluate(manifest([
            complete("TASK-001", affected_files=["shared/module.py"],
                     branch="feature/shared"),
            task("TASK-002", assigned_agent="OPENCODE", status="in_progress",
                 previous_status="planned", affected_files=["shared/module.py"],
                 branch="feature/shared"),
        ]))
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(result["blocked_tasks"], [])
        self.assertEqual(result["summary"]["complete"], 1)


if __name__ == "__main__":
    unittest.main()

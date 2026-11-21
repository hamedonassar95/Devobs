"""Behavioral tests for the offline agent security audit engine."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from devobs.agents.security_audit import audit_manifest, main  # noqa: E402

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


def blocked(task_id, **overrides):
    values = {"status": "blocked", "previous_status": "planned"}
    values.update(overrides)
    return task(task_id, **values)


def finding(result, category):
    matches = [item for item in result["findings"] if item["category"] == category]
    if len(matches) != 1:
        raise AssertionError(f"expected one {category} finding, got {len(matches)}")
    return matches[0]


class AgentSecurityAuditTests(unittest.TestCase):
    def test_clean_manifest_passes_without_findings(self):
        result = audit_manifest(manifest([
            task("TASK-001"),
            task("TASK-002", assigned_agent="OPENCODE"),
        ]))
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["read_only"])
        self.assertFalse(result["dispatched"])

    def test_duplicate_task_ownership_is_reported_with_agents(self):
        result = audit_manifest(manifest([
            task("TASK-001", affected_files=["codex.py"]),
            task("TASK-001", assigned_agent="OPENCODE", branch="feature/other",
                 affected_files=["opencode.py"]),
        ]))
        item = finding(result, "duplicate_task_ownership")
        self.assertEqual(item["severity"], "HIGH")
        self.assertEqual(item["evidence"]["task"], "TASK-001")
        self.assertEqual(set(item["evidence"]["agents"]), {"CODEX", "OPENCODE"})

    def test_case_only_file_conflict_is_reported(self):
        result = audit_manifest(manifest([
            task("TASK-001", affected_files=["Shared/Module.py"]),
            task("TASK-002", assigned_agent="OPENCODE",
                 affected_files=["shared/module.py"]),
        ]))
        item = finding(result, "conflicting_file_assignments")
        self.assertEqual(item["severity"], "HIGH")
        self.assertEqual(item["evidence"]["files"], ["shared/module.py"])
        self.assertEqual(item["evidence"]["tasks"], ["TASK-001", "TASK-002"])

    def test_protected_branch_and_invalid_ref_are_reported(self):
        for branch in ("main", "feature/../main", "feature//x"):
            with self.subTest(branch=branch):
                result = audit_manifest(manifest([task("TASK-001", branch=branch)]))
                item = finding(result, "protected_branch_violation")
                self.assertEqual(item["severity"], "HIGH")
                self.assertEqual(item["evidence"]["branch"], branch)
                self.assertTrue(item["evidence"]["reason"])

    def test_unknown_dependency_is_reported(self):
        result = audit_manifest(manifest([
            task("TASK-001", dependencies=["TASK-404"]),
        ]))
        item = finding(result, "missing_dependency")
        self.assertEqual(item["severity"], "HIGH")
        self.assertEqual(item["evidence"]["task"], "TASK-001")
        self.assertEqual(item["evidence"]["dependencies"], ["TASK-404"])

    def test_blocked_dependency_is_reported(self):
        result = audit_manifest(manifest([
            blocked("TASK-001"),
            task("TASK-002", dependencies=["TASK-001"]),
        ]))
        item = finding(result, "blocked_dependency")
        self.assertEqual(item["severity"], "MEDIUM")
        self.assertEqual(item["evidence"]["task"], "TASK-002")
        self.assertEqual(item["evidence"]["dependencies"], ["TASK-001"])

    def test_altered_human_approval_is_critical(self):
        approvals = {key: "pending_human" for key in RESTRICTED}
        approvals["merge"] = "agent_approved"
        result = audit_manifest(manifest([task("TASK-001")], approval=approvals))
        item = finding(result, "missing_human_approval")
        self.assertEqual(item["severity"], "CRITICAL")
        self.assertEqual(item["evidence"]["altered_fields"], ["merge"])

    def test_restricted_task_action_is_reported_as_human_gate_failure(self):
        result = audit_manifest(manifest([
            task("TASK-001", requested_actions=["code_change", "deploy"]),
        ]))
        item = finding(result, "missing_human_approval")
        self.assertEqual(item["evidence"]["tasks"], ["TASK-001"])
        self.assertEqual(item["evidence"]["restricted_actions"], ["deploy"])

    def test_stale_completion_evidence_is_reported(self):
        result = audit_manifest(manifest([
            task("TASK-001", status="complete", previous_status="evidence_ready"),
        ]))
        item = finding(result, "stale_task_assignment")
        self.assertEqual(item["severity"], "HIGH")
        self.assertEqual(item["evidence"]["task"], "TASK-001")
        self.assertIn("source_sha", item["evidence"]["missing"])

    def test_validator_exception_fails_closed_without_traceback(self):
        from devobs.agents import security_audit as module

        original = module.evaluate

        def raising_validator(_manifest):
            raise RuntimeError("validator unavailable")

        module.evaluate = raising_validator
        try:
            result = module.audit_manifest(manifest([task("TASK-001")]))
        finally:
            module.evaluate = original
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(
            item["category"] == "contract_validation_failure"
            for item in result["findings"]
        ))

    def test_malformed_task_fields_fail_closed_without_traceback(self):
        payload = manifest([task("TASK-001")])
        payload["tasks"][0]["id"] = ["not-a-string"]
        result = audit_manifest(payload)
        self.assertEqual(result["decision"], "FAIL")
        self.assertTrue(any(
            item["category"] == "contract_validation_failure"
            for item in result["findings"]
        ))

    def test_missing_manifest_fails_closed_with_exit_two(self):
        script = str(ROOT / "devobs" / "agents" / "security_audit.py")
        with tempfile.TemporaryDirectory() as folder:
            before = sorted(path.name for path in pathlib.Path(folder).iterdir())
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(pathlib.Path(folder) / "absent.json")],
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 2, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "FAIL")
            self.assertFalse(payload["dispatched"])
            self.assertEqual(payload["summary"]["findings"], 1)
            self.assertEqual(payload["summary"]["by_severity"]["CRITICAL"], 1)
            self.assertEqual(sorted(path.name for path in pathlib.Path(folder).iterdir()), before)

    def test_cli_is_read_only_and_emits_structured_findings(self):
        script = str(ROOT / "devobs" / "agents" / "security_audit.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            path = root / "tasks.json"
            path.write_text(json.dumps(manifest([
                task("TASK-001", dependencies=["TASK-404"]),
            ])), encoding="utf-8")
            run = subprocess.run([sys.executable, script, "--manifest", str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["audit_type"], "advisory_agent_security_audit")
            self.assertTrue(payload["read_only"])
            self.assertFalse(payload["dispatched"])
            item = finding(payload, "missing_dependency")
            self.assertIsInstance(item["evidence"], dict)
            self.assertIn(item["severity"], {"CRITICAL", "HIGH", "MEDIUM", "LOW"})
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["tasks.json"])

    def test_main_maps_decisions_to_exact_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "tasks.json"
            path.write_text(json.dumps(manifest([task("TASK-001")])), encoding="utf-8")
            self.assertEqual(main(["--manifest", str(path)]), 0)
            path.write_text(json.dumps(manifest([
                blocked("TASK-001"),
            ])), encoding="utf-8")
            self.assertEqual(main(["--manifest", str(path)]), 1)
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(main(["--manifest", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()

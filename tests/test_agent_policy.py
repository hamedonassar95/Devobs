"""Behavioral tests for the offline AI agent security policy engine."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from devobs.security import agent_policy as module
from devobs.security.agent_policy import evaluate_policy, load_request, main

APPROVED_ACTIONS = ["code_change", "review", "test", "documentation"]
REPO = "hamedonassar95/Devobs"


def _task(task_id="TASK-001", agent="CODEX", branch="feature/policy-engine",
          paths=None, actions=None, status="planned", previous="none"):
    return {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": agent,
        "branch": branch,
        "affected_files": list(paths or ["devobs/security/agent_policy.py"]),
        "dependencies": [],
        "status": status,
        "previous_status": previous,
        "source_sha": None,
        "verification": {
            "commands": [],
            "result": "PENDING",
            "evidence": "SENSITIVE_DO_NOT_EMIT",
        },
        "pr_reference": None,
        "requested_actions": list(actions or ["code_change", "test"]),
    }


def _manifest(tasks=None):
    return {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {
            "CODEX": {"enabled": True},
            "OPENCODE": {"enabled": True},
        },
        "approval": {
            "merge": "pending_human",
            "deploy": "pending_human",
            "billing": "pending_human",
            "production": "pending_human",
        },
        "tasks": list(tasks or [_task()]),
    }


def _request():
    return {
        "schema_version": 1,
        "mode": "DRY_RUN",
        "manifest": _manifest(),
        "agent_permissions": {
            "CODEX": list(APPROVED_ACTIONS),
            "OPENCODE": ["review", "documentation"],
        },
        "locks": [],
    }


class AgentPolicyTests(unittest.TestCase):
    def test_clean_dry_run_request_is_allowed_but_never_authorizes_execution(self):
        result = evaluate_policy(_request())

        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reason_codes"], [])
        self.assertFalse(result["authorization"]["execution_granted"])
        self.assertEqual(result["authorization"]["mode"], "DRY_RUN")
        self.assertTrue(result["authorization"]["human_approval_required"])
        self.assertTrue(result["audit_events"])

        event = result["audit_events"][0]
        self.assertEqual(
            set(event),
            {"event", "decision", "reason_codes", "task_ids", "agents",
             "counts", "source"},
        )
        self.assertNotIn("SENSITIVE_DO_NOT_EMIT", json.dumps(result))

    def test_altered_human_approval_is_denied(self):
        request = _request()
        request["manifest"]["approval"]["deploy"] = "approved"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("human_approval_altered", result["reason_codes"])

    def test_restricted_operation_is_denied(self):
        request = _request()
        request["manifest"]["tasks"][0]["requested_actions"] = ["deploy"]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("restricted_action_requested", result["reason_codes"])

    def test_unregistered_agent_is_denied(self):
        request = _request()
        request["manifest"]["tasks"][0]["assigned_agent"] = "STRAY_AGENT"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("unauthorized_agent", result["reason_codes"])

    def test_action_outside_declared_agent_permissions_is_denied(self):
        request = _request()
        request["agent_permissions"]["CODEX"] = ["review"]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("action_not_declared", result["reason_codes"])

    def test_permission_for_disabled_agent_is_denied(self):
        request = _request()
        request["manifest"]["agents"]["OPENCODE"]["enabled"] = False
        request["agent_permissions"]["OPENCODE"] = ["review"]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("permission_granted_to_disabled_agent", result["reason_codes"])

    def test_lock_held_by_another_task_is_denied(self):
        request = _request()
        request["manifest"]["tasks"].append(_task(
            task_id="TASK-002",
            agent="OPENCODE",
            branch="feature/other-docs",
            paths=["docs/other.md"],
            actions=["documentation"],
        ))
        request["agent_permissions"]["OPENCODE"] = ["review", "documentation"]
        request["locks"] = [{"path": "docs/other.md", "owner": "TASK-001"}]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("lock_conflict", result["reason_codes"])

    def test_protected_branch_is_denied(self):
        request = _request()
        request["manifest"]["tasks"][0]["branch"] = "main"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("protected_branch_violation", result["reason_codes"])

    def test_non_dry_run_mode_is_denied(self):
        request = _request()
        request["mode"] = "EXECUTE"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("dry_run_required", result["reason_codes"])

    def test_completed_task_is_not_treated_as_a_proposed_action(self):
        request = _request()
        request["manifest"]["tasks"][0]["status"] = "complete"
        request["manifest"]["tasks"][0]["previous_status"] = "evidence_ready"
        request["manifest"]["tasks"][0]["source_sha"] = "a" * 40
        request["manifest"]["tasks"][0]["verification"]["result"] = "PASS"
        request["manifest"]["tasks"][0]["verification"]["commands"] = ["python -m unittest"]
        request["manifest"]["tasks"][0]["verification"]["evidence"] = "offline pass"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["summary"]["active_tasks"], 0)

    def test_missing_lock_evidence_is_unverified_without_authorization(self):
        request = _request()
        del request["locks"]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("missing_required_evidence", result["reason_codes"])
        self.assertFalse(result["authorization"]["execution_granted"])

    def test_missing_permission_evidence_is_unverified(self):
        request = _request()
        del request["agent_permissions"]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("missing_required_evidence", result["reason_codes"])

    def test_invalid_lock_evidence_is_unverified(self):
        request = _request()
        request["locks"] = [{"path": "../secret.txt", "owner": "TASK-001"}]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("invalid_lock_evidence", result["reason_codes"])

    def test_malformed_request_is_denied_without_traceback(self):
        result = evaluate_policy({"schema_version": 1})

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_request", result["reason_codes"])

    def test_validator_exception_is_unverified_without_traceback(self):
        original = module.evaluate

        def raising_validator(_manifest):
            raise RuntimeError("validator unavailable")

        module.evaluate = raising_validator
        try:
            result = evaluate_policy(_request())
        finally:
            module.evaluate = original

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("validator_unavailable", result["reason_codes"])

    def test_unknown_validator_decision_is_unverified(self):
        original = module.evaluate

        def unknown_validator(_manifest):
            return {"decision": "UNKNOWN", "errors": [],
                    "blocked_tasks": [], "conflicts": [], "summary": {}}

        module.evaluate = unknown_validator
        try:
            result = evaluate_policy(_request())
        finally:
            module.evaluate = original

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("validator_decision_unknown", result["reason_codes"])

    def test_duplicate_lock_paths_are_unverified(self):
        request = _request()
        request["locks"] = [
            {"path": "docs/shared.md", "owner": "TASK-001"},
            {"path": "DOCS/shared.md", "owner": "TASK-001"},
        ]

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("invalid_lock_evidence", result["reason_codes"])

    def test_malformed_agent_registry_fails_closed_without_traceback(self):
        request = _request()
        request["manifest"]["agents"] = "CODEX"

        result = evaluate_policy(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_request", result["reason_codes"])

    def test_cli_exit_codes_match_allow_deny_and_unverified(self):
        allowed = _request()
        denied = _request()
        denied["manifest"]["approval"]["merge"] = "approved"
        unverified = _request()
        del unverified["locks"]

        with tempfile.TemporaryDirectory() as folder:
            paths = {}
            for name, payload in (("allow", allowed), ("deny", denied),
                                  ("unverified", unverified)):
                path = pathlib.Path(folder) / f"{name}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                paths[name] = path

            outcomes = {}
            for name, path in paths.items():
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = main(["--request", str(path)])
                outcomes[name] = (code, json.loads(stdout.getvalue())["decision"])

        self.assertEqual(outcomes["allow"], (module.EXIT_ALLOW, "ALLOW"))
        self.assertEqual(outcomes["deny"], (module.EXIT_DENY, "DENY"))
        self.assertEqual(outcomes["unverified"], (module.EXIT_UNVERIFIED, "UNVERIFIED"))

    def test_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "duplicate.json"
            path.write_text(
                '{"schema_version": 1, "schema_version": 2}', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_request(path)


if __name__ == "__main__":
    unittest.main()

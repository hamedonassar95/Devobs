"""Behavioral tests for the offline agent approval-gate validator."""
import contextlib
import copy
import io
import json
import os
import pathlib
import tempfile
import unittest

from devobs.agent_security import approval_gates as module
from devobs.agent_security.approval_gates import evaluate_approval, load_request, main
from devobs.agent_security.policy_models import task_fingerprint

REPO = "hamedonassar95/Devobs"
EVALUATED_AT = "2026-11-21T10:00:00Z"
ISSUED_AT = "2026-11-21T09:00:00Z"
EXPIRES_AT = "2026-11-21T10:30:00Z"
SECRET_MARKER = "SENSITIVE_DO_NOT_EMIT"


def _task(task_id="TASK-001", agent="CODEX", branch="feature/approval-gates",
          paths=None, actions=None, status="planned", previous="none", source_sha=None):
    return {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": agent,
        "branch": branch,
        "affected_files": list(paths or ["devobs/agent_security/approval_gates.py"]),
        "dependencies": [],
        "status": status,
        "previous_status": previous,
        "source_sha": source_sha,
        "verification": {
            "commands": [],
            "result": "PENDING",
            "evidence": SECRET_MARKER,
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


def _approval(task, action="code_change", approval_id="APR-001", policy_version=3,
              issued_at=ISSUED_AT, expires_at=EXPIRES_AT, agent=None, task_id=None):
    return {
        "schema_version": 1,
        "approval_id": approval_id,
        "task_id": task_id or task["id"],
        "agent": agent or task["assigned_agent"],
        "action": action,
        "scope": {
            "repository": task["repository"],
            "branch": task["branch"],
            "affected_files": list(task["affected_files"]),
            "source_sha": task["source_sha"],
        },
        "task_fingerprint": task_fingerprint(task),
        "policy_version": policy_version,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def _policy_state(version=3, status="ACTIVE", active=None, revoked=None,
                  consumed=None):
    return {
        "schema_version": 1,
        "status": status,
        "version": version,
        "active_approvals": list(active if active is not None else ["APR-001"]),
        "revoked_approvals": list(revoked or []),
        "consumed_approvals": list(consumed or []),
    }


def _request(task=None, action="code_change", approval=None, policy_state=None,
             manifest=None, task_id="TASK-001", mode="DRY_RUN", evaluated_at=EVALUATED_AT):
    manifest = manifest or _manifest([task] if task is not None else None)
    selected = task or manifest["tasks"][0]
    return {
        "schema_version": 1,
        "mode": mode,
        "task_id": task_id,
        "requested_action": action,
        "manifest": manifest,
        "approval": approval if approval is not None else _approval(selected, action=action),
        "policy_state": policy_state if policy_state is not None else _policy_state(),
        "evaluated_at": evaluated_at,
    }


class AgentApprovalGateTests(unittest.TestCase):
    def test_valid_dry_run_request_is_allowed_but_grants_no_approval(self):
        result = evaluate_approval(_request())

        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reason_codes"], [])
        self.assertEqual(result["validator_decision"], "PASS")
        self.assertFalse(result["authorization"]["execution_granted"])
        self.assertFalse(result["authorization"]["approval_granted"])
        self.assertEqual(result["authorization"]["mode"], "DRY_RUN")
        self.assertIsNone(result["authorization"]["executor"])
        self.assertEqual(len(result["audit_events"]), 1)

        event = result["audit_events"][0]
        self.assertEqual(
            set(event),
            {"event", "decision", "reason_codes", "task_id", "agent", "action",
             "approval_id", "approval_digest", "policy_version", "mode", "source"},
        )
        self.assertEqual(event["task_id"], "TASK-001")
        self.assertEqual(event["agent"], "CODEX")
        self.assertEqual(event["action"], "code_change")
        self.assertEqual(event["approval_id"], "APR-001")
        self.assertEqual(event["mode"], "DRY_RUN")
        self.assertNotIn(SECRET_MARKER, json.dumps(result))

    def test_missing_approval_is_denied(self):
        request = _request()
        del request["approval"]

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("missing_approval", result["reason_codes"])

    def test_expired_approval_is_denied(self):
        request = _request()
        request["approval"]["expires_at"] = EVALUATED_AT

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_expired", result["reason_codes"])

    def test_future_issued_approval_is_denied(self):
        request = _request()
        request["approval"]["issued_at"] = "2026-11-21T10:00:01Z"

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_not_yet_valid", result["reason_codes"])

    def test_excessive_approval_lifetime_is_denied(self):
        request = _request()
        request["approval"]["expires_at"] = "2026-11-28T09:00:01Z"

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_lifetime_too_long", result["reason_codes"])

    def test_mismatched_approval_action_is_denied(self):
        request = _request()
        request["approval"]["action"] = "review"

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_action_mismatch", result["reason_codes"])

    def test_restricted_action_is_denied(self):
        task = _task(actions=["deploy"])
        request = _request(task=task, action="deploy")

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("restricted_action_requested", result["reason_codes"])

    def test_unknown_action_is_denied(self):
        request = _request(action="execute")

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("unauthorized_action", result["reason_codes"])

    def test_action_not_requested_by_task_is_denied(self):
        task = _task(actions=["code_change"])
        request = _request(task=task, action="test")

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("action_not_requested", result["reason_codes"])

    def test_cross_task_approval_is_denied(self):
        first = _task()
        second = _task(task_id="TASK-002", agent="OPENCODE",
                       branch="feature/cross-task", paths=["docs/cross.md"],
                       actions=["review"])
        manifest = _manifest([first, second])
        request = _request(task=second, manifest=manifest, action="review",
                           approval=_approval(second, action="review"),
                           task_id="TASK-002")
        request["approval"] = _approval(first, action="code_change")

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("cross_task_authorization_denied", result["reason_codes"])

    def test_approval_becomes_stale_after_task_file_change(self):
        task = _task()
        approval = _approval(task)
        task["affected_files"].append("docs/extra.md")

        result = evaluate_approval(_request(task=task, approval=approval))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("stale_approval", result["reason_codes"])

    def test_approval_becomes_stale_after_branch_change(self):
        task = _task()
        approval = _approval(task)
        task["branch"] = "feature/changed-branch"

        result = evaluate_approval(_request(task=task, approval=approval))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("stale_approval", result["reason_codes"])

    def test_forged_fingerprint_is_denied(self):
        request = _request()
        request["approval"]["task_fingerprint"] = "sha256:" + "0" * 64

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("stale_approval", result["reason_codes"])

    def test_revoked_approval_is_denied(self):
        state = _policy_state(active=["APR-001"], revoked=["APR-001"])

        result = evaluate_approval(_request(policy_state=state))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_revoked", result["reason_codes"])

    def test_replayed_approval_is_denied(self):
        state = _policy_state(consumed=["APR-001"])

        result = evaluate_approval(_request(policy_state=state))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_replayed", result["reason_codes"])
        self.assertFalse(result["authorization"]["approval_granted"])

    def test_approval_absent_from_active_state_is_denied(self):
        result = evaluate_approval(_request(policy_state=_policy_state(active=[])))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("approval_not_active", result["reason_codes"])

    def test_inactive_policy_state_is_denied(self):
        state = _policy_state(status="SUSPENDED")

        result = evaluate_approval(_request(policy_state=state))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("policy_state_inactive", result["reason_codes"])

    def test_policy_version_mismatch_is_denied(self):
        request = _request()
        request["approval"]["policy_version"] = 4

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("policy_version_mismatch", result["reason_codes"])

    def test_missing_policy_state_is_unverified(self):
        request = _request()
        del request["policy_state"]

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("missing_required_evidence", result["reason_codes"])
        self.assertFalse(result["authorization"]["approval_granted"])

    def test_malformed_policy_state_is_denied(self):
        state = _policy_state()
        state["version"] = "3"

        result = evaluate_approval(_request(policy_state=state))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_policy_state", result["reason_codes"])

    def test_invalid_approval_scope_path_is_denied(self):
        request = _request()
        request["approval"]["scope"]["affected_files"] = ["../secret.txt"]

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_approval_scope", result["reason_codes"])

    def test_invalid_approval_id_is_denied(self):
        request = _request()
        request["approval"]["approval_id"] = "apr-1"

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_approval", result["reason_codes"])

    def test_non_dry_run_mode_is_denied(self):
        result = evaluate_approval(_request(mode="EXECUTE"))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("dry_run_required", result["reason_codes"])

    def test_missing_evaluated_at_is_denied(self):
        request = _request()
        del request["evaluated_at"]

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("malformed_request", result["reason_codes"])

    def test_unknown_task_is_denied(self):
        result = evaluate_approval(_request(task_id="TASK-999"))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("unknown_task", result["reason_codes"])

    def test_invalid_task_id_is_denied(self):
        result = evaluate_approval(_request(task_id="task-1"))

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("task_identity_invalid", result["reason_codes"])

    def test_shared_contract_failure_is_denied(self):
        request = _request()
        request["manifest"]["approval"]["merge"] = "approved"

        result = evaluate_approval(request)

        self.assertEqual(result["decision"], "DENY")
        self.assertIn("contract_validation_failed", result["reason_codes"])

    def test_validator_exception_is_unverified(self):
        original = module.evaluate

        def raising_validator(_manifest):
            raise RuntimeError("validator unavailable")

        module.evaluate = raising_validator
        try:
            result = evaluate_approval(_request())
        finally:
            module.evaluate = original

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("validator_unavailable", result["reason_codes"])

    def test_unknown_validator_decision_is_unverified(self):
        original = module.evaluate

        def unknown_validator(_manifest):
            return {"decision": "UNKNOWN", "errors": [], "blocked_tasks": [],
                    "conflicts": [], "summary": {}}

        module.evaluate = unknown_validator
        try:
            result = evaluate_approval(_request())
        finally:
            module.evaluate = original

        self.assertEqual(result["decision"], "UNVERIFIED")
        self.assertIn("validator_decision_unknown", result["reason_codes"])

    def test_repeated_evaluation_is_deterministic_and_read_only(self):
        request = _request()
        snapshot = copy.deepcopy(request)

        first = evaluate_approval(request)
        second = evaluate_approval(request)

        self.assertEqual(request, snapshot)
        self.assertEqual(first, second)
        self.assertEqual(first["audit_events"], second["audit_events"])

    def test_cli_exit_codes_match_decisions(self):
        denied = _request()
        denied["approval"]["expires_at"] = EVALUATED_AT
        unverified = _request()
        del unverified["policy_state"]

        with tempfile.TemporaryDirectory() as folder:
            paths = {}
            for name, payload in (("allow", _request()), ("deny", denied),
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

    def test_loader_rejects_symbolic_link(self):
        with tempfile.TemporaryDirectory() as folder:
            target = pathlib.Path(folder) / "request.json"
            target.write_text(json.dumps(_request()), encoding="utf-8")
            link = pathlib.Path(folder) / "link.json"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this host")
            with self.assertRaises(ValueError):
                load_request(link)


if __name__ == "__main__":
    unittest.main()

"""Deterministic, side-effect-free policy gate for proposed agent actions.

The engine validates a request that wraps the existing two-worker manifest
contract. It reuses ``scripts/check_two_agent_tasks.py`` as the rule source of
truth, then applies deny-by-default checks for agent identity, declared
permissions, task authorization, file locks, protected refs, human gates and
DRY_RUN mode.

It never starts an agent, executes a command, writes a file, changes Git state,
calls a network service or grants an approval. ALLOW is advisory evidence for a
human reviewer, not an execution grant.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from check_two_agent_tasks import (
        APPROVAL_VALUE,
        APPROVED_TASK_ACTIONS,
        BRANCH_RE,
        ID_RE,
        MAX_MANIFEST_BYTES,
        RESTRICTED_ACTIONS,
        TOP_LEVEL_KEYS,
        _normal_path,
        evaluate,
    )
except ImportError as exc:  # fail closed when the shared contract is unavailable
    IMPORT_ERROR = f"shared validator import failed: {type(exc).__name__}"
else:
    IMPORT_ERROR = None

POLICY_NAME = "devobs_agent_security_policy"
SCHEMA_VERSION = 1
MODE_DRY_RUN = "DRY_RUN"
REQUIRED_REQUEST_KEYS = frozenset(("schema_version", "mode", "manifest"))
OPTIONAL_REQUEST_KEYS = frozenset(("agent_permissions", "locks"))
LOCK_KEYS = frozenset(("path", "owner"))
ACTIONABLE_STATUSES = frozenset(("planned", "in_progress"))
PROTECTED_BRANCHES = frozenset(("main", "master", "develop", "release"))
MAX_REQUEST_BYTES = MAX_MANIFEST_BYTES
MAX_LOCKS = 200
MAX_PERMISSIONS = 20
EXIT_ALLOW = 0
EXIT_DENY = 1
EXIT_UNVERIFIED = 2

HUMAN_APPROVAL_ACTIONS = (
    "Human must review each proposed action before any worker starts.",
    "Human must keep merge, deploy, billing and production approvals pending.",
    "Human must complete Phase 8 owner approval; this policy never grants it.",
)


def _new_result():
    """Return the smallest fail-closed result shape."""
    return {
        "policy": POLICY_NAME,
        "schema_version": SCHEMA_VERSION,
        "decision": "UNVERIFIED",
        "reason_codes": [],
        "authorization": {
            "execution_granted": False,
            "scope": "advisory_only",
            "mode": MODE_DRY_RUN,
            "human_approval_required": True,
            "executor": None,
        },
        "validator_decision": None,
        "checks": [],
        "summary": {
            "tasks": 0,
            "active_tasks": 0,
            "agents": [],
            "locks": 0,
            "reasons": 0,
        },
        "audit_events": [],
        "human_approval_actions": list(HUMAN_APPROVAL_ACTIONS),
        "errors": [],
    }


class _Evaluation:
    """Accumulate only sanitized, deterministic verdict data."""

    def __init__(self):
        self.result = _new_result()
        self.denials = set()
        self.unverified_reasons = set()

    def deny(self, reason):
        self.denials.add(reason)

    def unverified(self, reason):
        self.unverified_reasons.add(reason)

    def check(self, name):
        self.result["checks"].append(name)

    def finalize(self):
        reasons = sorted(self.denials | self.unverified_reasons)
        if self.denials:
            decision = "DENY"
        elif self.unverified_reasons:
            decision = "UNVERIFIED"
        else:
            decision = "ALLOW"
        self.result["decision"] = decision
        self.result["reason_codes"] = reasons
        self.result["checks"] = sorted(set(self.result["checks"]))
        self.result["summary"]["reasons"] = len(reasons)
        self.result["audit_events"] = [{
            "event": "agent_policy_evaluation",
            "decision": decision,
            "reason_codes": reasons,
            "task_ids": list(self.result["summary"].get("task_ids", [])),
            "agents": list(self.result["summary"]["agents"]),
            "counts": {
                "tasks": self.result["summary"]["tasks"],
                "active_tasks": self.result["summary"]["active_tasks"],
                "locks": self.result["summary"]["locks"],
                "reasons": len(reasons),
            },
            "source": POLICY_NAME,
        }]
        self.result["summary"].pop("task_ids", None)
        return self.result


def _task_list(manifest):
    tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def _index(tasks):
    by_id = {}
    for task in tasks:
        task_id = task.get("id")
        if isinstance(task_id, str) and ID_RE.fullmatch(task_id):
            by_id.setdefault(task_id, task)
    return by_id


def _identifier(value):
    if isinstance(value, str) and ID_RE.fullmatch(value):
        return value
    return "<redacted>"


def _agent_names(manifest):
    agents = manifest.get("agents") if isinstance(manifest, dict) else None
    if not isinstance(agents, dict):
        return []
    return sorted(name for name in agents if isinstance(name, str))


def _invalid_branch_reason(branch):
    """Return a stable reason for a protected or malformed Git ref."""
    if not isinstance(branch, str) or not branch:
        return "missing_or_invalid_branch"
    if branch.casefold() in PROTECTED_BRANCHES:
        return "protected_branch_name"
    if not BRANCH_RE.fullmatch(branch):
        return "invalid_or_protected_ref"
    _, _, suffix = branch.partition("/")
    for segment in suffix.split("/"):
        if not segment:
            return "empty_ref_component"
        if segment in (".", "..") or ".." in segment:
            return "git_ref_traversal_or_dot_component"
    return None


def _check_human_approval(manifest, evaluation):
    approval = manifest.get("approval")
    if not isinstance(approval, dict) or set(approval) != set(RESTRICTED_ACTIONS):
        evaluation.deny("human_approval_altered")
        return
    if any(approval[name] != APPROVAL_VALUE for name in RESTRICTED_ACTIONS):
        evaluation.deny("human_approval_altered")


def _check_permissions(manifest, permissions, by_id, evaluation):
    agents = manifest.get("agents")
    if not isinstance(permissions, dict) or not isinstance(agents, dict):
        evaluation.unverified("missing_required_evidence")
        return
    if set(permissions) != set(agents):
        evaluation.unverified("missing_required_evidence")
        return
    for name in sorted(permissions):
        values = permissions[name]
        if (not isinstance(values, list) or len(values) > MAX_PERMISSIONS
                or any(not isinstance(action, str)
                       or action not in APPROVED_TASK_ACTIONS for action in values)):
            evaluation.unverified("invalid_permission_evidence")
            continue
        config = agents.get(name)
        if (isinstance(config, dict) and config.get("enabled") is False
                and values):
            evaluation.deny("permission_granted_to_disabled_agent")
    evaluation.check("declared_permissions")


def _normalise_locks(locks, by_id, evaluation):
    if not isinstance(locks, list):
        evaluation.unverified("missing_required_evidence")
        return []
    if len(locks) > MAX_LOCKS:
        evaluation.unverified("invalid_lock_evidence")
        return []
    normalised = []
    valid = True
    for entry in locks:
        if not isinstance(entry, dict) or set(entry) != LOCK_KEYS:
            valid = False
            continue
        path = _normal_path(entry["path"])
        owner = entry["owner"]
        if path is None or not isinstance(owner, str) or owner not in by_id:
            valid = False
            continue
        normalised.append((path.casefold(), owner))
    if not valid:
        evaluation.unverified("invalid_lock_evidence")
    evaluation.check("lock_evidence")
    return normalised


def _check_tasks(tasks, by_id, agents, permissions, locks, evaluation,
                 check_declared=True):
    active = 0
    for task in tasks:
        status = task.get("status")
        if status == "complete":
            continue
        active += 1
        if status not in ACTIONABLE_STATUSES:
            evaluation.deny("task_not_actionable")

        task_id = _identifier(task.get("id"))
        agent = task.get("assigned_agent")
        if not isinstance(agent, str) or agent not in agents:
            evaluation.deny("unauthorized_agent")
        elif not isinstance(agents[agent], dict) or not agents[agent].get("enabled"):
            evaluation.deny("agent_not_enabled")

        actions = task.get("requested_actions")
        if not isinstance(actions, list):
            evaluation.deny("unauthorized_operation")
        else:
            declared = permissions.get(agent, []) if isinstance(agent, str) else []
            declared = declared if isinstance(declared, list) else []
            for action in actions:
                if action in RESTRICTED_ACTIONS:
                    evaluation.deny("restricted_action_requested")
                elif action not in APPROVED_TASK_ACTIONS:
                    evaluation.deny("unauthorized_operation")
                elif check_declared and action not in declared:
                    evaluation.deny("action_not_declared")

        if _invalid_branch_reason(task.get("branch")):
            evaluation.deny("protected_branch_violation")

        paths = task.get("affected_files")
        paths = paths if isinstance(paths, list) else []
        for value in paths:
            path = _normal_path(value)
            if path is None:
                continue
            key = path.casefold()
            if any(key == lock_path and owner != task_id
                   for lock_path, owner in locks):
                evaluation.deny("lock_conflict")

    evaluation.result["summary"]["active_tasks"] = active
    evaluation.check("task_authorization")


def evaluate_policy(request):
    """Return a deterministic ALLOW/DENY/UNVERIFIED decision for one request.

    The function reads no files, starts no processes and mutates neither the
    request nor repository state. UNVERIFIED is always non-authorizing.
    """
    evaluation = _Evaluation()
    result = evaluation.result

    if (not isinstance(request, dict)
            or not REQUIRED_REQUEST_KEYS <= set(request)
            or not set(request) <= REQUIRED_REQUEST_KEYS | OPTIONAL_REQUEST_KEYS):
        evaluation.deny("malformed_request")
        return evaluation.finalize()
    if type(request["schema_version"]) is not int or request["schema_version"] != SCHEMA_VERSION:
        evaluation.deny("malformed_request")
        return evaluation.finalize()
    if request["mode"] != MODE_DRY_RUN:
        evaluation.deny("dry_run_required")
        evaluation.check("dry_run_mode")
        return evaluation.finalize()

    manifest = request["manifest"]
    tasks = _task_list(manifest)
    by_id = _index(tasks)
    agents = manifest.get("agents") if isinstance(manifest, dict) else None
    result["summary"]["tasks"] = len(tasks)
    result["summary"]["task_ids"] = sorted(by_id)
    result["summary"]["agents"] = _agent_names(manifest)

    if not isinstance(manifest, dict) or set(manifest) != TOP_LEVEL_KEYS:
        evaluation.deny("malformed_request")
        return evaluation.finalize()

    if IMPORT_ERROR:
        result["errors"].append(IMPORT_ERROR)
        evaluation.unverified("validator_unavailable")
        return evaluation.finalize()
    try:
        validator = evaluate(manifest)
    except Exception:  # fail closed on unexpected contract errors
        evaluation.unverified("validator_unavailable")
        return evaluation.finalize()
    if not isinstance(validator, dict) or validator.get("decision") not in (
            "PASS", "BLOCKED", "FAIL"):
        evaluation.unverified("validator_decision_unknown")
        return evaluation.finalize()

    result["validator_decision"] = validator["decision"]
    evaluation.check("shared_contract")
    if validator["decision"] == "FAIL":
        evaluation.deny("contract_validation_failed")
    elif validator["decision"] == "BLOCKED":
        evaluation.deny("contract_blocked")
    if validator.get("conflicts"):
        evaluation.deny("ownership_conflict")
    if validator.get("blocked_tasks"):
        evaluation.deny("blocked_task")

    permissions = request.get("agent_permissions")
    locks = request.get("locks")
    if permissions is None or locks is None:
        evaluation.unverified("missing_required_evidence")
    _check_permissions(manifest, permissions, by_id, evaluation)
    normalised_locks = _normalise_locks(locks, by_id, evaluation)
    result["summary"]["locks"] = len(normalised_locks)
    _check_human_approval(manifest, evaluation)
    safe_permissions = permissions if isinstance(permissions, dict) else {}
    _check_tasks(tasks, by_id, agents, safe_permissions, normalised_locks,
                 evaluation, check_declared=isinstance(permissions, dict))
    evaluation.check("human_gates")
    evaluation.check("protected_refs")
    return evaluation.finalize()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_request(path):
    """Read one bounded UTF-8 JSON request without duplicate keys."""
    path = pathlib.Path(path)
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("request exceeds 512 KiB")
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
    )


def exit_code(decision):
    """Map a decision to an exact exit code; unknown values fail closed."""
    if decision == "ALLOW":
        return EXIT_ALLOW
    if decision == "DENY":
        return EXIT_DENY
    return EXIT_UNVERIFIED


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=pathlib.Path,
                        help="Path to a local offline JSON policy request")
    args = parser.parse_args(argv)
    try:
        request = load_request(args.request)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        evaluation = _Evaluation()
        evaluation.deny("malformed_request")
        evaluation.result["errors"].append(
            f"invalid request file: {type(exc).__name__}"
        )
        result = evaluation.finalize()
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return EXIT_DENY

    result = evaluate_policy(request)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return exit_code(result["decision"])


if __name__ == "__main__":
    sys.exit(main())

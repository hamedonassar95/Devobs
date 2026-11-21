"""Offline, fail-closed validation of human approvals for proposed agent tasks.

This is an additive gate over the existing two-agent manifest contract. It
reuses ``scripts/check_two_agent_tasks.py`` as the rule source of truth and
validates one approval against one task, action, scope, expiry and current policy
state. It never starts an agent, executes a command, writes repository state,
calls a network service, changes IAM, or grants merge, deploy, billing,
production or Phase 8 approval. ``ALLOW`` is advisory only.
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
        APPROVED_TASK_ACTIONS,
        ID_RE,
        MAX_MANIFEST_BYTES,
        RESTRICTED_ACTIONS,
        WORKER_ROLES,
        evaluate,
    )
except ImportError:  # fail closed when the shared contract is unavailable
    IMPORT_ERROR = "shared validator import failed"
    APPROVED_TASK_ACTIONS = ()
    ID_RE = re.compile(r"(?!)")
    MAX_MANIFEST_BYTES = 512 * 1024
    RESTRICTED_ACTIONS = ("merge", "deploy", "billing", "production")
    WORKER_ROLES = ()
    evaluate = None
else:
    IMPORT_ERROR = None

from .policy_models import (  # noqa: E402
    MAX_APPROVAL_LIFETIME_SECONDS,
    MODE_DRY_RUN,
    REQUEST_KEYS,
    SCHEMA_VERSION,
    ModelValidationError,
    _task_paths,
    ApprovalRequest,
    task_fingerprint,
)

POLICY_NAME = "devobs_agent_approval_gate"
KNOWN_DECISIONS = frozenset(("PASS", "BLOCKED", "FAIL"))
ACTIONABLE_STATUSES = frozenset(("planned", "in_progress"))
EXIT_ALLOW = 0
EXIT_DENY = 1
EXIT_UNVERIFIED = 2

HUMAN_APPROVAL_ACTIONS = (
    "Human must review the exact task, action, scope and approval evidence before any worker starts.",
    "Human must keep merge, deploy, billing and production approvals pending and grant each separately.",
    "Human must complete Phase 8 owner approval; this validator never grants it.",
)


def _safe_id(value):
    return value if isinstance(value, str) and ID_RE.fullmatch(value) else "<redacted>"


def _safe_agent(value):
    return value if value in WORKER_ROLES else "<redacted>"


def _safe_action(value):
    allowed = set(APPROVED_TASK_ACTIONS) | set(RESTRICTED_ACTIONS)
    return value if value in allowed else "<redacted>"


def _new_result():
    return {
        "policy": POLICY_NAME,
        "schema_version": SCHEMA_VERSION,
        "decision": "UNVERIFIED",
        "reason_codes": [],
        "authorization": {
            "execution_granted": False,
            "approval_granted": False,
            "scope": "advisory_only",
            "mode": MODE_DRY_RUN,
            "executor": None,
        },
        "validator_decision": None,
        "checks": [],
        "summary": {
            "tasks": 0,
            "active_tasks": 0,
            "agents": [],
            "approvals": 0,
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
        self.audit = {
            "task_id": "<redacted>",
            "agent": "<redacted>",
            "action": "<redacted>",
            "approval_id": "<redacted>",
            "approval_digest": "unavailable",
            "policy_version": None,
        }

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
            "event": "agent_approval_gate_evaluation",
            "decision": decision,
            "reason_codes": reasons,
            "task_id": self.audit["task_id"],
            "agent": self.audit["agent"],
            "action": self.audit["action"],
            "approval_id": self.audit["approval_id"],
            "approval_digest": self.audit["approval_digest"],
            "policy_version": self.audit["policy_version"],
            "mode": MODE_DRY_RUN,
            "source": POLICY_NAME,
        }]
        return self.result


def _task_by_id(manifest):
    tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
    by_id = {}
    if not isinstance(tasks, list):
        return by_id
    for task in tasks:
        task_id = task.get("id") if isinstance(task, dict) else None
        if isinstance(task_id, str) and ID_RE.fullmatch(task_id):
            by_id.setdefault(task_id, task)
    return by_id


def _set_audit_context(evaluation, request):
    evaluation.audit.update({
        "task_id": _safe_id(request.task_id),
        "agent": _safe_agent(request.approval.agent),
        "action": _safe_action(request.action),
        "approval_id": _safe_id(request.approval.approval_id),
        "approval_digest": request.approval.digest(),
        "policy_version": request.approval.policy_version,
    })


def _check_policy_state(request, evaluation):
    state = request.policy_state
    approval = request.approval
    evaluation.check("current_policy_state")
    if state.status != "ACTIVE":
        evaluation.deny("policy_state_inactive")
    if approval.approval_id in state.revoked_approvals:
        evaluation.deny("approval_revoked")
    if approval.approval_id in state.consumed_approvals:
        evaluation.deny("approval_replayed")
    if approval.approval_id not in state.active_approvals:
        evaluation.deny("approval_not_active")
    if approval.policy_version != state.version:
        evaluation.deny("policy_version_mismatch")


def _check_timing(request, evaluation):
    approval = request.approval
    evaluation.check("approval_expiration")
    lifetime = (approval.expires_datetime - approval.issued_datetime).total_seconds()
    if approval.issued_datetime > request.evaluated_datetime:
        evaluation.deny("approval_not_yet_valid")
    if approval.expires_datetime <= request.evaluated_datetime:
        evaluation.deny("approval_expired")
    if lifetime <= 0 or lifetime > MAX_APPROVAL_LIFETIME_SECONDS:
        evaluation.deny("approval_lifetime_too_long")


def _check_action(request, task, evaluation):
    action = request.action
    evaluation.check("requested_action")
    if action in RESTRICTED_ACTIONS:
        evaluation.deny("restricted_action_requested")
    elif action not in APPROVED_TASK_ACTIONS:
        evaluation.deny("unauthorized_action")
    requested = task.get("requested_actions")
    if not isinstance(requested, list) or action not in requested:
        evaluation.deny("action_not_requested")
    if request.approval.action != action:
        evaluation.deny("approval_action_mismatch")


def _check_binding(request, task, evaluation):
    approval = request.approval
    evaluation.check("approval_binding")
    if approval.task_id != request.task_id:
        evaluation.deny("cross_task_authorization_denied")
    if approval.agent not in WORKER_ROLES or approval.agent != task.get("assigned_agent"):
        evaluation.deny("approval_agent_mismatch")
    if task.get("status") not in ACTIONABLE_STATUSES:
        evaluation.deny("task_not_actionable")


def _check_scope(request, task, evaluation):
    approval = request.approval
    evaluation.check("approval_scope_and_staleness")
    try:
        expected_fingerprint = task_fingerprint(task)
        expected_paths = _task_paths(task.get("affected_files"))
    except ModelValidationError:
        evaluation.deny("task_identity_invalid")
        return
    if approval.task_fingerprint != expected_fingerprint:
        evaluation.deny("stale_approval")
    scope = approval.scope
    if (scope.repository != task.get("repository")
            or scope.branch != task.get("branch")
            or scope.affected_files != expected_paths
            or scope.source_sha != task.get("source_sha")):
        evaluation.deny("stale_approval")


def evaluate_approval(request):
    """Return a deterministic advisory decision for one approval request."""
    evaluation = _Evaluation()

    if (not isinstance(request, dict) or not set(request) <= REQUEST_KEYS
            or "schema_version" not in request
            or "manifest" not in request):
        evaluation.deny("malformed_request")
        return evaluation.finalize()

    missing = REQUEST_KEYS - set(request)
    if "approval" in missing:
        evaluation.deny("missing_approval")
    if "policy_state" in missing:
        evaluation.unverified("missing_required_evidence")
    if missing - {"approval", "policy_state"}:
        evaluation.deny("malformed_request")
    if request.get("mode") != MODE_DRY_RUN:
        evaluation.deny("dry_run_required")
        evaluation.check("dry_run_mode")
        return evaluation.finalize()
    if missing:
        return evaluation.finalize()

    try:
        parsed = ApprovalRequest.from_json(request)
    except ModelValidationError as exc:
        if exc.reason == "validator_unavailable":
            evaluation.unverified("validator_unavailable")
        elif exc.reason == "malformed_approval_scope":
            evaluation.deny("malformed_approval_scope")
        else:
            evaluation.deny(exc.reason)
        return evaluation.finalize()
    _set_audit_context(evaluation, parsed)
    evaluation.result["summary"]["approvals"] = 1
    evaluation.check("request_shape")

    if IMPORT_ERROR:
        evaluation.result["errors"].append(IMPORT_ERROR)
        evaluation.unverified("validator_unavailable")
        return evaluation.finalize()
    try:
        validation = evaluate(parsed.manifest)
    except Exception:  # fail closed on unexpected shared-contract errors
        evaluation.unverified("validator_unavailable")
        return evaluation.finalize()
    if (not isinstance(validation, dict)
            or validation.get("decision") not in KNOWN_DECISIONS):
        evaluation.unverified("validator_decision_unknown")
        return evaluation.finalize()

    evaluation.result["validator_decision"] = validation["decision"]
    evaluation.check("shared_contract")
    if validation["decision"] == "FAIL":
        evaluation.deny("contract_validation_failed")
    elif validation["decision"] == "BLOCKED":
        evaluation.deny("contract_blocked")
    if validation.get("conflicts"):
        evaluation.deny("ownership_conflict")
    if validation.get("blocked_tasks"):
        evaluation.deny("blocked_task")

    by_id = _task_by_id(parsed.manifest)
    tasks = parsed.manifest.get("tasks")
    evaluation.result["summary"]["tasks"] = len(tasks) if isinstance(tasks, list) else 0
    evaluation.result["summary"]["active_tasks"] = sum(
        1 for task in tasks if isinstance(task, dict) and task.get("status") != "complete"
    ) if isinstance(tasks, list) else 0
    agents = parsed.manifest.get("agents")
    evaluation.result["summary"]["agents"] = sorted(
        name for name in agents if name in WORKER_ROLES
    ) if isinstance(agents, dict) else []

    if parsed.task_id not in by_id:
        evaluation.deny("unknown_task")
        return evaluation.finalize()

    task = by_id[parsed.task_id]
    _check_policy_state(parsed, evaluation)
    _check_timing(parsed, evaluation)
    _check_action(parsed, task, evaluation)
    _check_binding(parsed, task, evaluation)
    _check_scope(parsed, task, evaluation)
    return evaluation.finalize()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_request(path):
    """Read one bounded UTF-8 JSON request without following links or duplicates."""
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("request path must be a regular file")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("request exceeds 512 KiB")
    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ValueError("byte-order mark is not allowed")
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def exit_code(decision):
    if decision == "ALLOW":
        return EXIT_ALLOW
    if decision == "DENY":
        return EXIT_DENY
    return EXIT_UNVERIFIED


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=pathlib.Path,
                        help="Path to a local offline JSON approval request")
    args = parser.parse_args(argv)
    try:
        request = load_request(args.request)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        evaluation = _Evaluation()
        evaluation.deny("malformed_request")
        evaluation.result["errors"].append("invalid request: " + type(exc).__name__)
        result = evaluation.finalize()
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return EXIT_DENY

    result = evaluate_approval(request)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return exit_code(result["decision"])


if __name__ == "__main__":
    sys.exit(main())

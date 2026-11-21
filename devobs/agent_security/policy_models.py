"""Bounded data models for offline, human-approval gate requests.

The models parse untrusted JSON into fixed-shape records. They never read files,
call services, execute commands, or echo supplied values in errors. Fingerprints
are deterministic SHA-256 digests of canonicalized task data; they are staleness
evidence, not signatures and not approval grants.
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from check_two_agent_tasks import (
        BRANCH_RE,
        ID_RE,
        MAX_MANIFEST_BYTES,
        REPO_RE,
        SHA_RE,
        _normal_path,
    )
except ImportError:  # fail closed when the shared contract is unavailable
    SHARED_IMPORT_ERROR = "shared validator import failed"
else:
    SHARED_IMPORT_ERROR = None

SCHEMA_VERSION = 1
MODE_DRY_RUN = "DRY_RUN"
MAX_APPROVAL_LIFETIME_SECONDS = 7 * 24 * 60 * 60
POLICY_STATUSES = frozenset(("ACTIVE", "SUSPENDED", "REVOKED"))
PROTECTED_BRANCHES = frozenset(("main", "master", "develop", "release"))
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
REQUEST_KEYS = frozenset((
    "schema_version", "mode", "task_id", "requested_action", "manifest",
    "approval", "policy_state", "evaluated_at",
))
APPROVAL_KEYS = frozenset((
    "schema_version", "approval_id", "task_id", "agent", "action", "scope",
    "task_fingerprint", "policy_version", "issued_at", "expires_at",
))
SCOPE_KEYS = frozenset(("repository", "branch", "affected_files", "source_sha"))
POLICY_STATE_KEYS = frozenset((
    "schema_version", "status", "version", "active_approvals", "revoked_approvals",
    "consumed_approvals",
))


class ModelValidationError(ValueError):
    """A fail-closed parse error carrying only a stable reason code."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _text(value, limit=200):
    return isinstance(value, str) and 0 < len(value) <= limit


def _positive_int(value):
    return type(value) is int and 1 <= value <= 2_147_483_647


def _timestamp(value, reason):
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise ModelValidationError(reason)
    try:
        parsed = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ModelValidationError(reason) from exc
    return parsed.replace(tzinfo=datetime.timezone.utc)


def _fingerprint_text(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _task_paths(value, reason="task_identity_invalid"):
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        raise ModelValidationError(reason)
    normalised = [_normal_path(path) for path in value]
    if any(path is None for path in normalised) or len(set(normalised)) != len(normalised):
        raise ModelValidationError(reason)
    return tuple(sorted(normalised))


def task_fingerprint(task):
    """Return a canonical staleness digest for one proposed task."""
    if SHARED_IMPORT_ERROR:
        raise ModelValidationError("validator_unavailable")
    if not isinstance(task, dict) or not _text(task.get("id"), 64):
        raise ModelValidationError("task_identity_invalid")
    if not isinstance(task.get("requested_actions"), list):
        raise ModelValidationError("task_identity_invalid")
    actions = task["requested_actions"]
    if any(not isinstance(action, str) or not _text(action, 100) for action in actions):
        raise ModelValidationError("task_identity_invalid")
    source_sha = task.get("source_sha")
    if source_sha is not None and (
            not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha)):
        raise ModelValidationError("task_identity_invalid")
    payload = {
        "task_id": task["id"],
        "repository": task.get("repository"),
        "agent": task.get("assigned_agent"),
        "branch": task.get("branch"),
        "affected_files": list(_task_paths(task.get("affected_files"))),
        "status": task.get("status"),
        "source_sha": source_sha,
        "requested_actions": sorted(actions),
    }
    return _fingerprint_text(payload)


@dataclass(frozen=True)
class ApprovalScope:
    """The exact task context an approval was recorded for."""

    repository: str
    branch: str
    affected_files: tuple
    source_sha: object

    @classmethod
    def from_json(cls, value):
        if not isinstance(value, dict) or set(value) != SCOPE_KEYS:
            raise ModelValidationError("malformed_approval_scope")
        if SHARED_IMPORT_ERROR:
            raise ModelValidationError("validator_unavailable")
        repository = value["repository"]
        branch = value["branch"]
        source_sha = value["source_sha"]
        if (not _text(repository, 200) or not REPO_RE.fullmatch(repository)
                or not _text(branch, 200) or not BRANCH_RE.fullmatch(branch)
                or branch.casefold() in PROTECTED_BRANCHES):
            raise ModelValidationError("malformed_approval_scope")
        if source_sha is not None and (
                not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha)):
            raise ModelValidationError("malformed_approval_scope")
        return cls(repository, branch, _task_paths(
            value["affected_files"], "malformed_approval_scope"), source_sha)

    def canonical(self):
        return {
            "repository": self.repository,
            "branch": self.branch,
            "affected_files": list(self.affected_files),
            "source_sha": self.source_sha,
        }


@dataclass(frozen=True)
class ApprovalRecord:
    """One bounded, non-executable approval record."""

    approval_id: str
    task_id: str
    agent: str
    action: str
    scope: ApprovalScope
    task_fingerprint: str
    policy_version: int
    issued_at: str
    expires_at: str
    issued_datetime: object
    expires_datetime: object

    @classmethod
    def from_json(cls, value):
        if not isinstance(value, dict) or set(value) != APPROVAL_KEYS:
            raise ModelValidationError("malformed_approval")
        if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
            raise ModelValidationError("malformed_approval")
        if SHARED_IMPORT_ERROR:
            raise ModelValidationError("validator_unavailable")
        approval_id = value["approval_id"]
        task_id = value["task_id"]
        if (not isinstance(approval_id, str) or not ID_RE.fullmatch(approval_id)
                or not isinstance(task_id, str) or not ID_RE.fullmatch(task_id)):
            raise ModelValidationError("malformed_approval")
        agent = value["agent"]
        action = value["action"]
        fingerprint = value["task_fingerprint"]
        if (not _text(agent, 40) or not _text(action, 100)
                or not isinstance(fingerprint, str)
                or not FINGERPRINT_RE.fullmatch(fingerprint)
                or not _positive_int(value["policy_version"])):
            raise ModelValidationError("malformed_approval")
        issued = _timestamp(value["issued_at"], "malformed_approval")
        expires = _timestamp(value["expires_at"], "malformed_approval")
        return cls(
            approval_id=approval_id,
            task_id=task_id,
            agent=agent,
            action=action,
            scope=ApprovalScope.from_json(value["scope"]),
            task_fingerprint=fingerprint,
            policy_version=value["policy_version"],
            issued_at=value["issued_at"],
            expires_at=value["expires_at"],
            issued_datetime=issued,
            expires_datetime=expires,
        )

    def digest(self):
        payload = {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "agent": self.agent,
            "action": self.action,
            "scope": self.scope.canonical(),
            "task_fingerprint": self.task_fingerprint,
            "policy_version": self.policy_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }
        return _fingerprint_text(payload)


@dataclass(frozen=True)
class PolicyState:
    """Current approval registry; revocation and consumption outrank active."""

    status: str
    version: int
    active_approvals: frozenset
    revoked_approvals: frozenset
    consumed_approvals: frozenset

    @classmethod
    def from_json(cls, value):
        if not isinstance(value, dict) or set(value) != POLICY_STATE_KEYS:
            raise ModelValidationError("malformed_policy_state")
        if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
            raise ModelValidationError("malformed_policy_state")
        if SHARED_IMPORT_ERROR:
            raise ModelValidationError("validator_unavailable")
        status = value["status"]
        if status not in POLICY_STATUSES or not _positive_int(value["version"]):
            raise ModelValidationError("malformed_policy_state")
        active = value["active_approvals"]
        revoked = value["revoked_approvals"]
        consumed = value["consumed_approvals"]
        if not all(isinstance(items, list) for items in (active, revoked, consumed)):
            raise ModelValidationError("malformed_policy_state")
        if any(len(items) > 200 for items in (active, revoked, consumed)):
            raise ModelValidationError("malformed_policy_state")
        combined = active + revoked + consumed
        if any(not isinstance(item, str) or not ID_RE.fullmatch(item)
               for item in combined):
            raise ModelValidationError("malformed_policy_state")
        active_set = frozenset(active)
        revoked_set = frozenset(revoked)
        consumed_set = frozenset(consumed)
        if any(len(items) != len(set(items))
               for items in (active, revoked, consumed)):
            raise ModelValidationError("malformed_policy_state")
        return cls(status, value["version"], active_set, revoked_set, consumed_set)


@dataclass(frozen=True)
class ApprovalRequest:
    """One DRY_RUN request to validate a human approval against a task."""

    task_id: str
    action: str
    manifest: dict
    approval: ApprovalRecord
    policy_state: PolicyState
    evaluated_datetime: object

    @classmethod
    def from_json(cls, value):
        if not isinstance(value, dict) or set(value) != REQUEST_KEYS:
            raise ModelValidationError("malformed_request")
        if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
            raise ModelValidationError("malformed_request")
        if value["mode"] != MODE_DRY_RUN:
            raise ModelValidationError("dry_run_required")
        if SHARED_IMPORT_ERROR:
            raise ModelValidationError("validator_unavailable")
        task_id = value["task_id"]
        action = value["requested_action"]
        if not isinstance(task_id, str) or not ID_RE.fullmatch(task_id):
            raise ModelValidationError("task_identity_invalid")
        if not _text(action, 100):
            raise ModelValidationError("malformed_request")
        if not isinstance(value["manifest"], dict):
            raise ModelValidationError("malformed_request")
        return cls(
            task_id=task_id,
            action=action,
            manifest=value["manifest"],
            approval=ApprovalRecord.from_json(value["approval"]),
            policy_state=PolicyState.from_json(value["policy_state"]),
            evaluated_datetime=_timestamp(value["evaluated_at"], "malformed_request"),
        )

"""Immutable inputs and exports for the offline orchestration engine."""
from __future__ import annotations

import math
import pathlib
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in ("scripts", "tools"):
    _path = str(_ROOT / _folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from check_two_agent_tasks import APPROVAL_VALUE, RESTRICTED_ACTIONS, TASK_KEYS  # noqa: E402

from .audit import safe_value, scope_fingerprint  # noqa: E402

MODE_DRY_RUN = "DRY_RUN"
PASS = "PASS"
BLOCKED = "BLOCKED"
FAIL = "FAIL"
PENDING_HUMAN = APPROVAL_VALUE
MANIFEST_TASK_KEYS = frozenset(TASK_KEYS)
DEFAULT_APPROVALS = {action: PENDING_HUMAN for action in RESTRICTED_ACTIONS}
DEFAULT_VERIFICATION = {"commands": [], "result": "PENDING", "evidence": ""}


class ModelError(ValueError):
    """A bounded input violates the orchestration model contract."""


def _is_number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _text_tuple(name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ModelError(f"{name} must be a sequence of strings")
    result = tuple(value)
    if any(not isinstance(item, str) or not item for item in result):
        raise ModelError(f"{name} must contain non-empty strings")
    return result


@dataclass(frozen=True)
class TaskSpec:
    """One work item with canonical manifest fields plus advisory metadata."""

    task_id: str
    owner: str
    repository: str
    branch: str
    affected_files: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    status: str = "planned"
    previous_status: str = "none"
    source_sha: str | None = None
    verification: Mapping[str, Any] = field(default_factory=lambda: dict(DEFAULT_VERIFICATION))
    pr_reference: str | None = None
    requested_actions: tuple[str, ...] = ("code_change",)
    estimated_cost_usd: float | None = None
    provider_calls: int = 0
    failure_code: str | None = None
    failure_attempt: int = 0

    def __post_init__(self) -> None:
        for name in ("task_id", "owner", "repository", "branch"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ModelError(f"{name} must be a non-empty string")
        object.__setattr__(self, "affected_files", _text_tuple("affected_files", self.affected_files))
        object.__setattr__(self, "dependencies", _text_tuple("dependencies", self.dependencies))
        object.__setattr__(self, "requested_actions",
                           _text_tuple("requested_actions", self.requested_actions))
        if not isinstance(self.verification, Mapping):
            raise ModelError("verification must be a mapping")
        if self.estimated_cost_usd is not None and (
                not _is_number(self.estimated_cost_usd) or self.estimated_cost_usd < 0):
            raise ModelError("estimated_cost_usd must be a non-negative finite number")
        if not _is_count(self.provider_calls) or not _is_count(self.failure_attempt):
            raise ModelError("provider_calls and failure_attempt must be non-negative integers")
        if self.source_sha is not None and not isinstance(self.source_sha, str):
            raise ModelError("source_sha must be a string or null")

    def to_manifest_record(self) -> dict[str, Any]:
        """Return only the canonical validator fields, never advisory metadata."""
        return {
            "id": self.task_id,
            "repository": self.repository,
            "assigned_agent": self.owner,
            "branch": self.branch,
            "affected_files": list(self.affected_files),
            "dependencies": list(self.dependencies),
            "status": self.status,
            "previous_status": self.previous_status,
            "source_sha": self.source_sha,
            "verification": dict(self.verification),
            "pr_reference": self.pr_reference,
            "requested_actions": list(self.requested_actions),
        }

    @classmethod
    def from_manifest_record(cls, record: Mapping[str, Any], *,
                             metadata: Mapping[str, Any] | None = None) -> "TaskSpec":
        """Build a task from a canonical record and optional advisory metadata."""
        if not isinstance(record, Mapping):
            raise ModelError("task record must be a mapping")
        try:
            values = {
                "task_id": record["id"],
                "owner": record["assigned_agent"],
                "repository": record["repository"],
                "branch": record["branch"],
                "affected_files": tuple(record["affected_files"]),
                "dependencies": tuple(record["dependencies"]),
                "status": record["status"],
                "previous_status": record["previous_status"],
                "source_sha": record["source_sha"],
                "verification": dict(record["verification"]),
                "pr_reference": record["pr_reference"],
                "requested_actions": tuple(record["requested_actions"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelError("incomplete canonical task record") from exc
        values.update(dict(metadata or {}))
        try:
            return cls(**values)
        except TypeError as exc:
            raise ModelError("invalid advisory task metadata") from exc


@dataclass(frozen=True)
class CapacitySnapshot:
    """Caller-supplied capacity evidence; no capacity provider is contacted."""

    global_slots: int
    owner_slots: Mapping[str, int] = field(default_factory=dict)
    supports_priority: bool = False
    source: str = "injected"

    def __post_init__(self) -> None:
        if not _is_count(self.global_slots):
            raise ModelError("global_slots must be a non-negative integer")
        if not isinstance(self.owner_slots, Mapping):
            raise ModelError("owner_slots must be a mapping")
        if any(not isinstance(key, str) or not _is_count(value)
               for key, value in self.owner_slots.items()):
            raise ModelError("owner_slots must map owner names to non-negative integers")
        if not isinstance(self.supports_priority, bool):
            raise ModelError("supports_priority must be a boolean")


@dataclass(frozen=True)
class BudgetSnapshot:
    """Explicit budget state. Absent approval always blocks billable work."""

    approved: bool = False
    max_usd: float | None = None
    spent_usd: float = 0.0
    max_provider_calls: int = 0
    provider_calls: int = 0
    measured_baseline: bool = False
    source: str = "injected"

    def __post_init__(self) -> None:
        if not isinstance(self.approved, bool) or not isinstance(self.measured_baseline, bool):
            raise ModelError("approval and baseline flags must be booleans")
        if self.max_usd is not None and (not _is_number(self.max_usd) or self.max_usd < 0):
            raise ModelError("max_usd must be null or a non-negative finite number")
        if not _is_number(self.spent_usd) or self.spent_usd < 0:
            raise ModelError("spent_usd must be a non-negative finite number")
        if not _is_count(self.max_provider_calls) or not _is_count(self.provider_calls):
            raise ModelError("provider call limits and usage must be non-negative integers")


@dataclass(frozen=True)
class Assignment:
    """A proposed assignment that has not been dispatched."""

    task_id: str
    owner: str
    branch: str
    dependencies: tuple[str, ...]
    affected_files: tuple[str, ...]
    reason: str
    priority_rank: int = 0


@dataclass(frozen=True)
class BlockedTask:
    """A task that must not start under the current evidence and capacity."""

    task_id: str
    reason: str
    owner: str = ""
    dependencies: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class ApprovalBinding:
    """Result of binding an explicit human decision to one exact preview."""

    authorized: bool
    status: str
    reason: str
    final_state: str
    plan_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return safe_value(asdict(self))


@dataclass(frozen=True)
class Plan:
    """A deterministic advisory preview. It contains no execution capability."""

    assignments: tuple[Assignment, ...] = ()
    blocked: tuple[BlockedTask, ...] = ()
    events: tuple[Any, ...] = ()
    approvals: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_APPROVALS))
    summary: Mapping[str, Any] = field(default_factory=dict)
    decision: str = PASS
    errors: tuple[str, ...] = ()
    budget: Mapping[str, Any] = field(default_factory=dict)
    safety: Mapping[str, Any] = field(default_factory=lambda: {
        "executor_enabled": False,
        "network_calls_allowed": False,
        "mutations_allowed": False,
        "repository_state_changes": False,
        "external_actions": (),
        "human_gate": "PENDING HUMAN APPROVAL",
    })
    policy: Mapping[str, Any] = field(default_factory=dict)
    mode: str = MODE_DRY_RUN
    manifest_tasks: tuple[Mapping[str, Any], ...] = ()

    def unsigned_dict(self) -> dict[str, Any]:
        """Return the stable payload that is bound to the approval fingerprint."""
        payload = {
            "mode": self.mode,
            "decision": self.decision,
            "assignments": [asdict(item) for item in self.assignments],
            "blocked": [asdict(item) for item in self.blocked],
            "events": list(self.events),
            "approval": dict(self.approvals),
            "budget": dict(self.budget),
            "policy": dict(self.policy),
            "safety": dict(self.safety),
            "errors": list(self.errors),
            "summary": dict(self.summary),
            "manifest_tasks": list(self.manifest_tasks),
            "dispatched": False,
            "apply": False,
        }
        return safe_value(payload)

    def to_dict(self) -> dict[str, Any]:
        result = self.unsigned_dict()
        result["fingerprint"] = scope_fingerprint(result)
        return result


__all__ = [
    "BLOCKED",
    "DEFAULT_APPROVALS",
    "FAIL",
    "MANIFEST_TASK_KEYS",
    "MODE_DRY_RUN",
    "PENDING_HUMAN",
    "PASS",
    "RESTRICTED_ACTIONS",
    "ApprovalBinding",
    "Assignment",
    "BlockedTask",
    "BudgetSnapshot",
    "CapacitySnapshot",
    "ModelError",
    "Plan",
    "TaskSpec",
]

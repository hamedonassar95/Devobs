"""Advisory multi-agent work planner.

The orchestrator produces a dependency-ordered DRY_RUN plan from a task
registry, canonical conflict policy, injected capacity evidence, and optional
delivery evidence. It intentionally has no execution entry point and performs
no network, Git, GitHub, approval, merge, or deployment action.
"""

from __future__ import annotations

import copy
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_tools = str(_ROOT / "tools")
if _tools not in sys.path:
    sys.path.insert(0, _tools)

from agent_task_status_report import sanitize_display  # noqa: E402

from .conflict_detector import ConflictDetector  # noqa: E402
from .delivery_tracker import BLOCKED as DELIVERY_BLOCKED  # noqa: E402
from .delivery_tracker import DeliveryTracker, redact_secrets  # noqa: E402
from .task_registry import TaskRegistry  # noqa: E402

MODE_DRY_RUN = "DRY_RUN"
BLOCKED = "BLOCKED"
FAIL = "FAIL"
RESTRICTED_ACTIONS = ("merge", "deploy", "billing", "production")
PENDING_HUMAN = "pending_human"


@dataclass(frozen=True)
class CapacitySnapshot:
    """Caller-supplied capacity evidence; no capacity provider is contacted."""

    global_slots: int
    owner_slots: Mapping[str, int] = field(default_factory=dict)
    source: str = "injected"


@dataclass(frozen=True)
class Assignment:
    """A proposed assignment that has not been dispatched."""

    task_id: str
    owner: str
    branch: str
    dependencies: tuple[str, ...]
    affected_files: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class BlockedTask:
    """A task that must not start under the current evidence and capacity."""

    task_id: str
    reason: str
    owner: str = ""
    dependencies: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class OrchestrationPlan:
    """A complete advisory planning result."""

    mode: str
    decision: str
    assignments: tuple[Assignment, ...]
    blocked: tuple[BlockedTask, ...]
    events: tuple[dict[str, Any], ...]
    approval: dict[str, str]
    safety: dict[str, Any]
    delivery: dict[str, Any]
    errors: tuple[str, ...]
    summary: dict[str, Any]
    dispatched: bool = False
    apply: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "decision": self.decision,
            "assignments": [copy.deepcopy(dict(item.__dict__)) for item in self.assignments],
            "blocked": [copy.deepcopy(dict(item.__dict__)) for item in self.blocked],
            "events": copy.deepcopy(list(self.events)),
            "approval": copy.deepcopy(self.approval),
            "safety": copy.deepcopy(self.safety),
            "delivery": copy.deepcopy(self.delivery),
            "errors": list(self.errors),
            "summary": copy.deepcopy(self.summary),
            "dispatched": self.dispatched,
            "apply": self.apply,
        }


def _safe_text(value: Any, limit: int = 300) -> str:
    return redact_secrets(sanitize_display(value, limit=limit))


def _safe_value(value: Any) -> Any:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, Mapping):
        return {_safe_text(str(key), 80): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return _safe_text(value)


def _event(name: str, **fields: Any) -> dict[str, Any]:
    return {"event": _safe_text(name, 80), **{
        _safe_text(str(key), 80): _safe_value(value) for key, value in fields.items()
    }}


def _valid_capacity(snapshot: Any) -> tuple[bool, str]:
    if not isinstance(snapshot, CapacitySnapshot):
        return False, "capacity_snapshot_missing"
    if isinstance(snapshot.global_slots, bool) or not isinstance(snapshot.global_slots, int):
        return False, "invalid_capacity"
    if snapshot.global_slots < 0:
        return False, "invalid_capacity"
    if not isinstance(snapshot.owner_slots, Mapping):
        return False, "invalid_capacity"
    for value in snapshot.owner_slots.values():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return False, "invalid_capacity"
    return True, ""


def _topological_order(registry: TaskRegistry) -> tuple[list[str], list[str]]:
    remaining = {snapshot.task.task_id: snapshot.task for snapshot in registry.list()}
    order: list[str] = []
    while remaining:
        ready = sorted(
            task_id for task_id, task in remaining.items()
            if all(dependency not in remaining for dependency in task.dependencies)
        )
        if not ready:
            return order, sorted(remaining)
        order.extend(ready)
        for task_id in ready:
            remaining.pop(task_id)
    return order, []


def _empty_plan(decision: str, errors: tuple[str, ...], events: list[dict[str, Any]],
                *, delivery: dict[str, Any] | None = None,
                summary: dict[str, Any] | None = None) -> OrchestrationPlan:
    return OrchestrationPlan(
        mode=MODE_DRY_RUN,
        decision=decision,
        assignments=(),
        blocked=(),
        events=tuple(events),
        approval={action: PENDING_HUMAN for action in RESTRICTED_ACTIONS},
        safety={
            "executor_enabled": False,
            "network_calls_allowed": False,
            "mutations_allowed": False,
            "repository_state_changes": False,
            "external_actions": (),
            "human_gate": "PENDING HUMAN APPROVAL",
        },
        delivery=delivery or {"status": "UNVERIFIED", "tasks": {}},
        errors=errors,
        summary=summary or {"assignments": 0, "blocked": 0},
        dispatched=False,
        apply=False,
    )


class WorkOrchestrator:
    """Build advisory plans; deliberately exposes no execution methods."""

    def __init__(
        self,
        registry: TaskRegistry,
        capacity: CapacitySnapshot,
        delivery_tracker: DeliveryTracker | None = None,
        detector: ConflictDetector | None = None,
    ):
        self.registry = registry
        self.capacity = capacity
        self.delivery_tracker = delivery_tracker
        self.detector = detector or ConflictDetector(registry)

    def plan(self) -> OrchestrationPlan:
        events: list[dict[str, Any]] = []
        try:
            valid, reason = _valid_capacity(self.capacity)
            events.append(_event("capacity_validated", valid=valid, source=self.capacity.source))
            if not valid:
                return _empty_plan(FAIL, (reason,), events)

            conflicts = self.detector.evaluate()
            events.append(_event(
                "conflict_evaluation",
                decision=getattr(conflicts, "decision", "UNKNOWN"),
                findings=len(getattr(conflicts, "findings", ())),
            ))
            if getattr(conflicts, "decision", None) == FAIL:
                errors = tuple(_safe_text(item, 300)
                               for item in getattr(conflicts, "errors", ())) or ("validator_failed",)
                return _empty_plan(FAIL, errors, events)
            if getattr(conflicts, "decision", None) not in ("PASS", BLOCKED):
                return _empty_plan(FAIL, ("unknown_conflict_decision",), events)

            order, cycles = _topological_order(self.registry)
            order_index = {task_id: index for index, task_id in enumerate(order)}
            findings = tuple(getattr(conflicts, "findings", ()))
            hard_blocked = {
                task_id
                for finding in findings
                if finding.reason != "unresolved_dependency"
                for task_id in finding.task_ids
            }

            def can_sequence(task_id: str) -> bool:
                """A same-plan dependency is sequencing, not a hard block."""
                task = self.registry.get(task_id).task
                for dependency in task.dependencies:
                    if dependency in cycles or dependency in hard_blocked:
                        return False
                    dependency_task = self.registry.get(dependency).task
                    if dependency_task.status == "blocked":
                        return False
                    if dependency not in order_index:
                        return False
                    if order_index[dependency] >= order_index.get(task_id, len(order)):
                        return False
                return True

            blocked_by_validator: dict[str, tuple[str, str]] = {}
            for finding in findings:
                reason = "validator_conflict" if finding.kind == "conflict" else finding.reason
                detail = finding.reason if finding.kind == "conflict" else finding.detail
                for task_id in finding.task_ids:
                    if finding.reason == "unresolved_dependency" and can_sequence(task_id):
                        continue
                    blocked_by_validator.setdefault(task_id, (reason, detail))

            delivery = self._delivery_view(events)
            delivery_blocked = {
                task_id for task_id, value in delivery["tasks"].items()
                if value.get("status") == DELIVERY_BLOCKED
            }

            blocked: list[BlockedTask] = []
            assignments: list[Assignment] = []
            used_global = 0
            used_owner: dict[str, int] = {}

            for task_id in cycles:
                item = BlockedTask(task_id, "dependency_cycle")
                blocked.append(item)
                events.append(_event("task_blocked", task_id=task_id, reason=item.reason))

            for task_id in order:
                snapshot = self.registry.get(task_id)
                task = snapshot.task
                block = blocked_by_validator.get(task_id)
                if block is not None:
                    item = BlockedTask(task_id, block[0], task.owner,
                                       task.dependencies, block[1])
                elif task_id in cycles:
                    continue
                elif task.status != "planned":
                    events.append(_event("task_skipped", task_id=task_id, status=task.status))
                    continue
                elif task_id in delivery_blocked:
                    item = BlockedTask(task_id, "delivery_blocked", task.owner,
                                       task.dependencies)
                elif used_global >= self.capacity.global_slots:
                    item = BlockedTask(task_id, "capacity_exhausted", task.owner,
                                       task.dependencies)
                elif task.owner not in self.capacity.owner_slots:
                    item = BlockedTask(task_id, "owner_capacity_unavailable", task.owner,
                                       task.dependencies)
                elif used_owner.get(task.owner, 0) >= self.capacity.owner_slots[task.owner]:
                    item = BlockedTask(task_id, "owner_capacity_exhausted", task.owner,
                                       task.dependencies)
                else:
                    assignments.append(Assignment(
                        task_id=task_id,
                        owner=task.owner,
                        branch=task.branch,
                        dependencies=task.dependencies,
                        affected_files=task.affected_files,
                        reason="dry_run_dependency_ordered",
                    ))
                    used_global += 1
                    used_owner[task.owner] = used_owner.get(task.owner, 0) + 1
                    events.append(_event("task_scheduled", task_id=task_id, owner=task.owner))
                    continue

                blocked.append(item)
                events.append(_event("task_blocked", task_id=task_id,
                                     reason=item.reason, owner=item.owner))

            if blocked:
                decision = BLOCKED
            else:
                decision = "PASS"
            summary = {
                "assignments": len(assignments),
                "blocked": len(blocked),
                "total_tasks": len(order) + len(cycles),
                "capacity_source": _safe_text(self.capacity.source, 100),
            }
            events.append(_event("plan_created", decision=decision,
                                 assignments=len(assignments), blocked=len(blocked)))
            return OrchestrationPlan(
                mode=MODE_DRY_RUN,
                decision=decision,
                assignments=tuple(assignments),
                blocked=tuple(blocked),
                events=tuple(events),
                approval={action: PENDING_HUMAN for action in RESTRICTED_ACTIONS},
                safety={
                    "executor_enabled": False,
                    "network_calls_allowed": False,
                    "mutations_allowed": False,
                    "repository_state_changes": False,
                    "external_actions": (),
                    "human_gate": "PENDING HUMAN APPROVAL",
                },
                delivery=delivery,
                errors=(),
                summary=summary,
                dispatched=False,
                apply=False,
            )
        except Exception as exc:  # fail closed instead of emitting a partial plan
            events.append(_event("plan_failed", error_type=type(exc).__name__))
            return _empty_plan(FAIL, (f"planning_failure:{type(exc).__name__}",), events)

    def _delivery_view(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        if self.delivery_tracker is None:
            return {"status": "UNVERIFIED", "tasks": {}}
        try:
            report = self.delivery_tracker.report()
        except Exception as exc:
            events.append(_event("delivery_failure", error_type=type(exc).__name__))
            return {"status": "FAIL", "tasks": {}, "error": f"delivery_failure:{type(exc).__name__}"}
        tasks = {}
        for update in report.updates:
            tasks[_safe_text(update.task_id, 80)] = {
                "status": _safe_text(update.status, 80),
                "reasons": tuple(_safe_text(item, 200) for item in update.reasons),
                "evidence_excerpt": _safe_text(update.evidence_excerpt, 300),
            }
        events.append(_event("delivery_classified", status=report.status,
                             tasks=len(report.updates)))
        return {
            "status": _safe_text(report.status, 80),
            "tasks": tasks,
            "summary": {key: _safe_value(value) for key, value in report.summary.items()},
        }


__all__ = [
    "MODE_DRY_RUN",
    "Assignment",
    "BlockedTask",
    "CapacitySnapshot",
    "OrchestrationPlan",
    "WorkOrchestrator",
]

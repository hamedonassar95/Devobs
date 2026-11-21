"""Deterministic, offline DRY_RUN planner for advisory multi-agent work."""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict
from functools import lru_cache
from typing import Any, Callable, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_scripts = str(_ROOT / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from check_two_agent_tasks import (  # noqa: E402
    APPROVAL_VALUE,
    WORKER_ROLES,
    evaluate as canonical_evaluate,
)

from .audit import (  # noqa: E402
    POLICY,
    RETRYABLE,
    TERMINAL,
    AuditTrail,
    classify_failure,
    sanitize,
)
from .models import (  # noqa: E402
    BLOCKED,
    FAIL,
    PASS,
    RESTRICTED_ACTIONS,
    Assignment,
    BlockedTask,
    BudgetSnapshot,
    CapacitySnapshot,
    Plan,
    TaskSpec,
)
from .policy_adapter import OrchestrationPolicy, evaluate_task  # noqa: E402

Validator = Callable[[dict[str, Any]], dict[str, Any]]
KNOWN_DECISIONS = frozenset((PASS, BLOCKED, FAIL))


class Planner:
    """Build a complete advisory plan. Deliberately exposes no execution method."""

    def __init__(self, tasks: tuple[TaskSpec, ...] | list[TaskSpec],
                 capacity: CapacitySnapshot, policy: OrchestrationPolicy,
                 budget: BudgetSnapshot, *, validator: Validator | None = None,
                 plan_id: str = "advisory-plan"):
        self.tasks = tuple(sorted(tasks, key=lambda item: item.task_id))
        self.capacity = capacity
        self.policy = policy
        self.budget = budget
        self.validator = validator or canonical_evaluate
        self.plan_id = plan_id

    def plan(self) -> Plan:
        trail = AuditTrail(self.plan_id)
        try:
            by_id = {task.task_id: task for task in self.tasks}
            if len(by_id) != len(self.tasks):
                return self._fail(trail, ("duplicate_task_id",))
            graph_errors = self._validate_graph(by_id)
            if graph_errors:
                return self._fail(trail, graph_errors)
            trail.record("graph_validated", tasks=len(by_id))

            manifest = self._manifest()
            validation = self.validator(manifest)
            if not isinstance(validation, Mapping):
                return self._fail(trail, ("validator_returned_unexpected_shape",))
            decision = validation.get("decision")
            if decision not in KNOWN_DECISIONS:
                return self._fail(trail, ("validator_returned_unknown_decision",))
            errors = self._texts(validation.get("errors", []))
            trail.record("canonical_validator", decision=decision, issues=len(errors))
            if decision == FAIL:
                return self._fail(trail, errors or ("validator_failed",))

            cycles = self._cycles(by_id)
            order = self._order(by_id, cycles)
            hard = self._hard_blocks(validation, by_id)
            decisions = {}
            for task_id, task in by_id.items():
                result = evaluate_task(task, self.policy, self.budget)
                decisions[task_id] = result
                if not result.allowed:
                    hard.setdefault(task_id, ("policy_denied", ", ".join(result.reasons)))
                if task.failure_code:
                    classification = classify_failure(
                        task.failure_code,
                        attempt=task.failure_attempt,
                        max_retries=result.max_retries,
                    )
                    if not classification.retry_allowed:
                        hard.setdefault(task_id, (self._failure_reason(classification.category),
                                                  classification.reason))
            trail.record("ordering_selected",
                         priority_enabled=self.capacity.supports_priority,
                         ordered_tasks=len(order))

            assignments: list[Assignment] = []
            blocked: list[BlockedTask] = []
            used_global = 0
            used_owner: dict[str, int] = {}
            for task_id in order:
                task = by_id[task_id]
                if task_id in cycles:
                    continue
                if task_id in hard:
                    reason, detail = hard[task_id]
                    item = BlockedTask(task_id, reason, task.owner,
                                       task.dependencies, detail)
                elif task.status != "planned":
                    trail.record("task_skipped", task_id=task_id, status=task.status)
                    continue
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
                    reason = ("retry_eligible" if task.failure_code
                              and classify_failure(
                                  task.failure_code,
                                  attempt=task.failure_attempt,
                                  max_retries=decisions[task_id].max_retries,
                              ).retry_allowed else "dry_run_dependency_ordered")
                    assignments.append(Assignment(
                        task_id=task_id,
                        owner=task.owner,
                        branch=task.branch,
                        dependencies=task.dependencies,
                        affected_files=task.affected_files,
                        reason=reason,
                        priority_rank=len(assignments),
                    ))
                    used_global += 1
                    used_owner[task.owner] = used_owner.get(task.owner, 0) + 1
                    trail.record("task_scheduled", task_id=task_id, owner=task.owner,
                                 reason=reason)
                    continue

                blocked.append(item)
                trail.record("task_blocked", task_id=task_id, reason=item.reason,
                             owner=item.owner)

            result = BLOCKED if blocked else PASS
            trail.record("plan_created", decision=result,
                         assignments=len(assignments), blocked=len(blocked))
            return Plan(
                assignments=tuple(assignments),
                blocked=tuple(blocked),
                events=trail.events,
                decision=result,
                summary={
                    "assignments": len(assignments),
                    "blocked": len(blocked),
                    "total_tasks": len(by_id),
                    "capacity_source": self.capacity.source,
                    "priority_enabled": self.capacity.supports_priority,
                },
                budget=self._budget_view(),
                policy=self._policy_view(),
                manifest_tasks=tuple(manifest["tasks"]),
            )
        except Exception as exc:  # fail closed; never emit a partial plan
            trail.record("plan_failed", error_type=type(exc).__name__)
            return self._fail(trail, (f"planning_failure:{type(exc).__name__}",))

    def _manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "repositories": sorted({task.repository for task in self.tasks}),
            "agents": {role: {"enabled": True} for role in WORKER_ROLES},
            "approval": {action: APPROVAL_VALUE for action in RESTRICTED_ACTIONS},
            "tasks": [task.to_manifest_record() for task in self.tasks],
        }

    @staticmethod
    def _validate_graph(by_id: Mapping[str, TaskSpec]) -> tuple[str, ...]:
        errors: set[str] = set()
        for task_id, task in by_id.items():
            for dependency in task.dependencies:
                if dependency == task_id:
                    errors.add("self_dependency")
                elif dependency not in by_id:
                    errors.add("unknown_dependency")
        return tuple(sorted(errors))

    def _cycles(self, by_id: Mapping[str, TaskSpec]) -> set[str]:
        colour: dict[str, int] = {}
        cyclic: set[str] = set()

        def visit(task_id: str) -> None:
            colour[task_id] = 1
            for dependency in by_id[task_id].dependencies:
                if dependency not in by_id:
                    continue
                if colour.get(dependency) == 1:
                    cyclic.add(task_id)
                elif colour.get(dependency) is None:
                    visit(dependency)
            colour[task_id] = 2

        for task_id in by_id:
            if colour.get(task_id) is None:
                visit(task_id)
        return cyclic

    def _order(self, by_id: Mapping[str, TaskSpec], cycles: set[str]) -> list[str]:
        remaining = set(by_id) - cycles
        dependents: dict[str, list[str]] = defaultdict(list)
        for task_id, task in by_id.items():
            for dependency in task.dependencies:
                dependents[dependency].append(task_id)

        @lru_cache(maxsize=None)
        def longest_path(task_id: str) -> int:
            children = dependents.get(task_id, ())
            return 1 + max((longest_path(child) for child in children), default=0)

        @lru_cache(maxsize=None)
        def downstream_set(task_id: str) -> frozenset[str]:
            found: set[str] = set()
            for child in dependents.get(task_id, ()):
                found.add(child)
                found.update(downstream_set(child))
            return frozenset(found)

        def downstream_count(task_id: str) -> int:
            return len(downstream_set(task_id))

        order: list[str] = []
        while remaining:
            ready = [task_id for task_id in remaining
                     if all(dependency not in remaining
                            for dependency in by_id[task_id].dependencies)]
            if not ready:
                order.extend(sorted(remaining))
                break
            if self.capacity.supports_priority:
                ready.sort(key=lambda item: (-longest_path(item), -downstream_count(item), item))
            else:
                ready.sort()
            order.extend(ready)
            remaining.difference_update(ready)
        return order

    def _hard_blocks(self, validation: Mapping[str, Any],
                     by_id: Mapping[str, TaskSpec]) -> dict[str, tuple[str, str]]:
        hard: dict[str, tuple[str, str]] = {}
        for conflict in validation.get("conflicts", []):
            if not isinstance(conflict, Mapping):
                continue
            reason = sanitize(conflict.get("reason", "validator_conflict"), 80)
            for task_id in conflict.get("tasks", []):
                if isinstance(task_id, str) and task_id in by_id:
                    hard.setdefault(task_id, ("ownership_conflict", reason))
        for item in validation.get("blocked_tasks", []):
            if not isinstance(item, Mapping):
                continue
            task_id = item.get("task")
            reason = sanitize(item.get("reason", "validator_blocked"), 80)
            if not isinstance(task_id, str) or task_id not in by_id:
                continue
            if reason == "unresolved_dependency" and self._sequencing_only(by_id, task_id):
                continue
            hard.setdefault(task_id, ("validator_blocked", reason))
        return hard

    @staticmethod
    def _sequencing_only(by_id: Mapping[str, TaskSpec], task_id: str) -> bool:
        pending = list(by_id[task_id].dependencies)
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current in seen or current not in by_id:
                return False
            seen.add(current)
            if by_id[current].status not in ("planned", "complete"):
                return False
            pending.extend(by_id[current].dependencies)
        return True

    @staticmethod
    def _failure_reason(category: str) -> str:
        if category == TERMINAL:
            return "terminal_failure"
        if category == POLICY:
            return "policy_failure_gate"
        if category == RETRYABLE:
            return "retry_limit_exhausted"
        return "unclassified_failure"

    @staticmethod
    def _texts(values: Any) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)):
            return ()
        return tuple(sanitize(value, 300) for value in values
                     if isinstance(value, (str, int, float, bool)))

    def _budget_view(self) -> dict[str, Any]:
        return {
            "approved": self.budget.approved,
            "max_usd": self.budget.max_usd,
            "spent_usd": self.budget.spent_usd,
            "max_provider_calls": self.budget.max_provider_calls,
            "provider_calls": self.budget.provider_calls,
            "measured_baseline": self.budget.measured_baseline,
            "source": self.budget.source,
        }

    def _policy_view(self) -> dict[str, Any]:
        return {
            "max_retries": self.policy.max_retries,
            "production_mutations_allowed": self.policy.production_mutations_allowed,
            "budget_approval_variable": self.policy.budget_approval_variable,
            "budget_approval_is_dollar_cap": self.policy.budget_approval_is_dollar_cap,
            "source": self.policy.source,
        }

    def _fail(self, trail: AuditTrail, errors: tuple[str, ...]) -> Plan:
        return Plan(
            decision=FAIL,
            errors=self._texts(errors) or ("planning_failed",),
            events=trail.events,
            summary={"assignments": 0, "blocked": 0},
            budget=self._budget_view(),
            policy=self._policy_view(),
        )


__all__ = ["Planner", "Validator"]

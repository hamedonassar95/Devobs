"""Read-only facade binding canonical manifests, plans, and human approval."""
from __future__ import annotations

import copy
import pathlib
import re
import sys
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in ("scripts", "tools"):
    _path = str(_ROOT / _folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from human_approval_gate import evaluate as evaluate_base_approval  # noqa: E402

from .audit import scope_fingerprint, sanitize  # noqa: E402
from .models import (  # noqa: E402
    FAIL,
    MODE_DRY_RUN,
    PENDING_HUMAN,
    RESTRICTED_ACTIONS,
    ApprovalBinding,
    BudgetSnapshot,
    CapacitySnapshot,
    ModelError,
    Plan,
    TaskSpec,
)
from .planner import Planner  # noqa: E402
from .policy_adapter import OrchestrationPolicy, PolicyError, load_policy  # noqa: E402

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")


class Coordinator:
    """Compose previews and bind approvals without any execution capability."""

    def __init__(self, manifest: Mapping[str, Any], tasks: tuple[TaskSpec, ...],
                 capacity: CapacitySnapshot, policy: OrchestrationPolicy,
                 budget: BudgetSnapshot, *, plan_id: str = "advisory-plan",
                 init_error: str | None = None):
        self._manifest = copy.deepcopy(dict(manifest))
        self.tasks = tasks
        self.capacity = capacity
        self.policy = policy
        self.budget = budget
        self.plan_id = plan_id
        self.init_error = init_error
        self.planner = None if init_error else Planner(
            tasks, capacity, policy, budget, plan_id=plan_id)

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, Any], *,
                      capacity: CapacitySnapshot | None = None,
                      budget: BudgetSnapshot | None = None,
                      policy_path: str | pathlib.Path | None = None,
                      metadata: Mapping[str, Mapping[str, Any]] | None = None,
                      plan_id: str = "advisory-plan") -> "Coordinator":
        """Build a coordinator from a canonical manifest. Advisory extras stay separate."""
        empty_capacity = CapacitySnapshot(global_slots=0)
        empty_policy = OrchestrationPolicy(
            max_retries=0,
            production_mutations_allowed=False,
            production_mutations_require_human_approval=True,
            budget_approval_variable="UNKNOWN",
            budget_approval_is_dollar_cap=False,
            unmeasured_baseline_blocks_autonomous_production_use=True,
            agents={},
            source="unavailable",
        )
        try:
            if not isinstance(manifest, Mapping):
                raise ModelError("manifest must be a mapping")
            records = manifest.get("tasks")
            if not isinstance(records, (list, tuple)):
                raise ModelError("manifest tasks must be a sequence")
            extras = dict(metadata or {})
            tasks = tuple(
                TaskSpec.from_manifest_record(
                    record,
                    metadata=extras.get(record.get("id")) if isinstance(record, Mapping) else None,
                )
                for record in records
            )
            policy = load_policy(policy_path)
            if capacity is None:
                owners: dict[str, int] = {}
                for task in tasks:
                    owners[task.owner] = owners.get(task.owner, 0) + 1
                capacity = CapacitySnapshot(global_slots=len(tasks), owner_slots=owners)
            return cls(
                manifest, tasks, capacity, policy, budget or BudgetSnapshot(),
                plan_id=plan_id,
            )
        except (ModelError, PolicyError, TypeError, ValueError) as exc:
            return cls(
                manifest if isinstance(manifest, Mapping) else {}, (),
                empty_capacity, empty_policy, budget or BudgetSnapshot(),
                plan_id=plan_id,
                init_error=f"coordinator_input_error:{type(exc).__name__}",
            )

    def manifest(self) -> dict[str, Any]:
        """Return a deep copy of the canonical manifest used for this preview."""
        return copy.deepcopy(self._manifest)

    def plan(self) -> Plan:
        if self.planner is None:
            return Plan(
                decision=FAIL,
                errors=(self.init_error or "coordinator_unavailable",),
                summary={"assignments": 0, "blocked": 0},
            )
        return self.planner.plan()

    def preview(self) -> dict[str, Any]:
        """Return a deterministic, sanitized, non-dispatching plan preview."""
        return self.plan().to_dict()

    def approve(self, preview: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
        """Bind an explicit human decision to one exact preview; never executes it."""
        fingerprint = sanitize(preview.get("fingerprint", ""), 80) if isinstance(preview, Mapping) else ""
        base = evaluate_base_approval(dict(record)) if isinstance(record, Mapping) else None
        if base is None:
            return ApprovalBinding(False, "BLOCKED", "invalid_approval_record",
                                   "PENDING HUMAN APPROVAL", fingerprint).to_dict()
        if not base.authorized:
            return ApprovalBinding(False, base.status, base.reason, base.final_state,
                                   fingerprint).to_dict()
        if not isinstance(preview, Mapping):
            return ApprovalBinding(False, "BLOCKED", "invalid_plan_preview",
                                   "PENDING HUMAN APPROVAL", fingerprint).to_dict()

        rejection = self._binding_rejection(preview, record)
        if rejection:
            return ApprovalBinding(False, "BLOCKED", rejection,
                                   "PENDING HUMAN APPROVAL", fingerprint).to_dict()
        return ApprovalBinding(
            True, "HUMAN_APPROVED",
            "verified preview explicitly approved by an authorized human",
            "HUMAN APPROVED", fingerprint,
        ).to_dict()

    @staticmethod
    def _binding_rejection(preview: Mapping[str, Any], record: Mapping[str, Any]) -> str:
        unsigned = dict(preview)
        claimed = unsigned.pop("fingerprint", None)
        if not isinstance(claimed, str) or not FINGERPRINT_RE.fullmatch(claimed):
            return "invalid_plan_fingerprint"
        if scope_fingerprint(unsigned) != claimed:
            return "plan_fingerprint_mismatch"
        approved_fingerprint = record.get("scope_fingerprint")
        if (not isinstance(approved_fingerprint, str)
                or not FINGERPRINT_RE.fullmatch(approved_fingerprint)
                or approved_fingerprint != claimed):
            return "approval_fingerprint_mismatch"
        if preview.get("mode") != MODE_DRY_RUN or preview.get("dispatched") is not False \
                or preview.get("apply") is not False:
            return "preview_is_not_read_only"
        if any(preview.get("approval", {}).get(action) != PENDING_HUMAN
               for action in RESTRICTED_ACTIONS):
            return "restricted_approval_not_pending"
        reviewed_sha = record.get("reviewed_sha")
        if not isinstance(reviewed_sha, str) or not SHA_RE.fullmatch(reviewed_sha):
            return "invalid_reviewed_sha"
        assignments = preview.get("assignments")
        if not isinstance(assignments, list):
            return "invalid_plan_scope"
        expected_tasks = sorted(
            item.get("task_id") for item in assignments
            if isinstance(item, Mapping) and isinstance(item.get("task_id"), str)
        )
        approved_tasks = record.get("approved_task_ids")
        if not isinstance(approved_tasks, (list, tuple)) or sorted(approved_tasks) != expected_tasks:
            return "approval_scope_mismatch"
        expected_actions: set[str] = set()
        by_id = {item.get("id"): item for item in Coordinator._manifest_tasks(preview)
                 if isinstance(item, Mapping)}
        for task_id in expected_tasks:
            values = by_id.get(task_id, {}).get("requested_actions", [])
            if isinstance(values, (list, tuple)):
                expected_actions.update(value for value in values if isinstance(value, str))
        approved_actions = record.get("approved_actions")
        if not isinstance(approved_actions, (list, tuple)) \
                or set(approved_actions) != expected_actions:
            return "approval_action_mismatch"
        return ""

    @staticmethod
    def _manifest_tasks(preview: Mapping[str, Any]) -> list[Any]:
        """Use the manifest attached to a preview when present; otherwise none."""
        value = preview.get("manifest_tasks", [])
        return value if isinstance(value, list) else []


__all__ = ["Coordinator"]

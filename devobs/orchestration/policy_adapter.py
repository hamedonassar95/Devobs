"""Read-only adapter for the repository's machine-readable agent policy."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any, Mapping

from .models import BudgetSnapshot, RESTRICTED_ACTIONS, TaskSpec

_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = _ROOT / "agent-spec.yaml"
MAX_SPEC_BYTES = 512 * 1024
REQUIRED_POLICY_KEYS = (
    "max_retries",
    "production_mutations_allowed",
    "production_mutations_require_human_approval",
    "budget_approval_variable",
    "budget_approval_is_dollar_cap",
    "unmeasured_baseline_blocks_autonomous_production_use",
)
REQUIRED_AGENT_KEYS = (
    "id", "max_retries", "max_provider_calls_per_run", "production_write",
)


class PolicyError(ValueError):
    """The policy source is missing, malformed, or unusable."""


@dataclass(frozen=True)
class AgentPolicy:
    agent_id: str
    max_retries: int
    max_provider_calls_per_run: int
    production_write: bool


@dataclass(frozen=True)
class OrchestrationPolicy:
    max_retries: int
    production_mutations_allowed: bool
    production_mutations_require_human_approval: bool
    budget_approval_variable: str
    budget_approval_is_dollar_cap: bool
    unmeasured_baseline_blocks_autonomous_production_use: bool
    agents: Mapping[str, AgentPolicy]
    source: str


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]
    max_retries: int


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load_policy(path: str | pathlib.Path | None = None) -> OrchestrationPolicy:
    """Parse agent-spec.yaml strictly. No environment or credential is read."""
    source = pathlib.Path(path) if path is not None else DEFAULT_SPEC_PATH
    try:
        raw = source.read_text(encoding="utf-8")
        if len(raw.encode("utf-8")) > MAX_SPEC_BYTES:
            raise PolicyError("policy file exceeds 512 KiB")
        document = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise PolicyError("policy source is unreadable or invalid") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise PolicyError("unsupported policy schema")
    policy = document.get("policy")
    if not isinstance(policy, dict) or any(key not in policy for key in REQUIRED_POLICY_KEYS):
        raise PolicyError("policy block is incomplete")
    if not _is_count(policy["max_retries"]):
        raise PolicyError("max_retries must be a non-negative integer")
    for key in ("production_mutations_allowed",
                "production_mutations_require_human_approval",
                "budget_approval_is_dollar_cap",
                "unmeasured_baseline_blocks_autonomous_production_use"):
        if not isinstance(policy[key], bool):
            raise PolicyError(f"{key} must be a boolean")
    if not isinstance(policy["budget_approval_variable"], str) or not policy["budget_approval_variable"]:
        raise PolicyError("budget_approval_variable must be a non-empty string")

    agents_value = document.get("agents")
    if not isinstance(agents_value, list) or not agents_value:
        raise PolicyError("agents must be a non-empty list")
    agents: dict[str, AgentPolicy] = {}
    for record in agents_value:
        if not isinstance(record, dict) or any(key not in record for key in REQUIRED_AGENT_KEYS):
            raise PolicyError("agent record is incomplete")
        agent_id = record["id"]
        if (not isinstance(agent_id, str) or not agent_id or agent_id in agents
                or not _is_count(record["max_retries"])
                or not _is_count(record["max_provider_calls_per_run"])
                or not isinstance(record["production_write"], bool)):
            raise PolicyError("invalid agent record")
        agents[agent_id] = AgentPolicy(
            agent_id=agent_id,
            max_retries=record["max_retries"],
            max_provider_calls_per_run=record["max_provider_calls_per_run"],
            production_write=record["production_write"],
        )

    return OrchestrationPolicy(
        max_retries=policy["max_retries"],
        production_mutations_allowed=policy["production_mutations_allowed"],
        production_mutations_require_human_approval=policy["production_mutations_require_human_approval"],
        budget_approval_variable=policy["budget_approval_variable"],
        budget_approval_is_dollar_cap=policy["budget_approval_is_dollar_cap"],
        unmeasured_baseline_blocks_autonomous_production_use=policy["unmeasured_baseline_blocks_autonomous_production_use"],
        agents=agents,
        source=str(source),
    )


def evaluate_task(task: TaskSpec, policy: OrchestrationPolicy,
                  budget: BudgetSnapshot) -> PolicyDecision:
    """Evaluate budget and mutation policy without spending or approving anything."""
    reasons: list[str] = []
    restricted = [action for action in task.requested_actions
                  if action in RESTRICTED_ACTIONS]
    if restricted:
        reasons.append("restricted_action_requires_human_gate")
    if "production" in task.requested_actions:
        if not policy.production_mutations_allowed:
            reasons.append("production_mutation_not_allowed")
        if (policy.production_mutations_require_human_approval
                and not budget.approved):
            reasons.append("production_approval_required")
        if (policy.unmeasured_baseline_blocks_autonomous_production_use
                and not budget.measured_baseline):
            reasons.append("production_baseline_required")

    billable = task.provider_calls > 0 or task.estimated_cost_usd is not None
    if billable and not budget.approved:
        reasons.append("budget_approval_required")
    if billable and budget.approved:
        if task.provider_calls and (
                budget.max_provider_calls == 0
                or budget.provider_calls + task.provider_calls > budget.max_provider_calls):
            reasons.append("provider_call_limit_exceeded")
        if task.estimated_cost_usd is not None and budget.max_usd is not None:
            if budget.spent_usd + task.estimated_cost_usd > budget.max_usd:
                reasons.append("budget_exceeded")
        elif task.provider_calls and budget.max_usd is not None:
            reasons.append("unmeasured_cost_blocks_cap_enforcement")

    agent_policy = policy.agents.get(task.owner)
    max_retries = policy.max_retries
    if agent_policy is not None:
        max_retries = min(max_retries, agent_policy.max_retries)
        if (task.provider_calls > agent_policy.max_provider_calls_per_run):
            reasons.append("agent_provider_call_limit_exceeded")

    return PolicyDecision(not reasons, tuple(sorted(set(reasons))), max_retries)


__all__ = [
    "DEFAULT_SPEC_PATH",
    "AgentPolicy",
    "OrchestrationPolicy",
    "PolicyDecision",
    "PolicyError",
    "evaluate_task",
    "load_policy",
]

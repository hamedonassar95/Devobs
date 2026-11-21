"""Advisory, offline, deterministic orchestration primitives for Devobs.

This package produces DRY_RUN plans from canonical manifests. It never starts
agents, changes Git state, calls external services, merges, deploys, bills, or
grants approval. Human approval is bound to an exact preview fingerprint and
remains advisory until an owner acts through the existing reviewed gates.
"""
from __future__ import annotations

from .audit import AuditTrail, classify_failure, redact_secrets, scope_fingerprint
from .coordinator import Coordinator
from .models import (
    ApprovalBinding,
    Assignment,
    BlockedTask,
    BudgetSnapshot,
    CapacitySnapshot,
    Plan,
    TaskSpec,
)
from .planner import Planner
from .policy_adapter import (
    AgentPolicy,
    OrchestrationPolicy,
    PolicyDecision,
    PolicyError,
    evaluate_task,
    load_policy,
)

__all__ = [
    "AgentPolicy",
    "ApprovalBinding",
    "Assignment",
    "AuditTrail",
    "BlockedTask",
    "BudgetSnapshot",
    "CapacitySnapshot",
    "Coordinator",
    "OrchestrationPolicy",
    "Plan",
    "Planner",
    "PolicyDecision",
    "PolicyError",
    "TaskSpec",
    "classify_failure",
    "evaluate_task",
    "load_policy",
    "redact_secrets",
    "scope_fingerprint",
]

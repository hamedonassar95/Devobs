"""Advisory, fail-closed orchestration primitives for Devobs.

This package never starts agents, changes Git state, calls GitHub, merges,
deploys, bills, or grants approval. It records intended work, detects
conflicts, plans DRY_RUN assignments, and classifies supplied delivery
evidence.
"""

from __future__ import annotations

from .conflict_detector import ConflictDetector, ConflictFinding, ConflictReport
from .delivery_tracker import (
    BLOCKED,
    DELIVERED,
    PARTIAL,
    UNVERIFIED,
    CheckSummary,
    DeliveryEvidence,
    DeliveryReport,
    DeliveryTracker,
    DeliveryUpdate,
    classify,
    redact_secrets,
)
from .task_registry import (
    DependencyError,
    DuplicateTaskError,
    OrchestrationError,
    StoreError,
    Task,
    TaskRegistry,
    TaskSnapshot,
    TransitionError,
    UpdateResult,
    ValidationError,
)
from .work_orchestrator import (
    MODE_DRY_RUN,
    Assignment,
    BlockedTask,
    CapacitySnapshot,
    OrchestrationPlan,
    WorkOrchestrator,
)

__all__ = [
    "BLOCKED",
    "DELIVERED",
    "MODE_DRY_RUN",
    "PARTIAL",
    "UNVERIFIED",
    "Assignment",
    "BlockedTask",
    "CapacitySnapshot",
    "CheckSummary",
    "ConflictDetector",
    "ConflictFinding",
    "ConflictReport",
    "DeliveryEvidence",
    "DeliveryReport",
    "DeliveryTracker",
    "DeliveryUpdate",
    "DependencyError",
    "DuplicateTaskError",
    "OrchestrationError",
    "OrchestrationPlan",
    "StoreError",
    "Task",
    "TaskRegistry",
    "TaskSnapshot",
    "TransitionError",
    "UpdateResult",
    "ValidationError",
    "WorkOrchestrator",
    "classify",
    "redact_secrets",
]

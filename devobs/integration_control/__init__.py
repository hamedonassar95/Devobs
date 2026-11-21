"""Integration control plane package.

Deterministic, fail-closed, read-only coordination and PR readiness evaluation.
Never merges, deploys, or modifies production/GitHub settings.
"""

from .advisory import AdvisoryProvider, StaticAdvisoryProvider, build_advisory
from .collector import CollectionError, OfflineSnapshotProvider, StateProvider, collect_repository_state
from .engine import evaluate_integration
from .models import (
    BLOCKED,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
)
from .report import render_json_report, render_markdown_report

__all__ = [
    "AdvisoryProvider",
    "BLOCKED",
    "CollectionError",
    "NEEDS_EVIDENCE",
    "OfflineSnapshotProvider",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "StateProvider",
    "StaticAdvisoryProvider",
    "build_advisory",
    "collect_repository_state",
    "evaluate_integration",
    "render_json_report",
    "render_markdown_report",
]

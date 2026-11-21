"""Integration control plane package.

Deterministic, fail-closed, read-only coordination and PR readiness evaluation.
Never merges, deploys, or modifies production/GitHub settings.
"""

from .advisory import AdvisoryProvider, DeterministicAdvisoryProvider, build_advisory
from .collector import collect_repository_state
from .engine import build_failure_report, evaluate_integration
from .models import (
    BLOCKED,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
)
from .pipeline import evaluate_collected_integration
from .report import render_json_report, render_markdown_report

__all__ = [
    "AdvisoryProvider",
    "BLOCKED",
    "DeterministicAdvisoryProvider",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "build_advisory",
    "build_failure_report",
    "collect_repository_state",
    "evaluate_collected_integration",
    "evaluate_integration",
    "render_json_report",
    "render_markdown_report",
]

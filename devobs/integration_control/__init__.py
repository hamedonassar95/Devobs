"""Integration control plane package.

Deterministic, fail-closed, read-only coordination and PR readiness evaluation.
Never merges, deploys, or modifies production/GitHub settings.
"""

from .engine import evaluate_integration
from .models import (
    BLOCKED,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
)
from .report import render_json_report, render_markdown_report

__all__ = [
    "BLOCKED",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "evaluate_integration",
    "render_json_report",
    "render_markdown_report",
]

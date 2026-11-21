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
from .readiness import evaluate_readiness
from .reporting import build_readiness_report, render_json, render_markdown

__all__ = [
    "BLOCKED",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "build_readiness_report",
    "evaluate_integration",
    "evaluate_readiness",
    "render_json",
    "render_json_report",
    "render_markdown",
    "render_markdown_report",
]

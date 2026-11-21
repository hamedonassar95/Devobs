"""PR readiness engine package.

Deterministic, fail-closed, read-only evaluation of pull request evidence.
Never approves or merges pull requests.
"""

from .models import (
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
    BLOCKED,
    NEEDS_EVIDENCE,
    PRReadinessReport,
    ReadinessDecision,
)
from .policy import evaluate_pr_readiness
from .report import render_json_report, render_markdown_report

__all__ = [
    "BLOCKED",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "PRReadinessReport",
    "READY_FOR_HUMAN_REVIEW",
    "ReadinessDecision",
    "evaluate_pr_readiness",
    "render_json_report",
    "render_markdown_report",
]

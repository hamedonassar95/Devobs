"""PR readiness engine package.

Deterministic, fail-closed, read-only evaluation of pull request evidence.
Never approves or merges pull requests.
"""

from .evaluator import evaluate
from .models import (
    BLOCKED,
    INSUFFICIENT_EVIDENCE,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    PRReadinessReport,
    READY_FOR_HUMAN_REVIEW,
    ReadinessDecision,
)
from .policy import evaluate_pr_readiness
from .report import render_json_report, render_markdown_report

__all__ = [
    "BLOCKED",
    "INSUFFICIENT_EVIDENCE",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "PRReadinessReport",
    "READY_FOR_HUMAN_REVIEW",
    "ReadinessDecision",
    "evaluate",
    "evaluate_pr_readiness",
    "render_json_report",
    "render_markdown_report",
]

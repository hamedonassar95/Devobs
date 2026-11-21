"""Deterministic, offline-first integration verification hub.

The hub inventories known Devobs integration components, validates contracts,
dependency and ownership evidence, and emits fail-closed readiness reports.
It never merges, deploys, or approves changes.
"""

from .evaluator import evaluate_hub
from .models import (
    BLOCKED,
    INSUFFICIENT_EVIDENCE,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
)
from .reporting import render_json_report, render_markdown_report

__all__ = [
    "BLOCKED",
    "INSUFFICIENT_EVIDENCE",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "evaluate_hub",
    "render_json_report",
    "render_markdown_report",
]

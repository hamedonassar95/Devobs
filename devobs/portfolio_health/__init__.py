"""Offline-first integration portfolio health and evidence dashboard.

Deterministic, read-only, fail-closed. Never merges, deploys, approves,
or calls external APIs. All recommendations are advisory only.
"""

from .evaluator import evaluate_portfolio_health
from .report import render_json_report, render_markdown_report

__all__ = [
    "evaluate_portfolio_health",
    "render_json_report",
    "render_markdown_report",
]

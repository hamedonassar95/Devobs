"""Deterministic, offline production-readiness intelligence engine.

Advisory only. No merges, deploys, production changes, or paid services.
AI analysis is optional, read-only, and disabled by default.
"""

from .readiness_engine import evaluate_production_readiness
from .reporting import render_json_report, render_markdown_report

__all__ = ["evaluate_production_readiness", "render_json_report", "render_markdown_report"]

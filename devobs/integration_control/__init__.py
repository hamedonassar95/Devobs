"""Offline-first integration control plane.

The engine coordinates read-only PR evidence, two-agent task ownership, approval
state, and bounded artifacts. It never merges, deploys, approves, or calls a
network service.
"""

from __future__ import annotations

from .engine import IntegrationControlPlane
from .report import render_report_json, render_report_markdown, validate_report

__all__ = [
    "IntegrationControlPlane",
    "render_report_json",
    "render_report_markdown",
    "validate_report",
]

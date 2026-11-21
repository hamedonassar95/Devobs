"""Offline-first open-source integration readiness engine."""

from .catalog import DEFAULT_FIXTURE_PATH, load_catalog, normalize_catalog
from .compatibility import parse_spec, parse_version, satisfies
from .evaluator import evaluate_catalog
from .models import (
    BLOCKED,
    GUARDRAILS,
    NEEDS_APPROVAL,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
    CatalogError,
    Finding,
    ReadinessError,
)
from .reporting import render_diagnostic, render_json_report, render_markdown_report
from .security import classify_license, redact_text, redact_value, safe_relative_path

__all__ = [
    "BLOCKED",
    "DEFAULT_FIXTURE_PATH",
    "GUARDRAILS",
    "NEEDS_APPROVAL",
    "NEEDS_EVIDENCE",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "CatalogError",
    "Finding",
    "ReadinessError",
    "classify_license",
    "evaluate_catalog",
    "load_catalog",
    "normalize_catalog",
    "parse_spec",
    "parse_version",
    "redact_text",
    "redact_value",
    "render_diagnostic",
    "render_json_report",
    "render_markdown_report",
    "safe_relative_path",
    "satisfies",
]

"""Offline-first AI incident intelligence for Devobs."""
from __future__ import annotations

from .analyzer import (
    AIProvider,
    DisabledAIProvider,
    analyze_incident,
    analyze_signals,
    analyze_workflow_run,
    render_summary,
)
from .models import (
    AIProviderReport,
    Evidence,
    Hypothesis,
    IncidentInput,
    IncidentReport,
    Recommendation,
)
from .rules import (
    CATEGORY_CI_FAILURE,
    CATEGORY_CONFIGURATION,
    CATEGORY_DEPENDENCY,
    CATEGORY_INFRASTRUCTURE,
    CATEGORY_TEST,
    CATEGORY_TIMEOUT,
    CATEGORY_UNKNOWN,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    EVIDENCE_INFERRED,
    EVIDENCE_UNVERIFIED,
    EVIDENCE_VERIFIED,
)
from .schema import SchemaError, validate_report_json

__all__ = [
    "AIProvider",
    "AIProviderReport",
    "CATEGORY_CI_FAILURE",
    "CATEGORY_CONFIGURATION",
    "CATEGORY_DEPENDENCY",
    "CATEGORY_INFRASTRUCTURE",
    "CATEGORY_TEST",
    "CATEGORY_TIMEOUT",
    "CATEGORY_UNKNOWN",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "DisabledAIProvider",
    "EVIDENCE_INFERRED",
    "EVIDENCE_UNVERIFIED",
    "EVIDENCE_VERIFIED",
    "Evidence",
    "Hypothesis",
    "IncidentInput",
    "IncidentReport",
    "Recommendation",
    "SchemaError",
    "analyze_incident",
    "analyze_signals",
    "analyze_workflow_run",
    "render_summary",
    "validate_report_json",
]

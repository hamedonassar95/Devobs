"""Offline-first AI incident intelligence for Devobs."""
from __future__ import annotations

from .analyzer import (
    AIProvider,
    DisabledAIProvider,
    analyze_incident,
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

__all__ = [
    "AIProvider",
    "AIProviderReport",
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
    "analyze_incident",
    "analyze_workflow_run",
    "render_summary",
]

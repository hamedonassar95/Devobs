"""Offline-first incident ingestion, classification and advisory reporting.

This package is a thin orchestration layer over the already merged
``devobs.incident_intelligence`` and ``scripts.ci_failure_intelligence``
modules. It never executes remediation.
"""
from __future__ import annotations

from .models import (
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
    CATEGORY_SERVICE_HEALTH_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
    SUPPORTED_CATEGORIES,
    ApprovalDecision,
    AdvisoryRecommendation,
    CorrelationLink,
    EngineReport,
    Evidence,
    IncidentEngineError,
    IncidentRecord,
    InvestigationReport,
    RepeatedSignature,
    TimelineEvent,
)

__all__ = [
    "AdvisoryRecommendation",
    "ApprovalDecision",
    "CATEGORY_AUTHENTICATION_CONFIGURATION",
    "CATEGORY_CI_CONFIGURATION_FAILURE",
    "CATEGORY_CONTAINER_BUILD_FAILURE",
    "CATEGORY_DEPENDENCY_FAILURE",
    "CATEGORY_INFRASTRUCTURE_CONFIGURATION",
    "CATEGORY_SERVICE_HEALTH_FAILURE",
    "CATEGORY_TEST_FAILURE",
    "CATEGORY_UNKNOWN_FAILURE",
    "CorrelationLink",
    "EngineReport",
    "Evidence",
    "IncidentEngineError",
    "IncidentRecord",
    "InvestigationReport",
    "RepeatedSignature",
    "SUPPORTED_CATEGORIES",
    "TimelineEvent",
]

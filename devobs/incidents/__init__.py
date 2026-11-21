"""Offline-first incident ingestion, classification and advisory reporting.

This package is a thin orchestration layer over the already merged
``devobs.incident_intelligence`` and ``scripts.ci_failure_intelligence``
modules. It never executes remediation.
"""
from __future__ import annotations

from .approval import ApprovalEngine, ApprovalRecord
from .engine import IncidentIntelligenceEngine
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
from .observability import (
    EVENT_NAMES,
    LoggingEventSink,
    MemoryEventSink,
    NullEventSink,
)
from .reports import (
    render_engine_json,
    render_engine_markdown,
    validate_engine_report_json,
)

__all__ = [
    "AdvisoryRecommendation",
    "ApprovalDecision",
    "ApprovalEngine",
    "ApprovalRecord",
    "EVENT_NAMES",
    "IncidentIntelligenceEngine",
    "LoggingEventSink",
    "MemoryEventSink",
    "NullEventSink",
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
    "render_engine_json",
    "render_engine_markdown",
    "validate_engine_report_json",
]

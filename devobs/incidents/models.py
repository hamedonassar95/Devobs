"""Frozen, JSON-normalizable data models for the incident engine.

Existing evidence and confidence models are imported from the merged offline
incident-intelligence package so this layer does not duplicate them.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from devobs.incident_intelligence.models import Evidence
from devobs.incident_intelligence.rules import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
)

SCHEMA_VERSION = "incident-engine/1.0"

CATEGORY_CI_CONFIGURATION_FAILURE = "CI_CONFIGURATION_FAILURE"
CATEGORY_TEST_FAILURE = "TEST_FAILURE"
CATEGORY_DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
CATEGORY_CONTAINER_BUILD_FAILURE = "CONTAINER_BUILD_FAILURE"
CATEGORY_AUTHENTICATION_CONFIGURATION = "AUTHENTICATION_CONFIGURATION"
CATEGORY_INFRASTRUCTURE_CONFIGURATION = "INFRASTRUCTURE_CONFIGURATION"
CATEGORY_SERVICE_HEALTH_FAILURE = "SERVICE_HEALTH_FAILURE"
CATEGORY_UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
SUPPORTED_CATEGORIES = frozenset({
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
    CATEGORY_SERVICE_HEALTH_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
})

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"
SUPPORTED_SEVERITIES = frozenset({
    SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
})

APPROVAL_NOT_REQUIRED = "NOT_REQUIRED"
APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"
APPROVAL_FORBIDDEN = "FORBIDDEN"
SUPPORTED_APPROVAL_STATES = frozenset({
    APPROVAL_NOT_REQUIRED, APPROVAL_PENDING, APPROVAL_APPROVED,
    APPROVAL_REJECTED, APPROVAL_FORBIDDEN,
})


class IncidentEngineError(ValueError):
    """Fail-closed error whose args contain only fixed non-sensitive codes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class IngestionError(IncidentEngineError):
    """Fixed ingestion validation error."""


class SchemaValidationError(IncidentEngineError):
    """Fixed report validation error."""


class ApprovalError(IncidentEngineError):
    """Fixed approval-gate error."""


@dataclass(frozen=True)
class TimelineEvent:
    """A bounded event in the incident timeline."""

    timestamp: str
    incident_id: str
    event: str
    detail: str


@dataclass(frozen=True)
class IncidentRecord:
    """A sanitized, deterministic incident record ready for classification."""

    incident_id: str
    kind: str
    timestamp: str
    severity: str
    title: str
    evidence: tuple[Evidence, ...]
    text: tuple[str, ...]
    metadata: dict[str, str]
    warnings: tuple[str, ...]
    signature_ids: tuple[str, ...]
    provider_status: str = "disabled"
    duplicate_of: str = ""


@dataclass(frozen=True)
class ClassificationResult:
    """One classification with evidence references and explicit unknowns."""

    incident_id: str
    category: str
    confidence: str
    evidence_ids: tuple[str, ...]
    missing_information: tuple[str, ...]
    diagnostic_step: str
    rationale: str
    signature_ids: tuple[str, ...]


@dataclass(frozen=True)
class RepeatedSignature:
    """A normalized error signature observed more than once."""

    signature_id: str
    count: int
    incident_ids: tuple[str, ...]


@dataclass(frozen=True)
class CorrelationLink:
    """A rule-based relationship between incidents or categories."""

    from_incident_id: str
    to_incident_id: str
    relationship: str
    evidence_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ApprovalDecision:
    """Advisory approval state. It never authorizes execution by itself."""

    action_id: str
    action: str
    state: str
    requires_human: bool
    rationale: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AdvisoryRecommendation:
    """A safe next diagnostic step with its verification and approval state."""

    id: str
    incident_id: str
    category: str
    action: str
    verification: str
    evidence_ids: tuple[str, ...]
    approval: ApprovalDecision


@dataclass(frozen=True)
class InvestigationReport:
    """Structured rule-based correlation and root-cause baseline."""

    incident_ids: tuple[str, ...]
    findings: tuple[ClassificationResult, ...]
    repeated_signatures: tuple[RepeatedSignature, ...]
    correlations: tuple[CorrelationLink, ...]
    probable_cause_category: str
    probable_cause_confidence: str
    symptom_categories: tuple[str, ...]
    insufficient_evidence: tuple[str, ...]
    timeline: tuple[TimelineEvent, ...]


@dataclass(frozen=True)
class EngineReport:
    """Complete offline report suitable for deterministic JSON rendering."""

    schema_version: str
    incident_ids: tuple[str, ...]
    duplicate_incident_ids: tuple[str, ...]
    severity: str
    classifications: tuple[ClassificationResult, ...]
    investigation: InvestigationReport
    recommendations: tuple[AdvisoryRecommendation, ...]
    evidence: tuple[Evidence, ...]
    verification_instructions: tuple[str, ...]
    warnings: tuple[str, ...]
    ai_provider_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-normalized view; tuples become lists."""
        return json.loads(json.dumps(asdict(self), sort_keys=True, separators=(",", ":")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "APPROVAL_APPROVED",
    "APPROVAL_FORBIDDEN",
    "APPROVAL_NOT_REQUIRED",
    "APPROVAL_PENDING",
    "APPROVAL_REJECTED",
    "AdvisoryRecommendation",
    "ApprovalDecision",
    "ApprovalError",
    "CATEGORY_AUTHENTICATION_CONFIGURATION",
    "CATEGORY_CI_CONFIGURATION_FAILURE",
    "CATEGORY_CONTAINER_BUILD_FAILURE",
    "CATEGORY_DEPENDENCY_FAILURE",
    "CATEGORY_INFRASTRUCTURE_CONFIGURATION",
    "CATEGORY_SERVICE_HEALTH_FAILURE",
    "CATEGORY_TEST_FAILURE",
    "CATEGORY_UNKNOWN_FAILURE",
    "ClassificationResult",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "CorrelationLink",
    "EngineReport",
    "Evidence",
    "IncidentEngineError",
    "IncidentRecord",
    "IngestionError",
    "InvestigationReport",
    "RepeatedSignature",
    "SCHEMA_VERSION",
    "SUPPORTED_APPROVAL_STATES",
    "SUPPORTED_CATEGORIES",
    "SUPPORTED_SEVERITIES",
    "SchemaValidationError",
    "TimelineEvent",
]

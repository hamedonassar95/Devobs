"""Rule-based mapping of sanitized incidents to the eight required categories.

The deterministic rules in ``devobs.incident_intelligence`` remain the primary
classifier. This module adds a bounded adapter for categories that the existing
seven-category vocabulary does not name explicitly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from devobs.incident_intelligence.rules import (
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
    classify_failure,
)
from scripts.ci_failure_intelligence import redact_secrets

from .models import (
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
    CATEGORY_SERVICE_HEALTH_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
    ClassificationResult,
    IncidentRecord,
)

HIGH = CONFIDENCE_HIGH
MEDIUM = CONFIDENCE_MEDIUM
LOW = CONFIDENCE_LOW


@dataclass(frozen=True)
class CategoryRule:
    """A closed, deterministic extended classification rule."""

    name: str
    category: str
    pattern: re.Pattern[str]
    confidence: str
    missing_information: tuple[str, ...]
    diagnostic_step: str


_MISSING = {
    CATEGORY_CI_CONFIGURATION_FAILURE: (
        "Workflow definition and required check configuration were not supplied.",
        "The exact workflow revision was not independently verified.",
    ),
    CATEGORY_TEST_FAILURE: (
        "Full test output and the changed code path were not supplied.",
        "Test flakiness versus a deterministic regression is not yet distinguished.",
    ),
    CATEGORY_DEPENDENCY_FAILURE: (
        "Manifest, lockfile and resolved versions were not supplied together.",
        "Registry availability at the incident time was not verified.",
    ),
    CATEGORY_CONTAINER_BUILD_FAILURE: (
        "Dockerfile, build context and image digest were not supplied together.",
        "Builder resource state was not independently verified.",
    ),
    CATEGORY_AUTHENTICATION_CONFIGURATION: (
        "Issuer, client identity and callback configuration were not verified.",
        "Secret values were deliberately not inspected.",
    ),
    CATEGORY_INFRASTRUCTURE_CONFIGURATION: (
        "Resource quotas, runner health and provider status were not supplied.",
        "Configuration ownership was not independently verified.",
    ),
    CATEGORY_SERVICE_HEALTH_FAILURE: (
        "Readiness, liveness and upstream health history were not supplied.",
        "The observation window and request path were not independently verified.",
    ),
    CATEGORY_UNKNOWN_FAILURE: (
        "No trusted pattern matched the supplied sanitized evidence.",
        "Additional evidence is required before a cause category can be supported.",
    ),
}

_STEPS = {
    CATEGORY_CI_CONFIGURATION_FAILURE: (
        "Inspect the workflow file and required checks at the pinned source revision; "
        "do not rerun or edit checks without approval."
    ),
    CATEGORY_TEST_FAILURE: (
        "Reproduce the failing assertion locally from the pinned source and compare "
        "the changed test or code path."
    ),
    CATEGORY_DEPENDENCY_FAILURE: (
        "Compare the dependency manifest, lockfile and resolved versions at the "
        "pinned source revision."
    ),
    CATEGORY_CONTAINER_BUILD_FAILURE: (
        "Inspect the Dockerfile, build context and builder status; do not push or "
        "rebuild images without approval."
    ),
    CATEGORY_AUTHENTICATION_CONFIGURATION: (
        "Verify configuration key names and issuer metadata without printing or "
        "copying secret values."
    ),
    CATEGORY_INFRASTRUCTURE_CONFIGURATION: (
        "Check resource quotas, runner health and provider status for the affected "
        "window; do not modify infrastructure."
    ),
    CATEGORY_SERVICE_HEALTH_FAILURE: (
        "Collect bounded readiness, liveness and upstream health evidence for the "
        "affected window."
    ),
    CATEGORY_UNKNOWN_FAILURE: (
        "Collect additional sanitized evidence and keep the incident unverified "
        "until a trusted pattern supports a category."
    ),
}

RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        name="auth-configuration",
        category=CATEGORY_AUTHENTICATION_CONFIGURATION,
        pattern=re.compile(
            r"(?im)\bbad credentials\b|401 unauthorized|403 forbidden|permission denied|"
            r"resource not accessible by integration|invalid_staging_config stage=oidc|"
            r"missing issuer|invalid_client|pkce|client_secret"
        ),
        confidence=MEDIUM,
        missing_information=_MISSING[CATEGORY_AUTHENTICATION_CONFIGURATION],
        diagnostic_step=_STEPS[CATEGORY_AUTHENTICATION_CONFIGURATION],
    ),
    CategoryRule(
        name="container-build",
        category=CATEGORY_CONTAINER_BUILD_FAILURE,
        pattern=re.compile(
            r"(?im)docker build failed|failed to solve|dockerfile|container build|"
            r"cannot connect to the docker daemon|oci image|image manifest.*not found"
        ),
        confidence=HIGH,
        missing_information=_MISSING[CATEGORY_CONTAINER_BUILD_FAILURE],
        diagnostic_step=_STEPS[CATEGORY_CONTAINER_BUILD_FAILURE],
    ),
    CategoryRule(
        name="service-health",
        category=CATEGORY_SERVICE_HEALTH_FAILURE,
        pattern=re.compile(
            r"(?im)readiness probe failed|liveness probe failed|health check failed|"
            r"/readyz|connection refused|crashloopbackoff|service unavailable|"
            r"502 bad gateway|503 service unavailable"
        ),
        confidence=HIGH,
        missing_information=_MISSING[CATEGORY_SERVICE_HEALTH_FAILURE],
        diagnostic_step=_STEPS[CATEGORY_SERVICE_HEALTH_FAILURE],
    ),
    CategoryRule(
        name="infrastructure-configuration",
        category=CATEGORY_INFRASTRUCTURE_CONFIGURATION,
        pattern=re.compile(
            r"(?im)runner lost communication|no space left on device|disk quota exceeded|"
            r"OOMKilled|out of memory|resource quota|insufficient capacity|"
            r"capacity pressure|terraform.*invalid|invalid configuration"
        ),
        confidence=MEDIUM,
        missing_information=_MISSING[CATEGORY_INFRASTRUCTURE_CONFIGURATION],
        diagnostic_step=_STEPS[CATEGORY_INFRASTRUCTURE_CONFIGURATION],
    ),
    CategoryRule(
        name="ci-configuration",
        category=CATEGORY_CI_CONFIGURATION_FAILURE,
        pattern=re.compile(
            r"(?im)invalid workflow file|unknown workflow event|required check.*(missing|failed)|"
            r"workflow.*invalid|actionlint|workflow_dispatch"
        ),
        confidence=MEDIUM,
        missing_information=_MISSING[CATEGORY_CI_CONFIGURATION_FAILURE],
        diagnostic_step=_STEPS[CATEGORY_CI_CONFIGURATION_FAILURE],
    ),
)

_EXISTING_MAP = {
    CATEGORY_CI_FAILURE: (CATEGORY_CI_CONFIGURATION_FAILURE, MEDIUM),
    CATEGORY_CONFIGURATION: (CATEGORY_CI_CONFIGURATION_FAILURE, MEDIUM),
    CATEGORY_DEPENDENCY: (CATEGORY_DEPENDENCY_FAILURE, HIGH),
    CATEGORY_TEST: (CATEGORY_TEST_FAILURE, HIGH),
    CATEGORY_INFRASTRUCTURE: (CATEGORY_INFRASTRUCTURE_CONFIGURATION, MEDIUM),
    CATEGORY_TIMEOUT: (CATEGORY_SERVICE_HEALTH_FAILURE, MEDIUM),
    CATEGORY_UNKNOWN: (CATEGORY_UNKNOWN_FAILURE, LOW),
}


def missing_information_for(category: str) -> tuple[str, ...]:
    return _MISSING.get(category, _MISSING[CATEGORY_UNKNOWN_FAILURE])


def diagnostic_step_for(category: str) -> str:
    return _STEPS.get(category, _STEPS[CATEGORY_UNKNOWN_FAILURE])


def _evidence_ids(record: IncidentRecord) -> tuple[str, ...]:
    return tuple(item.id for item in record.evidence[:20])


def _metadata_text(record: IncidentRecord) -> tuple[str, str]:
    job = record.metadata.get("job", "")
    step = record.metadata.get("step", "")
    return job, step


def _from_existing(record: IncidentRecord) -> tuple[str, str, str]:
    if record.metadata.get("ci_overall_category") == CATEGORY_CI_FAILURE:
        return (
            CATEGORY_CI_CONFIGURATION_FAILURE,
            MEDIUM,
            "Mapped the existing offline CI-failure signal to the bounded incident vocabulary.",
        )
    job, step = _metadata_text(record)
    existing = classify_failure(record.text, job, step)
    category, confidence = _EXISTING_MAP.get(existing.category, (CATEGORY_UNKNOWN_FAILURE, LOW))
    if existing.confidence == LOW and category != CATEGORY_UNKNOWN_FAILURE:
        confidence = LOW
    rationale = (
        "Mapped the merged deterministic incident-intelligence rule "
        f"'{existing.signal}' to the bounded incident vocabulary."
    )
    return category, confidence, rationale


def classify_record(record: IncidentRecord) -> ClassificationResult:
    """Classify one sanitized record; unknown remains explicit and low confidence."""
    haystack = "\n".join(record.text)
    for rule in RULES:
        if rule.pattern.search(haystack):
            category = rule.category
            confidence = rule.confidence
            rationale = f"Extended deterministic rule '{rule.name}' matched redacted evidence."
            break
    else:
        category, confidence, rationale = _from_existing(record)
        if category == CATEGORY_UNKNOWN_FAILURE:
            rationale = (
                "No trusted extended or existing rule matched the sanitized evidence; "
                "the cause remains unverified."
            )

    step = diagnostic_step_for(category)
    return ClassificationResult(
        incident_id=record.incident_id,
        category=category,
        confidence=confidence,
        evidence_ids=_evidence_ids(record),
        missing_information=missing_information_for(category),
        diagnostic_step=step,
        rationale=redact_secrets(rationale),
        signature_ids=record.signature_ids,
    )


def classify_records(records: Iterable[IncidentRecord]) -> tuple[ClassificationResult, ...]:
    return tuple(classify_record(record) for record in records)


__all__ = [
    "RULES",
    "classify_record",
    "classify_records",
    "diagnostic_step_for",
    "missing_information_for",
]

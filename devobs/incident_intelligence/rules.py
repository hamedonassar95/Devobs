"""Deterministic classification and advisory rules for incidents.

The rules deliberately reuse the redaction primitive from PR #734's CI Failure
Intelligence analyzer instead of implementing a second sanitizer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from scripts.ci_failure_intelligence import (
    FINDING_INFERRED as EVIDENCE_INFERRED,
    FINDING_UNVERIFIED as EVIDENCE_UNVERIFIED,
    FINDING_VERIFIED as EVIDENCE_VERIFIED,
    redact_secrets,
)

CATEGORY_DEPENDENCY = "dependency"
CATEGORY_CONFIGURATION = "configuration"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_TEST = "test"
CATEGORY_INFRASTRUCTURE = "infrastructure"
CATEGORY_CI_FAILURE = "ci_failure"
CATEGORY_UNKNOWN = "unknown"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

# Mapping from the existing offline adviser's bounded signal categories. The
# adviser deliberately emits only these known strings, so classification stays
# deterministic and cannot be steered by freeform model output.
ADVISER_SIGNAL_CLASSES = {
    "ci_failure": (CATEGORY_CI_FAILURE, CONFIDENCE_HIGH),
    "high_error_rate": (CATEGORY_INFRASTRUCTURE, CONFIDENCE_MEDIUM),
    "capacity_pressure": (CATEGORY_INFRASTRUCTURE, CONFIDENCE_MEDIUM),
    "unknown": (CATEGORY_UNKNOWN, CONFIDENCE_LOW),
}


@dataclass(frozen=True)
class FailureRule:
    name: str
    category: str
    pattern: re.Pattern[str]
    confidence: str = CONFIDENCE_HIGH
    evidence_confidence: str = EVIDENCE_VERIFIED


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: str
    signal: str
    excerpt: str
    evidence_confidence: str
    rationale: str


FAILURE_RULES: tuple[FailureRule, ...] = (
    FailureRule(
        name="dependency-install",
        category=CATEGORY_DEPENDENCY,
        pattern=re.compile(
            r"(?im)\bnpm ERR!|\bERESOLVE\b|ResolutionImpossible|Could not find a version|"
            r"\bETARGET\b|pip(?:3)? install\b.*(?:failed|error)|"
            r"\bModuleNotFoundError\b|No module named"
        ),
    ),
    FailureRule(
        name="configuration",
        category=CATEGORY_CONFIGURATION,
        pattern=re.compile(
            r"(?im)\bConfigurationError\b|InvalidConfiguration|"
            r"required environment variable[^\n]*\b(?:not set|missing|undefined)\b|"
            r"KeyError:\s*['\"]?[A-Z][A-Z0-9_]+|"
            r"\byaml\b[^\n]*\b(?:invalid|could not find expected)\b|"
            r"\bJSONDecodeError\b"
        ),
    ),
    FailureRule(
        name="timeout",
        category=CATEGORY_TIMEOUT,
        pattern=re.compile(r"(?im)\bETIMEDOUT\b|\bTimeoutError\b|\btimed? out\b|timeout exceeded"),
    ),
    FailureRule(
        name="test-assertion",
        category=CATEGORY_TEST,
        pattern=re.compile(
            r"(?im)\bFAILED\b|\bAssertionError\b|\bFAIL:\s|\bTests? failed\b|test suite failed"
        ),
    ),
    FailureRule(
        name="runner-or-external-infrastructure",
        category=CATEGORY_INFRASTRUCTURE,
        pattern=re.compile(
            r"(?im)runner lost communication|No space left on device|disk quota exceeded|"
            r"\bOOMKilled\b|out of memory|502 Bad Gateway|503 Service Unavailable|"
            r"\brate limit\b|connection reset|Could not resolve host"
        ),
    ),
)

_HYPOTHESES = {
    CATEGORY_CI_FAILURE: (
        "Existing aggregate signals show failing CI checks; the leading explanation "
        "is a CI failure at the pinned source revision."
    ),
    CATEGORY_DEPENDENCY: (
        "A dependency resolution or installation failure is the leading explanation "
        "for this incident."
    ),
    CATEGORY_CONFIGURATION: (
        "A configuration value or required environment setting is the leading "
        "explanation for this incident."
    ),
    CATEGORY_TIMEOUT: (
        "A timeout while waiting on an external operation is the leading explanation "
        "for this incident."
    ),
    CATEGORY_TEST: (
        "A failing test assertion is the leading explanation for this incident."
    ),
    CATEGORY_INFRASTRUCTURE: (
        "A runner or external service infrastructure failure is the leading "
        "explanation for this incident."
    ),
    CATEGORY_UNKNOWN: (
        "No trusted pattern matched the supplied evidence; the root cause remains unverified."
    ),
}

_RECOMMENDATIONS = {
    CATEGORY_CI_FAILURE: (
        "Inspect the failed checks and their bounded evidence digests at the pinned "
        "source revision; do not rerun workflows or change checks without approval.",
        "The existing offline adviser classified failed checks from aggregate signals only.",
    ),
    CATEGORY_DEPENDENCY: (
        "Inspect the dependency manifest and lockfile at the pinned source SHA; compare "
        "the resolved versions with the failing install step.",
        "Dependency errors usually leave a reproducible resolution or install signature.",
    ),
    CATEGORY_CONFIGURATION: (
        "Verify required configuration keys and environment variable names against the "
        "approved reference; do not print or copy their values.",
        "Configuration failures are often name or presence errors rather than code defects.",
    ),
    CATEGORY_TIMEOUT: (
        "Review the step duration and the referenced service status for the incident window; "
        "treat any timeout change as a human-reviewed follow-up.",
        "A timeout signal shows where waiting stopped, not why the dependency was slow.",
    ),
    CATEGORY_TEST: (
        "Reproduce the failing assertion locally from the pinned source SHA and inspect "
        "the changed test or code path.",
        "Assertion evidence identifies a failing expectation but not necessarily its owner.",
    ),
    CATEGORY_INFRASTRUCTURE: (
        "Check runner health and external service status for the affected window; do not "
        "rerun workflows, merge, or deploy without approval.",
        "Infrastructure signals can be transient and are not proof of a code defect.",
    ),
    CATEGORY_UNKNOWN: (
        "Collect additional sanitized logs and job metadata; keep the incident unverified "
        "until a trusted pattern supports a category.",
        "Fail-closed reporting is safer than inventing a root cause from ambiguous text.",
    ),
}


def classify_failure(logs: Iterable[str], job: str = "", step: str = "") -> Classification:
    """Classify sanitized evidence deterministically, without model inference."""
    log_text = "\n".join(str(log) for log in logs)
    metadata = "\n".join(part for part in (job, step) if part)

    for rule in FAILURE_RULES:
        match = rule.pattern.search(log_text)
        if match:
            excerpt = redact_secrets(match.group(0))[:240]
            return Classification(
                category=rule.category,
                confidence=rule.confidence,
                signal=rule.name,
                excerpt=excerpt or "[REDACTED]",
                evidence_confidence=rule.evidence_confidence,
                rationale=f"{rule.name} matched sanitized log evidence.",
            )
        if rule.pattern.search(metadata):
            return Classification(
                category=rule.category,
                confidence=CONFIDENCE_MEDIUM,
                signal=rule.name,
                excerpt=redact_secrets(metadata)[:240] or "[REDACTED]",
                evidence_confidence=EVIDENCE_INFERRED,
                rationale=f"{rule.name} matched job or step metadata only.",
            )

    if log_text.strip():
        fallback = redact_secrets(log_text.strip())[:240]
    else:
        fallback = "No sanitized log evidence supplied."
    return Classification(
        category=CATEGORY_UNKNOWN,
        confidence=CONFIDENCE_LOW,
        signal="unknown",
        excerpt=fallback,
        evidence_confidence=EVIDENCE_UNVERIFIED,
        rationale="No trusted pattern matched the supplied evidence.",
    )


def classify_adviser_signal(signal: str) -> tuple[str, str]:
    """Map a bounded adviser category to an incident category and confidence label."""
    return ADVISER_SIGNAL_CLASSES.get(signal, (CATEGORY_UNKNOWN, CONFIDENCE_LOW))


def hypothesis_statement(category: str) -> str:
    return _HYPOTHESES.get(category, _HYPOTHESES[CATEGORY_UNKNOWN])


def recommendation_for(category: str) -> tuple[str, str]:
    return _RECOMMENDATIONS.get(category, _RECOMMENDATIONS[CATEGORY_UNKNOWN])

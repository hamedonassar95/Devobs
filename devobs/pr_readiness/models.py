"""Data models for PR readiness evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
BLOCKED = "BLOCKED"
NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
POLICY_VIOLATION = "POLICY_VIOLATION"
DECISIONS = (READY_FOR_HUMAN_REVIEW, BLOCKED, NEEDS_EVIDENCE, POLICY_VIOLATION)

MAX_CHECKS = 200
MAX_CHANGED_FILES = 5000
MAX_FINDINGS = 500
MAX_STRING = 4096


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clip(text: Any, limit: int = MAX_STRING) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # info|warning|error
    category: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": _clip(self.code, 120),
            "severity": self.severity,
            "category": _clip(self.category, 120),
            "message": _clip(self.message),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class PRIdentity:
    repository: str
    pr_number: int | None
    base_branch: str
    head_branch: str
    head_sha: str
    reviewed_head_sha: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "pr_number": self.pr_number,
            "base_branch": self.base_branch,
            "head_branch": self.head_branch,
            "head_sha": self.head_sha,
            "reviewed_head_sha": self.reviewed_head_sha,
        }


@dataclass(frozen=True)
class ReadinessDecision:
    decision: str
    reasons: tuple[str, ...]
    human_review_required: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": list(self.reasons),
            "human_review_required": self.human_review_required,
        }


def bounded_findings(findings: list[Finding]) -> tuple[Finding, ...]:
    if len(findings) > MAX_FINDINGS:
        findings = findings[:MAX_FINDINGS]
    return tuple(findings)


@dataclass(frozen=True)
class PRReadinessReport:
    pr: PRIdentity
    evidence_timestamps: dict[str, str | None]
    ci: dict[str, Any]
    security: dict[str, Any]
    policy: dict[str, Any]
    ownership: dict[str, Any]
    decision: ReadinessDecision
    recommended_next_action: str
    findings: tuple[Finding, ...]
    advisory: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "engine": "devobs.pr_readiness",
            "generated_at": utc_now_iso(),
            "pr": self.pr.as_dict(),
            "evidence_timestamps": dict(sorted(self.evidence_timestamps.items())),
            "ci": self.ci,
            "security": self.security,
            "policy": self.policy,
            "ownership": self.ownership,
            "readiness_decision": self.decision.as_dict(),
            "human_review_required": self.decision.human_review_required,
            "recommended_next_action": self.recommended_next_action,
            "findings": [f.as_dict() for f in self.findings],
            "advisory": self.advisory,
        }

"""Models and closed vocabularies for portfolio health dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "portfolio-health/1.0"
POLICY_VERSION = "portfolio-health-policy-v1"

READY = "READY_FOR_HUMAN_REVIEW"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"
READINESS_STATES = frozenset({READY, DEGRADED, BLOCKED, UNKNOWN})

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}

FRESH = "FRESH"
STALE = "STALE"
MISSING = "MISSING"
EVIDENCE_STATES = frozenset({FRESH, STALE, MISSING, UNKNOWN})

MAX_ITEMS = 200
MAX_FINDINGS = 500
MAX_STRING = 4096
MAX_ID = 128


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clip(text: Any, limit: int = MAX_STRING) -> str:
    value = str(text)
    return value if len(value) <= limit else value[: limit - 3] + "..."


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    category: str
    message: str
    component: str = ""
    evidence_ids: tuple[str, ...] = ()
    remediation: str = ""
    inferred: bool = False

    def as_dict(self) -> dict[str, Any]:
        sev = self.severity if self.severity in SEVERITY_RANK else "HIGH"
        return {
            "code": clip(self.code, MAX_ID),
            "severity": sev,
            "category": clip(self.category, MAX_ID),
            "component": clip(self.component, 200),
            "message": clip(self.message),
            "evidence_ids": list(self.evidence_ids[:20]),
            "remediation": clip(self.remediation),
            "inferred": bool(self.inferred),
        }


@dataclass
class EvidenceRecord:
    evidence_id: str
    source: str
    kind: str
    observed_at: str
    status: str = UNKNOWN
    sha: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": clip(self.evidence_id, MAX_ID),
            "source": clip(self.source, 500),
            "kind": clip(self.kind, MAX_ID),
            "observed_at": clip(self.observed_at, 64),
            "status": self.status if self.status in EVIDENCE_STATES else UNKNOWN,
            "sha": clip(self.sha, 64),
            "details": self.details,
        }

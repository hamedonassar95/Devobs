"""Models and closed vocabularies for production readiness intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "production-readiness/1.0"
READY = "READY_FOR_HUMAN_REVIEW"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"
STATUSES = frozenset({READY, DEGRADED, BLOCKED, UNKNOWN})

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}

MAX_ITEMS = 200
MAX_FINDINGS = 500
MAX_STR = 4096


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clip(value: Any, limit: int = MAX_STR) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    category: str
    message: str
    component: str = ""
    remediation: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        sev = self.severity if self.severity in SEV_RANK else "HIGH"
        return {
            "code": clip(self.code, 120),
            "severity": sev,
            "category": clip(self.category, 120),
            "component": clip(self.component, 200),
            "message": clip(self.message),
            "remediation": clip(self.remediation),
            "evidence": self.evidence,
        }

"""Models and constants for integration control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
BLOCKED = "BLOCKED"
POLICY_VIOLATION = "POLICY_VIOLATION"
DECISIONS = (READY_FOR_HUMAN_REVIEW, NEEDS_EVIDENCE, BLOCKED, POLICY_VIOLATION)

MAX_STRING = 4096
MAX_LIST = 500
MAX_FILES = 5000
MAX_FINDINGS = 500


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clip(value: Any, limit: int = MAX_STRING) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # error|warning|info
    category: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": clip(self.code, 120),
            "severity": self.severity,
            "category": clip(self.category, 120),
            "message": clip(self.message, MAX_STRING),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class EvidenceRecord:
    source: str
    kind: str
    ref: str
    sha: str | None = None
    timestamp: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def identity(self) -> tuple[str, str, str, str]:
        return (self.source, self.kind, self.ref, self.sha or "")

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": clip(self.source, 200),
            "kind": clip(self.kind, 120),
            "ref": clip(self.ref, 500),
            "sha": self.sha,
            "timestamp": self.timestamp,
            "data": self.data,
        }

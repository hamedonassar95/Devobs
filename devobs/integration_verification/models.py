"""Models and constants for integration verification hub."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
BLOCKED = "BLOCKED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
POLICY_VIOLATION = "POLICY_VIOLATION"
DECISIONS = (READY_FOR_HUMAN_REVIEW, BLOCKED, INSUFFICIENT_EVIDENCE, POLICY_VIOLATION)

# Inventory classification
IMPLEMENTED_AND_TESTED = "IMPLEMENTED_AND_TESTED"
IMPLEMENTED_UNVERIFIED = "IMPLEMENTED_UNVERIFIED"
PARTIALLY_IMPLEMENTED = "PARTIALLY_IMPLEMENTED"
DOCUMENTATION_ONLY = "DOCUMENTATION_ONLY"
ABSENT = "ABSENT"
CAPABILITY_BLOCKED = "BLOCKED"
CAPABILITY_STATUSES = (
    IMPLEMENTED_AND_TESTED,
    IMPLEMENTED_UNVERIFIED,
    PARTIALLY_IMPLEMENTED,
    DOCUMENTATION_ONLY,
    ABSENT,
    CAPABILITY_BLOCKED,
)

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
MAX_STRING = 4096
MAX_LIST = 500
MAX_COMPONENTS = 200
MAX_EVIDENCE = 1000
MAX_FINDINGS = 1000
SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    evidence: dict[str, Any] = field(default_factory=dict)
    inferred: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": clip(self.code, 120),
            "severity": self.severity if self.severity in SEVERITIES else "HIGH",
            "category": clip(self.category, 120),
            "component": clip(self.component, 200),
            "message": clip(self.message),
            "evidence": self.evidence,
            "inferred": bool(self.inferred),
        }


@dataclass(frozen=True)
class ComponentRecord:
    name: str
    source_path: str
    owning_branch: str
    evidence_type: str
    test_coverage: str
    integration_dependencies: tuple[str, ...]
    verification_status: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": clip(self.name, 200),
            "source_path": clip(self.source_path, 500),
            "owning_branch": clip(self.owning_branch, 200),
            "evidence_type": clip(self.evidence_type, 120),
            "test_coverage": clip(self.test_coverage, 120),
            "integration_dependencies": list(self.integration_dependencies),
            "verification_status": self.verification_status,
            "details": self.details,
        }

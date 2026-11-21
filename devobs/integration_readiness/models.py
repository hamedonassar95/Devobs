"""Stable constants and value objects for offline integration readiness reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REPORT_SCHEMA = "devobs.integration_readiness.v1"
CATALOG_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1

READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
NEEDS_APPROVAL = "NEEDS_APPROVAL"
BLOCKED = "BLOCKED"
POLICY_VIOLATION = "POLICY_VIOLATION"

PRIORITIES = ("P0", "P1", "P2", "P3")
PRIORITY_RANK = {priority: index for index, priority in enumerate(PRIORITIES)}
SEVERITY_BY_PRIORITY = {"P0": "error", "P1": "error", "P2": "warning", "P3": "info"}

MAX_CATALOG_BYTES = 1_048_576
MAX_INTEGRATIONS = 200
MAX_ITEMS = 100
MAX_STRING = 2048
MAX_SHORT_STRING = 256
MAX_FINDINGS = 200

GUARDRAILS: dict[str, Any] = {
    "read_only": True,
    "installs_packages": False,
    "deploys": False,
    "merges": False,
    "restarts_services": False,
    "network_access": False,
    "executes_repository_commands": False,
    "ai_recommendations_authoritative": False,
    "human_approval_required": True,
}


class ReadinessError(ValueError):
    """Fail-closed error with a stable, non-sensitive code."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class CatalogError(ReadinessError):
    """Catalog input is malformed, unsafe, or oversized."""


class CompatibilityError(ReadinessError):
    """A version or requirement string cannot be parsed safely."""


@dataclass(frozen=True)
class Finding:
    """One deterministic, redacted readiness finding."""

    code: str
    priority: str
    category: str
    integration_id: str
    message: str
    remediation: str
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self, position: int) -> dict[str, Any]:
        return {
            "id": f"F-{position:03d}",
            "code": self.code,
            "severity": SEVERITY_BY_PRIORITY[self.priority],
            "priority": self.priority,
            "category": self.category,
            "integration_id": self.integration_id,
            "message": self.message,
            "remediation": self.remediation,
            "evidence": list(self.evidence),
        }


__all__ = [
    "BLOCKED",
    "CATALOG_SCHEMA_VERSION",
    "GUARDRAILS",
    "MAX_CATALOG_BYTES",
    "MAX_FINDINGS",
    "MAX_INTEGRATIONS",
    "MAX_ITEMS",
    "MAX_SHORT_STRING",
    "MAX_STRING",
    "NEEDS_APPROVAL",
    "NEEDS_EVIDENCE",
    "PRIORITIES",
    "PRIORITY_RANK",
    "POLICY_VIOLATION",
    "READY_FOR_HUMAN_REVIEW",
    "REPORT_SCHEMA",
    "REPORT_SCHEMA_VERSION",
    "CatalogError",
    "CompatibilityError",
    "Finding",
    "ReadinessError",
]

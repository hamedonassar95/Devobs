"""Shared closed vocabularies and immutable result models."""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "integration-control/1.0"
INPUT_SCHEMA_VERSION = 1
POLICY_VERSION = "integration-control-policy-v1"

PROCEED = "PROCEED_TO_HUMAN_REVIEW"
BLOCKED = "BLOCKED"
UNVERIFIED = "UNVERIFIED"
INVALID = "INVALID"
DECISIONS = frozenset({PROCEED, BLOCKED, UNVERIFIED, INVALID})

BLOCKER = "BLOCKER"
UNVERIFIED_SEVERITY = "UNVERIFIED"
ADVISORY = "ADVISORY"
SEVERITIES = frozenset({BLOCKER, UNVERIFIED_SEVERITY, ADVISORY})

PENDING_HUMAN = "PENDING_HUMAN"
RESTRICTED_ACTIONS = ("merge", "deploy", "billing", "production")


class ControlError(ValueError):
    """Fixed, non-sensitive diagnostic code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    source: str
    message: str = ""

    def __post_init__(self) -> None:
        if not self.code or self.severity not in SEVERITIES:
            raise ControlError("invalid_finding")
        if not self.message:
            object.__setattr__(self, "message", self.code.replace("_", " ").lower())

    def to_record(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
        }


@dataclass(frozen=True)
class ComponentResult:
    name: str
    status: str
    findings: tuple[Finding, ...]
    evidence_ids: tuple[str, ...] = ()
    check_passed: str | None = None
    check_failed: str | None = None
    details: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "BLOCKED", "UNVERIFIED", "SKIPPED", "FAIL"}:
            raise ControlError("invalid_component_status")
        if bool(self.check_passed) == bool(self.check_failed):
            raise ControlError("invalid_component_check")

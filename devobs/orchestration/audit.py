"""Sanitized, deterministic audit primitives for advisory orchestration."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_tools = str(_ROOT / "tools")
if _tools not in sys.path:
    sys.path.insert(0, _tools)

from agent_task_status_report import sanitize_display  # noqa: E402

REDACTED = "[REDACTED]"
RETRYABLE = "RETRYABLE"
TERMINAL = "TERMINAL"
POLICY = "POLICY"
UNKNOWN = "UNKNOWN"

_RETRYABLE_CODES = frozenset((
    "timeout", "rate_limited", "temporary_network", "provider_unavailable",
    "conflict_retry",
))
_TERMINAL_CODES = frozenset((
    "validation_error", "contract_violation", "dependency_cycle",
    "ownership_conflict", "budget_exceeded", "production_write_denied",
    "approval_denied",
))
_POLICY_CODES = frozenset((
    "approval_required", "budget_approval_required", "human_gate_required",
    "unverified_evidence",
))

_TOKEN_PATTERNS = (
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


def redact_secrets(value: str) -> str:
    """Replace common credential shapes before a value is logged or exported."""
    result = value
    for pattern in _TOKEN_PATTERNS:
        result = pattern.sub(REDACTED, result)
    return result


def scope_fingerprint(value: Any) -> str:
    """Return a stable SHA-256 digest of canonical, sanitized scope data."""
    canonical = json.dumps(
        safe_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FailureClassification:
    """Advisory failure category; only explicitly transient failures may retry."""

    code: str
    category: str
    retry_allowed: bool
    reason: str


def classify_failure(code: Any, *, attempt: int = 1, max_retries: int = 0) -> FailureClassification:
    """Classify a recorded failure without executing recovery."""
    normalized = sanitize(code, 80).strip().lower()
    if normalized in _RETRYABLE_CODES:
        category = RETRYABLE
        allowed = 0 <= attempt < max_retries
        reason = "retry_permitted" if allowed else "retry_limit_exhausted"
    elif normalized in _TERMINAL_CODES:
        category, allowed, reason = TERMINAL, False, "non_retryable_failure"
    elif normalized in _POLICY_CODES:
        category, allowed, reason = POLICY, False, "human_policy_gate"
    else:
        category, allowed, reason = UNKNOWN, False, "unclassified_failure"
    return FailureClassification(normalized, category, allowed, reason)


def sanitize(value: Any, limit: int = 2000) -> str:
    """Return a bounded, single-line, credential-sanitized display string."""
    return redact_secrets(sanitize_display(value, limit=limit))


def safe_value(value: Any) -> Any:
    """Recursively sanitize an untrusted value for a JSON-serializable event."""
    if isinstance(value, Mapping):
        return {sanitize(str(key), 80): safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_value(item) for item in value]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return sanitize(value)


@dataclass(frozen=True)
class AuditEvent:
    """One deterministic, credential-sanitized planning event."""

    sequence: int
    plan_id: str
    event: str
    fields: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "plan_id": self.plan_id,
            "event": self.event,
            "fields": dict(self.fields),
        }


class AuditTrail:
    """Ordered in-memory event log with no clock, network, or persistence."""

    def __init__(self, plan_id: str = "unbound"):
        self.plan_id = sanitize(plan_id, 80)
        self._events: list[AuditEvent] = []

    def record(self, event: str, **fields: Any) -> AuditEvent:
        item = AuditEvent(
            sequence=len(self._events) + 1,
            plan_id=self.plan_id,
            event=sanitize(event, 80),
            fields={sanitize(str(key), 80): safe_value(value)
                    for key, value in fields.items()},
        )
        self._events.append(item)
        return item

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def to_dict(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]


__all__ = [
    "POLICY",
    "REDACTED",
    "RETRYABLE",
    "TERMINAL",
    "UNKNOWN",
    "AuditEvent",
    "AuditTrail",
    "FailureClassification",
    "classify_failure",
    "redact_secrets",
    "safe_value",
    "sanitize",
    "scope_fingerprint",
]

"""Optional bounded event adapter for integration-control decisions.

The repository's incident engine exposes a stable local ``EventSink`` boundary,
not a tracing backend. This module reuses that boundary only when it imports
cleanly; otherwise it falls back to an in-process no-op/in-memory adapter.
No event is transmitted, persisted to disk, or derived from untrusted text.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from .report import validate_report
from .security import redact

try:  # Optional, read-only integration with the merged incident observability API.
    from devobs.incidents.observability import (
        APPROVAL_REQUIRED,
        EVIDENCE_MISSING,
        REPORT_GENERATED,
        VALIDATION_COMPLETED,
        MemoryEventSink,
        NullEventSink,
        sanitize_event,
    )
    EVENT_INTERFACE = "incident_observability"
except Exception:  # noqa: BLE001 - unavailable or unstable interface disables reuse.
    APPROVAL_REQUIRED = "approval_required"
    EVIDENCE_MISSING = "evidence_missing"
    REPORT_GENERATED = "report_generated"
    VALIDATION_COMPLETED = "validation_completed"
    EVENT_INTERFACE = "offline_fallback"

    def sanitize_event(event: Any) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise ControlEventError("invalid_event")
        allowed = {
            "event", "incident_id", "category", "confidence", "status",
            "counts", "warnings", "report_digest", "detail",
        }
        result: dict[str, Any] = {}
        for key, value in event.items():
            if key not in allowed:
                continue
            if isinstance(value, str):
                safe, _changed = redact(value, limit=512)
                result[key] = safe
            elif type(value) in (int, float, bool):
                result[key] = value
            elif isinstance(value, (list, tuple)):
                result[key] = [
                    redact(str(item), limit=128)[0] for item in list(value)[:20]
                ]
            elif isinstance(value, dict):
                result[key] = {
                    str(name): redact(str(item), limit=128)[0]
                    for name, item in list(value.items())[:20]
                }
            else:
                result[key] = "[UNSUPPORTED_VALUE]"
        return result

    class NullEventSink:  # type: ignore[no-redef]
        """Validate an event without retaining it."""

        def emit(self, event: dict[str, Any]) -> None:
            sanitize_event(event)

    class MemoryEventSink:  # type: ignore[no-redef]
        """Deterministic in-process sink used by offline fixtures."""

        def __init__(self) -> None:
            self.events: list[dict[str, Any]] = []

        def emit(self, event: dict[str, Any]) -> None:
            self.events.append(sanitize_event(event))


class ControlEventError(ValueError):
    """Fixed, non-sensitive event emission diagnostic code."""


class EventSink(Protocol):
    """Adapter interface for local structured event consumers."""

    def emit(self, event: dict[str, Any]) -> None: ...


def make_memory_sink() -> MemoryEventSink:
    """Return a local memory sink using the available stable interface."""
    return MemoryEventSink()


def make_null_sink() -> NullEventSink:
    """Return a local validate-only sink using the available stable interface."""
    return NullEventSink()


def _event_common(report: dict[str, Any]) -> dict[str, Any]:
    counts = {
        "findings": len(report["findings"]),
        "failed_checks": len(report["checks"]["failed"]),
    }
    warnings = [item for item in report["warnings"] if isinstance(item, str)][:20]
    return {
        "incident_id": report["run_id"],
        "category": "integration_control",
        "counts": counts,
        "warnings": warnings,
    }


def build_control_events(report: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return bounded, redacted events derived only from a validated report."""
    validate_report(report)
    common = _event_common(report)
    decision = str(report["decision"])
    detail, _changed = redact(f"decision={decision}", limit=128)

    events: list[dict[str, Any]] = [
        {
            "event": VALIDATION_COMPLETED,
            **common,
            "status": decision,
            "detail": detail,
        },
        {
            "event": APPROVAL_REQUIRED,
            **common,
            "status": "PENDING_HUMAN",
            "detail": "human approval remains pending",
        },
        {
            "event": REPORT_GENERATED,
            **common,
            "status": decision,
            "report_digest": report["report_digest"],
            "detail": "schema-valid report generated",
        },
    ]

    missing_codes = {
        "APPROVAL_EVIDENCE_MISSING",
        "APPROVAL_EVIDENCE_PENDING",
        "COORDINATION_EVIDENCE_MISSING",
        "EXPECTED_SHA_MISSING",
    }
    codes = {item["code"] for item in report["findings"]}
    if codes & missing_codes or decision == "UNVERIFIED":
        events.append({
            "event": EVIDENCE_MISSING,
            **common,
            "status": "UNVERIFIED",
            "detail": "bounded evidence gaps remain",
        })

    return tuple(events)


def emit_control_events(report: dict[str, Any], *, sinks: Iterable[EventSink] = ()) -> int:
    """Emit sanitized events to local sinks; return the number of emitted events."""
    events = build_control_events(report)
    emitted = 0
    for sink in sinks:
        if not hasattr(sink, "emit"):
            raise ControlEventError("invalid_event_sink")
        for event in events:
            try:
                sink.emit(sanitize_event(event))
            except ControlEventError:
                raise
            except Exception as exc:  # noqa: BLE001 - never log sink internals or secrets.
                raise ControlEventError("event_sink_failed") from exc
            emitted += 1
    return emitted


__all__ = [
    "APPROVAL_REQUIRED",
    "EVIDENCE_MISSING",
    "EVENT_INTERFACE",
    "REPORT_GENERATED",
    "VALIDATION_COMPLETED",
    "ControlEventError",
    "EventSink",
    "MemoryEventSink",
    "NullEventSink",
    "build_control_events",
    "emit_control_events",
    "make_memory_sink",
    "make_null_sink",
]

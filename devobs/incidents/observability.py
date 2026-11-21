"""Structured local event interface for the incident engine.

No generic tracing event sink exists in this repository: the existing OpenTelemetry
adapter is metrics-only. ``EventSink`` is therefore a documented local adapter
boundary. Sinks receive only bounded, redacted structured fields.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from scripts.ci_failure_intelligence import redact_secrets

from .models import IncidentEngineError

INCIDENT_RECEIVED = "incident_received"
VALIDATION_COMPLETED = "validation_completed"
CLASSIFICATION_COMPLETED = "classification_completed"
EVIDENCE_MISSING = "evidence_missing"
REPORT_GENERATED = "report_generated"
APPROVAL_REQUIRED = "approval_required"
EVENT_NAMES = frozenset({
    INCIDENT_RECEIVED,
    VALIDATION_COMPLETED,
    CLASSIFICATION_COMPLETED,
    EVIDENCE_MISSING,
    REPORT_GENERATED,
    APPROVAL_REQUIRED,
})

_ALLOWED_FIELDS = frozenset({
    "event", "incident_id", "category", "confidence", "status", "counts",
    "warnings", "report_digest", "detail",
})
MAX_STRING_CHARS = 512
MAX_COLLECTION_ITEMS = 20
MAX_EVENT_BYTES = 4096


def _safe_string(value: Any) -> str:
    text = redact_secrets(str(value)).strip()
    return text[:MAX_STRING_CHARS] + ("[TRUNCATED]" if len(text) > MAX_STRING_CHARS else "")


def _safe_value(value: Any) -> Any:
    if type(value) is str:
        return _safe_string(value)
    if type(value) in (int, float, bool):
        return value
    if isinstance(value, Mapping):
        return {
            _safe_string(key): _safe_value(item)
            for key, item in list(value.items())[:MAX_COLLECTION_ITEMS]
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in list(value)[:MAX_COLLECTION_ITEMS]]
    return "[UNSUPPORTED_VALUE]"


def sanitize_event(event: Any) -> dict[str, Any]:
    """Return a bounded, redacted event or fail closed with a fixed code."""
    if not isinstance(event, Mapping):
        raise IncidentEngineError("invalid_event")
    name = event.get("event")
    if type(name) is not str or name not in EVENT_NAMES:
        raise IncidentEngineError("invalid_event_name")
    raw_allowed = {
        key: value for key, value in event.items()
        if isinstance(key, str) and key in _ALLOWED_FIELDS
    }
    raw_encoded = json.dumps(raw_allowed, sort_keys=True, separators=(",", ":"), default=str)
    if len(raw_encoded.encode("utf-8")) > MAX_EVENT_BYTES:
        raise IncidentEngineError("event_too_large")
    result = {str(key): _safe_value(value) for key, value in event.items()
              if isinstance(key, str) and key in _ALLOWED_FIELDS}
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    if len(encoded.encode("utf-8")) > MAX_EVENT_BYTES:
        raise IncidentEngineError("event_too_large")
    return result


class EventSink(Protocol):
    """Adapter interface for local structured event consumers."""

    def emit(self, event: dict[str, Any]) -> None: ...


class MemoryEventSink:
    """In-process sink useful for deterministic tests and local adapters."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(sanitize_event(event))


class LoggingEventSink:
    """Emit sanitized JSON through the standard logging module only."""

    def __init__(self, logger_name: str = "devobs.incidents") -> None:
        self.logger = logging.getLogger(logger_name)

    def emit(self, event: dict[str, Any]) -> None:
        payload = sanitize_event(event)
        self.logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))


class NullEventSink:
    """Validate an event without persisting or transmitting it."""

    def emit(self, event: dict[str, Any]) -> None:
        sanitize_event(event)


def emit_events(sinks: Iterable[EventSink], event: dict[str, Any]) -> None:
    """Emit one sanitized event to each configured local sink."""
    for sink in sinks:
        sink.emit(event)


__all__ = [
    "APPROVAL_REQUIRED",
    "CLASSIFICATION_COMPLETED",
    "EVIDENCE_MISSING",
    "EVENT_NAMES",
    "INCIDENT_RECEIVED",
    "LoggingEventSink",
    "MemoryEventSink",
    "NullEventSink",
    "REPORT_GENERATED",
    "VALIDATION_COMPLETED",
    "emit_events",
    "sanitize_event",
]

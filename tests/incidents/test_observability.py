"""Behavior tests for bounded, redacted structured local events."""
from __future__ import annotations

import unittest

from devobs.incidents.models import IncidentEngineError
from devobs.incidents.observability import (
    CLASSIFICATION_COMPLETED,
    INCIDENT_RECEIVED,
    LoggingEventSink,
    MemoryEventSink,
    NullEventSink,
    emit_events,
    sanitize_event,
)


class ObservabilityTests(unittest.TestCase):
    def test_event_is_redacted_bounded_and_allowlisted(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        event = sanitize_event({
            "event": INCIDENT_RECEIVED,
            "incident_id": "inc-1",
            "detail": f"token={secret}",
            "counts": {"evidence": 2, "secret": secret},
            "untrusted_field": "must not appear",
        })
        rendered = str(event)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("untrusted_field", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertEqual(event["event"], INCIDENT_RECEIVED)

    def test_memory_sink_keeps_a_sanitized_copy(self) -> None:
        sink = MemoryEventSink()
        emit_events((sink,), {"event": CLASSIFICATION_COMPLETED, "category": "TEST_FAILURE"})
        self.assertEqual(len(sink.events), 1)
        self.assertEqual(sink.events[0]["category"], "TEST_FAILURE")

    def test_logging_sink_does_not_emit_raw_secret(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        with self.assertLogs("devobs.incidents.test", level="INFO") as captured:
            LoggingEventSink("devobs.incidents.test").emit({
                "event": INCIDENT_RECEIVED,
                "detail": f"token={secret}",
            })
        self.assertNotIn(secret, "\n".join(captured.output))

    def test_invalid_events_fail_closed(self) -> None:
        for event, code in (
            (None, "invalid_event"),
            ({"event": "unknown"}, "invalid_event_name"),
            ({"event": INCIDENT_RECEIVED, "detail": "x" * 10_000}, "event_too_large"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(IncidentEngineError) as raised:
                    sanitize_event(event)
                self.assertEqual(raised.exception.code, code)

    def test_null_sink_validates_without_state(self) -> None:
        sink = NullEventSink()
        sink.emit({"event": INCIDENT_RECEIVED})
        self.assertFalse(hasattr(sink, "events"))


if __name__ == "__main__":
    unittest.main()

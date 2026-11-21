"""Offline observability behavior for integration-control hardening."""

from __future__ import annotations

import json
import socket
import subprocess
import unittest
from unittest import mock

from devobs.integration_control.control_events import (
    EVENT_INTERFACE,
    ControlEventError,
    build_control_events,
    emit_control_events,
    make_memory_sink,
    make_null_sink,
)
from devobs.integration_control.hardening import evaluate_hardened
from devobs.integration_control.report import finalize_report, validate_report

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/integration_control
    import helpers as h

EXPECTED_EVENTS = {
    "validation_completed",
    "approval_required",
    "report_generated",
    "evidence_missing",
}


class ControlEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = evaluate_hardened(h.snapshot(), approval_evidence=[])

    def test_event_interface_is_declared(self) -> None:
        self.assertIn(EVENT_INTERFACE, {"incident_observability", "offline_fallback"})
        self.assertTrue(validate_report(self.report))

    def test_events_are_bounded_and_use_allowlisted_names(self) -> None:
        events = build_control_events(self.report)

        self.assertEqual(len(events), 4)
        self.assertTrue(all(event["event"] in EXPECTED_EVENTS for event in events))
        self.assertTrue(all(event["incident_id"] == self.report["run_id"] for event in events))
        self.assertTrue(all(len(json.dumps(event)) < 4096 for event in events))

    def test_memory_sink_receives_sanitized_events(self) -> None:
        sink = make_memory_sink()

        emitted = emit_control_events(self.report, sinks=[sink])

        self.assertEqual(emitted, 4)
        self.assertEqual(len(sink.events), 4)
        self.assertEqual(sink.events[0]["event"], "validation_completed")

    def test_null_sink_validates_without_retaining(self) -> None:
        sink = make_null_sink()

        emitted = emit_control_events(self.report, sinks=[sink])

        self.assertEqual(emitted, 4)
        self.assertFalse(hasattr(sink, "events"))

    def test_secret_in_report_metadata_is_redacted(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        report = finalize_report({**self.report, "run_id": secret})
        sink = make_memory_sink()

        emit_control_events(report, sinks=[sink])
        rendered = json.dumps(sink.events, sort_keys=True)

        self.assertNotIn(secret, rendered)

    def test_invalid_sink_fails_closed(self) -> None:
        with self.assertRaises(ControlEventError) as context:
            emit_control_events(self.report, sinks=[object()])

        self.assertEqual(str(context.exception), "invalid_event_sink")

    def test_event_emission_uses_no_network_or_subprocess(self) -> None:
        def forbidden(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("network or subprocess access attempted")

        with mock.patch.object(socket.socket, "connect", forbidden), \
                mock.patch("socket.create_connection", forbidden), \
                mock.patch.object(subprocess, "run", forbidden), \
                mock.patch.object(subprocess, "Popen", forbidden):
            emit_control_events(self.report, sinks=[make_memory_sink()])

        self.assertTrue(self.report["offline"])


if __name__ == "__main__":
    unittest.main()

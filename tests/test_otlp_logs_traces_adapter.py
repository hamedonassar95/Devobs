"""Synthetic, offline tests for the OTLP/JSON logs and traces SafeSignal adapter."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from integrations.otlp_logs_traces_adapter import (  # noqa: E402
    MAX_INPUT_BYTES,
    OtlpAdapterError,
    convert_text,
)

NOW = datetime.now(timezone.utc).replace(microsecond=0)
SCOPE = {"tenant": "alpha", "project": "devobs-local", "source_sha": "a" * 40,
         "now_utc": NOW}
SCRIPT = ROOT / "scripts/integrations/otlp_logs_traces_adapter.py"


def nanos(seconds: int = 0) -> str:
    value = NOW + timedelta(seconds=seconds)
    return str(int(value.timestamp()) * 1_000_000_000 + value.microsecond * 1000)


def log_record(seconds: int = 0, operation: str = "http.request", status: str = "error") -> dict:
    return {
        "timeUnixNano": nanos(seconds),
        "attributes": [
            {"key": "devobs.operation", "value": {"stringValue": operation}},
            {"key": "devobs.status", "value": {"stringValue": status}},
        ],
    }


def resource_logs(service: str = "api", records: list[dict] | None = None) -> dict:
    return {
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": service}},
        ]},
        "scopeLogs": [{"scope": {}, "logRecords": [log_record()] if records is None else records}],
    }


def request(groups: list[dict] | None = None) -> dict:
    return {"resourceLogs": [resource_logs()] if groups is None else groups}


def span_record(seconds: int = -3, duration_ms: int = 250, status: int = 2,
                operation: str = "http.request") -> dict:
    start = int((NOW + timedelta(seconds=seconds)).timestamp()) * 1_000_000_000
    return {
        "traceId": "1" * 32,
        "spanId": "2" * 16,
        "name": operation,
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(start + duration_ms * 1_000_000),
        "status": {"code": status},
    }


def resource_spans(service: str = "api", spans: list[dict] | None = None) -> dict:
    return {
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": service}},
        ]},
        "scopeSpans": [{"scope": {}, "spans": [span_record()] if spans is None else spans}],
    }


def trace_request(groups: list[dict] | None = None) -> dict:
    return {"resourceSpans": [resource_spans()] if groups is None else groups}


class OtlpLogsTracesAdapterTests(unittest.TestCase):
    def test_valid_logs_become_only_scoped_safe_metadata(self):
        result = convert_text(json.dumps(request()), **SCOPE)
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual((signal.kind, signal.service, signal.operation, signal.status),
                         ("log", "api", "http.request", "error"))
        self.assertEqual((signal.tenant, signal.project, signal.source_sha),
                         ("alpha", "devobs-local", "a" * 40))
        self.assertEqual(signal.observed_at, NOW.isoformat().replace("+00:00", "Z"))
        self.assertEqual(len(signal.evidence_digest), 64)
        self.assertNotIn("body", repr(signal))

    def test_valid_traces_keep_only_safe_scope_and_duration(self):
        signal, = convert_text(json.dumps(trace_request()), **SCOPE)
        self.assertEqual((signal.kind, signal.service, signal.operation, signal.status),
                         ("trace", "api", "http.request", "error"))
        self.assertEqual(signal.duration_ms, 250)
        self.assertEqual((signal.tenant, signal.project, signal.source_sha),
                         ("alpha", "devobs-local", "a" * 40))
        self.assertNotIn("traceId", repr(signal))
        self.assertNotIn("spanId", repr(signal))

    def test_trace_status_codes_map_to_bounded_safe_values(self):
        for code, expected in ((0, "unknown"), (1, "ok"), (2, "error")):
            with self.subTest(code=code):
                signal, = convert_text(
                    json.dumps(trace_request([resource_spans(spans=[span_record(status=code)])])),
                    **SCOPE,
                )
                self.assertEqual(signal.status, expected)
        default_status = span_record()
        del default_status["status"]
        signal, = convert_text(
            json.dumps(trace_request([resource_spans(spans=[default_status])])), **SCOPE
        )
        self.assertEqual(signal.status, "unknown")

    def test_multiple_resources_sort_deterministically_and_fallback_to_observed_time(self):
        first = resource_logs("worker", [log_record(-10, "ci.check", "ok")])
        second_record = log_record(-20, "deploy.change", "unknown")
        second_record["observedTimeUnixNano"] = second_record.pop("timeUnixNano")
        second_record["timeUnixNano"] = "0"
        second = resource_logs("api", [second_record])
        forward = convert_text(json.dumps(request([first, second])), **SCOPE)
        reverse = convert_text(json.dumps(request([second, first])), **SCOPE)
        self.assertEqual(forward, reverse)
        self.assertEqual([item.service for item in forward], ["api", "worker"])

    def test_raw_body_trace_ids_severity_and_arbitrary_attributes_fail_closed(self):
        bad_records = [
            log_record() | {"body": {"stringValue": "password=synthetic"}},
            log_record() | {"traceId": "a" * 32},
            log_record() | {"severityText": "ERROR"},
            log_record() | {"attributes": log_record()["attributes"] + [
                {"key": "user.email", "value": {"stringValue": "person@example.test"}},
            ]},
            log_record() | {"attributes": [
                {"key": "devobs.operation", "value": {"stringValue": "unknown.operation"}},
                {"key": "devobs.status", "value": {"stringValue": "error"}},
            ]},
        ]
        for record in bad_records:
            with self.subTest(record_keys=sorted(record)):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(request([resource_logs(records=[record])])), **SCOPE)

    def test_unreviewed_resources_scopes_attributes_and_mixed_batches_are_denied(self):
        wrong_resource = resource_logs()
        wrong_resource["resource"]["attributes"].append(
            {"key": "host.name", "value": {"stringValue": "node-1"}}
        )
        named_scope = resource_logs()
        named_scope["scopeLogs"][0]["scope"] = {"name": "library"}
        mixed_batch = request([resource_logs(), resource_logs(records=[log_record() | {"body": "unsafe"}])])
        for value in (request([wrong_resource]), request([named_scope]), mixed_batch):
            with self.subTest(value=value):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(value), **SCOPE)

    def test_trace_attributes_events_links_and_free_status_text_are_rejected(self):
        bad_spans = [
            span_record() | {"attributes": [{"key": "user.email", "value": {
                "stringValue": "person@example.test"}}]},
            span_record() | {"events": [{"name": "synthetic-private-marker"}]},
            span_record() | {"links": [{"traceId": "1" * 32}]},
            span_record() | {"status": {"code": 2, "message": "private-marker"}},
            span_record(operation="user/314159"),
        ]
        for span in bad_spans:
            with self.subTest(span_keys=sorted(span)):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(trace_request([resource_spans(spans=[span])])), **SCOPE)

    def test_invalid_trace_ids_status_duration_and_timestamps_fail_closed(self):
        invalid_spans = [
            span_record() | {"traceId": "0" * 32},
            span_record() | {"spanId": "not-hex-value!!"},
            span_record() | {"status": {"code": 3}},
            span_record() | {"startTimeUnixNano": "18446744073709551616"},
            span_record(duration_ms=600_001),
            span_record(seconds=0, duration_ms=-1),
        ]
        for span in invalid_spans:
            with self.subTest(span=span):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(trace_request([resource_spans(spans=[span])])), **SCOPE)

    def test_invalid_timestamps_stale_events_duplicates_and_batch_limits_fail(self):
        invalid_records = [
            log_record() | {"timeUnixNano": "18446744073709551616"},
            log_record() | {"timeUnixNano": "not-a-timestamp"},
            log_record() | {"timeUnixNano": "0"},
            log_record(-901),
            log_record() | {"timeUnixNano": True},
        ]
        for record in invalid_records:
            with self.subTest(record=record):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(request([resource_logs(records=[record])])), **SCOPE)
        duplicate = request([resource_logs(records=[log_record(), log_record()])])
        with self.assertRaises(OtlpAdapterError):
            convert_text(json.dumps(duplicate), **SCOPE)
        too_many = request([resource_logs(records=[log_record(-i) for i in range(33)])])
        with self.assertRaises(OtlpAdapterError):
            convert_text(json.dumps(too_many), **SCOPE)

    def test_duplicate_json_keys_malformed_input_and_oversize_are_rejected(self):
        for raw in (
            '{"resourceLogs":[],"resourceLogs":[]}',
            '{"resourceLogs":[{"resource":{"attributes":[]},"scopeLogs":[]}]}',
            "not-json",
            "x" * (MAX_INPUT_BYTES + 1),
        ):
            with self.subTest(length=len(raw)):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(raw, **SCOPE)

    def test_empty_resource_scope_and_record_collections_are_rejected(self):
        empty_resources = request([])
        empty_scopes = request([resource_logs() | {"scopeLogs": []}])
        empty_records = request([resource_logs(records=[])])
        for value in (empty_resources, empty_scopes, empty_records):
            with self.subTest(value=value):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(value), **SCOPE)

        invalid_trace_batches = (
            {"resourceSpans": []},
            {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": []}]},
            trace_request([resource_spans(spans=[])]),
            trace_request([resource_spans(spans=[span_record(seconds=-index) for index in range(33)])]),
            request() | trace_request(),
        )
        for value in invalid_trace_batches:
            with self.subTest(value=value):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(value), **SCOPE)

    def test_caller_scope_and_source_sha_are_required_by_the_existing_gate(self):
        for changes in (
            {"tenant": "person@example.test"},
            {"project": "../private"},
            {"source_sha": "not-a-sha"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(OtlpAdapterError):
                    convert_text(json.dumps(request()), **(SCOPE | changes))

    def test_cli_emits_only_safe_output_and_fixed_errors_for_file_and_stdin(self):
        raw = json.dumps(request())
        common = ["--tenant", "alpha", "--project", "devobs-local", "--source-sha", "a" * 40]
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "safe.json"
            input_path.write_text(raw, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(input_path), *common],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertNotIn("resourceLogs", result.stdout)
            self.assertNotIn("body", result.stdout)
            output = json.loads(result.stdout)
            self.assertEqual(output["service"], "api")
            self.assertEqual(output["source_sha"], "a" * 40)

            trace_path = Path(folder) / "trace.json"
            trace_path.write_text(json.dumps(trace_request()), encoding="utf-8")
            traced = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(trace_path), *common],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(traced.returncode, 0, traced.stderr)
            trace_output = json.loads(traced.stdout)
            self.assertEqual((trace_output["kind"], trace_output["duration_ms"]),
                             ("trace", 250))
            self.assertNotIn("traceId", traced.stdout)

            poisoned = json.dumps(request([resource_logs(records=[
                log_record() | {"body": {"stringValue": "private-marker"}},
            ])]))
            failed = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", "-", *common],
                input=poisoned, check=False, capture_output=True, text=True,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(failed.stdout, "")
            self.assertEqual(failed.stderr, "otlp-adapter: invalid_otlp_record\n")
            self.assertNotIn("private-marker", failed.stderr)

            link = Path(folder) / "input-link.json"
            link.symlink_to(input_path)
            rejected_link = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(link), *common],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(rejected_link.returncode, 2)
            self.assertEqual(rejected_link.stdout, "")
            self.assertEqual(rejected_link.stderr, "otlp-adapter: input_unavailable\n")


if __name__ == "__main__":
    unittest.main()

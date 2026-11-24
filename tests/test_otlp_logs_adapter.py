"""Synthetic, offline tests for the OTLP/JSON logs SafeSignal adapter."""
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

from integrations.otlp_logs_adapter import (  # noqa: E402
    MAX_INPUT_BYTES,
    OtlpLogsAdapterError,
    convert_text,
)

NOW = datetime.now(timezone.utc).replace(microsecond=0)
SCOPE = {"tenant": "alpha", "project": "devobs-local", "source_sha": "a" * 40,
         "now_utc": NOW}
SCRIPT = ROOT / "scripts/integrations/otlp_logs_adapter.py"


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


class OtlpLogsAdapterTests(unittest.TestCase):
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
                with self.assertRaises(OtlpLogsAdapterError):
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
                with self.assertRaises(OtlpLogsAdapterError):
                    convert_text(json.dumps(value), **SCOPE)

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
                with self.assertRaises(OtlpLogsAdapterError):
                    convert_text(json.dumps(request([resource_logs(records=[record])])), **SCOPE)
        duplicate = request([resource_logs(records=[log_record(), log_record()])])
        with self.assertRaises(OtlpLogsAdapterError):
            convert_text(json.dumps(duplicate), **SCOPE)
        too_many = request([resource_logs(records=[log_record(-i) for i in range(33)])])
        with self.assertRaises(OtlpLogsAdapterError):
            convert_text(json.dumps(too_many), **SCOPE)

    def test_duplicate_json_keys_malformed_input_and_oversize_are_rejected(self):
        for raw in (
            '{"resourceLogs":[],"resourceLogs":[]}',
            '{"resourceLogs":[{"resource":{"attributes":[]},"scopeLogs":[]}]}',
            "not-json",
            "x" * (MAX_INPUT_BYTES + 1),
        ):
            with self.subTest(length=len(raw)):
                with self.assertRaises(OtlpLogsAdapterError):
                    convert_text(raw, **SCOPE)

    def test_empty_resource_scope_and_record_collections_are_rejected(self):
        empty_resources = request([])
        empty_scopes = request([resource_logs() | {"scopeLogs": []}])
        empty_records = request([resource_logs(records=[])])
        for value in (empty_resources, empty_scopes, empty_records):
            with self.subTest(value=value):
                with self.assertRaises(OtlpLogsAdapterError):
                    convert_text(json.dumps(value), **SCOPE)

    def test_caller_scope_and_source_sha_are_required_by_the_existing_gate(self):
        for changes in (
            {"tenant": "person@example.test"},
            {"project": "../private"},
            {"source_sha": "not-a-sha"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(OtlpLogsAdapterError):
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

            poisoned = json.dumps(request([resource_logs(records=[
                log_record() | {"body": {"stringValue": "private-marker"}},
            ])]))
            failed = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", "-", *common],
                input=poisoned, check=False, capture_output=True, text=True,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(failed.stdout, "")
            self.assertEqual(failed.stderr, "otlp-logs-adapter: invalid_otlp_record\n")
            self.assertNotIn("private-marker", failed.stderr)

            link = Path(folder) / "input-link.json"
            link.symlink_to(input_path)
            rejected_link = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(link), *common],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(rejected_link.returncode, 2)
            self.assertEqual(rejected_link.stdout, "")
            self.assertEqual(rejected_link.stderr, "otlp-logs-adapter: input_unavailable\n")


if __name__ == "__main__":
    unittest.main()

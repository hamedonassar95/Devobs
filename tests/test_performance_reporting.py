"""Tests for the versioned, privacy-minimized benchmark report format."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine as engine  # noqa: E402
from performance_intelligence import reporting  # noqa: E402


def valid_result(samples=(0.01, 0.02, 0.03)):
    return engine.BenchmarkResult(
        benchmark_id="devobs.event_evidence.parse_events.v1",
        name=engine.BENCHMARK_NAMES["devobs.event_evidence.parse_events.v1"],
        samples_seconds=samples,
    )


def valid_results():
    return [
        engine.BenchmarkResult(benchmark_id, name, (0.01, 0.02, 0.03))
        for benchmark_id, name in engine.BENCHMARK_NAMES.items()
    ]


def valid_metadata(**overrides):
    result = {
        "source_sha": "a" * 40,
        "python_version": "3.12.14",
        "platform": "linux",
        "architecture": "x86_64",
        "measurement_mode": "smoke",
    }
    result.update(overrides)
    return result


def valid_native_json():
    return json.dumps({
        "version": "1.0",
        "metadata": {"unit": "second"},
        "benchmarks": [
            {"metadata": {"name": name}, "runs": [{"values": [0.01, 0.02], "warmups": []}]}
            for name in engine.BENCHMARK_NAMES
        ],
    }).encode()


class PerformanceReportingTests(unittest.TestCase):
    def test_summary_contains_valid_statistics_and_schema(self):
        summary = reporting.build_summary([valid_result()], **valid_metadata())
        self.assertEqual(summary["schema_version"], reporting.SCHEMA_VERSION)
        self.assertEqual(summary["source_sha"], "a" * 40)
        row = summary["benchmarks"][0]
        self.assertAlmostEqual(row["mean_seconds"], 0.02)
        self.assertAlmostEqual(row["median_seconds"], 0.02)
        self.assertEqual(row["sample_count"], 3)
        reporting.validate_summary(summary)

    def test_empty_or_schema_incompatible_reports_fail_closed(self):
        with self.assertRaises(reporting.ReportValidationError):
            reporting.build_summary([], **valid_metadata())
        report = reporting.build_summary([valid_result()], **valid_metadata())
        report["schema_version"] += 1
        with self.assertRaises(reporting.ReportValidationError):
            reporting.validate_summary(report)

    def test_invalid_numeric_values_are_rejected(self):
        for invalid in (-1.0, float("nan"), float("inf")):
            with self.subTest(invalid=invalid), self.assertRaises(
                (engine.BenchmarkValidationError, reporting.ReportValidationError)
            ):
                result = valid_result((0.01, invalid))
                reporting.build_summary([result], **valid_metadata())

    def test_csv_output_has_expected_columns_and_values(self):
        report = reporting.build_summary([valid_result()], **valid_metadata())
        with tempfile.TemporaryDirectory() as temporary:
            json_path = Path(temporary) / "summary.json"
            csv_path = Path(temporary) / "summary.csv"
            reporting.write_summary_files(report, json_path, csv_path)
            with csv_path.open(newline="", encoding="utf-8") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["benchmark_id"], "devobs.event_evidence.parse_events.v1")
            self.assertEqual(row["sample_count"], "3")
            self.assertAlmostEqual(float(row["mean_seconds"]), 0.02)
            self.assertEqual(json.loads(json_path.read_text())["schema_version"], 1)

    def test_existing_reports_are_not_overwritten_without_consent(self):
        report = reporting.build_summary([valid_result()], **valid_metadata())
        with tempfile.TemporaryDirectory() as temporary:
            json_path = Path(temporary) / "summary.json"
            csv_path = Path(temporary) / "summary.csv"
            json_path.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(reporting.ReportWriteError, "exists"):
                reporting.write_summary_files(report, json_path, csv_path)
            self.assertEqual(json_path.read_text(encoding="utf-8"), "preserve")

    def test_sensitive_metadata_is_rejected_and_never_serialized(self):
        with self.assertRaises(reporting.ReportValidationError):
            reporting.build_summary(
                [valid_result()], **valid_metadata(hostname="private-host")
            )
        report = reporting.build_summary([valid_result()], **valid_metadata())
        serialized = json.dumps(report)
        for sensitive_key in ("hostname", "environment", "cwd", "executable"):
            self.assertNotIn(sensitive_key, serialized)
        self.assertNotIn("private-host", serialized)

    def test_invalid_output_destinations_are_rejected(self):
        report = reporting.build_summary(valid_results(), **valid_metadata())
        with tempfile.TemporaryDirectory() as temporary:
            repo_path = ROOT / "README.md"
            with self.assertRaises(reporting.ReportWriteError):
                reporting.write_run_reports(
                    report,
                    ROOT / "tests" / "fixtures" / "performance",
                    "a" * 40,
                    native_pyperf_json=valid_native_json(),
                    repository_root=repo_path.parent,
                )

    def test_run_reports_create_all_formats_without_overwrite(self):
        report = reporting.build_summary(valid_results(), **valid_metadata())
        with tempfile.TemporaryDirectory() as temporary:
            outputs = reporting.write_run_reports(
                report, Path(temporary), "a" * 40, valid_native_json(), ROOT,
            )
            self.assertTrue(outputs[0].name.endswith(".pyperf.json"))
            self.assertTrue(outputs[1].name.endswith(".json"))
            self.assertTrue(outputs[2].name.endswith(".csv"))
            original = outputs[1].read_text(encoding="utf-8")
            with self.assertRaisesRegex(reporting.ReportWriteError, "exists"):
                reporting.write_run_reports(
                    report, Path(temporary), "a" * 40, valid_native_json(), ROOT,
                )
            self.assertEqual(outputs[1].read_text(encoding="utf-8"), original)

    def test_native_pyperf_report_must_be_sanitized(self):
        report = reporting.build_summary([valid_result()], **valid_metadata())
        native = json.loads(valid_native_json())
        native["metadata"]["hostname"] = "private-host"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(reporting.ReportWriteError, "native"):
                reporting.write_run_reports(
                    report, Path(temporary), "a" * 40,
                    json.dumps(native).encode(), repository_root=ROOT,
                )


if __name__ == "__main__":
    unittest.main()

"""Offline contract tests for sanitized pyperformance reports."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import pyperformance_reporting as reporting  # noqa: E402
from performance_intelligence.pyperformance_contract import PY_PERFORMANCE_COMMIT  # noqa: E402


class PyPerformanceReportingTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "source_sha": "a" * 40,
            "suite_source_sha": PY_PERFORMANCE_COMMIT,
            "python_version": "3.12.14",
            "platform": "linux",
            "architecture": "x86_64",
            "measurement_mode": "smoke",
        }
        self.results = [
            reporting.PyPerformanceResult("float", (0.01, 0.02, 0.03)),
            reporting.PyPerformanceResult("json_dumps", (0.02, 0.03, 0.04)),
        ]

    def test_valid_results_produce_stable_versioned_summary(self):
        summary = reporting.build_summary(self.results, **self.metadata)
        reporting.validate_summary(summary)
        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["suite_name"], "pyperformance")
        self.assertEqual(summary["suite_source_sha"], PY_PERFORMANCE_COMMIT)
        self.assertEqual(summary["benchmarks"][0]["benchmark_id"], "pyperformance.float.v1")
        self.assertEqual(summary["benchmarks"][0]["sample_count"], 3)

    def test_empty_or_unexpected_results_fail_closed(self):
        with self.assertRaisesRegex(reporting.ReportValidationError, "empty_suite"):
            reporting.build_summary([], **self.metadata)
        with self.assertRaises(reporting.ReportValidationError):
            reporting.build_summary(
                [reporting.PyPerformanceResult("unreviewed", (0.1, 0.2))],
                **self.metadata,
            )

    def test_invalid_numeric_values_and_metadata_are_rejected(self):
        for samples in ((-0.1, 0.2), (float("nan"), 0.2), (float("inf"), 0.2), (0.1,)):
            with self.subTest(samples=samples), self.assertRaises(reporting.ReportValidationError):
                reporting.build_summary(
                    [reporting.PyPerformanceResult("float", samples)], **self.metadata
                )
        with self.assertRaises(reporting.ReportValidationError):
            reporting.build_summary(
                self.results, **(self.metadata | {"hostname": "private-host"})
            )
        for metadata in (
            self.metadata | {"python_version": "3.13.0"},
            self.metadata | {"platform": []},
        ):
            with self.subTest(metadata=metadata), self.assertRaises(reporting.ReportValidationError):
                reporting.build_summary(self.results, **metadata)

    def test_unknown_schema_and_sensitive_fields_are_rejected(self):
        summary = reporting.build_summary(self.results, **self.metadata)
        with self.assertRaisesRegex(reporting.ReportValidationError, "incompatible_schema"):
            reporting.validate_summary(summary | {"schema_version": 2})
        with self.assertRaises(reporting.ReportValidationError):
            reporting.validate_summary(summary | {"environment": {"TOKEN": "secret"}})

    def test_json_and_csv_reports_are_valid_and_exclude_sensitive_metadata(self):
        summary = reporting.build_summary(self.results, **self.metadata)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            native = reporting.sanitized_native_json(
                [
                    ("float", [0.01, 0.02, 0.03]),
                    ("json_dumps", [0.02, 0.03, 0.04]),
                ]
            )
            paths = reporting.write_reports(summary, native, output, overwrite=False)
            json_report = json.loads(paths[1].read_text(encoding="utf-8"))
            with paths[2].open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(json_report, summary)
            self.assertEqual(len(rows), 2)
            self.assertNotIn(b"hostname", paths[0].read_bytes())
            self.assertNotIn(b"private-host", b"".join(path.read_bytes() for path in paths))

    def test_native_report_requires_allowlisted_names_and_finite_samples(self):
        valid = reporting.sanitized_native_json([("float", [0.01, 0.02])])
        reporting.validate_native_json(valid, {"float"})
        invalid = valid.replace(b'"name": "float"', b'"name": "unknown"')
        with self.assertRaises(reporting.ReportValidationError):
            reporting.validate_native_json(invalid, {"float"})
        non_finite = valid.replace(b"0.01", b"NaN ")
        with self.assertRaises(reporting.ReportValidationError):
            reporting.validate_native_json(non_finite, {"float"})

    def test_existing_outputs_are_not_overwritten_without_explicit_consent(self):
        summary = reporting.build_summary(self.results, **self.metadata)
        native = reporting.sanitized_native_json(
            [("float", [0.01, 0.02, 0.03]), ("json_dumps", [0.02, 0.03, 0.04])]
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            reporting.write_reports(summary, native, output, overwrite=False)
            with self.assertRaisesRegex(reporting.ReportWriteError, "destination_exists"):
                reporting.write_reports(summary, native, output, overwrite=False)

    def test_native_sample_counts_must_match_summary(self):
        summary = reporting.build_summary(self.results, **self.metadata)
        native = reporting.sanitized_native_json(
            [("float", [0.01, 0.02]), ("json_dumps", [0.02, 0.03])]
        )
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(reporting.ReportWriteError, "sample_count_mismatch"):
                reporting.write_reports(summary, native, Path(temporary))


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for bounded memory measurement reports."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine, comparison, resource_reporting  # noqa: E402


class ResourceReportingTests(unittest.TestCase):
    def test_builds_peak_private_memory_report_from_synthetic_samples(self):
        results = [
            resource_reporting.MemoryResult(benchmark_id, name, (1024, 1200, 1100))
            for benchmark_id, name in benchmark_engine.BENCHMARK_NAMES.items()
        ]
        summary = resource_reporting.build_summary(
            results, source_sha="a" * 40, suite_name="devobs",
            suite_version="1", suite_source_sha="a" * 40,
            python_version="3.12.14", platform="linux", architecture="x86_64",
            measurement_mode="statistical",
        )
        self.assertEqual(summary["metric"], "peak_private_bytes")
        self.assertEqual(summary["benchmarks"][0]["sample_count"], 3)
        self.assertGreater(summary["benchmarks"][0]["mean_bytes"], 0)

    def test_native_pyperf_memory_report_requires_byte_units_and_complete_samples(self):
        benchmark_id = next(iter(benchmark_engine.BENCHMARK_NAMES))
        native = {
            "version": "1.0", "metadata": {"unit": "byte"},
            "benchmarks": [{
                "metadata": {"name": benchmark_id},
                "runs": [{"values": [1000.0, 1100.0], "warmups": [[1, 900.0]]}],
            }],
        }
        self.assertEqual(resource_reporting.validate_native_json(
            json.dumps(native).encode(), {benchmark_id},
        ), {benchmark_id: 2})
        native["metadata"] = {"unit": "second"}
        with self.assertRaises(resource_reporting.ResourceReportError):
            resource_reporting.validate_native_json(
                json.dumps(native).encode(), {benchmark_id},
            )
        native["metadata"] = {"unit": "byte"}
        native["benchmarks"][0]["runs"][0]["values"] = [1000.0]
        with self.assertRaises(resource_reporting.ResourceReportError):
            resource_reporting.validate_native_json(
                json.dumps(native).encode(), {benchmark_id},
            )

    def test_single_upstream_pyperf_memory_name_is_normalized_and_sanitized(self):
        native = {
            "version": "1.0", "metadata": {"name": "float", "unit": "byte"},
            "benchmarks": [{
                "runs": [{"values": [1200.0, 1300.0], "warmups": []}],
            }],
        }
        normalized = resource_reporting.normalize_native_json(
            json.dumps(native).encode(), {"pyperformance.float.v1"},
        )
        parsed = json.loads(normalized)
        self.assertEqual(parsed["metadata"], {"unit": "byte"})
        self.assertEqual(parsed["benchmarks"][0]["metadata"], {"name": "float"})
        self.assertEqual(resource_reporting.validate_native_json(
            normalized, {"pyperformance.float.v1"},
        ), {"pyperformance.float.v1": 2})

    def test_run_writer_requires_native_values_to_match_json_and_csv_summaries(self):
        rows = [
            resource_reporting.MemoryResult(benchmark_id, name, (1024, 1200, 1100))
            for benchmark_id, name in benchmark_engine.BENCHMARK_NAMES.items()
        ]
        summary = resource_reporting.build_summary(
            rows, source_sha="a" * 40, suite_name="devobs", suite_version="1",
            suite_source_sha="a" * 40, python_version="3.12.14", platform="linux",
            architecture="x86_64", measurement_mode="smoke",
        )
        native = {
            "version": "1.0", "metadata": {"unit": "byte"},
            "benchmarks": [{
                "metadata": {"name": benchmark_id},
                "runs": [{"values": [1024, 1200, 1100], "warmups": []}],
            } for benchmark_id in benchmark_engine.BENCHMARK_NAMES],
        }
        encoded = json.dumps(native).encode()
        with tempfile.TemporaryDirectory() as directory:
            output = resource_reporting.write_run_report(
                summary, encoded, Path(directory), repository_root=ROOT,
            )
            self.assertTrue(all(path.is_file() for path in output))
            bad_summary = json.loads(json.dumps(summary))
            bad_summary["benchmarks"][0]["mean_bytes"] += 1
            with self.assertRaisesRegex(resource_reporting.ResourceReportWriteError, "native_summary_mismatch"):
                resource_reporting.write_run_report(
                    bad_summary, encoded, Path(directory), repository_root=ROOT,
                    overwrite=True,
                )

    def test_invalid_memory_values_and_unknown_benchmarks_are_rejected(self):
        for samples in ((), (-1, 3), (float("nan"), 1), (True, 2)):
            results = [
                resource_reporting.MemoryResult(benchmark_id, name, samples)
                for benchmark_id, name in benchmark_engine.BENCHMARK_NAMES.items()
            ]
            with self.subTest(samples=samples), self.assertRaises(resource_reporting.ResourceReportError):
                resource_reporting.build_summary(
                    results, source_sha="a" * 40, suite_name="devobs", suite_version="1",
                    suite_source_sha="a" * 40, python_version="3.12.14", platform="linux",
                    architecture="x86_64", measurement_mode="statistical",
                )

    def test_memory_reports_can_be_compared_only_as_statistical_same_host_runs(self):
        def make(source_sha: str, scale: float) -> dict[str, object]:
            results = [
                resource_reporting.MemoryResult(
                    benchmark_id, name,
                    tuple((index + 1) * 1024 * scale + sample for sample in range(20)),
                )
                for index, (benchmark_id, name) in enumerate(benchmark_engine.BENCHMARK_NAMES.items())
            ]
            return resource_reporting.build_summary(
                results, source_sha=source_sha, suite_name="devobs", suite_version="1",
                suite_source_sha=source_sha, python_version="3.12.14", platform="linux",
                architecture="x86_64", measurement_mode="statistical",
            )

        result = comparison.compare_summaries(
            make("a" * 40, 1), make("b" * 40, 2), same_host_confirmed=True,
        )
        self.assertEqual(result["metric"], "peak_private_bytes")
        self.assertTrue(all(row["status"] == "REGRESSION" for row in result["benchmarks"]))


if __name__ == "__main__":
    unittest.main()

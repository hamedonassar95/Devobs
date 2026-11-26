"""Behavioral tests for privacy-limited Prometheus textfile export."""
from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import (
    benchmark_engine, comparison, prometheus_export, reporting, resource_reporting,
)  # noqa: E402


def _summary() -> dict[str, object]:
    rows = [
        benchmark_engine.BenchmarkResult(
            benchmark_id, name, tuple(0.01 + sample / 100000 for sample in range(20)),
        )
        for benchmark_id, name in benchmark_engine.BENCHMARK_NAMES.items()
    ]
    return reporting.build_summary(
        rows, source_sha="a" * 40, python_version="3.12.14", platform="linux",
        architecture="x86_64", measurement_mode="statistical",
    )


class PrometheusExportTests(unittest.TestCase):
    def test_renders_allowlisted_metrics_without_paths_or_host_data(self):
        rendered = prometheus_export.render_metrics(_summary())
        self.assertIn("devobs_benchmark_mean_seconds", rendered)
        self.assertIn('benchmark_id="devobs.event_evidence.parse_events.v1"', rendered)
        self.assertIn('source_sha="' + "a" * 40 + '"', rendered)
        self.assertNotIn("/workspace", rendered)
        self.assertNotIn("hostname", rendered.lower())

    def test_export_is_atomic_and_refuses_existing_or_symlink_destinations(self):
        rendered = prometheus_export.render_metrics(_summary())
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "performance.prom"
            prometheus_export.write_metrics(rendered, destination)
            self.assertEqual(destination.read_text(), rendered)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o644)
            with self.assertRaises(prometheus_export.PrometheusExportError):
                prometheus_export.write_metrics(rendered, destination)

    def test_unknown_schema_or_unsafe_metadata_is_rejected(self):
        with self.assertRaises(prometheus_export.PrometheusExportError):
            prometheus_export.render_metrics({"schema_version": 999})
        bad = _summary() | {"python_version": '3.12.0",evil="x'}
        with self.assertRaises(prometheus_export.PrometheusExportError):
            prometheus_export.render_metrics(bad)
        with self.assertRaises(prometheus_export.PrometheusExportError):
            prometheus_export.render_metrics({"comparison_kind": "unknown"})

    def test_comparison_metrics_include_only_bounded_source_labels(self):
        baseline = _summary()
        candidate = baseline | {"source_sha": "b" * 40}
        result = comparison.compare_summaries(
            baseline, candidate, same_host_confirmed=True,
        )
        rendered = prometheus_export.render_metrics(result)
        self.assertIn("devobs_benchmark_change_percent", rendered)
        self.assertIn('baseline_sha="' + "a" * 40 + '"', rendered)
        self.assertNotIn("/tmp", rendered)

    def test_memory_summary_exports_private_bytes_metric(self):
        rows = [
            resource_reporting.MemoryResult(benchmark_id, name, tuple(1024 + value for value in range(20)))
            for benchmark_id, name in benchmark_engine.BENCHMARK_NAMES.items()
        ]
        summary = resource_reporting.build_summary(
            rows, source_sha="a" * 40, suite_name="devobs", suite_version="1",
            suite_source_sha="a" * 40, python_version="3.12.14", platform="linux",
            architecture="x86_64", measurement_mode="statistical",
        )
        rendered = prometheus_export.render_metrics(summary)
        self.assertIn("devobs_benchmark_peak_private_bytes_mean", rendered)
        self.assertIn("measurement_mode=\"statistical\"", rendered)

    def test_symlink_destination_is_rejected(self):
        rendered = prometheus_export.render_metrics(_summary())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.prom"
            destination = Path(directory) / "linked.prom"
            target.write_text("existing\n")
            destination.symlink_to(target)
            with self.assertRaises(prometheus_export.PrometheusExportError):
                prometheus_export.write_metrics(rendered, destination, overwrite=True)


if __name__ == "__main__":
    unittest.main()

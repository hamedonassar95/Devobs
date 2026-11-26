"""Behavioral tests for offline baseline/candidate comparison."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine, comparison, reporting  # noqa: E402


def _summary(source_sha: str, *, python_version: str = "3.12.14",
             mode: str = "statistical", scale: float = 1.0) -> dict[str, object]:
    rows = []
    for index, (benchmark_id, name) in enumerate(benchmark_engine.BENCHMARK_NAMES.items()):
        base = (index + 1) * 0.001 * scale
        samples = tuple(base + (sample * base / 100) for sample in range(20))
        rows.append(benchmark_engine.BenchmarkResult(benchmark_id, name, samples))
    return reporting.build_summary(
        rows, source_sha=source_sha, python_version=python_version, platform="linux",
        architecture="x86_64", measurement_mode=mode,
    )


class PerformanceComparisonTests(unittest.TestCase):
    def test_compares_statistical_reports_and_applies_multiple_test_correction(self):
        result = comparison.compare_summaries(
            _summary("a" * 40), _summary("b" * 40, scale=1.5), same_host_confirmed=True,
        )
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["comparison_kind"], "source_revision")
        self.assertEqual(len(result["benchmarks"]), 3)
        for row in result["benchmarks"]:
            self.assertIn(row["status"], {"REGRESSION", "IMPROVEMENT", "NO_DETECTED_CHANGE"})
            self.assertGreater(row["delta_percent"], 0)
            self.assertGreaterEqual(row["adjusted_p_value"], row["p_value"])

    def test_smoke_or_missing_same_host_confirmation_is_rejected(self):
        with self.assertRaises(comparison.ComparisonValidationError):
            comparison.compare_summaries(
                _summary("a" * 40, mode="smoke"), _summary("b" * 40), same_host_confirmed=True,
            )
        with self.assertRaises(comparison.ComparisonValidationError):
            comparison.compare_summaries(_summary("a" * 40), _summary("b" * 40))

    def test_same_source_reports_repeatability_variation_not_improvement(self):
        result = comparison.compare_summaries(
            _summary("a" * 40), _summary("a" * 40, scale=1.5), same_host_confirmed=True,
        )
        self.assertEqual(result["comparison_kind"], "repeatability")
        self.assertTrue(all(
            row["status"] == "REPEATABILITY_VARIATION" for row in result["benchmarks"]
        ))

    def test_cross_python_version_comparison_requires_explicit_opt_in(self):
        baseline = _summary("a" * 40)
        candidate = _summary("a" * 40, python_version="3.15.0")
        with self.assertRaises(comparison.ComparisonValidationError):
            comparison.compare_summaries(baseline, candidate, same_host_confirmed=True)
        result = comparison.compare_summaries(
            baseline, candidate, same_host_confirmed=True, allow_python_version_change=True,
        )
        self.assertEqual(result["comparison_kind"], "python_version")
        self.assertEqual(result["candidate"]["python_version"], "3.15.0")

    def test_invalid_and_incompatible_reports_fail_closed(self):
        with self.assertRaises(comparison.ComparisonValidationError):
            comparison.compare_summaries({}, _summary("b" * 40), same_host_confirmed=True)
        wrong_platform = _summary("b" * 40) | {"platform": "windows"}
        with self.assertRaises(comparison.ComparisonValidationError):
            comparison.compare_summaries(
                _summary("a" * 40), wrong_platform, same_host_confirmed=True,
            )

    def test_report_writer_preserves_existing_files_unless_overwrite_is_explicit(self):
        report = comparison.compare_summaries(
            _summary("a" * 40), _summary("b" * 40, scale=1.2), same_host_confirmed=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = comparison.write_comparison_report(report, Path(directory))
            self.assertTrue(all(path.exists() for path in paths))
            self.assertEqual(json.loads(paths[0].read_text())['schema_version'], 1)
            with self.assertRaises(comparison.ComparisonWriteError):
                comparison.write_comparison_report(report, Path(directory))

    def test_identical_report_files_cannot_be_compared_as_independent_runs(self):
        report = _summary("a" * 40)
        encoded = json.dumps(report).encode()
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            candidate = Path(directory) / "candidate.json"
            baseline.write_bytes(encoded)
            candidate.write_bytes(encoded)
            with self.assertRaisesRegex(comparison.ComparisonValidationError, "identical_reports"):
                comparison._load_report_pair(baseline, candidate)


if __name__ == "__main__":
    unittest.main()

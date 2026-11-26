"""Offline tests for the manual Devobs benchmark engine."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine as engine  # noqa: E402


class BenchmarkEngineTests(unittest.TestCase):
    def test_builtin_suite_uses_three_stable_offline_operations(self):
        suite = engine.benchmark_definitions()
        self.assertEqual(
            [item.benchmark_id for item in suite],
            [
                "devobs.event_evidence.parse_events.v1",
                "devobs.task_graph.evaluate.v1",
                "devobs.evaluation_splits.summarize.v1",
            ],
        )
        self.assertEqual(len({item.name for item in suite}), 3)
        self.assertTrue(all(item.run() is not None for item in suite))

    def test_synthetic_fixture_is_deterministic_and_not_a_timing_baseline(self):
        first = engine.load_synthetic_workloads()
        second = engine.load_synthetic_workloads()
        self.assertEqual(first, second)
        self.assertEqual(first["fixture_kind"], "synthetic_workload_sizes")
        self.assertNotIn("mean_seconds", json.dumps(first))

    def test_missing_or_malformed_synthetic_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "invalid.json"
            with mock.patch.object(engine, "FIXTURE", fixture):
                with self.assertRaisesRegex(engine.BenchmarkValidationError, "invalid_synthetic_fixture"):
                    engine.load_synthetic_workloads()
            fixture.write_text('{"schema_version": NaN}', encoding="utf-8")
            with mock.patch.object(engine, "FIXTURE", fixture):
                with self.assertRaisesRegex(engine.BenchmarkValidationError, "invalid_synthetic_fixture"):
                    engine.load_synthetic_workloads()

    def test_valid_result_and_measurement_configuration(self):
        result = engine.BenchmarkResult(
            benchmark_id="devobs.event_evidence.parse_events.v1",
            name=engine.BENCHMARK_NAMES["devobs.event_evidence.parse_events.v1"],
            samples_seconds=(0.01, 0.02, 0.03),
        )
        engine.validate_results([result])
        smoke = engine.MeasurementConfig.for_mode("smoke")
        statistical = engine.MeasurementConfig.for_mode("statistical")
        self.assertEqual(smoke.processes, 1)
        self.assertGreaterEqual(statistical.processes, 3)
        self.assertGreater(statistical.values, smoke.values)
        self.assertEqual(smoke.mode, "smoke")

    def test_empty_results_are_rejected(self):
        with self.assertRaisesRegex(engine.BenchmarkValidationError, "empty_suite"):
            engine.validate_results([])

    def test_negative_nan_and_infinite_samples_are_rejected(self):
        for value in (-0.1, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                result = engine.BenchmarkResult(
                    "devobs.example.operation.v1", "Example", (0.01, value)
                )
                with self.assertRaises(engine.BenchmarkValidationError):
                    engine.validate_results([result])

    def test_metadata_allowlist_rejects_missing_or_sensitive_fields(self):
        metadata = {
            "source_sha": "a" * 40,
            "python_version": "3.12.14",
            "platform": "linux",
            "architecture": "x86_64",
            "measurement_mode": "smoke",
        }
        engine.validate_metadata(metadata)
        engine.validate_metadata(metadata | {"python_version": "3.15.0"})
        for invalid in (
            {key: value for key, value in metadata.items() if key != "source_sha"},
            {**metadata, "hostname": "private-host"},
            {**metadata, "python_version": "unknown"},
            {**metadata, "python_version": "3.13.0"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(
                engine.BenchmarkValidationError
            ):
                engine.validate_metadata(invalid)

    def test_timeout_and_worker_failure_are_fail_closed(self):
        with mock.patch.object(
            engine, "_execute_process", side_effect=engine.subprocess.TimeoutExpired(["python"], 1)
        ):
            with self.assertRaisesRegex(engine.BenchmarkExecutionError, "timeout"):
                engine.run_bounded_command(["python", "benchmark"], timeout_seconds=1)
        failed = engine.subprocess.CompletedProcess(["python"], 9, "", "")
        with mock.patch.object(engine, "_execute_process", return_value=failed):
            with self.assertRaisesRegex(engine.BenchmarkExecutionError, "worker_failed"):
                engine.run_bounded_command(["python", "benchmark"], timeout_seconds=1)

    def test_real_subprocess_timeout_and_nonzero_exit_are_bounded(self):
        with self.assertRaisesRegex(engine.BenchmarkExecutionError, "timeout"):
            engine.run_bounded_command(
                [sys.executable, "-c", "import time; time.sleep(2)"], timeout_seconds=1
            )
        with self.assertRaisesRegex(engine.BenchmarkExecutionError, "worker_failed"):
            engine.run_bounded_command(
                [sys.executable, "-c", "raise SystemExit(3)"], timeout_seconds=5
            )

    def test_bounded_process_accepts_only_explicit_environment_and_working_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = engine.run_bounded_command(
                [sys.executable, "-c", "import os; print(os.getenv('DEVOBS_FIXTURE')); print(os.getcwd())"],
                timeout_seconds=5,
                env={"DEVOBS_FIXTURE": "synthetic", "PATH": os.defpath},
                cwd=Path(temporary),
            )
        self.assertEqual(result.stdout.splitlines(), ["synthetic", temporary])
        with self.assertRaisesRegex(engine.BenchmarkValidationError, "process_environment"):
            engine.run_bounded_command(
                [sys.executable, "-c", "pass"], timeout_seconds=5, env={"BAD": "contains\0null"}
            )

    def test_benchmark_commands_are_argument_vectors_without_shell(self):
        config = engine.MeasurementConfig.for_mode("smoke")
        command = engine.pyperf_command(
            python_executable="/venv/bin/python",
            benchmark_script=ROOT / "benchmarks" / "devobs_benchmarks.py",
            output_path=Path("/tmp/raw.json"),
            config=config,
        )
        self.assertIsInstance(command, list)
        self.assertIn("--processes", command)
        self.assertIn("--values", command)
        self.assertNotIn("shell", command)

    def test_memory_measurement_uses_pyperf_tracking_flag(self):
        config = engine.MeasurementConfig.for_mode("smoke")
        self.assertEqual(engine.MeasurementConfig.for_metric("smoke", "memory").processes, 3)
        self.assertEqual(engine.MeasurementConfig.for_metric("statistical", "memory").processes, 20)
        self.assertEqual(engine.MeasurementConfig.for_metric("smoke", "memory").values, 1)
        self.assertEqual(engine.MeasurementConfig.for_metric("statistical", "memory").values, 1)
        command = engine.pyperf_command(
            python_executable="/venv/bin/python",
            benchmark_script=ROOT / "benchmarks" / "devobs_benchmarks.py",
            output_path=Path("/tmp/raw-memory.json"),
            config=config,
            metric="memory",
        )
        self.assertIn("--track-memory", command)
        with self.assertRaises(engine.BenchmarkValidationError):
            engine.pyperf_command(
                "/venv/bin/python", ROOT / "benchmarks" / "devobs_benchmarks.py",
                Path("/tmp/raw.json"), config, metric="shell",
            )

    def test_memory_run_rejects_non_linux_without_starting_a_benchmark(self):
        with mock.patch.object(engine.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(engine.BenchmarkValidationError, "linux_only"):
                engine.run("smoke", Path("/tmp/out"), metric="memory")


if __name__ == "__main__":
    unittest.main()

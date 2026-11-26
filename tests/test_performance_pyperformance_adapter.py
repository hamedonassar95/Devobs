"""Contract tests for safe PyPerformance selection and bounded execution."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine  # noqa: E402
from performance_intelligence import pyperformance_adapter as adapter  # noqa: E402


class PyPerformanceAdapterTests(unittest.TestCase):
    def test_only_reviewed_benchmarks_and_bounded_mode_selections_are_accepted(self):
        self.assertEqual(adapter.validate_benchmark_selection("float,json_dumps", "smoke"),
                         ("float", "json_dumps"))
        self.assertEqual(adapter.validate_benchmark_selection(None, "smoke"),
                         adapter.DEFAULT_SMOKE_BENCHMARKS)
        for raw, mode in (("arbitrary", "smoke"), ("float,float", "smoke"), ("", "smoke"),
                          ("float,json_dumps,regex_dna,regex_v8", "statistical"), (None, "unknown")):
            with self.subTest(raw=raw, mode=mode), self.assertRaises(adapter.PyPerformanceValidationError):
                adapter.validate_benchmark_selection(raw, mode)

    def test_upstream_command_is_fixed_manual_offline_and_timeout_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            command = adapter.pyperformance_command(
                sys.executable, source, ("float",), "smoke", Path(temporary) / "raw.json"
            )
            self.assertIn("-m", command)
            self.assertIn("pyperformance", command)
            self.assertIn("--benchmarks=float", command)
            self.assertIn("--timeout=60", command)
            self.assertFalse(any("upload" in item or "compile" in item for item in command))
            with self.assertRaises(adapter.PyPerformanceValidationError):
                adapter.pyperformance_command(
                    sys.executable, source, ("unknown",), "smoke", Path(temporary) / "raw.json"
                )

    def test_run_fails_closed_for_missing_environment_and_worker_failure(self):
        with mock.patch.object(adapter, "require_runtime_toolchain",
                                side_effect=adapter.PyPerformanceExecutionError("toolchain_unavailable")):
            with self.assertRaisesRegex(adapter.PyPerformanceExecutionError, "toolchain_unavailable"):
                adapter.run("smoke", None, Path("/tmp/source.tar.gz"), Path("/tmp/wheelhouse"), Path("/tmp/out"))
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            inputs = Path(temporary) / "inputs"
            inputs.mkdir()
            archive = inputs / "source.tar.gz"
            archive.write_bytes(b"synthetic archive")
            wheelhouse = inputs / "wheelhouse"
            wheelhouse.mkdir()
            (wheelhouse / "pyperf-2.11.0-py3-none-any.whl").write_bytes(b"synthetic wheel")
            with mock.patch.object(adapter, "require_runtime_toolchain"), \
                 mock.patch.object(benchmark_engine, "source_revision", return_value="a" * 40), \
                 mock.patch.object(adapter, "validate_wheelhouse", return_value={}), \
                 mock.patch.object(adapter, "verify_source_archive", side_effect=lambda path: path), \
                 mock.patch.object(adapter, "extract_verified_source", return_value=source), \
                 mock.patch.object(benchmark_engine, "run_bounded_command",
                                   side_effect=benchmark_engine.BenchmarkExecutionError("worker_failed")):
                with self.assertRaisesRegex(adapter.PyPerformanceExecutionError, "worker_failed"):
                    adapter.run("smoke", "float", archive, wheelhouse, Path("/tmp/out"))

    def test_timeout_is_bounded_and_translated_to_safe_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            inputs = Path(temporary) / "inputs"
            inputs.mkdir()
            archive = inputs / "source.tar.gz"
            archive.write_bytes(b"synthetic archive")
            wheelhouse = inputs / "wheelhouse"
            wheelhouse.mkdir()
            (wheelhouse / "pyperf-2.11.0-py3-none-any.whl").write_bytes(b"synthetic wheel")
            with mock.patch.object(adapter, "require_runtime_toolchain"), \
                 mock.patch.object(benchmark_engine, "source_revision", return_value="a" * 40), \
                 mock.patch.object(adapter, "validate_wheelhouse", return_value={}), \
                 mock.patch.object(adapter, "verify_source_archive", side_effect=lambda path: path), \
                 mock.patch.object(adapter, "extract_verified_source", return_value=source), \
                 mock.patch.object(benchmark_engine, "run_bounded_command",
                                   side_effect=benchmark_engine.BenchmarkExecutionError("benchmark_timeout")):
                with self.assertRaisesRegex(adapter.PyPerformanceExecutionError, "benchmark_timeout"):
                    adapter.run("smoke", "float", archive, wheelhouse, Path("/tmp/out"))


if __name__ == "__main__":
    unittest.main()

"""Contract tests for safe PyPerformance selection and bounded execution."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import benchmark_engine  # noqa: E402
from performance_intelligence import pyperformance_adapter as adapter  # noqa: E402
from performance_intelligence.pyperformance_contract import INVENTORY_PATH  # noqa: E402


class PyPerformanceAdapterTests(unittest.TestCase):
    def test_pinned_inventory_is_complete_and_matches_execution_allowlist(self):
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        groups = inventory["groups"]
        names = [entry["name"] for entry in groups]
        integrated = {entry["name"]: tuple(entry["outputs"])
                      for entry in groups if entry["status"] == "INTEGRATED"}
        deferred = [entry for entry in groups if entry["status"] == "DEFERRED"]
        self.assertEqual(inventory["upstream_commit"], adapter.PY_PERFORMANCE_COMMIT)
        self.assertEqual(len(groups), 75)
        self.assertEqual(names, sorted(set(names)))
        self.assertEqual(len(integrated), 50)
        self.assertEqual(len(deferred), 25)
        self.assertEqual(integrated, adapter.SAFE_BENCHMARK_OUTPUTS)
        self.assertFalse(any(entry["declared_dependencies"] for entry in groups
                             if entry["status"] == "INTEGRATED"))
        self.assertFalse(any(entry["undeclared_runtime_dependencies"] for entry in groups
                             if entry["status"] == "INTEGRATED"))
        audit = (ROOT / "docs" / "PYPERFORMANCE_WORKLOAD_AUDIT_2026-11-26.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(all(f"`{name}`" in audit for name in names))

    def test_newly_reviewed_workloads_map_to_fixed_upstream_outputs(self):
        selected = adapter.validate_benchmark_selection(
            "argparse,async_tree,concurrent_imap,sqlite_synth", "smoke"
        )
        self.assertEqual(selected, ("argparse", "async_tree", "concurrent_imap", "sqlite_synth"))
        self.assertEqual(adapter._expected_output_names(selected), {
            "many_optionals", "async_tree_none", "bench_mp_pool", "bench_thread_pool", "sqlite_synth",
        })
        for deferred in ("fastapi", "yaml", "dask", "2to3"):
            with self.subTest(deferred=deferred), self.assertRaises(adapter.PyPerformanceValidationError):
                adapter.validate_benchmark_selection(deferred, "smoke")

    def test_only_reviewed_benchmarks_and_bounded_mode_selections_are_accepted(self):
        self.assertEqual(adapter.validate_benchmark_selection("float,json_dumps", "smoke"),
                         ("float", "json_dumps"))
        self.assertEqual(adapter.validate_benchmark_selection(None, "smoke"),
                         adapter.DEFAULT_SMOKE_BENCHMARKS)
        self.assertEqual(len(adapter.DEFAULT_SMOKE_BENCHMARKS), 8)
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

    def test_upstream_memory_mode_uses_only_fixed_memory_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            command = adapter.pyperformance_command(
                sys.executable, source, ("float",), "smoke", Path(temporary) / "raw.json",
                metric="memory",
            )
        self.assertIn("--track-memory", command)
        self.assertIn("--benchmarks=float", command)
        self.assertFalse(any("--python=" in item and item.endswith("arbitrary") for item in command))

    def test_memory_mode_rejects_non_linux_before_using_external_artifacts(self):
        with mock.patch.object(adapter.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(adapter.PyPerformanceValidationError, "linux_only"):
                adapter.run(
                    "smoke", "float", Path("/missing/source"), Path("/missing/wheels"),
                    Path("/tmp/out"), metric="memory",
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

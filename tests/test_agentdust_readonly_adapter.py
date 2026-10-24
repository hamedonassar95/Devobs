"""Synthetic-only tests for the AgentDust read-only report adapter."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agentdust_readonly_adapter as adapter  # noqa: E402


SENTINEL = "SYNTHETIC_PRIVATE_PROCESS_SENTINEL"


def valid_report() -> dict[str, object]:
    return {
        "version": 1,
        "counts": {
            "managed": 1,
            "owned-live": 2,
            "owned-ended": 3,
            "likely-owned": 4,
            "suspect": 5,
            "unknown": 6,
        },
        "findings": [{"pid": 4242, "cmdline": SENTINEL, "path": "/synthetic/private/path"}],
    }


class AgentDustReadOnlyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="agentdust-adapter-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def write_json(self, name: str, value: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def assert_rejected(self, path: Path, expected_code: str) -> None:
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.summarize_report(path)
        self.assertEqual(caught.exception.code, expected_code)

    def test_valid_report_returns_aggregate_summary_only(self) -> None:
        path = self.write_json("valid.json", valid_report())
        summary = adapter.summarize_report(path)
        self.assertEqual(
            summary,
            {
                "status_code": "REPORT_VALID",
                "processes_detected": 21,
                "findings_count": 1,
            },
        )
        self.assertEqual(set(summary), {"status_code", "processes_detected", "findings_count"})

    def test_nested_json_at_depth_limit_is_accepted(self) -> None:
        report = valid_report()
        nested: object = "synthetic leaf"
        # The report object and findings array already contribute two levels.
        for _ in range(adapter.MAX_JSON_DEPTH - 2):
            nested = [nested]
        report["findings"] = [nested]
        summary = adapter.summarize_report(self.write_json("depth-limit.json", report))
        self.assertEqual(summary["status_code"], "REPORT_VALID")

    def test_json_beyond_depth_limit_is_rejected_before_full_parse(self) -> None:
        report = valid_report()
        nested: object = SENTINEL
        for _ in range(adapter.MAX_JSON_DEPTH - 1):
            nested = [nested]
        report["findings"] = [nested]
        path = self.write_json("too-deep.json", report)
        with mock.patch.object(adapter.json, "loads") as json_loads:
            self.assert_rejected(path, "json_complexity_exceeded")
            json_loads.assert_not_called()

    def test_json_beyond_node_limit_is_rejected_before_full_parse(self) -> None:
        report = valid_report()
        # Each object contributes one node, ten key strings, and ten values.
        report["findings"] = [{f"k{key_index}": key_index for key_index in range(10)} for _ in range(5_000)]
        path = self.write_json("too-many-nodes.json", report)
        self.assertLess(path.stat().st_size, adapter.MAX_REPORT_BYTES)
        with mock.patch.object(adapter.json, "loads") as json_loads:
            self.assert_rejected(path, "json_complexity_exceeded")
            json_loads.assert_not_called()

    def test_invalid_json_is_rejected_without_echoing_input(self) -> None:
        path = self.root / "invalid.json"
        path.write_text(f'{{"private":"{SENTINEL}"', encoding="utf-8")
        self.assert_rejected(path, "invalid_json")

    def test_duplicate_json_keys_are_rejected(self) -> None:
        path = self.root / "duplicate-keys.json"
        path.write_text('{"version":1,"version":1}', encoding="utf-8")
        self.assert_rejected(path, "duplicate_json_key")

    def test_non_object_json_is_rejected(self) -> None:
        path = self.root / "scalar.json"
        path.write_text("[]", encoding="utf-8")
        self.assert_rejected(path, "report_not_object")

    def test_wrong_version_is_rejected(self) -> None:
        report = valid_report()
        report["version"] = 2
        self.assert_rejected(self.write_json("version.json", report), "version_mismatch")

    def test_missing_count_key_is_rejected(self) -> None:
        report = valid_report()
        del report["counts"]["unknown"]  # type: ignore[index]
        self.assert_rejected(self.write_json("counts.json", report), "count_keys_mismatch")

    def test_invalid_count_values_are_rejected(self) -> None:
        for name, value in (("bool", True), ("negative", -1), ("float", 1.5)):
            with self.subTest(value=value):
                report = valid_report()
                report["counts"]["managed"] = value  # type: ignore[index]
                self.assert_rejected(self.write_json(f"counts-{name}.json", report), "count_values_invalid")

    def test_maximum_count_value_is_accepted_and_sum_is_bounded(self) -> None:
        report = valid_report()
        report["counts"] = {key: 0 for key in adapter.COUNT_KEYS}
        report["counts"]["managed"] = adapter.MAX_COUNT_VALUE  # type: ignore[index]
        summary = adapter.summarize_report(self.write_json("maximum-count.json", report))
        self.assertEqual(summary["processes_detected"], adapter.MAX_COUNT_VALUE)
        self.assertLessEqual(summary["processes_detected"], adapter.MAX_TOTAL_COUNT)

    def test_count_one_above_limit_is_rejected(self) -> None:
        report = valid_report()
        report["counts"]["managed"] = adapter.MAX_COUNT_VALUE + 1  # type: ignore[index]
        self.assert_rejected(self.write_json("count-over-limit.json", report), "count_value_limit_exceeded")

    def test_integer_token_longer_than_limit_is_rejected(self) -> None:
        report = json.dumps(valid_report())
        self.assertIn('"managed": 1', report)
        long_integer = "9" * (adapter.MAX_JSON_INTEGER_DIGITS + 1)
        path = self.root / "long-integer.json"
        path.write_text(report.replace('"managed": 1', f'"managed": {long_integer}', 1), encoding="utf-8")
        self.assert_rejected(path, "integer_too_long")

    def test_report_larger_than_two_mib_is_rejected(self) -> None:
        path = self.root / "large.json"
        path.write_bytes(b" " * (adapter.MAX_REPORT_BYTES + 1))
        self.assert_rejected(path, "file_too_large")

    def test_report_exactly_two_mib_is_accepted(self) -> None:
        raw = json.dumps(valid_report()).encode("utf-8")
        self.assertLessEqual(len(raw), adapter.MAX_REPORT_BYTES)
        path = self.root / "exact-limit.json"
        path.write_bytes(raw + b" " * (adapter.MAX_REPORT_BYTES - len(raw)))
        self.assertEqual(path.stat().st_size, adapter.MAX_REPORT_BYTES)
        self.assertEqual(adapter.summarize_report(path)["status_code"], "REPORT_VALID")

    def test_more_than_ten_thousand_findings_are_rejected(self) -> None:
        report = valid_report()
        report["findings"] = [None] * (adapter.MAX_FINDINGS + 1)
        self.assert_rejected(self.write_json("too-many-findings.json", report), "findings_limit_exceeded")

    def test_symbolic_link_is_rejected(self) -> None:
        target = self.write_json("target.json", valid_report())
        link = self.root / "report-link.json"
        link.symlink_to(target)
        self.assert_rejected(link, "symbolic_link_rejected")

    def test_symbolic_link_in_parent_path_is_rejected(self) -> None:
        target_dir = self.root / "target-dir"
        target_dir.mkdir()
        self.write_json("target-dir/report.json", valid_report())
        link_dir = self.root / "linked-dir"
        link_dir.symlink_to(target_dir, target_is_directory=True)
        self.assert_rejected(link_dir / "report.json", "symbolic_link_rejected")

    def test_parent_traversal_is_rejected(self) -> None:
        path = self.write_json("traversal.json", valid_report())
        self.assert_rejected(path.parent / "unused" / ".." / path.name, "invalid_path")

    def test_non_regular_file_is_rejected_without_blocking(self) -> None:
        fifo = self.root / "report.fifo"
        os.mkfifo(fifo)
        self.assert_rejected(fifo, "not_regular_file")

    def test_cli_does_not_leak_findings_or_process_details(self) -> None:
        path = self.write_json("private.json", valid_report())
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main([str(path)])
        output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertNotIn(SENTINEL, output)
        self.assertNotIn("4242", output)
        self.assertNotIn("/synthetic/private/path", output)
        self.assertEqual(json.loads(stdout.getvalue())["status_code"], "REPORT_VALID")
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_rejects_invalid_data_without_leaking_it(self) -> None:
        path = self.root / "private-invalid.json"
        path.write_text(f'{{"private":"{SENTINEL}"', encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main([str(path)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "adapter_error=invalid_json\n")
        self.assertNotIn(SENTINEL, stdout.getvalue() + stderr.getvalue())

    def test_complexity_rejection_does_not_leak_report_content(self) -> None:
        report = valid_report()
        nested: object = SENTINEL
        for _ in range(adapter.MAX_JSON_DEPTH - 1):
            nested = [nested]
        report["findings"] = [nested]
        path = self.write_json("private-too-deep.json", report)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main([str(path)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "adapter_error=json_complexity_exceeded\n")
        self.assertNotIn(SENTINEL, stdout.getvalue() + stderr.getvalue())

    def test_adapter_imports_no_process_or_network_modules(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_roots = {"subprocess", "socket", "urllib", "http", "requests"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots))

    def test_adapter_does_not_spawn_processes_or_open_network_connections(self) -> None:
        path = self.write_json("no-side-effects.json", valid_report())
        forbidden_calls = (
            mock.patch("subprocess.Popen", side_effect=AssertionError("process spawn attempted")),
            mock.patch("subprocess.run", side_effect=AssertionError("process run attempted")),
            mock.patch("os.system", side_effect=AssertionError("system command attempted")),
            mock.patch("socket.socket", side_effect=AssertionError("socket created")),
            mock.patch("socket.create_connection", side_effect=AssertionError("network connection attempted")),
            mock.patch("urllib.request.urlopen", side_effect=AssertionError("URL opened")),
        )
        with contextlib.ExitStack() as stack:
            for patcher in forbidden_calls:
                stack.enter_context(patcher)
            self.assertEqual(adapter.summarize_report(path)["status_code"], "REPORT_VALID")


if __name__ == "__main__":
    unittest.main()

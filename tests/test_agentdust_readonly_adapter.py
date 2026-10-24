"""Synthetic-only tests for the AgentDust read-only report adapter."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agentdust_readonly_adapter as adapter  # noqa: E402


SENTINEL = "SYNTHETIC_PRIVATE_PROCESS_SENTINEL"


def valid_report() -> dict[str, object]:
    # Synthetic Linux-shaped report based on AgentDust v1.8.1's JsonView.
    return {
        "version": 1,
        "owned_classes": {"available": True, "reason": None},
        "cgroup_unit_evidence": {"available": True},
        "sessions": {
            "records": 3,
            "skipped_lines": 0,
            "active": 1,
            "ended": 1,
            "unknown": 0,
            "degraded": 0,
        },
        "unexplained_tags": 0,
        "counts": {
            "managed": 4,
            "owned-live": 1,
            "owned-ended": 1,
            "likely-owned": 0,
            "suspect": 1,
            "unknown": 2,
        },
        "findings": [
            {
                "item_id": "p4242-1a2b",
                "class": "owned-ended",
                "exe_base": "node",
                "pid": 4242,
                "age_secs": 3600,
                "evidence": ["owned.tag", "owned.agent_gone"],
                "cwd_relation": "other_repo",
            },
            {
                "item_id": "p4243-2b3c",
                "class": "suspect",
                "exe_base": "node",
                "pid": 4243,
                "age_secs": 3600,
                "evidence": ["suspect.parent_init", "suspect.same_user"],
                "cwd_relation": "other_repo",
            },
            {
                "item_id": "p4244-3c4d",
                "class": "owned-live",
                "exe_base": "node",
                "pid": 4244,
                "age_secs": 120,
                "evidence": ["owned.tag", "owned.agent_alive"],
                "cwd_relation": "same_repo",
            },
        ],
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

    def run_workflow_source_validation(
        self,
        *,
        fetch_fails: bool = False,
        fetched_sha: str = "1" * 40,
        files_missing: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        workflow = (ROOT / ".github/workflows/agentdust-doctor-sandbox.yml").read_text(
            encoding="utf-8"
        )
        block_start = workflow.index('          source_dir="$work_dir/devobs-source"')
        block_end = workflow.index("          node_path=", block_start)
        validation_block = textwrap.dedent(workflow[block_start:block_end])

        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent(
                """
                import os
                import sys

                args = sys.argv[1:]
                if args and args[0] == "init":
                    os.makedirs(args[-1], exist_ok=True)
                    raise SystemExit(0)
                if len(args) >= 3 and args[0] == "-C":
                    repo, command = args[1], args[2]
                    if command == "remote":
                        raise SystemExit(0)
                    if command == "fetch":
                        raise SystemExit(9 if os.environ.get("SIM_FETCH_FAIL") == "1" else 0)
                    if command == "rev-parse":
                        print(os.environ["SIM_FETCHED_SHA"])
                        raise SystemExit(0)
                    if command == "checkout":
                        if os.environ.get("SIM_FILES_MISSING") != "1":
                            for relative in (
                                "scripts/agentdust_readonly_adapter.py",
                                "tests/test_agentdust_readonly_adapter.py",
                            ):
                                path = os.path.join(repo, relative)
                                os.makedirs(os.path.dirname(path), exist_ok=True)
                                with open(path, "w", encoding="utf-8"):
                                    pass
                        raise SystemExit(0)
                raise SystemExit(97)
                """
            ),
            encoding="utf-8",
        )
        fake_git.chmod(0o700)
        fake_python = fake_bin / "python3"
        fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_python.chmod(0o700)

        work_dir = self.root / "workflow-work"
        work_dir.mkdir()
        (work_dir / "tmp").mkdir()
        harness = textwrap.dedent(
            """
            set -Eeuo pipefail
            fail() { printf '%s\\n' "$1" >&2; exit 1; }
            work_dir="$WORK_DIR"
            tmp_dir="$WORK_DIR/tmp"
            """
        )
        env = {
            "PATH": str(fake_bin),
            "WORK_DIR": str(work_dir),
            "GITHUB_REPOSITORY": "hamedonassar95/Devobs",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_SHA": "1" * 40,
            "GITHUB_REF": "refs/heads/test/agentdust-doctor-diagnostics",
            "SIM_FETCH_FAIL": "1" if fetch_fails else "0",
            "SIM_FETCHED_SHA": fetched_sha,
            "SIM_FILES_MISSING": "1" if files_missing else "0",
            "TMPDIR": str(self.root),
        }
        return subprocess.run(
            ["/bin/bash", "-c", harness + validation_block],
            capture_output=True,
            check=False,
            env=env,
            text=True,
            timeout=5,
        )

    def test_valid_report_returns_aggregate_summary_only(self) -> None:
        path = self.write_json("valid.json", valid_report())
        summary = adapter.summarize_report(path)
        self.assertEqual(
            summary,
            {
                "status_code": "REPORT_VALID",
                "processes_detected": 9,
                "findings_count": 3,
            },
        )
        self.assertEqual(set(summary), {"status_code", "processes_detected", "findings_count"})
        self.assertEqual(summary["processes_detected"], sum(valid_report()["counts"].values()))  # type: ignore[union-attr]

    def test_agentdust_v1_extra_fields_are_allowed_and_not_emitted(self) -> None:
        report = valid_report()
        report["future_metadata"] = {"private": SENTINEL, "path": "/synthetic/private/path"}
        summary = adapter.summarize_report(self.write_json("extended-v1.json", report))
        output = json.dumps(summary)
        self.assertEqual(summary["status_code"], "REPORT_VALID")
        self.assertNotIn("future_metadata", output)
        self.assertNotIn(SENTINEL, output)
        self.assertNotIn("/synthetic/private/path", output)

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
        self.assertIn('"managed": 4', report)
        long_integer = "9" * (adapter.MAX_JSON_INTEGER_DIGITS + 1)
        path = self.root / "long-integer.json"
        path.write_text(report.replace('"managed": 4', f'"managed": {long_integer}', 1), encoding="utf-8")
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
        report = valid_report()
        report["findings"][0]["exe_base"] = SENTINEL  # type: ignore[index]
        report["private_path"] = "/synthetic/private/path"
        path = self.write_json("private.json", report)
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

    def test_missing_file_error_is_fixed_and_does_not_leak_path(self) -> None:
        path = self.root / "private-missing-report.json"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main([str(path)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "adapter_error=path_unavailable\n")
        self.assertNotIn(str(path), stdout.getvalue() + stderr.getvalue())

    def test_read_error_is_fixed_and_does_not_leak_exception_text(self) -> None:
        path = self.write_json("read-error.json", valid_report())
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(adapter.os, "read", side_effect=OSError(SENTINEL)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = adapter.main([str(path)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "adapter_error=read_failed\n")
        self.assertNotIn(SENTINEL, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(str(path), stdout.getvalue() + stderr.getvalue())

    def test_file_metadata_change_during_read_is_rejected(self) -> None:
        path = self.write_json("changing-report.json", valid_report())
        initial_bytes = path.read_bytes()
        changed_bytes = initial_bytes.replace(b'"managed": 4', b'"managed": 5', 1)
        self.assertEqual(len(changed_bytes), len(initial_bytes))
        original_read = os.read
        changed = False

        def change_file_then_read(fd: int, size: int) -> bytes:
            nonlocal changed
            if not changed:
                changed = True
                path.write_bytes(changed_bytes)
                current = path.stat()
                os.utime(
                    path,
                    ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000_000),
                )
            return original_read(fd, size)

        with mock.patch.object(adapter.os, "read", side_effect=change_file_then_read):
            self.assert_rejected(path, "file_changed")

    def test_file_size_change_during_read_is_rejected(self) -> None:
        path = self.write_json("growing-report.json", valid_report())
        original_read = os.read
        changed = False

        def grow_file_then_read(fd: int, size: int) -> bytes:
            nonlocal changed
            if not changed:
                changed = True
                with path.open("ab") as report_file:
                    report_file.write(b" ")
            return original_read(fd, size)

        with mock.patch.object(adapter.os, "read", side_effect=grow_file_then_read):
            self.assert_rejected(path, "file_changed")

    def test_unexpected_programming_error_is_fixed_and_fails_closed(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        path = self.root / "internal-error-report.json"
        with mock.patch.object(adapter, "summarize_report", side_effect=RuntimeError(SENTINEL)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = adapter.main([str(path)])
        self.assertEqual(exit_code, 3)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "adapter_error=internal_error\n")
        self.assertNotIn(SENTINEL, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(str(path), stdout.getvalue() + stderr.getvalue())

    def test_workflow_summary_hides_unexpected_programming_error_and_fails_closed(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        path = self.root / "workflow-internal-error.json"
        with mock.patch.object(adapter, "summarize_report", side_effect=RuntimeError(SENTINEL)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = adapter.main(["--workflow-summary", str(path), "0"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "doctor_exit_code=0",
                "processes_detected=unavailable",
                "findings=unavailable",
                "doctor_success=false",
                "doctor_failure_reason=validator_internal_error",
            ],
        )
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(SENTINEL, stdout.getvalue())
        self.assertNotIn(str(path), stdout.getvalue())

    def test_workflow_source_fetch_failure_fails_closed(self) -> None:
        result = self.run_workflow_source_validation(fetch_fails=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "Could not fetch the event source commit.")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)

    def test_workflow_source_sha_mismatch_fails_closed(self) -> None:
        result = self.run_workflow_source_validation(fetched_sha="2" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "Fetched source does not match the event commit.")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)

    def test_workflow_source_missing_validator_files_fails_closed(self) -> None:
        result = self.run_workflow_source_validation(files_missing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "Shared validator files are missing.")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)

    def test_workflow_source_validation_uses_same_event_commit(self) -> None:
        result = self.run_workflow_source_validation()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "validator_self_tests=PASS")

    def test_workflow_summary_emits_only_safe_aggregate_fields(self) -> None:
        path = self.write_json("workflow-summary.json", valid_report())
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main(["--workflow-summary", str(path), "0"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "doctor_exit_code=0",
                "processes_detected=9",
                "findings=3",
                "doctor_success=true",
            ],
        )
        self.assertEqual(stderr.getvalue(), "")

    def test_workflow_summary_rejects_invalid_report_without_leaking_it(self) -> None:
        path = self.root / "invalid-workflow.json"
        path.write_text(f'{{"private":"{SENTINEL}"', encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = adapter.main(["--workflow-summary", str(path), "0"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "doctor_exit_code=0",
                "processes_detected=unavailable",
                "findings=unavailable",
                "doctor_success=false",
                "doctor_failure_reason=invalid_json",
            ],
        )
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(SENTINEL, stdout.getvalue())

    def test_workflow_summary_fails_closed_when_doctor_exit_is_nonzero(self) -> None:
        path = self.write_json("nonzero-workflow.json", valid_report())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = adapter.main(["--workflow-summary", str(path), "7"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "doctor_exit_code=7",
                "processes_detected=9",
                "findings=3",
                "doctor_success=false",
                "doctor_failure_reason=doctor_nonzero",
            ],
        )

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

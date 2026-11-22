"""Synthetic-only behavioral checks for the offline artifact boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import agent_output_guard as guard
from scripts import agentdust_readonly_adapter as reader

SENTINEL = "SYNTHETIC_ARTIFACT_SENTINEL_DO_NOT_ECHO"


class AgentOutputGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.workspace = self.folder / "workspace"
        self.workspace.mkdir()

    def write(self, name, content):
        path = self.workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    def assess(self, *paths):
        return guard.assess_artifacts(self.workspace, list(paths))

    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/agent_output_guard.py"), *arguments],
            cwd=self.workspace, capture_output=True, text=True, timeout=10,
        )

    def test_clean_json_is_deterministic_and_does_not_change_the_artifact(self):
        path = self.write("result.json", '{"message":"مرحبا","count":2}')
        before = path.read_bytes(), path.stat().st_mtime_ns
        first = self.assess("result.json")
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first, self.assess("result.json"))
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
        self.assertEqual(first["artifacts"][0]["index"], 1)

    def test_supported_text_types_are_data_and_are_never_executed(self):
        for suffix in (".md", ".txt", ".py", ".yaml", ".yml", ".toml", ".diff", ".patch"):
            with self.subTest(suffix=suffix):
                self.write("artifact" + suffix,
                           "from pathlib import Path\nPath('executed.txt').write_text('bad')\n")
                self.assertEqual(self.assess("artifact" + suffix)["status"], "PASS")
        self.assertFalse((self.workspace / "executed.txt").exists())

    def test_invalid_or_excessively_complex_json_is_blocked(self):
        for raw in ('{broken', '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}',
                    '{"x":1e999}', '{"x":' + '9' * 5000 + '}',
                    '[' * 65 + '0' + ']' * 65, '{"x":"\\ud800"}'):
            with self.subTest(length=len(raw)):
                self.write("invalid.json", raw)
                self.assertEqual(self.assess("invalid.json")["status"], "BLOCKED")

    def test_oversized_file_is_blocked_without_a_full_read(self):
        self.write("oversize.txt", b"x" * (reader.MAX_REPORT_BYTES + 1))
        with mock.patch.object(reader.os, "read", side_effect=AssertionError("must not read")):
            report = self.assess("oversize.txt")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["artifacts"][0]["reason_codes"], ["FILE_TOO_LARGE"])

    def test_canonical_credential_patterns_are_blocked_and_never_echoed(self):
        for raw in ("token=" + SENTINEL, "ghp_" + "A" * 36,
                    json.dumps({"token": SENTINEL}), 'token=[REDACTED]'):
            self.write("result.txt", raw)
            report = self.assess("result.txt")
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["artifacts"][0]["reason_codes"], ["CREDENTIAL_PATTERN"])
            self.assertNotIn(SENTINEL, json.dumps(report))
            self.assertNotIn(raw, json.dumps(report))

    def test_json_escaped_keys_and_values_cannot_hide_canonical_patterns(self):
        for raw in ('{"\\u0074oken":"' + SENTINEL + '"}',
                    '{"message":"\\u0067hp_' + 'B' * 36 + '"}'):
            self.write("encoded.json", raw)
            self.assertEqual(self.assess("encoded.json")["status"], "BLOCKED")

    def test_unsafe_paths_are_rejected_before_open(self):
        paths = ("../outside.txt", "dir/../a.txt", "/outside.txt", "./a.txt",
                 "C:\\a.txt", "dir\\a.txt", "a.txt:stream", "a\x00.txt",
                 "a\n.txt", "a\t.txt", "", ".")
        with mock.patch.object(reader, "_open_explicit_regular_file") as opened:
            for value in paths:
                self.assertEqual(self.assess(value)["status"], "BLOCKED", repr(value))
            opened.assert_not_called()

    def test_external_file_and_parent_symlinks_are_rejected_without_reading(self):
        outside = self.folder / "outside.txt"
        outside.write_text(SENTINEL)
        (self.workspace / "escape.txt").symlink_to(outside)
        (self.workspace / "external").symlink_to(self.folder, target_is_directory=True)
        with mock.patch.object(reader, "_read_bounded_report") as read:
            self.assertEqual(self.assess("escape.txt")["status"], "BLOCKED")
            self.assertEqual(self.assess("external/outside.txt")["status"], "BLOCKED")
            read.assert_not_called()

    def test_internal_symlinks_are_conservatively_blocked(self):
        self.write("clean.txt", "clean")
        (self.workspace / "alias.txt").symlink_to(self.workspace / "clean.txt")
        self.assertEqual(self.assess("alias.txt")["status"], "BLOCKED")

    def test_binary_or_invalid_utf8_content_is_blocked(self):
        for raw in (b"hello\x00world", b"\xff\xfe", b"PK\x03\x04", "x\x85y".encode()):
            self.write("binary.txt", raw)
            self.assertEqual(self.assess("binary.txt")["status"], "BLOCKED")

    def test_missing_file_is_blocked(self):
        report = self.assess("missing.json")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["artifacts"][0]["reason_codes"], ["PATH_UNAVAILABLE"])

    def test_unreadable_file_error_is_sanitized(self):
        self.write("clean.json", "{}")
        with mock.patch.object(reader.os, "open", side_effect=PermissionError(SENTINEL)) as opened:
            with mock.patch.object(reader.os, "supports_dir_fd", reader.os.supports_dir_fd | {opened}):
                report = self.assess("clean.json")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertNotIn(SENTINEL, json.dumps(report))

    def test_no_read_permissions_are_blocked_even_for_privileged_processes(self):
        self.write("unreadable.txt", "synthetic").chmod(0)
        with mock.patch.object(reader, "_read_bounded_report") as read:
            self.assertEqual(self.assess("unreadable.txt")["status"], "BLOCKED")
            read.assert_not_called()

    def test_hardlinks_are_blocked_before_reading(self):
        outside = self.folder / "outside.txt"
        outside.write_text(SENTINEL)
        os.link(outside, self.workspace / "linked.txt")
        with mock.patch.object(reader, "_read_bounded_report") as read:
            report = self.assess("linked.txt")
            read.assert_not_called()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["artifacts"][0]["reason_codes"], ["HARDLINK_REJECTED"])

    def test_exact_size_limit_is_accepted(self):
        self.write("bounded.txt", b"x" * reader.MAX_REPORT_BYTES)
        self.assertEqual(self.assess("bounded.txt")["status"], "PASS")

    def test_json_node_limit_and_decoded_controls_are_blocked(self):
        for raw in ('[' + ','.join(['0'] * 100001) + ']',
                    '{"x":"\\u0000"}', '{"\\u202ekey":"value"}'):
            self.write("bounded.json", raw)
            self.assertEqual(self.assess("bounded.json")["status"], "BLOCKED")

    def test_repeated_incomplete_private_key_headers_are_bounded(self):
        header = "-----BEGIN " + "PRIVATE KEY-----\n"
        self.write("headers.txt", header * 10000)
        result = self.invoke("--workspace", str(self.workspace), "headers.txt")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")

    def test_unicode_private_key_markers_take_the_bounded_precheck(self):
        header = "-----BEGIN " + "PR\u0130VATE \u212aEY-----\n"
        inherited_rule = mock.Mock()
        inherited_rule.search.side_effect = AssertionError("unbounded rule must not run")
        self.assertTrue(guard._credential_like(header * 1000, [inherited_rule]))
        self.write("unicode.txt", header * 4)
        self.assertEqual(self.assess("unicode.txt")["status"], "BLOCKED")

    def test_sensitive_directory_cannot_be_admitted_as_a_deeper_workspace(self):
        self.write("credentials/nested/data.json", '{"message":"synthetic"}')
        self.assertEqual(self.assess("credentials/nested/data.json")["status"], "BLOCKED")
        for root, path in ((self.workspace / "credentials", "nested/data.json"),
                           (self.workspace / "credentials/nested", "data.json")):
            with mock.patch.object(reader, "_read_bounded_report") as read:
                self.assertEqual(guard.assess_artifacts(root, [path])["status"], "FAIL")
                read.assert_not_called()

    def test_trusted_workspace_may_be_inside_an_agent_worktree(self):
        root = self.workspace / ".worktrees/feature-example/artifacts"
        root.mkdir(parents=True)
        (root / "clean.json").write_text("{}")
        self.assertEqual(guard.assess_artifacts(root, ["clean.json"])["status"], "PASS")

    def test_unsupported_types_and_sensitive_paths_are_not_opened(self):
        for name in ("artifact.bin", ".env.json", "credentials/data.json", "service-account-demo.json"):
            self.write(name, "{}")
            with mock.patch.object(reader, "_open_explicit_regular_file") as opened:
                self.assertEqual(self.assess(name)["status"], "BLOCKED")
                opened.assert_not_called()

    def test_directories_and_fifos_are_blocked(self):
        (self.workspace / "directory.txt").mkdir()
        self.assertEqual(self.assess("directory.txt")["status"], "BLOCKED")
        os.mkfifo(self.workspace / "pipe.txt")
        self.assertEqual(self.assess("pipe.txt")["status"], "BLOCKED")

    def test_file_change_during_read_is_blocked(self):
        self.write("clean.txt", "clean")
        with mock.patch.object(reader, "_read_bounded_report", side_effect=reader.AdapterError("file_changed")):
            report = self.assess("clean.txt")
        self.assertEqual(report["status"], "BLOCKED")

    def test_unavailable_secure_reader_and_unexpected_errors_fail_closed(self):
        self.write("clean.txt", "clean")
        for error in (reader.AdapterError("secure_open_unavailable"), RuntimeError(SENTINEL)):
            with mock.patch.object(reader, "_open_explicit_regular_file", side_effect=error):
                report = self.assess("clean.txt")
            self.assertEqual(report["status"], "FAIL")
            self.assertNotIn(SENTINEL, json.dumps(report))

    def test_no_artifacts_excess_artifacts_and_bad_workspace_fail_closed(self):
        self.assertEqual(self.assess()["status"], "FAIL")
        self.assertEqual(self.assess(*(["a.txt"] * 33))["status"], "FAIL")
        self.assertEqual(guard.assess_artifacts(self.folder / "missing", ["a.txt"])["status"], "FAIL")

    def test_maximum_batch_and_workspace_symlink_policy(self):
        self.write("clean.txt", "clean")
        self.assertEqual(self.assess(*(["clean.txt"] * 32))["status"], "PASS")
        alias = self.folder / "alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        self.assertEqual(guard.assess_artifacts(alias, ["clean.txt"])["status"], "FAIL")

    def test_batch_status_never_promotes_a_rejection(self):
        self.write("clean.txt", "clean")
        report = self.assess("clean.txt", "missing.txt")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual([row["status"] for row in report["artifacts"]], ["PASS", "BLOCKED"])

    def test_validation_makes_no_network_calls(self):
        self.write("clean.json", "{}")
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(self.assess("clean.json")["status"], "PASS")

    def test_cli_json_is_deterministic_redacted_and_has_correct_exit_codes(self):
        self.write("clean.json", "{}")
        args = ["--workspace", str(self.workspace), "clean.json"]
        first = self.invoke(*args)
        second = self.invoke(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["status"], "PASS")
        self.assertEqual(sorted(path.name for path in self.workspace.iterdir()), ["clean.json"])
        name = "ghp_" + "Z" * 24 + ".txt"
        self.write(name, "token=" + SENTINEL)
        result = self.invoke("--workspace", str(self.workspace), name)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")
        for hidden in (SENTINEL, name, str(self.workspace)):
            self.assertNotIn(hidden, result.stdout + result.stderr)

    def test_cli_usage_errors_never_echo_untrusted_arguments_and_help_works(self):
        result = self.invoke("--" + SENTINEL)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL")
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)
        self.assertEqual(self.invoke("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()

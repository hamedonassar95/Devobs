"""Offline behavioral tests using temporary Git commits, no remote network or credentials."""
import contextlib
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gitlab_fast_forward_preflight as sync  # noqa: E402


class FastForwardPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.checkout = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Synthetic Test")
        self.sha1 = self.commit("one")
        self.sha2 = self.commit("two")

    def git(self, *args):
        p = subprocess.run(["git", "-C", str(self.checkout), *args],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()

    def commit(self, value):
        (self.checkout / "fixture.txt").write_text(value, encoding="utf-8")
        self.git("add", "fixture.txt")
        self.git("commit", "-q", "-m", f"fixture {value}")
        return self.git("rev-parse", "HEAD")

    def remote(self, github, gitlab):
        def lookup(url, label):
            return github if label == "github" else gitlab
        return lookup

    def test_stale_gitlab_ancestor_gives_candidate_without_write(self):
        result = sync.check_preflight(self.checkout, self.remote(self.sha2, self.sha1))
        self.assertEqual(result["status"], "FAST_FORWARD_CANDIDATE")
        self.assertEqual(result["gitlab_sha"], self.sha1)
        self.assertFalse(result["write_performed"])
        self.assertEqual(self.git("rev-parse", "main"), self.sha2)

    def test_matching_tips_not_a_candidate(self):
        result = sync.check_preflight(self.checkout, self.remote(self.sha2, self.sha2))
        self.assertEqual(result["status"], "ALREADY_MATCHED")
        self.assertFalse(result["write_performed"])

    def test_remote_ahead_is_never_rewritten(self):
        self.git("reset", "--hard", self.sha1)
        with self.assertRaisesRegex(sync.PreflightBlocked, "gitlab_main_not_ancestor"):
            sync.check_preflight(self.checkout, self.remote(self.sha1, self.sha2))

    def test_missing_local_commit_blocks(self):
        with self.assertRaisesRegex(sync.PreflightBlocked, "gitlab_commit_not_in_local_checkout"):
            sync.check_preflight(self.checkout, self.remote(self.sha2, "f" * 40))

    def test_stale_local_main_blocks(self):
        self.git("reset", "--hard", self.sha1)
        with self.assertRaisesRegex(sync.PreflightBlocked, "local_main_not_at_github_sha"):
            sync.check_preflight(self.checkout, self.remote(self.sha2, self.sha1))

    def test_bad_public_sha_blocks(self):
        with self.assertRaisesRegex(sync.PreflightBlocked, "invalid_remote_sha"):
            sync.check_preflight(self.checkout, self.remote("UNSAFE", self.sha1))

    def test_unknown_checkout_blocks(self):
        with self.assertRaisesRegex(sync.PreflightBlocked, "checkout_unavailable"):
            sync.check_preflight(self.checkout / "does-not-exist", self.remote(self.sha2, self.sha1))

    def test_failure_from_gitlab_is_sanitized(self):
        def failing(_url, label):
            if label == "gitlab":
                raise sync.PreflightBlocked("gitlab_unavailable")
            return self.sha2
        with self.assertRaisesRegex(sync.PreflightBlocked, "gitlab_unavailable"):
            sync.check_preflight(self.checkout, failing)

    def test_endpoint_allowlist(self):
        with self.assertRaisesRegex(sync.PreflightBlocked, "endpoint_not_allowed"):
            sync._remote_head("http://127.0.0.1:80/", "github")

    def test_unapproved_git_operation_is_refused(self):
        with self.assertRaisesRegex(sync.PreflightBlocked, "git_operation_not_allowed"):
            sync._git("push", "origin", "main")

    def test_bad_transport_does_not_echo_stderr(self):
        fake = subprocess.CompletedProcess([], 128, "", "SYNTHETIC_PRIVATE_ERROR")
        with patch.object(sync, "_git", return_value=fake):
            with self.assertRaises(sync.PreflightBlocked) as raised:
                sync._remote_head(sync.GITLAB_URL, "gitlab")
        self.assertEqual(str(raised.exception), "gitlab_unavailable")
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR", str(raised.exception))

    def test_git_command_only_reads_git_objects(self):
        with patch.object(sync, "_git", wraps=sync._git) as runner:
            sync.check_preflight(self.checkout, self.remote(self.sha2, self.sha1))
        operations = [call.args[0] for call in runner.call_args_list]
        self.assertTrue(set(operations) <= {"rev-parse", "cat-file", "merge-base"})
        self.assertNotIn("push", operations)
        self.assertNotIn("fetch", operations)

    def test_cli_fail_closed_without_checkout(self):
        output = StringIO()
        with contextlib.redirect_stdout(output):
            rc = sync.main(["--repo", str(self.checkout / "nonexistent"), "--json"])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(output.getvalue()),
                         {"status":"BLOCKED","reason":"checkout_unavailable","write_performed":False})


if __name__ == "__main__":
    unittest.main()

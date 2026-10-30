"""Pure/offline P01 checkout binding tests; no network or deployments."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verify_p01_checkout", ROOT / "scripts" / "verify_p01_checkout.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SHA = "a" * 40
OTHER_SHA = "b" * 40


class P01CheckoutTests(unittest.TestCase):
    def test_accepts_only_exact_main_commit(self):
        self.assertIsNone(guard.verify(SHA, SHA, "refs/heads/main"))

    def test_rejects_wrong_revision_even_if_both_shas_well_formed(self):
        with self.assertRaisesRegex(guard.InvalidCheckout, "differs"):
            guard.verify(SHA, OTHER_SHA, "refs/heads/main")

    def test_rejects_missing_malformed_or_noncanonical_expected_sha(self):
        for invalid in ("", "main", "A" * 40, SHA + "\n", SHA + "extra", None):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(guard.InvalidCheckout, "requested"):
                    guard.verify(invalid, SHA, "refs/heads/main")

    def test_rejects_non_main_or_missing_event_ref(self):
        for invalid in ("refs/heads/feature", "refs/tags/v1", "", None):
            with self.subTest(ref=invalid):
                with self.assertRaisesRegex(guard.InvalidCheckout, "main"):
                    guard.verify(SHA, SHA, invalid)

    def test_rejects_missing_or_malformed_checkout_sha(self):
        for invalid in ("", OTHER_SHA.upper(), "f" * 39, None):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(guard.InvalidCheckout, "checked-out"):
                    guard.verify(SHA, invalid, "refs/heads/main")

    def test_git_command_failure_does_not_disclose_output(self):
        for error in (OSError("secret payload"),
                      subprocess.CalledProcessError(1, "git", stderr="secret payload"),
                      subprocess.TimeoutExpired("git", 5)):
            with self.subTest(error=type(error).__name__):
                with patch.object(guard.subprocess, "run", side_effect=error):
                    with self.assertRaises(guard.InvalidCheckout) as raised:
                        guard._checkout_sha()
                self.assertEqual(str(raised.exception), "unable to verify checked-out commit")
                self.assertNotIn("secret payload", str(raised.exception))

    def test_cli_exit_status_is_fail_closed(self):
        with patch.dict(guard.os.environ, {"GITHUB_REF": "refs/heads/main"}):
            with patch.object(guard, "_checkout_sha", return_value=OTHER_SHA):
                output = io.StringIO()
                with redirect_stderr(output):
                    self.assertEqual(guard.main(["--expected-sha", SHA]), 1)
                self.assertIn("NO-GO", output.getvalue())
            with patch.object(guard, "_checkout_sha", return_value=SHA):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(guard.main(["--expected-sha", SHA]), 0)
                self.assertIn("independent review", output.getvalue())

    def test_workflow_runs_revision_guard_before_evidence_gate(self):
        text = (ROOT / ".github/workflows/p01-evidence-gate.yml").read_text(encoding="utf-8")
        self.assertIn("ref: "+ "$"+"{{ github.sha }}", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("python3 scripts/verify_p01_checkout.py --expected-sha", text)
        self.assertLess(text.index("verify_p01_checkout.py"), text.index("check_p01_evidence.py"))


if __name__ == "__main__":
    unittest.main()

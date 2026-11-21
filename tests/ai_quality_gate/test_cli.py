"""CLI contract tests for the advisory AI quality gate."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from devobs.ai_quality_gate.cli import EXIT_CODES, main

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/ai_quality_gate
    import helpers as h


class AIQualityGateCLITests(unittest.TestCase):
    def _args(self, *extra: str) -> list[str]:
        return [
            "--input", str(h.EXAMPLES / "snapshot.json"),
            "--ci-run-json", str(h.EXAMPLES / "ci_run.json"),
            "--ci-jobs-json", str(h.EXAMPLES / "ci_jobs.json"),
            *extra,
        ]

    def test_json_output_defaults_to_dry_run_and_pass(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(self._args())
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, EXIT_CODES[result["decision"]])
        self.assertEqual(code, 0)
        self.assertEqual(result["mode"], "DRY_RUN")
        self.assertIs(result["merge_authorized"], False)

    def test_markdown_output_never_claims_authorization(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(self._args("--format", "markdown"))
        text = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("- Merge authorized: `false`", text)
        self.assertIn("- Human approval: `PENDING_HUMAN`", text)
        self.assertIn("merge: `PENDING_HUMAN`", text)

    def test_non_dry_run_mode_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(self._args("--mode", "EXECUTE"))
        self.assertEqual(caught.exception.code, 2)

    def test_unreadable_input_fails_closed(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--input", str(h.EXAMPLES / "does-not-exist.json")])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(result["decision"], "INVALID")
        self.assertEqual(result["mode"], "DRY_RUN")


if __name__ == "__main__":
    unittest.main()

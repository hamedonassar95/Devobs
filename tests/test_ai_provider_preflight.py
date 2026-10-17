import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.check_copilot_preflight import evaluate, main


ROOT = Path(__file__).resolve().parents[1]


class CopilotPreflightWorkflowContractTests(unittest.TestCase):
    def test_workflow_uses_the_separately_testable_credential_checker(self):
        workflow = (ROOT / ".github/workflows/ai-provider-preflight.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("python3 scripts/check_copilot_preflight.py", workflow)
        self.assertIn("COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}", workflow)
        self.assertRegex(workflow, r"actions/checkout@[0-9a-f]{40} # v[0-9.]+")


class CopilotPreflightEvaluationTests(unittest.TestCase):
    def test_missing_secret_fails_with_exact_setup_instructions(self):
        passed, summary = evaluate(None, "owner/repo")

        self.assertFalse(passed)
        self.assertIn("COPILOT_GITHUB_TOKEN", summary)
        self.assertIn("Copilot Requests: Read", summary)
        self.assertIn("POLICY_AUDIT_TOKEN", summary)
        self.assertIn("https://github.com/owner/repo/settings/secrets/actions", summary)
        self.assertIn("No model request was made", summary)

    def test_unsupported_format_fails_without_disclosing_the_value(self):
        token = "not-a-real-credential"
        passed, summary = evaluate(token, "owner/repo")

        self.assertFalse(passed)
        self.assertIn("github_pat_", summary)
        self.assertIn("Copilot Requests: Read", summary)
        self.assertNotIn(token, summary)

    def test_accepted_prefix_is_explicitly_limited_to_format_validation(self):
        token = "github" + "_pat_" + "fixture_not_secret"
        passed, summary = evaluate(token, "owner/repo")

        self.assertTrue(passed)
        self.assertIn("format accepted", summary)
        self.assertIn("does not verify", summary)
        self.assertIn("POLICY_AUDIT_TOKEN", summary)
        self.assertIn("Copilot Requests: Read", summary)
        self.assertIn("No model request was made", summary)
        self.assertNotIn(token, summary)

    def test_command_accepts_valid_prefix_but_does_not_disclose_it(self):
        token = "github" + "_pat_" + "fixture_not_secret"
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            with patch.dict(
                os.environ,
                {
                    "COPILOT_GITHUB_TOKEN": token,
                    "GITHUB_REPOSITORY": "owner/repo",
                    "GITHUB_STEP_SUMMARY": str(summary_path),
                },
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(), 0)

            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("format accepted", summary)
            self.assertIn("POLICY_AUDIT_TOKEN", summary)
            self.assertNotIn(token, summary)
            self.assertNotIn(token, output.getvalue())

    def test_command_writes_guidance_to_github_step_summary_and_fails_closed(self):
        token = "legacy-test-fixture"
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            with patch.dict(
                os.environ,
                {
                    "COPILOT_GITHUB_TOKEN": token,
                    "GITHUB_REPOSITORY": "owner/repo",
                    "GITHUB_STEP_SUMMARY": str(summary_path),
                },
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(), 1)

            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("Copilot Requests: Read", summary)
            self.assertNotIn(token, summary)
            self.assertNotIn(token, output.getvalue())

    def test_local_command_without_summary_path_prints_safe_guidance(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}, clear=True):
            with redirect_stdout(output):
                self.assertEqual(main(), 1)

        self.assertIn("COPILOT_GITHUB_TOKEN", output.getvalue())
        self.assertIn("Copilot Requests: Read", output.getvalue())
        self.assertNotIn("github.com//settings", output.getvalue())


if __name__ == "__main__":
    unittest.main()

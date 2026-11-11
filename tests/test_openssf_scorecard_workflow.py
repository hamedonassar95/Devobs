import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]
REUSABLE_PATH = ROOT / ".github/workflows/reusable-openssf-scorecard.yml"
CALLER_PATH = ROOT / ".github/workflows/openssf-scorecard.yml"
REUSABLE_TEXT = REUSABLE_PATH.read_text(encoding="utf-8")
CALLER_TEXT = CALLER_PATH.read_text(encoding="utf-8")


class OpenSSFScorecardWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reusable_text = REUSABLE_TEXT
        cls.caller_text = CALLER_TEXT

    def test_devobs_entrypoint_is_manual_and_does_not_upload_public_artifacts(self):
        self.assertIn("on:\n  workflow_dispatch:\n", self.caller_text)
        self.assertNotIn("schedule:", self.caller_text)
        self.assertNotIn("pull_request:", self.caller_text)
        self.assertIn("permissions: {}", self.caller_text)
        self.assertIn("checks: read", self.caller_text)
        self.assertIn("contents: read", self.caller_text)
        self.assertIn("issues: read", self.caller_text)
        self.assertIn("pull-requests: read", self.caller_text)
        self.assertIn("uses: ./.github/workflows/reusable-openssf-scorecard.yml", self.caller_text)
        self.assertIn("upload_report_artifact: false", self.caller_text)

    def test_reusable_workflow_exposes_only_workflow_call_and_read_permissions(self):
        self.assertIn("on:\n  workflow_call:\n    inputs:", self.reusable_text)
        self.assertNotIn("schedule:", self.reusable_text)
        self.assertNotIn("pull_request:", self.reusable_text)
        self.assertIn("permissions: {}", self.reusable_text)
        self.assertIn("type: boolean", self.reusable_text)
        self.assertIn("default: false", self.reusable_text)
        for permission in ("checks", "contents", "issues", "pull-requests"):
            self.assertIn(f"{permission}: read", self.reusable_text)
        self.assertNotIn(": write", self.reusable_text)

    def test_cli_download_is_checksum_pinned_before_extraction(self):
        text = REUSABLE_PATH.read_text(encoding="utf-8")
        self.assertIn('SCORECARD_VERSION: "5.6.0"', text)
        self.assertIn(
            'SCORECARD_SHA256: "19bde07129450cb65a95c6e3b9f34e034341579e6f0e241546ec3ae6efb2dd9a"',
            text,
        )
        self.assertLess(text.index("sha256sum --check"), text.index("tar -xzf"))
        self.assertIn('--local="$GITHUB_WORKSPACE"', text)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", text)

    def _summary_script(self):
        section = self.reusable_text.split("      - name: Summarize the validated report\n", 1)[1]
        section = section.split("      - name: Upload the full JSON report when the caller opts in\n", 1)[0]
        run = section.split("        run: |\n", 1)[1]
        python_lines = []
        for line in run.splitlines():
            if line.startswith("      - name:"):
                break
            if line.startswith("          "):
                python_lines.append(line[10:])
            elif not line:
                python_lines.append("")
            else:
                raise AssertionError("Unexpected content in the Scorecard summary workflow step")
        run = "\n".join(python_lines)
        marker = "python3 - <<'PY'\n"
        self.assertIn(marker, run)
        return run.split(marker, 1)[1].rsplit("\nPY", 1)[0]

    def test_summary_runs_from_the_reusable_workflow_without_caller_repo_files(self):
        self.assertIn("report_bytes = Path(os.environ[\"SCORECARD_REPORT\"]).read_bytes()", self._summary_script())

    def _run_summary(self, report_text):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report_path = root / "scorecard.json"
            summary_path = root / "summary.md"
            report_path.write_text(report_text, encoding="utf-8")
            environment = {
                "SCORECARD_REPORT": str(report_path),
                "GITHUB_STEP_SUMMARY": str(summary_path),
                "GITHUB_REPOSITORY": "hamedonassar95/Devobs",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_SHA": "a" * 40,
            }
            result = subprocess.run(
                [sys.executable, "-c", self._summary_script()],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            content = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
            return result, content

    def test_scorecard_summary_renders_provenance_and_escapes_untrusted_finding_text(self):
        report = {
            "score": 6.7,
            "checks": [
                {"name": "zeta", "score": 7, "reason": "unsafe | `code` <tag> [link](https://invalid.example)\nsecond line"},
                {"name": "alpha", "score": -1, "reason": "not evaluated"},
            ],
        }
        result, summary = self._run_summary(json.dumps(report))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Source SHA: `" + "a" * 40 + "`", summary)
        self.assertIn("Overall Scorecard score: **6.7/10**", summary)
        self.assertLess(summary.index("alpha"), summary.index("zeta"))
        self.assertIn("&#124; &#96;code&#96; &lt;tag&gt; &#91;link&#93;", summary)
        self.assertNotIn("[link]", summary)
        self.assertIn("not applicable", summary)

    def test_invalid_scorecard_json_fails_without_writing_a_summary(self):
        result, summary = self._run_summary('{"checks":[],"checks":[{}]}')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(summary, "")

    def test_oversized_or_malformed_scorecard_reports_fail_closed(self):
        result, summary = self._run_summary(" " * 2_000_001)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(summary, "")
        result, summary = self._run_summary(json.dumps({"checks": []}))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(summary, "")
        result, summary = self._run_summary(json.dumps({"checks": [{}] * 101}))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(summary, "")

    def test_full_report_artifact_is_opt_in_and_short_lived(self):
        artifact = self.reusable_text.split("- name: Upload the full JSON report when the caller opts in", 1)[1]
        self.assertIn("if: inputs.upload_report_artifact", artifact)
        self.assertIn("if-no-files-found: error", artifact)
        self.assertIn("retention-days: 14", artifact)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REUSABLE_PATH = ROOT / ".github/workflows/reusable-openssf-scorecard.yml"
CALLER_PATH = ROOT / ".github/workflows/openssf-scorecard.yml"
READ_ONLY_PERMISSIONS = {
    "checks": "read",
    "contents": "read",
    "issues": "read",
    "pull-requests": "read",
}


def load_workflow(path: Path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class OpenSSFScorecardWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reusable = load_workflow(REUSABLE_PATH)
        cls.caller = load_workflow(CALLER_PATH)

    def test_devobs_entrypoint_is_manual_and_does_not_upload_public_artifacts(self):
        self.assertEqual(set(self.caller["on"]), {"workflow_dispatch"})
        self.assertEqual(self.caller["permissions"], {})
        job = self.caller["jobs"]["scorecard"]
        self.assertEqual(job["permissions"], READ_ONLY_PERMISSIONS)
        self.assertEqual(job["uses"], "./.github/workflows/reusable-openssf-scorecard.yml")
        self.assertEqual(job["with"]["upload_report_artifact"], "false")

    def test_reusable_workflow_exposes_only_workflow_call_and_read_permissions(self):
        self.assertEqual(set(self.reusable["on"]), {"workflow_call"})
        self.assertEqual(self.reusable["permissions"], {})
        inputs = self.reusable["on"]["workflow_call"]["inputs"]
        self.assertEqual(inputs["upload_report_artifact"]["type"], "boolean")
        self.assertEqual(inputs["upload_report_artifact"]["default"], "false")
        self.assertEqual(self.reusable["jobs"]["scorecard"]["permissions"], READ_ONLY_PERMISSIONS)

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
        step = next(
            step
            for step in self.reusable["jobs"]["scorecard"]["steps"]
            if step.get("name") == "Summarize the validated report"
        )
        run = step["run"]
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
        text = REUSABLE_PATH.read_text(encoding="utf-8")
        artifact = text.split("- name: Upload the full JSON report when the caller opts in", 1)[1]
        self.assertIn("if: inputs.upload_report_artifact", artifact)
        self.assertIn("if-no-files-found: error", artifact)
        self.assertIn("retention-days: 14", artifact)


if __name__ == "__main__":
    unittest.main()

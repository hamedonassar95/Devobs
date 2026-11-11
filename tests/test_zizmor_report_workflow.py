"""Test the manual zizmor report workflow and its JSON summary boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.summarize_zizmor_report import InvalidReport, render_summary, validate_report


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/zizmor-report.yml"


class ZizmorReportWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_workflow_is_manual_read_only_offline_and_checksum_pinned(self):
        self.assertIn("on:\n  workflow_dispatch:\n", self.workflow_text)
        self.assertNotIn("pull_request:", self.workflow_text)
        self.assertNotIn("schedule:", self.workflow_text)
        self.assertIn("permissions: {}", self.workflow_text)
        self.assertIn("contents: read", self.workflow_text)
        self.assertIn("persist-credentials: false", self.workflow_text)
        self.assertIn('ZIZMOR_VERSION: "1.32.0"', self.workflow_text)
        self.assertIn(
            'ZIZMOR_SHA256: "bb110cc765eca9cd7efb2e284a956be5974c60027b0970f16397d86208a9957b"',
            self.workflow_text,
        )
        self.assertLess(self.workflow_text.index("sha256sum --check"), self.workflow_text.index("tar -xzf"))
        for option in ("--offline", "--strict-collection", "--no-config", "--no-exit-codes", "--collect=workflows"):
            self.assertIn(option, self.workflow_text)
        self.assertIn("list_authored_workflows", self.workflow_text)
        self.assertIn("scripts/summarize_zizmor_report.py", self.workflow_text)
        self.assertNotIn("GITHUB_TOKEN", self.workflow_text)
        self.assertNotIn(": write", self.workflow_text)

    def _report(self, **overrides):
        finding = {
            "ident": "template-injection",
            "desc": "unsafe | `value` <tag> [link]",
            "determinations": {"severity": "High", "confidence": "High"},
            "ignored": False,
            "locations": [{
                "symbolic": {"key": {"Local": {"verbatim_path": ".github/workflows/sample.yml"}}},
                "concrete": {"kind": "Primary", "location": {"start_point": {"row": 17}}},
            }],
        }
        finding.update(overrides)
        return [finding]

    def test_summary_validates_provenance_and_escapes_untrusted_markdown(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.json"
            report_path.write_text(json.dumps(self._report()), encoding="utf-8")
            findings = validate_report(report_path)
            summary = render_summary(findings, "hamedonassar95/Devobs", "a" * 40)
        self.assertIn(f"Source SHA: `{('a' * 40)}`", summary)
        self.assertIn(".github/workflows/sample.yml:17", summary)
        self.assertIn("High | High | [`template-injection`]", summary)
        self.assertIn("&#124; &#96;value&#96; &lt;tag&gt; &#91;link&#93;", summary)
        self.assertNotIn("[link]", summary)
        self.assertIn("informational and does not block merges", summary)

    def test_invalid_or_oversized_reports_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.json"
            for content in ("{invalid", "{}", json.dumps(self._report(ident="BAD")), " " * 2_000_001):
                report_path.write_text(content, encoding="utf-8")
                with self.assertRaises(InvalidReport):
                    validate_report(report_path)

    def test_out_of_scope_paths_and_invalid_provenance_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.json"
            outside = self._report()
            outside[0]["locations"][0]["symbolic"]["key"]["Local"]["verbatim_path"] = "../secrets.txt"
            report_path.write_text(json.dumps(outside), encoding="utf-8")
            with self.assertRaises(InvalidReport):
                validate_report(report_path)

        with self.assertRaises(InvalidReport):
            render_summary([], "hamedonassar95/Devobs", "not-a-sha")

    def test_cli_appends_summary_and_rejects_missing_environment(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report_path = root / "report.json"
            summary_path = root / "summary.md"
            report_path.write_text(json.dumps(self._report()), encoding="utf-8")
            environment = dict(os.environ)
            environment.update({
                "GITHUB_REPOSITORY": "hamedonassar95/Devobs",
                "GITHUB_SHA": "b" * 40,
                "GITHUB_STEP_SUMMARY": str(summary_path),
            })
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/summarize_zizmor_report.py"), str(report_path)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("b" * 40, summary_path.read_text(encoding="utf-8"))

            environment.pop("GITHUB_STEP_SUMMARY")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/summarize_zizmor_report.py"), str(report_path)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("summary path is missing", result.stderr)


if __name__ == "__main__":
    unittest.main()

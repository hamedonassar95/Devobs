import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import container_image_scan as scan


class ScanEvaluationTests(unittest.TestCase):
    def test_vulnerability_free_report_passes(self):
        passed, counts = scan.evaluate({"ArtifactType": "container_image", "Results": [{"Vulnerabilities": []}]})
        self.assertTrue(passed)
        self.assertEqual(counts["HIGH"], 0)

    def test_high_and_critical_findings_fail(self):
        for severity in ("HIGH", "CRITICAL"):
            with self.subTest(severity=severity):
                passed, counts = scan.evaluate({"ArtifactType": "container_image", "Results": [{"Vulnerabilities": [{"Severity": severity}]}]})
                self.assertFalse(passed)
                self.assertEqual(counts[severity], 1)

    def test_medium_low_findings_report_without_blocking(self):
        passed, _ = scan.evaluate({"ArtifactType": "container_image", "Results": [{"Vulnerabilities": [{"Severity": "MEDIUM"}, {"Severity": "LOW"}]}]})
        self.assertTrue(passed)

    def test_malformed_report_fails_closed(self):
        with self.assertRaises(ValueError):
            scan.evaluate({"Results": []})

    def test_malformed_vulnerability_collections_fail_closed(self):
        for vulnerabilities in ({}, "", "not-a-list"):
            with self.subTest(vulnerabilities=vulnerabilities):
                report = {
                    "ArtifactType": "container_image",
                    "Results": [{"Vulnerabilities": vulnerabilities}],
                }
                with self.assertRaises(ValueError):
                    scan.evaluate(report)


class CliTests(unittest.TestCase):
    def test_missing_image_configuration_is_not_configured(self):
        with patch.dict(os.environ, {"IMAGE_TAG": ""}):
            with patch.object(sys, "argv", ["container_image_scan.py"]):
                self.assertEqual(scan.main(), 0)

    def test_scanner_execution_failure_fails(self):
        with patch("scripts.container_image_scan.shutil.which", return_value="/bin/trivy"), patch("scripts.container_image_scan.subprocess.run", side_effect=OSError("scanner failed")):
            with tempfile.TemporaryDirectory() as directory, patch.object(sys, "argv", ["scan", "--image", "devobs:test", "--report", f"{directory}/report.json", "--summary", f"{directory}/summary.md"]):
                self.assertEqual(scan.main(), 2)

    def test_trivy_nonzero_exit_fails(self):
        failed = subprocess.CompletedProcess([], 1, "", "database error")
        with patch("scripts.container_image_scan.shutil.which", return_value="/bin/trivy"), patch("scripts.container_image_scan.subprocess.run", return_value=failed):
            with tempfile.TemporaryDirectory() as directory, patch.object(sys, "argv", ["scan", "--image", "devobs:test", "--report", f"{directory}/report.json", "--summary", f"{directory}/summary.md"]):
                self.assertEqual(scan.main(), 2)

    def test_controlled_high_finding_fails_cli_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            report, summary = Path(directory) / "report.json", Path(directory) / "summary.md"
            report.write_text(json.dumps({"ArtifactType": "container_image", "Results": [{"Vulnerabilities": [{"Severity": "HIGH"}]}]}))
            with patch("scripts.container_image_scan.shutil.which", return_value="/bin/trivy"), patch("scripts.container_image_scan.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with patch.object(sys, "argv", ["scan", "--image", "fixture:high", "--report", str(report), "--summary", str(summary)]):
                    self.assertEqual(scan.main(), 1)
            self.assertIn("FAIL", summary.read_text())

    def test_report_and_summary_written(self):
        with tempfile.TemporaryDirectory() as directory:
            report, summary = Path(directory) / "report.json", Path(directory) / "summary.md"
            report.write_text(json.dumps({"ArtifactType": "container_image", "Results": [{"Vulnerabilities": []}]}))
            with patch("scripts.container_image_scan.shutil.which", return_value="/bin/trivy"), patch("scripts.container_image_scan.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with patch.object(sys, "argv", ["scan", "--image", "devobs:test", "--report", str(report), "--summary", str(summary)]):
                    self.assertEqual(scan.main(), 0)
            self.assertIn("PASS", summary.read_text())


class WorkflowGateTests(unittest.TestCase):
    def setUp(self):
        self.workflow = Path(".github/workflows/ci.yml").read_text()
        validate_job = self.workflow.split("\n  validate:\n", 1)[1].split("\n  production-release:\n", 1)[0]
        needs_line = next(line.strip() for line in validate_job.splitlines() if line.strip().startswith("needs:"))
        needs_list = needs_line.split(":", 1)[1].strip()
        if not (needs_list.startswith("[") and needs_list.endswith("]")):
            raise AssertionError("validate.needs must be an inline YAML list")
        self.validate_needs = {job.strip() for job in needs_list[1:-1].split(",") if job.strip()}

    def test_scan_job_is_required_by_validate_and_report_uploads(self):
        self.assertIn("container-image-scan:", self.workflow)
        self.assertIn("container-image-scan", self.validate_needs)
        self.assertIn("SCAN_RESULT:", self.workflow)
        self.assertIn("retention-days: 7", self.workflow)
        self.assertIn("version=0.76.1", self.workflow)
        self.assertIn("sha256sum --check", self.workflow)
        self.assertIn("--ignore-unfixed=false", Path("scripts/container_image_scan.py").read_text())
        self.assertIn("$SCAN_RESULT", self.workflow)

    def test_rollback_profile_skips_scan_and_requires_skip(self):
        self.assertIn("if: inputs.validation_profile != 'rollback'", self.workflow)
        self.assertIn('SCAN_RESULT" != "skipped"', self.workflow)

    def test_production_gate_remains_validate_only(self):
        release = self.workflow.split("  production-release:", 1)[1]
        self.assertIn("needs: validate", release)
        self.assertIn("needs.validate.result == 'success'", release)


if __name__ == "__main__":
    unittest.main()

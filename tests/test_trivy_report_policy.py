"""Behavioral and workflow-gate tests for the Trivy JSON policy evaluator."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.trivy_report_policy import main


REVISION = "0123456789abcdef0123456789abcdef01234567"


def report(*severities):
    return {
        "ArtifactType": "container_image",
        "Results": [
            {"Target": "synthetic", "Vulnerabilities": [{"Severity": severity} for severity in severities]}
        ],
    }


class TrivyReportPolicyTests(unittest.TestCase):
    def invoke(self, payload, revision=REVISION, summary_name="summary.md"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        report_path = root / "report.json"
        if payload is not None:
            if isinstance(payload, bytes):
                report_path.write_bytes(payload)
            else:
                report_path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        summary_path = root / summary_name
        stdout, stderr = io.StringIO(), io.StringIO()
        args = ["--report", str(report_path), "--summary", str(summary_path), "--revision", revision]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(args)
        return status, stdout.getvalue(), stderr.getvalue(), summary_path

    def test_clean_image_and_missing_or_null_vulnerability_lists_pass(self):
        for result in ({}, {"Vulnerabilities": None}, {"Vulnerabilities": []}):
            with self.subTest(result=result):
                status, out, err, summary = self.invoke({"ArtifactType": "container_image", "Results": [result]})
                self.assertEqual(status, 0)
                self.assertEqual(err, "")
                self.assertIn("PASS", out)
                self.assertIn("| CRITICAL | 0 |", summary.read_text(encoding="utf-8"))

    def test_medium_low_and_unknown_are_counted_without_blocking(self):
        status, out, _, summary = self.invoke(report("MEDIUM", "LOW", "UNKNOWN"))
        self.assertEqual(status, 0)
        self.assertIn("MEDIUM=1", out)
        self.assertIn("LOW=1", out)
        contents = summary.read_text(encoding="utf-8")
        self.assertIn("UNKNOWN | 1", contents)
        self.assertIn(REVISION[:12], contents)

    def test_high_and_critical_each_fail_the_gate(self):
        for severity in ("HIGH", "CRITICAL"):
            with self.subTest(severity=severity):
                status, out, _, summary = self.invoke(report(severity))
                self.assertNotEqual(status, 0)
                self.assertIn("FAIL", out)
                self.assertIn(f"| {severity} | 1 |", summary.read_text(encoding="utf-8"))

    def test_missing_empty_malformed_and_non_dict_json_fail_safely(self):
        invalid_reports = (
            None,
            "",
            "  ",
            "{malformed",
            b"\xff",
            [],
            "null",
            7,
        )
        for payload in invalid_reports:
            with self.subTest(payload=payload):
                status, out, err, _ = self.invoke(payload)
                self.assertNotEqual(status, 0)
                self.assertEqual(out, "")
                self.assertIn("ERROR", err)

    def test_invalid_artifact_and_results_shapes_fail_closed(self):
        invalid_reports = (
            {"ArtifactType": "filesystem", "Results": [{"Vulnerabilities": []}]},
            {"ArtifactType": "container_image"},
            {"ArtifactType": "container_image", "Results": None},
            {"ArtifactType": "container_image", "Results": {}},
            {"ArtifactType": "container_image", "Results": []},
            {"ArtifactType": "container_image", "Results": ["bad result"]},
        )
        for payload in invalid_reports:
            with self.subTest(payload=payload):
                status, _, err, _ = self.invoke(payload)
                self.assertNotEqual(status, 0)
                self.assertIn("ERROR", err)

    def test_invalid_vulnerability_shapes_or_severity_fail_without_echoing_payload(self):
        bad_values = ({}, "bad list", ["bad record"], [{"Severity": "SEVERE token=synthetic"}])
        for value in bad_values:
            with self.subTest(value=value):
                payload = {"ArtifactType": "container_image", "Results": [{"Vulnerabilities": value}]}
                status, out, err, _ = self.invoke(payload)
                self.assertNotEqual(status, 0)
                self.assertNotIn("token=synthetic", out + err)
                self.assertNotIn("SEVERE", out + err)

    def test_missing_severity_is_invalid(self):
        payload = {"ArtifactType": "container_image", "Results": [{"Vulnerabilities": [{}]}]}
        status, _, err, _ = self.invoke(payload)
        self.assertNotEqual(status, 0)
        self.assertIn("ERROR", err)

    def test_invalid_revision_is_rejected_without_leaking_input(self):
        status, out, err, _ = self.invoke(report(), revision="not-a-safe-revision-token")
        self.assertNotEqual(status, 0)
        self.assertNotIn("not-a-safe-revision-token", out + err)

    def test_missing_report_and_summary_write_failure_fail_closed(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(["--report", str(root / "absent.json"), "--summary", str(root / "summary.md"), "--revision", REVISION])
        self.assertNotEqual(status, 0)
        self.assertNotIn(str(root), stdout.getvalue() + stderr.getvalue())

        status, out, err, _ = self.invoke(report(), summary_name="missing/summary.md")
        self.assertNotEqual(status, 0)
        self.assertEqual(out, "")
        self.assertNotIn("summary.md", err)


class TrivyWorkflowContractTests(unittest.TestCase):
    def test_single_scan_job_is_required_and_keeps_rollback_skipped(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("  container-image-scan:"), 1)
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        validate = workflow.split("\n  validate:\n", 1)[1].split("\n  production-release:", 1)[0]
        self.assertIn("container-image-scan", validate.split("needs:", 1)[1].splitlines()[0])
        self.assertIn("CONTAINER_SCAN_RESULT", validate)
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)
        self.assertIn('"$CONTAINER_SCAN_RESULT" != "skipped"', validate)

    def test_scan_is_single_run_all_severities_and_fail_closed_policy_follows(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        scan_step = job.split("      - name: Scan image and enforce fail-closed vulnerability policy\n", 1)[1].split("      - name: Upload Trivy report\n", 1)[0]
        scan_at = job.index("trivy image")
        parser_at = job.index("scripts/trivy_report_policy.py")
        self.assertEqual(job.count("trivy image"), 1)
        self.assertLess(scan_at, parser_at)
        self.assertLess(scan_step.index("set -euo pipefail"), scan_step.index("trivy image"))
        for option in (
            "--scanners vuln",
            "--severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
            "--ignore-unfixed=false",
            "--exit-code 0",
            "--format json",
        ):
            self.assertIn(option, job)
        self.assertIn("set -euo pipefail", job)
        self.assertIn("if-no-files-found: error", job)
        self.assertIn("retention-days: 7", job)
        self.assertIn("version=0.76.1", job)
        self.assertIn('grep -Fx "Version: $version"', job)

    def test_build_identity_uses_checked_out_commit_not_github_event_sha(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        self.assertIn("git rev-parse HEAD", job)
        self.assertIn("COMMIT_SHA", job)
        self.assertIn("devobs-web:${COMMIT_SHA}", job)
        self.assertNotIn("devobs-web:${{ github.sha }}", job)

    def test_image_scan_does_not_publish_and_artifact_upload_runs_after_failure(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        self.assertNotIn("docker push", job)
        self.assertIn("if: always()", job)


if __name__ == "__main__":
    unittest.main()

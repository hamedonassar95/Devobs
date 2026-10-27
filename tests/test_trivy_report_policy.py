"""Behavioral and workflow-gate tests for the Trivy JSON policy evaluator."""

import contextlib
import io
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.trivy_report_policy import main


REVISION = "0123456789abcdef0123456789abcdef01234567"
EXPECTED_IMAGE = f"devobs-web:{REVISION}"


def report(*severities, image=EXPECTED_IMAGE):
    return {
        "ArtifactName": image,
        "ArtifactType": "container_image",
        "Results": [
            {"Target": "synthetic", "Vulnerabilities": [{"Severity": severity} for severity in severities]}
        ],
    }


class TrivyReportPolicyTests(unittest.TestCase):
    def invoke(self, payload, revision=REVISION, expected_image=EXPECTED_IMAGE,
               summary_name="summary.md"):
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
        if expected_image is not None:
            args.extend(["--expected-image", expected_image])
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                status = main(args)
            except SystemExit as exc:
                status = int(exc.code)
        return status, stdout.getvalue(), stderr.getvalue(), summary_path

    def test_clean_image_and_missing_or_null_vulnerability_lists_pass(self):
        for result in (
            {"Target": "alpine:fixture (alpine 3)"},
            {"Target": "alpine:fixture (alpine 3)", "Vulnerabilities": None},
            {"Target": "alpine:fixture (alpine 3)", "Vulnerabilities": []},
        ):
            with self.subTest(result=result):
                status, out, err, summary = self.invoke({
                    "ArtifactName": EXPECTED_IMAGE,
                    "ArtifactType": "container_image",
                    "Results": [result],
                })
                self.assertEqual(status, 0)
                self.assertEqual(err, "")
                self.assertIn("PASS", out)
                self.assertIn("| CRITICAL | 0 |", summary.read_text(encoding="utf-8"))

    def test_expected_image_identity_must_be_present_well_formed_and_exact(self):
        invalid_cases = (
            (report(image=None), EXPECTED_IMAGE),
            (report(image=""), EXPECTED_IMAGE),
            (report(image="devobs-web:latest"), EXPECTED_IMAGE),
            (report(), "other-web:" + REVISION),
            (report(), "devobs-web:latest"),
            (report(), "devobs-web:" + REVISION.upper()),
        )
        for payload, expected_image in invalid_cases:
            with self.subTest(payload=payload, expected_image=expected_image):
                status, out, err, _ = self.invoke(payload, expected_image=expected_image)
                self.assertEqual(status, 2)
                self.assertEqual(out, "")
                self.assertEqual(err, "ERROR: missing, malformed, or unsupported Trivy JSON report\n")

        status, out, err, _ = self.invoke(report(), expected_image=None)
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIn("expected-image", err)

    def test_targetless_or_invalid_targets_fail_with_sanitized_error(self):
        invalid_results = (
            {},
            {"Target": None},
            {"Target": ""},
            {"Target": "   "},
            {"Target": 42},
            {"Target": {"value": "synthetic-untrusted-target"}},
        )
        for result in invalid_results:
            with self.subTest(result=result):
                payload = {"ArtifactType": "container_image", "Results": [result]}
                status, out, err, _ = self.invoke(payload)
                self.assertEqual(status, 2)
                self.assertEqual(out, "")
                self.assertEqual(err, "ERROR: missing, malformed, or unsupported Trivy JSON report\n")
                self.assertNotIn("synthetic-untrusted-target", out + err)

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
            status = main([
                "--report", str(root / "absent.json"), "--summary", str(root / "summary.md"),
                "--revision", REVISION, "--expected-image", EXPECTED_IMAGE,
            ])
        self.assertNotEqual(status, 0)
        self.assertNotIn(str(root), stdout.getvalue() + stderr.getvalue())

        status, out, err, _ = self.invoke(report(), summary_name="missing/summary.md")
        self.assertNotEqual(status, 0)
        self.assertEqual(out, "")
        self.assertNotIn("summary.md", err)


class TrivyWorkflowContractTests(unittest.TestCase):
    def run_scan_step_with_stubs(self, *, image_missing=False, scanner_failure=False):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        scan_step = job.split("      - name: Scan image and enforce fail-closed vulnerability policy\n", 1)[1].split("\n      - name: Upload Trivy report", 1)[0]
        script = textwrap.dedent(scan_step.split("        run: |\n", 1)[1])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(
            '#!/bin/sh\n'
            '[ "${FAKE_DOCKER_FAILURE:-0}" != 1 ] || exit 31\n'
            '[ "$1" = image ] && [ "$2" = inspect ] && [ "$3" = "$IMAGE_TAG" ]\n',
            encoding="utf-8",
        )
        trivy = bin_dir / "trivy"
        trivy.write_text(
            '#!/bin/sh\n'
            ': > "$TRIVY_MARKER"\n'
            '[ "${FAKE_TRIVY_FAILURE:-0}" != 1 ] || exit 32\n'
            'printf "%s" "$FAKE_REPORT" > "$REPORT_PATH"\n',
            encoding="utf-8",
        )
        docker.chmod(0o755)
        trivy.chmod(0o755)
        report_path = root / "report.json"
        summary_path = root / "summary.md"
        marker = root / "trivy-called"
        env = os.environ.copy()
        env.update({
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "REPORT_PATH": str(report_path),
            "GITHUB_STEP_SUMMARY": str(summary_path),
            "COMMIT_SHA": REVISION,
            "IMAGE_TAG": EXPECTED_IMAGE,
            "TRIVY_MARKER": str(marker),
            "FAKE_REPORT": json.dumps(report()),
            "FAKE_DOCKER_FAILURE": "1" if image_missing else "0",
            "FAKE_TRIVY_FAILURE": "1" if scanner_failure else "0",
        })
        result = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script],
            cwd=Path.cwd(), env=env, text=True, capture_output=True, check=False,
        )
        return result, marker.exists(), summary_path.exists()

    def test_single_scan_job_is_required_and_keeps_rollback_skipped(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("  container-image-scan:"), 1)
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        validate = workflow.split("\n  validate:\n", 1)[1].split("\n  production-release:", 1)[0]
        self.assertIn("container-image-scan", validate.split("needs:", 1)[1].splitlines()[0])
        self.assertIn("CONTAINER_SCAN_RESULT", validate)
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)
        self.assertIn('"$CONTAINER_SCAN_RESULT" != "skipped"', validate)

    def test_scan_builds_and_scans_the_same_local_checked_out_image(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        self.assertIn('echo "IMAGE_TAG=devobs-web:$commit_sha" >> "$GITHUB_ENV"', job)
        self.assertEqual(job.count('docker build --pull --tag "$IMAGE_TAG" .'), 1)
        self.assertIn('docker image inspect "$IMAGE_TAG"', job)
        scan_step = job.split("      - name: Scan image and enforce fail-closed vulnerability policy\n", 1)[1].split("      - name: Upload Trivy report\n", 1)[0]
        self.assertLess(scan_step.index('docker image inspect "$IMAGE_TAG"'), scan_step.index("trivy image"))
        self.assertIn("trivy image --image-src docker", scan_step)
        self.assertIn('"$IMAGE_TAG"', scan_step)
        self.assertIn('--expected-image "$IMAGE_TAG"', scan_step)
        self.assertNotIn("docker push", job)
        self.assertIn("contents: read", job.split("steps:", 1)[0])

    def test_missing_local_image_and_scanner_failure_stop_before_policy(self):
        missing_image, marker, summary = self.run_scan_step_with_stubs(image_missing=True)
        self.assertNotEqual(missing_image.returncode, 0)
        self.assertFalse(marker)
        self.assertFalse(summary)

        scanner_failure, marker, summary = self.run_scan_step_with_stubs(scanner_failure=True)
        self.assertEqual(scanner_failure.returncode, 32)
        self.assertTrue(marker)
        self.assertFalse(summary)

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
        self.assertIn('echo "IMAGE_TAG=devobs-web:$commit_sha"', job)
        self.assertNotIn("devobs-web:${{ github.sha }}", job)

    def test_image_scan_does_not_publish_and_artifact_upload_runs_after_failure(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  container-image-scan:\n", 1)[1].split("\n  terraform-validate:", 1)[0]
        self.assertNotIn("docker push", job)
        self.assertIn("if: always()", job)


if __name__ == "__main__":
    unittest.main()

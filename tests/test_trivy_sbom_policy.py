"""Fail-closed validation for the CycloneDX image inventory artifact."""

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.trivy_sbom_policy import MAX_SBOM_BYTES, InvalidSbom, _read_sbom, evaluate_sbom, main


REVISION = "0123456789abcdef0123456789abcdef01234567"
EXPECTED_IMAGE = f"devobs-web:{REVISION}"
IMAGE_ID = "sha256:" + "a" * 64
TRIVY_VERSION = "0.76.1"


def make_sbom(*components):
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": list(components),
    }


def make_component(name="nginx", version="1.31.8", kind="application"):
    return {"type": kind, "name": name, "version": version}


class TrivySbomPolicyTests(unittest.TestCase):
    def invoke(self, payload, *, revision=REVISION, expected_image=EXPECTED_IMAGE,
               image_id=IMAGE_ID, trivy_version=TRIVY_VERSION, summary_path=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        sbom_path = root / "sbom.cdx.json"
        evidence_path = root / "evidence.json"
        if payload is not None:
            if isinstance(payload, bytes):
                sbom_path.write_bytes(payload)
            else:
                sbom_path.write_text(
                    payload if isinstance(payload, str) else json.dumps(payload),
                    encoding="utf-8",
                )
        summary = Path(summary_path) if summary_path else root / "summary.md"
        stdout, stderr = io.StringIO(), io.StringIO()
        args = [
            "--sbom", str(sbom_path),
            "--evidence", str(evidence_path),
            "--summary", str(summary),
            "--revision", revision,
            "--expected-image", expected_image,
            "--image-id", image_id,
            "--trivy-version", trivy_version,
        ]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(args)
        return status, stdout.getvalue(), stderr.getvalue(), evidence_path, summary, sbom_path

    def test_valid_cyclonedx_document_is_accepted(self):
        spec_version, count = evaluate_sbom(
            make_sbom(make_component(), make_component("libc", "2.39", "library")),
        )
        self.assertEqual(spec_version, "1.6")
        self.assertEqual(count, 2)

    def test_empty_malformed_or_wrong_cyclonedx_shape_fails_closed(self):
        invalid = (
            None,
            "",
            "{broken",
            b"\xff",
            [],
            {"bomFormat": "SPDX", "specVersion": "1.6", "components": [make_component()]},
            {"bomFormat": "CycloneDX", "specVersion": "", "components": [make_component()]},
            {"bomFormat": "CycloneDX", "specVersion": "1.6"},
            make_sbom(),
            make_sbom("bad component"),
            make_sbom({"type": "unknown", "name": "package"}),
            make_sbom({"type": [], "name": "package"}),
            make_sbom({"type": "library", "name": "  "}),
            make_sbom({"type": "library", "name": "package", "version": 42}),
        )
        for value in invalid:
            with self.subTest(value=value):
                if value is not None and not isinstance(value, (str, bytes)):
                    with self.assertRaises(ValueError):
                        evaluate_sbom(value)
                    continue
                status, out, err, evidence, _, _ = self.invoke(value)
                self.assertNotEqual(status, 0)
                self.assertEqual(out, "")
                self.assertEqual(
                    err,
                    "ERROR: missing, malformed, or unsupported CycloneDX SBOM\n",
                )
                self.assertFalse(evidence.exists())

    def test_oversized_sbom_is_rejected_with_bounded_read(self):
        with tempfile.TemporaryDirectory() as temp:
            sbom_path = Path(temp) / "oversized.cdx.json"
            with sbom_path.open("wb") as oversized:
                oversized.truncate(MAX_SBOM_BYTES + 1)
            with self.assertRaises(InvalidSbom):
                _read_sbom(sbom_path)

    def test_valid_report_writes_hash_bound_evidence_without_component_names(self):
        payload = make_sbom(make_component("synthetic-runtime-package"))
        raw = json.dumps(payload).encode("utf-8")
        status, out, err, evidence_path, summary_path, _ = self.invoke(payload)

        self.assertEqual(status, 0)
        self.assertEqual(err, "")
        self.assertIn("PASS: CycloneDX", out)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["sourceRevision"], REVISION)
        self.assertEqual(evidence["image"], {"tag": EXPECTED_IMAGE, "id": IMAGE_ID})
        self.assertEqual(evidence["sbom"]["format"], "CycloneDX")
        self.assertEqual(evidence["sbom"]["specVersion"], "1.6")
        self.assertEqual(evidence["sbom"]["componentCount"], 1)
        self.assertEqual(evidence["sbom"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(evidence["generator"], {"name": "Trivy", "version": TRIVY_VERSION})
        self.assertNotIn("synthetic-runtime-package", json.dumps(evidence))
        summary = summary_path.read_text(encoding="utf-8")
        self.assertIn(REVISION, summary)
        self.assertIn(IMAGE_ID, summary)
        self.assertIn(hashlib.sha256(raw).hexdigest(), summary)
        self.assertIn("Unsigned inventory", summary)
        self.assertNotIn("synthetic-runtime-package", summary)

    def test_revision_image_digest_and_tool_version_are_validated(self):
        invalid_contexts = (
            {"revision": REVISION.upper()},
            {"revision": "main"},
            {"expected_image": "devobs-web:latest"},
            {"expected_image": "other:" + REVISION},
            {"image_id": "sha256:short"},
            {"image_id": "sha256:" + "A" * 64},
            {"trivy_version": "latest"},
        )
        for kwargs in invalid_contexts:
            with self.subTest(kwargs=kwargs):
                status, out, err, evidence, _, _ = self.invoke(
                    make_sbom(make_component()), **kwargs,
                )
                self.assertEqual(status, 2)
                self.assertEqual(out, "")
                self.assertEqual(err, "ERROR: invalid SBOM image identity or tool version\n")
                self.assertFalse(evidence.exists())

    def test_report_must_be_present_and_summary_must_be_writable(self):
        status, out, err, evidence, _, _ = self.invoke(None)
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "ERROR: missing, malformed, or unsupported CycloneDX SBOM\n")
        self.assertFalse(evidence.exists())

        with tempfile.TemporaryDirectory() as temp:
            bad_summary = Path(temp) / "missing" / "summary.md"
            status, out, err, evidence, _, _ = self.invoke(
                make_sbom(make_component()), summary_path=bad_summary,
            )
            self.assertEqual(status, 2)
            self.assertEqual(out, "")
            self.assertEqual(err, "ERROR: unable to write SBOM evidence summary\n")
            self.assertFalse(evidence.exists())


class TrivySbomWorkflowContractTests(unittest.TestCase):
    def container_job(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        return workflow.split("  container-build:\n", 1)[1].split(
            "\n  terraform-validate:\n", 1,
        )[0]

    def sbom_step(self):
        return self.container_job().split(
            "      - name: Generate CycloneDX SBOM for the exact Trivy-scanned image\n",
            1,
        )[1].split("\n      - name: Scan the exact image that passed the smoke test", 1)[0]

    def run_sbom_step_with_stubs(self, *, image_missing=False, scanner_failure=False,
                                 invalid_sbom=False):
        script = self.sbom_step().split("        run: |\n", 1)[1]
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(
            '#!/bin/sh\n'
            '[ "$FAKE_DOCKER_FAILURE" != 1 ] || exit 31\n'
            '[ "$1" = image ] && [ "$2" = inspect ] && [ "$3" = --format ] && [ "$5" = "$IMAGE_TAG" ] || exit 33\n'
            'printf "%s\\n" "$IMAGE_ID"\n',
            encoding="utf-8",
        )
        trivy = bin_dir / "trivy"
        trivy.write_text(
            '#!/bin/sh\n'
            '[ "$FAKE_TRIVY_FAILURE" != 1 ] || exit 32\n'
            'printf "%s" "$FAKE_SBOM" > "$SBOM_PATH"\n',
            encoding="utf-8",
        )
        docker.chmod(0o755)
        trivy.chmod(0o755)
        sbom_path = root / "sbom.cdx.json"
        evidence_path = root / "evidence.json"
        summary_path = root / "summary.md"
        sbom_value = make_sbom(make_component())
        if invalid_sbom:
            sbom_value["bomFormat"] = "invalid"
        env = os.environ.copy()
        env.update({
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "SBOM_PATH": str(sbom_path),
            "EVIDENCE_PATH": str(evidence_path),
            "GITHUB_STEP_SUMMARY": str(summary_path),
            "COMMIT_SHA": REVISION,
            "IMAGE_TAG": EXPECTED_IMAGE,
            "IMAGE_ID": IMAGE_ID,
            "TRIVY_VERSION": TRIVY_VERSION,
            "FAKE_SBOM": json.dumps(sbom_value),
            "FAKE_DOCKER_FAILURE": "1" if image_missing else "0",
            "FAKE_TRIVY_FAILURE": "1" if scanner_failure else "0",
        })
        result = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script],
            cwd=Path.cwd(), env=env, text=True, capture_output=True, check=False,
        )
        return result, sbom_path, evidence_path, summary_path

    def test_sbom_generation_is_tied_to_the_smoke_tested_local_image(self):
        job = self.container_job()
        self.assertEqual(job.count("trivy image"), 2)
        step = self.sbom_step()
        self.assertLess(
            job.index("Generate CycloneDX SBOM"),
            job.index("Scan the exact image that passed the smoke test"),
        )
        self.assertLess(
            step.index('actual_image_id="$(docker image inspect'),
            step.index("trivy image"),
        )
        self.assertIn('if [[ "$actual_image_id" != "$IMAGE_ID" ]]', step)
        self.assertIn("--image-src docker", step)
        self.assertIn("--format cyclonedx", step)
        self.assertIn('"$IMAGE_TAG"', step)
        self.assertIn("scripts/trivy_sbom_policy.py", step)
        self.assertIn('--image-id "$IMAGE_ID"', step)
        self.assertIn('--revision "$COMMIT_SHA"', step)
        self.assertNotIn("--scanners vuln", step)

    def test_sbom_artifact_is_bounded_and_uploaded_without_publish_or_write_permissions(self):
        job = self.container_job()
        upload = job.split("      - name: Upload Trivy report\n", 1)[1]
        self.assertIn("if: always()", upload)
        self.assertIn("trivy-image-sbom-", upload)
        self.assertIn("github.run_id", upload)
        self.assertIn("github.run_attempt", upload)
        self.assertIn("trivy-image-sbom.cdx.json", upload)
        self.assertIn("trivy-image-sbom-evidence.json", upload)
        self.assertIn("trivy-image-report.json", upload)
        self.assertIn("if-no-files-found: error", upload)
        self.assertIn("retention-days: 7", upload)
        self.assertNotIn("docker push", job)
        self.assertNotIn("security-events: write", job)
        self.assertIn("permissions:\n      contents: read", job)

    def test_generation_and_manifest_succeed_for_expected_image(self):
        result, sbom_path, evidence_path, summary_path = self.run_sbom_step_with_stubs()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(sbom_path.exists())
        self.assertTrue(evidence_path.exists())
        self.assertIn("CycloneDX", summary_path.read_text(encoding="utf-8"))

    def test_missing_image_or_scanner_failure_stops_before_evidence(self):
        missing_image, sbom_path, evidence_path, _ = self.run_sbom_step_with_stubs(image_missing=True)
        self.assertNotEqual(missing_image.returncode, 0)
        self.assertFalse(sbom_path.exists())
        self.assertFalse(evidence_path.exists())

        scanner_failure, _, evidence_path, _ = self.run_sbom_step_with_stubs(scanner_failure=True)
        self.assertEqual(scanner_failure.returncode, 32)
        self.assertFalse(evidence_path.exists())

    def test_invalid_sbom_output_fails_closed(self):
        result, sbom_path, evidence_path, summary_path = self.run_sbom_step_with_stubs(invalid_sbom=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(sbom_path.exists())
        self.assertFalse(evidence_path.exists())
        self.assertFalse(summary_path.exists())
        self.assertIn("missing, malformed, or unsupported CycloneDX SBOM", result.stderr)


if __name__ == "__main__":
    unittest.main()

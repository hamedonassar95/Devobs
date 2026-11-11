"""Behavioral tests for the offline Terraform HCL policy gate."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "policy" / "terraform"
PINNED_VERSION = "0.71.1"

VALID_CONFIG = '''
terraform {
  required_version = "~> 1.17.0"
  backend "gcs" {
    bucket = "replace-with-existing-terraform-state-bucket"
    prefix = "devobs/terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "devobs_images" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Fixture only; no cloud API is contacted."
  format        = "DOCKER"
  labels = {
    application = "devobs"
    managed_by  = "terraform"
  }
}
'''


class ConftestTerraformPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conftest = os.environ.get("CONFTEST_BIN") or shutil.which("conftest")
        if not cls.conftest:
            raise RuntimeError(
                "Conftest 0.71.1 is required; install the checksum-pinned release "
                "described in docs/integrations/terraform-policy.md"
            )
        result = subprocess.run(
            [cls.conftest, "--version"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0 or f"Conftest: {PINNED_VERSION}" not in result.stdout:
            raise RuntimeError(
                f"expected Conftest {PINNED_VERSION}; got {result.stdout.strip()} "
                f"{result.stderr.strip()}"
            )

    def run_policy(self, files):
        command = [
            self.conftest,
            "test",
            "--combine",
            "--parser",
            "hcl2",
            "--no-color",
            "--policy",
            str(POLICY),
            *[str(path) for path in files],
        ]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def assert_rejected(self, config, expected_message):
        with tempfile.TemporaryDirectory(prefix="devobs-conftest-") as directory:
            fixture = Path(directory) / "main.tf"
            fixture.write_text(config, encoding="utf-8")
            result = self.run_policy([fixture])
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(expected_message, output)

    def test_current_terraform_configuration_passes(self):
        files = sorted((ROOT / "infra" / "terraform").glob("*.tf"))
        self.assertTrue(files, "no Terraform HCL files found; policy input is missing")
        result = self.run_policy(files)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 failures", result.stdout)

    def test_unreviewed_google_resource_is_rejected(self):
        fixture = VALID_CONFIG + '''
resource "google_compute_instance" "unexpected" {
  name         = "fixture-only"
  machine_type = "e2-micro"
  zone         = "us-central1-a"
}
'''
        self.assert_rejected(
            fixture,
            "Terraform resource type is not allowlisted: google_compute_instance",
        )

    def test_changed_required_label_is_rejected(self):
        fixture = VALID_CONFIG.replace('application = "devobs"', 'application = "other"')
        self.assert_rejected(fixture, "required repository labels must be set")

    def test_unreviewed_repository_label_is_rejected(self):
        fixture = VALID_CONFIG.replace(
            'managed_by  = "terraform"',
            'managed_by  = "terraform"\n    extra = "unreviewed"',
        )
        self.assert_rejected(fixture, "repository must use exactly the reviewed labels")

    def test_missing_artifact_registry_resource_is_rejected(self):
        fixture = '''
provider "google" {
  project = var.project_id
  region  = var.region
}
'''
        self.assert_rejected(
            fixture,
            "exactly one google_artifact_registry_repository.devobs_images block is required",
        )

    def test_unreviewed_data_source_is_rejected(self):
        fixture = VALID_CONFIG + '''
data "google_project" "current" {}
'''
        self.assert_rejected(fixture, "top-level Terraform block is not allowlisted: data")

    def test_inline_provider_credentials_are_rejected(self):
        fixture = VALID_CONFIG.replace(
            "  region  = var.region\n}",
            '  region  = var.region\n  credentials = "fixture-not-a-real-credential"\n}',
            1,
        )
        self.assert_rejected(
            fixture,
            "Google provider must use project_id and region variables only",
        )


if __name__ == "__main__":
    unittest.main()

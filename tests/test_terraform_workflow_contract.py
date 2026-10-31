import unittest
import re
from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
VALIDATE_JOB = WORKFLOW.split("\n  validate:\n", 1)[1].split("\n  production-release:\n", 1)[0]
NEEDS_LINE = next(line.strip() for line in VALIDATE_JOB.splitlines() if line.strip().startswith("needs:"))
NEEDS_LIST = NEEDS_LINE.split(":", 1)[1].strip()
if not (NEEDS_LIST.startswith("[") and NEEDS_LIST.endswith("]")):
    raise AssertionError("validate.needs must be an inline YAML list")
VALIDATE_NEEDS = {job.strip() for job in NEEDS_LIST[1:-1].split(",") if job.strip()}


class TerraformWorkflowContractTests(unittest.TestCase):
    def test_terraform_is_formatted_initialized_without_backend_and_validated(self):
        self.assertIn("  terraform-validate:\n", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform fmt -check", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform init -backend=false -input=false -lockfile=readonly", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform validate", WORKFLOW)
        self.assertIn("hashicorp/setup-terraform@dfe3c3f87815947d99a8997f908cb6525fc44e9e # v4.0.1", WORKFLOW)
        self.assertNotIn("terraform apply", WORKFLOW)
        self.assertNotIn("terraform plan", WORKFLOW)

    def test_mocked_terraform_plan_is_plan_only_and_runs_in_required_ci(self):
        fixture = Path("infra/terraform/tests/registry_mock.tftest.hcl").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'(?m)^mock_provider "google"\\s*\\{\\}', fixture)), 1)
        self.assertEqual(len(re.findall(r'(?m)^run "[a-z_]+"\\s*\\{', fixture)), 3)
        self.assertEqual(len(re.findall(r'(?m)^\\s*command\\s*=\\s*plan\\s*
        self.assertIn("container-build", VALIDATE_NEEDS)
        self.assertIn("terraform-validate", VALIDATE_NEEDS)
        self.assertIn("TERRAFORM_RESULT", WORKFLOW)
        job = WORKFLOW.split("  terraform-validate:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)


if __name__ == "__main__":
    unittest.main()
, fixture)), 3)
        self.assertNotRegex(fixture, r'(?m)^\\s*(provider "google"|command\\s*=\\s*apply)')
        self.assertNotIn("credentials", fixture.lower())
        self.assertIn('expect_failures = [var.project_id]', fixture)
        self.assertIn('expect_failures = [var.repository_id]', fixture)
        job = WORKFLOW.split("  terraform-validate:\\n", 1)[1].split("\\n  validate:\\n", 1)[0]
        self.assertIn("terraform -chdir=infra/terraform test -no-color", job)
        self.assertNotIn("terraform apply", job)
        self.assertNotIn("terraform plan", job)

    def test_terraform_validation_is_required_and_skipped_for_rollback(self):
        self.assertIn("container-build", VALIDATE_NEEDS)
        self.assertIn("terraform-validate", VALIDATE_NEEDS)
        self.assertIn("TERRAFORM_RESULT", WORKFLOW)
        job = WORKFLOW.split("  terraform-validate:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)


if __name__ == "__main__":
    unittest.main()

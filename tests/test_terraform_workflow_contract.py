import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


class TerraformWorkflowContractTests(unittest.TestCase):
    def test_terraform_is_formatted_initialized_without_backend_and_validated(self):
        self.assertIn("  terraform-validate:\n", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform fmt -check", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform init -backend=false -input=false -lockfile=readonly", WORKFLOW)
        self.assertIn("terraform -chdir=infra/terraform validate", WORKFLOW)
        self.assertIn("hashicorp/setup-terraform@dfe3c3f87815947d99a8997f908cb6525fc44e9e # v4.0.1", WORKFLOW)
        self.assertNotIn("terraform apply", WORKFLOW)
        self.assertNotIn("terraform plan", WORKFLOW)

    def test_terraform_validation_is_required_and_skipped_for_rollback(self):
        self.assertIn("container-build, terraform-validate]", WORKFLOW)
        self.assertIn("TERRAFORM_RESULT", WORKFLOW)
        job = WORKFLOW.split("  terraform-validate:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)


if __name__ == "__main__":
    unittest.main()

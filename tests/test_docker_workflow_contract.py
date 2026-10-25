import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


class DockerWorkflowContractTests(unittest.TestCase):
    def test_container_is_built_smoke_tested_and_required_by_validate(self):
        self.assertIn("  container-build:\n", WORKFLOW)
        self.assertIn("docker build --pull --tag", WORKFLOW)
        self.assertIn("docker run --detach --rm", WORKFLOW)
        self.assertIn("127.0.0.1:18080:8080", WORKFLOW)
        self.assertIn("container-build]", WORKFLOW)
        self.assertIn("CONTAINER_RESULT", WORKFLOW)
        self.assertNotIn("docker push", WORKFLOW)

    def test_container_build_is_skipped_for_rollback_profile(self):
        job = WORKFLOW.split("  container-build:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)


if __name__ == "__main__":
    unittest.main()

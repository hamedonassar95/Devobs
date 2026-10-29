import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
DOCKERFILE = Path("Dockerfile").read_text(encoding="utf-8")
VALIDATE_JOB = WORKFLOW.split("\n  validate:\n", 1)[1].split("\n  production-release:\n", 1)[0]
NEEDS_LINE = next(line.strip() for line in VALIDATE_JOB.splitlines() if line.strip().startswith("needs:"))
NEEDS_LIST = NEEDS_LINE.split(":", 1)[1].strip()
if not (NEEDS_LIST.startswith("[") and NEEDS_LIST.endswith("]")):
    raise AssertionError("validate.needs must be an inline YAML list")
VALIDATE_NEEDS = {job.strip() for job in NEEDS_LIST[1:-1].split(",") if job.strip()}


class DockerWorkflowContractTests(unittest.TestCase):
    def test_runtime_base_is_digest_pinned_and_preserves_deployment_contract(self):
        self.assertIn(
            "FROM nginx/nginx-unprivileged:1.31.8-alpine3.24-slim@"
            "sha256:629d3227f39ec10201345e420e2d9d430e463a9893d374b515a8eb6541e71938 AS runtime",
            DOCKERFILE,
        )
        self.assertIn("USER 101:101", DOCKERFILE)
        self.assertIn("EXPOSE 8080", DOCKERFILE)
        self.assertIn("HEALTHCHECK", DOCKERFILE)

    def test_container_is_built_smoke_tested_scanned_and_required_by_validate(self):
        self.assertIn("  container-build:\n", WORKFLOW)
        self.assertIn("docker build --pull --tag", WORKFLOW)
        self.assertIn("docker run --detach --rm", WORKFLOW)
        self.assertIn("127.0.0.1:18080:8080", WORKFLOW)
        self.assertIn("trivy image --image-src docker", WORKFLOW)
        self.assertIn("scripts/trivy_report_policy.py", WORKFLOW)
        self.assertIn('docker image inspect --format', WORKFLOW)
        self.assertIn("container-build", VALIDATE_NEEDS)
        self.assertNotIn("container-image-scan", VALIDATE_NEEDS)
        self.assertIn("CONTAINER_RESULT", WORKFLOW)
        self.assertNotIn("docker push", WORKFLOW)

    def test_container_build_is_skipped_for_rollback_profile(self):
        job = WORKFLOW.split("  container-build:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("if: inputs.validation_profile != 'rollback'", job)


if __name__ == "__main__":
    unittest.main()

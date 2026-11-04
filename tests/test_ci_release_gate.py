import unittest
from pathlib import Path
import re


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
PAGES_WORKFLOW = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")


class CIReleaseGateContractTests(unittest.TestCase):
    def test_pages_release_survives_skipped_optional_checks_but_requires_validation(self):
        expected = (
            "if: ${{ !cancelled() && github.event_name == 'push' && "
            "github.ref == 'refs/heads/main' && needs.validate.result == 'success' }}"
        )
        self.assertIn(expected, WORKFLOW)

    def test_pages_deploy_action_timeout_is_below_job_timeout(self):
        deploy = re.search(
            r"(?ms)^  deploy:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", PAGES_WORKFLOW
        )
        self.assertIsNotNone(deploy)
        action_step = re.search(
            r"(?ms)^      - name: Deploy to GitHub Pages\n(.*?)(?=^      - name: |\Z)",
            deploy.group(1),
        )
        self.assertIsNotNone(action_step)
        action_timeout = re.search(r"(?m)^          timeout: ([0-9]+)$", action_step.group(1))
        job_timeout = re.search(r"(?m)^    timeout-minutes: ([0-9]+)$", deploy.group(1))
        self.assertIsNotNone(action_timeout)
        self.assertIsNotNone(job_timeout)
        action_timeout_ms = int(action_timeout.group(1))
        self.assertGreater(action_timeout_ms, 600_000)
        self.assertGreater(int(job_timeout.group(1)) * 60_000, action_timeout_ms)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
import re


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
PAGES_WORKFLOW = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")


class CIReleaseGateContractTests(unittest.TestCase):
    def test_pages_release_survives_skipped_optional_checks_but_requires_manual_confirmation_and_validation(self):
        expected = (
            "if: ${{ !cancelled() && github.event_name == 'workflow_dispatch' && "
            "github.ref == 'refs/heads/main' && inputs.confirm_release == true && "
            "inputs.controlled_incident_failure != true && needs.validate.result == 'success' }}"
        )
        self.assertIn(expected, WORKFLOW)
        self.assertIn("release_confirmation: ${{ inputs.confirm_release }}", WORKFLOW)

    def test_pages_release_has_no_push_to_main_trigger(self):
        release = WORKFLOW.split("  production-release:\n", 1)[1].split("\n  controlled-incident-drill:", 1)[0]
        dispatch_inputs = WORKFLOW.split("  workflow_dispatch:\n", 1)[1].split("  workflow_call:", 1)[0]
        release_input = dispatch_inputs.split("      confirm_release:\n", 1)[1].split(
            "\n      controlled_incident_failure:", 1
        )[0]
        pages_eligible = PAGES_WORKFLOW.split("  eligible:\n", 1)[1].split("\n  deploy:", 1)[0]

        self.assertIn("github.event_name == 'workflow_dispatch'", release)
        self.assertNotIn("github.event_name == 'push'", release)
        self.assertIn("default: false", release_input)
        self.assertIn("github.event_name == 'workflow_dispatch'", pages_eligible)
        self.assertIn("inputs.release_confirmation == true", pages_eligible)
        self.assertNotIn("github.event_name == 'push'", pages_eligible)

    def test_pages_reruns_select_one_attempt_specific_artifact(self):
        deploy = PAGES_WORKFLOW.split("  deploy:\n", 1)[1].split("\n  verify:", 1)[0]
        upload = deploy.split("- name: Upload Pages artifact\n", 1)[1].split("- name: Deploy to GitHub Pages\n", 1)[0]
        publish = deploy.split("- name: Deploy to GitHub Pages\n", 1)[1]
        upload_name = re.search(r"(?m)^          name: (.+)$", upload)
        publish_name = re.search(r"(?m)^          artifact_name: (.+)$", publish)
        upload_template = upload_name.group(1) if upload_name else "github-pages"
        publish_template = publish_name.group(1) if publish_name else "github-pages"

        def render(template, run_id, attempt):
            return template.replace("${{ github.run_id }}", str(run_id)).replace(
                "${{ github.run_attempt }}", str(attempt)
            )

        artifacts = [render(upload_template, run, attempt) for run, attempt in ((123, 1), (123, 2), (124, 1))]
        self.assertEqual(len(set(artifacts)), 3, "retry artifacts must not share a name")
        for run, attempt in ((123, 1), (123, 2), (124, 1)):
            requested = render(publish_template, run, attempt)
            self.assertEqual(artifacts.count(requested), 1, "deployment must select exactly its own upload")

    def test_pages_deploy_action_uses_capped_timeout_below_job_timeout(self):
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
        self.assertEqual(action_timeout_ms, 600_000)
        self.assertGreater(int(job_timeout.group(1)) * 60_000, action_timeout_ms)


if __name__ == "__main__":
    unittest.main()

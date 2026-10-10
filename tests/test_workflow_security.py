import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def shell_run_blocks(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    blocks = []
    for index, line in enumerate(lines):
        if line.lstrip().startswith("run: |"):
            indent = len(line) - len(line.lstrip())
            block = []
            for following in lines[index + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                block.append(following)
            blocks.append("\n".join(block))
    return blocks


class WorkflowSecurityTests(unittest.TestCase):
    def test_rollback_dispatch_inputs_are_not_interpolated_into_shell(self):
        workflow = (ROOT / ".github/workflows/rollback-pages.yml").read_text(encoding="utf-8")
        shell = "\n".join(shell_run_blocks(workflow))
        self.assertNotRegex(shell, re.compile(r"\$\{\{\s*inputs\.(?:confirmation|release_tag)\s*\}\}"))
        self.assertIn("CONFIRMATION: ${{ inputs.confirmation }}", workflow)
        self.assertIn("RELEASE_TAG: ${{ inputs.release_tag }}", workflow)

    def test_rollback_jobs_only_run_from_main(self):
        workflow = (ROOT / ".github/workflows/rollback-pages.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("if: github.ref == 'refs/heads/main'"), 2)
        self.assertIn('git merge-base --is-ancestor "$commit_sha" "$GITHUB_SHA"', workflow)

    def test_incident_response_checks_source_branch_repository_and_event(self):
        workflow = (ROOT / ".github/workflows/incident-response.yml").read_text(encoding="utf-8")
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", workflow)
        self.assertIn("API_HEAD_REPOSITORY\" != \"$GH_REPO", workflow)
        self.assertIn("trusted_investigation(comment)", workflow)


if __name__ == "__main__":
    unittest.main()

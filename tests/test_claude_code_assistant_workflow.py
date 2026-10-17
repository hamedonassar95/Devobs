from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ClaudeCodeAssistantWorkflowTests(unittest.TestCase):
    def test_action_is_pinned_and_secret_is_checked_before_invocation(self):
        workflow = (ROOT / ".github/workflows/claude-code-assistant.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "anthropics/claude-code-action@f27be6b65a4652f08a2ba3cff79114829b588967 # v1.0.0",
            workflow,
        )
        self.assertIn("secrets.ANTHROPIC_API_KEY", workflow)
        self.assertIn('[[ -z "${ANTHROPIC_API_KEY:-}" ]]', workflow)
        self.assertIn("steps.credential.outputs.enabled == 'true'", workflow)

    def test_invocations_require_mention_and_trusted_same_repository_actor(self):
        workflow = (ROOT / ".github/workflows/claude-code-assistant.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("contains(github.event.comment.body, '@claude')", workflow)
        self.assertIn("contains(github.event.issue.body, '@claude')", workflow)
        self.assertIn("github.event.comment.author_association == 'OWNER'", workflow)
        self.assertIn("github.event.issue.author_association == 'OWNER'", workflow)
        self.assertIn("github.event.issue.pull_request == null", workflow)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            workflow,
        )

    def test_permissions_are_limited_to_code_and_discussion_writes(self):
        workflow = (ROOT / ".github/workflows/claude-code-assistant.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("contents: write", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("issues: write", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("actions: read", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()

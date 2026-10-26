from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ClaudeCodeAssistantWorkflowTests(unittest.TestCase):
    def test_action_is_pinned_and_secret_is_checked_before_invocation(self):
        workflow = (ROOT / ".github/workflows/claude-code-assistant.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "anthropics/claude-code-action@16f9f71ab9c490faf367f94dd294897edc25be33 # v1.0.261",
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

    def test_permissions_and_agent_tools_are_read_only_for_code(self):
        workflow = (ROOT / ".github/workflows/claude-code-assistant.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("contents: read", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("actions: read", workflow)
        self.assertIn("--allowedTools Read,Grep,Glob", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()

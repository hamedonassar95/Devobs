"""Offline safety contract for the optional, read-only GitHub MCP example."""
import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".codex/examples/github-mcp-readonly.toml"


class GitHubMcpExampleTests(unittest.TestCase):
    def test_example_is_optional_and_read_only_with_pinned_image(self):
        raw = EXAMPLE.read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        server = config["mcp_servers"]["github"]
        args = server["args"]
        env = server["env"]

        self.assertIn("NOT loaded by Devobs by default", raw)
        self.assertEqual(server["command"], "docker")
        self.assertEqual(server["env_vars"], ["GITHUB_PERSONAL_ACCESS_TOKEN"])
        self.assertEqual(env["GITHUB_READ_ONLY"], "true")
        self.assertEqual(env["GITHUB_OAUTH_SCOPES"], "public_repo")
        self.assertEqual(
            env["GITHUB_TOOLSETS"], "repos,issues,pull_requests,actions"
        )
        self.assertEqual(env["GITHUB_OAUTH_CALLBACK_PORT"], "8085")
        port_index = args.index("-p")
        self.assertEqual(args[port_index + 1], "127.0.0.1:8085:8085")
        self.assertRegex(
            args[-1],
            r"^ghcr\.io/github/github-mcp-server:v2\.1\.0@sha256:[0-9a-f]{64}$",
        )
        self.assertNotRegex(raw, r"(?:gh[pousr]_|github_pat_|Bearer\s+[A-Za-z0-9])")

    def test_readme_and_guide_link_each_other(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs/GITHUB_MCP_INTEGRATION.md").read_text(encoding="utf-8")
        root_config = tomllib.loads(
            (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        )
        self.assertIn("docs/GITHUB_MCP_INTEGRATION.md", readme)
        self.assertIn(".codex/examples/github-mcp-readonly.toml", guide)
        self.assertNotIn("github", root_config.get("mcp_servers", {}))


if __name__ == "__main__":
    unittest.main()

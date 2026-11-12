"""Offline safety contract for the optional Argo CD MCP example."""

import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".codex/examples/argocd-mcp-readonly.toml"
SOURCE_COMMIT = "28d15ca69b0c31387cc6ec73d201fd13c5d22b6a"
IMAGE_DIGEST = (
    "sha256:dffc6c719d8635be2d5f2c8ad1c0178540325da4b40da0b373307e12b4c48f86"
)


class ArgoCdMcpExampleTests(unittest.TestCase):
    def test_codex_example_is_opt_in_and_allows_only_approved_listing(self):
        raw = EXAMPLE.read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        server = config["mcp_servers"]["argocd"]

        self.assertIn("NOT loaded by Devobs by default", raw)
        self.assertEqual(server["command"], "docker")
        self.assertIn("--pull=always", server["args"])
        self.assertIn("-i", server["args"])
        self.assertIn("stdio", server["args"])
        self.assertIn(
            f"ghcr.io/argoproj-labs/mcp-for-argocd@{IMAGE_DIGEST}",
            server["args"],
        )
        self.assertIn("-e", server["args"])
        self.assertEqual(
            server["env_vars"], ["ARGOCD_BASE_URL", "ARGOCD_API_TOKEN"]
        )
        self.assertEqual(server["env"], {"MCP_READ_ONLY": "true"})
        self.assertEqual(server["enabled_tools"], ["list_applications"])
        self.assertEqual(server["default_tools_approval_mode"], "prompt")
        self.assertEqual(
            server["tools"]["list_applications"]["approval_mode"], "prompt"
        )
        self.assertEqual(
            server["tools"]["list_applications"]["output_token_limit"], 3000
        )
        self.assertNotIn("url", server)
        self.assertNotIn("ARGOCD_API_TOKEN", server.get("env", {}))
        self.assertNotRegex(
            raw, r"(?:Bearer\s+[A-Za-z0-9._~-]{12,}|eyJ[a-zA-Z0-9_-]{16,})"
        )

        root_config = tomllib.loads(
            (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        )
        self.assertNotIn("argocd", root_config.get("mcp_servers", {}))

    def test_guide_pins_source_provenance_and_runtime_limits(self):
        guide = (ROOT / "docs/ARGOCD_MCP_INTEGRATION.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(SOURCE_COMMIT, guide)
        self.assertIn(IMAGE_DIGEST, guide)
        self.assertIn("Apache-2.0", guide)
        self.assertIn("SLSA", guide)
        self.assertIn("MCP_READ_ONLY=true", guide)
        self.assertIn("UNVERIFIED", guide)
        self.assertIn("docs/ARGOCD_MCP_INTEGRATION.md", readme)
        self.assertIn("list_applications", readme)


if __name__ == "__main__":
    unittest.main()

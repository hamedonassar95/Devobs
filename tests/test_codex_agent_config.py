"""Offline contract checks for Devobs's Codex agent configuration.

These prove repository configuration structure, NOT that Codex has run agents
or that the declared instructions enforce host permissions.
"""
import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".codex" / "config.toml"
AGENT_DIR = ROOT / ".codex" / "agents"


class CodexAgentConfigurationTests(unittest.TestCase):
    def test_scoped_config_is_valid_and_bounded(self):
        data = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        agents = data["agents"]
        self.assertIs(agents["enabled"], True)
        self.assertGreaterEqual(agents["max_concurrent_threads_per_session"], 1)
        self.assertLessEqual(agents["max_concurrent_threads_per_session"], 2)
        self.assertNotIn("model", data)
        self.assertNotIn("model_provider", data)
        self.assertNotIn("approval_policy", data)

    def test_all_four_agent_roles_have_valid_contracts(self):
        expected = {
            "devobs_architecture",
            "devobs_security",
            "devobs_qa",
            "devobs_operations",
        }
        seen = set()
        for path in sorted(AGENT_DIR.glob("*.toml")):
            role = tomllib.loads(path.read_text(encoding="utf-8"))
            name = role["name"]
            self.assertEqual(path.stem, name)
            self.assertNotIn(name, seen)
            seen.add(name)
            self.assertTrue(role["description"].strip())
            self.assertTrue(role["developer_instructions"].strip())
            self.assertNotIn("model", role)
            self.assertNotIn("sandbox_mode", role)
            self.assertNotIn("mcp_servers", role)
        self.assertEqual(seen, expected)

    def test_mutation_and_cost_boundaries_are_documented(self):
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Never push directly to main", instructions)
        self.assertIn("Never merge or deploy without explicit owner approval", instructions)
        self.assertIn("Do not enable billable AI inference", instructions)
        skill = (
            ROOT / ".agents" / "skills"
            / "devobs-codex-operating-cycle" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("BLOCKED", skill)
        self.assertIn("Do not merge", skill)


if __name__ == "__main__":
    unittest.main()

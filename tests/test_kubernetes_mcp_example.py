"""Offline contract for the optional namespaced Kubernetes MCP example."""

import pathlib
import re
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CODEX_EXAMPLE = ROOT / ".codex/examples/kubernetes-events-readonly.toml"
SERVER_EXAMPLE = ROOT / ".codex/examples/kubernetes-events-server-readonly.toml"
RBAC_EXAMPLE = ROOT / ".codex/examples/kubernetes-events-reader-rbac.yaml"
SOURCE_COMMIT = "66553fed5c16454e5814b41e331b4357f15806d8"
WINDOWS_EXE_SHA256 = "2ed4b885f2b94ea8664bed028993370a0abda65fa72863ff4456a4c5b5cc4053"


class KubernetesMcpExampleTests(unittest.TestCase):
    def test_codex_example_is_opt_in_and_tool_approval_is_prompted(self):
        raw = CODEX_EXAMPLE.read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        server = config["mcp_servers"]["kubernetes_events"]
        self.assertIn("NOT loaded by Devobs by default", raw)
        self.assertIn("kubernetes-mcp-server-windows-amd64.exe", server["command"])
        self.assertIn("--config", server["args"])
        self.assertEqual(server["enabled_tools"], ["events_list"])
        self.assertEqual(server["default_tools_approval_mode"], "prompt")
        self.assertEqual(
            server["tools"]["events_list"]["approval_mode"], "prompt"
        )
        self.assertEqual(server["tools"]["events_list"]["output_token_limit"], 3000)

        root_config = tomllib.loads(
            (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        )
        self.assertNotIn("kubernetes_events", root_config.get("mcp_servers", {}))

    def test_upstream_config_allows_events_only_and_has_data_limit(self):
        raw = SERVER_EXAMPLE.read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        self.assertEqual(config["toolsets"], ["core"])
        self.assertTrue(config["read_only"])
        self.assertEqual(config["enabled_tools"], ["events_list"])
        self.assertEqual(config["max_backend_response_bytes"], 262144)
        self.assertIn("namespace", config["server_instructions"])
        self.assertIn("limit no greater than 100", config["server_instructions"])
        self.assertIn("kubernetes-events-reader.kubeconfig", config["kubeconfig"])

    def test_rbac_example_is_namespace_role_with_events_list_only(self):
        raw = RBAC_EXAMPLE.read_text(encoding="utf-8")
        self.assertEqual(raw.count("---"), 2)
        self.assertIn("kind: ServiceAccount", raw)
        self.assertIn("kind: Role\n", raw)
        self.assertIn("kind: RoleBinding", raw)
        self.assertIn('resources: ["events"]', raw)
        self.assertIn('verbs: ["list"]', raw)
        self.assertNotIn("kind: ClusterRole", raw)
        self.assertNotIn("kind: ClusterRoleBinding", raw)
        self.assertNotRegex(raw, r"(?im)^\s*(?:resources|verbs):\s*\[?\s*['\"]?\*\b")
        self.assertNotRegex(raw, r"(?i)secrets|pods/log|pods/exec|configmaps")

    def test_guide_pins_source_and_discloses_runtime_and_license_limits(self):
        guide = (ROOT / "docs/KUBERNETES_MCP_INTEGRATION.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(SOURCE_COMMIT, guide)
        self.assertIn(WINDOWS_EXE_SHA256, guide)
        self.assertIn("afad2c8a41a3c7258f46c7a968acbc5d2221cfeb", guide)
        self.assertIn("FSL-1.1-Apache-2.0", guide)
        self.assertIn("UNVERIFIED", guide)
        self.assertIn("docs/KUBERNETES_MCP_INTEGRATION.md", readme)


if __name__ == "__main__":
    unittest.main()

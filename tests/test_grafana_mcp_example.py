"""Offline safety contract for the optional, local Grafana MCP example."""
import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".codex/examples/grafana-mcp-readonly.toml"
SOURCE_COMMIT = "c8cafb67854c45e79f8f9b5fca7d9b3a403f1771"
WINDOWS_ARCHIVE_SHA256 = (
    "13049249ff4e5251ee60ba38ea47e6aba96c20939fbf133915b482a93827edfe"
)


class GrafanaMcpExampleTests(unittest.TestCase):
    def test_example_is_optional_local_and_read_only(self):
        raw = EXAMPLE.read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        server = config["mcp_servers"]["grafana"]
        args = server["args"]
        environment = server["env"]

        self.assertIn("NOT loaded by Devobs by default", raw)
        self.assertEqual(server["command"], "C:/path/to/mcp-grafana.exe")
        self.assertEqual(environment["GRAFANA_URL"], "http://127.0.0.1:3000")
        self.assertEqual(
            environment["GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE"],
            "C:/Users/you/AppData/Local/Devobs/secrets/grafana-mcp-token.txt",
        )
        self.assertIn("--transport=stdio", args)
        self.assertIn("--disable-write", args)
        self.assertIn("--disable-api", args)
        self.assertIn("--usage-stats=disabled", args)
        self.assertIn(
            "--enabled-tools=search,datasource,prometheus,dashboard", args
        )
        self.assertIn("--prometheus-guardrail-mode=enforce", args)
        self.assertIn("--prometheus-guardrail-max-range=24h", args)
        self.assertIn("--prometheus-guardrail-max-points=5000", args)
        self.assertNotRegex(
            raw, r"(?:glc_|eyJ[a-zA-Z0-9_-]{10,}|Bearer\s+[A-Za-z0-9])"
        )

        enabled = next(arg for arg in args if arg.startswith("--enabled-tools="))
        enabled_categories = set(enabled.partition("=")[2].split(","))
        self.assertEqual(
            enabled_categories,
            {"search", "datasource", "prometheus", "dashboard"},
        )
        self.assertNotIn("api", enabled_categories)
        self.assertNotIn("alerting", enabled_categories)
        self.assertNotIn("loki", enabled_categories)
        self.assertNotIn("sql", enabled_categories)

    def test_guide_pins_upstream_source_and_keeps_runtime_unverified(self):
        guide = (ROOT / "docs/GRAFANA_MCP_INTEGRATION.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        root_config = tomllib.loads(
            (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        )
        raw_example = EXAMPLE.read_text(encoding="utf-8")

        self.assertIn(SOURCE_COMMIT, guide)
        self.assertIn(WINDOWS_ARCHIVE_SHA256, guide)
        self.assertIn("GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE", guide)
        self.assertIn("--disable-write", guide)
        self.assertIn("--disable-api", guide)
        self.assertIn("Codex runtime", guide)
        self.assertIn("docs/GRAFANA_MCP_INTEGRATION.md", readme)
        self.assertNotIn("grafana", root_config.get("mcp_servers", {}))
        self.assertNotRegex(
            raw_example,
            r"GRAFANA_SERVICE_ACCOUNT_TOKEN\s*=\s*['\"][^<]",
        )


if __name__ == "__main__":
    unittest.main()

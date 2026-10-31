"""Offline behavioral/negative checks for the opt-in Docs MCP registration probe."""
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_codex_docs_mcp import (  # noqa: E402
    ProbeFailure,
    verify_local_codex_registration,
    verify_repository_config,
)


class DocsMcpProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = pathlib.Path(self.temp.name) / "config.toml"
        self.config.write_text(
            '[mcp_servers.openaiDeveloperDocs]\nurl = "https://developers.openai.com/mcp"\n',
            encoding="utf-8",
        )

    def test_exact_offline_config_accepted(self):
        self.assertIsNone(verify_repository_config(self.config))

    def test_missing_config_fails_closed(self):
        with self.assertRaisesRegex(ProbeFailure, "missing or invalid"):
            verify_repository_config(self.config.with_name("missing.toml"))

    def test_unsafe_url_and_secret_field_rejected(self):
        for changed in (
            '[mcp_servers.openaiDeveloperDocs]\nurl = "https://untrusted.example/mcp"\n',
            '[mcp_servers.openaiDeveloperDocs]\nurl = "https://developers.openai.com/mcp"\nauthorization = "secret"\n',
            '[mcp_servers.openaiDeveloperDocs]\nurl = "https://developers.openai.com/mcp"\n[mcp_servers.unreviewed]\nurl = "https://other.example/mcp"\n',
        ):
            with self.subTest(changed=changed[:45]):
                self.config.write_text(changed, encoding="utf-8")
                with self.assertRaises(ProbeFailure):
                    verify_repository_config(self.config)

    def test_missing_codex_cli_fails_closed_without_running(self):
        process = Mock()
        with self.assertRaisesRegex(ProbeFailure, "unavailable"):
            verify_local_codex_registration(locate=lambda _: None, run=process)
        process.assert_not_called()

    def test_matching_cli_listing_reports_registration_only(self):
        runner = Mock(return_value=Mock(returncode=0, stdout=(
            'openaiDeveloperDocs https://developers.openai.com/mcp enabled'
        )))
        verify_local_codex_registration(locate=lambda _: "/usr/bin/codex", run=runner)
        runner.assert_called_once_with(
            ["codex", "mcp", "list"], capture_output=True,
            text=True, check=False, timeout=10,
        )

    def test_cli_failure_and_missing_server_are_blocked(self):
        for status, output in ((1, "error"), (0, "other-server")):
            with self.subTest(status=status):
                with self.assertRaises(ProbeFailure):
                    verify_local_codex_registration(
                        locate=lambda _: "/usr/bin/codex",
                        run=lambda *args, **kwargs: Mock(returncode=status, stdout=output),
                    )

    def test_cli_timeout_is_blocked(self):
        def timed_out(*args, **kwargs):
            raise subprocess.TimeoutExpired("codex", 10)
        with self.assertRaisesRegex(ProbeFailure, "could not be completed"):
            verify_local_codex_registration(locate=lambda _: "/usr/bin/codex", run=timed_out)

    def test_cli_output_never_echoed_on_failure(self):
        self.config.write_text('invalid = [', encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_codex_docs_mcp.py"),
             "--config", str(self.config)], capture_output=True, text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("MCP_RUNTIME_UNVERIFIED", proc.stderr)
        self.assertNotIn("invalid = [", proc.stderr)


if __name__ == "__main__":
    unittest.main()

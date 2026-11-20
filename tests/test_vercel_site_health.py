from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from tests.platform_support import (
    require_bash,
    to_bash_path,
    write_python3_shim,
    write_python_cli_shim,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "a" * 40
PRIVATE_PATHS = (
    "/scripts/check_site.py",
    "/docs/CI.md",
    "/README.md",
    "/site-contract.json",
)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            body = self.server.page_body
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        elif path == "/deployment.json":
            body = json.dumps({"schema_version": 1, "source_sha": self.server.source_sha}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif path == "/README.md" and self.server.redirect_private_to_login:
            body = b"login redirect"
            self.send_response(302)
            self.send_header("Location", "/login")
        elif path == "/login":
            body = b"<!doctype html><html><title>Sign in to Vercel</title><body>Authentication required</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        else:
            status = self.server.private_statuses.get(path, 404)
            body = (
                b"Authentication required: deployment is protected"
                if self.server.protection_body and status == 404
                else b"repository file" if status == 200 else b"not found"
            )
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class VercelSiteHealthBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
        self.server.source_sha = EXPECTED_SHA
        self.server.page_body = b"<!doctype html><html><body><h1>Devobs</h1></body></html>"
        self.server.private_statuses = {}
        self.server.redirect_private_to_login = False
        self.server.protection_body = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.contract = Path(self.temp_dir.name) / "site-contract.json"
        self.contract.write_text(json.dumps({"required_text_any": ["Devobs"]}), encoding="utf-8")
        self.bin_dir = Path(self.temp_dir.name) / "bin"
        self.bin_dir.mkdir()
        self.fake_python3 = write_python3_shim(self.bin_dir)
        self.fake_jq = write_python_cli_shim(
            self.bin_dir, "jq", ROOT / "tests" / "fixtures" / "fake_jq.py"
        )
        self.checker_script = Path(self.temp_dir.name) / "check_vercel_site.fixture.sh"
        self.checker_script.write_text(self._patched_checker_script(), encoding="utf-8")

    def _patched_checker_script(self):
        """Bind the production script's CLI calls to explicit offline fixtures."""
        script = (ROOT / "scripts" / "check_vercel_site.sh").read_text(encoding="utf-8")
        marker = "\ndone\n"
        tool_loop_end = script.index(marker) + len(marker)
        head, tail = script[:tool_loop_end], script[tool_loop_end:]
        patched_tail = tail.replace("python3 ", '"$FAKE_PYTHON3" ').replace(
            "jq ", '"$FAKE_JQ" '
        )
        patched = head + patched_tail
        self.assertIn('"$FAKE_PYTHON3" -', patched)
        self.assertIn('"$FAKE_JQ" -e', patched)
        self.assertIn("for tool in curl jq python3", head)
        self.assertNotIn(" python3 ", patched_tail)
        self.assertNotIn(" jq ", patched_tail)
        return patched

    def checker_environment(self):
        env = os.environ.copy()
        env["PATH"] = f"{to_bash_path(self.bin_dir)}:{env.get('PATH', '')}"
        env["FAKE_PYTHON3"] = to_bash_path(self.fake_python3)
        env["FAKE_JQ"] = to_bash_path(self.fake_jq)
        return env

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_checker(self, expected_sha=EXPECTED_SHA):
        bash = require_bash(self)
        env = self.checker_environment()
        env.update({
            "SITE_URL": f"http://127.0.0.1:{self.server.server_port}",
            "EXPECTED_SHA": expected_sha,
            "CONTRACT_FILE": str(self.contract),
            "ALLOW_INSECURE_LOCALHOST": "true",
            "MAX_ATTEMPTS": "1",
            "POLL_INTERVAL_SECONDS": "0",
        })
        return subprocess.run(
            [bash, to_bash_path(self.checker_script)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_matching_sha_passes(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wrong_sha_fails(self):
        result = self.run_checker("b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected SHA", result.stdout + result.stderr)

    def test_site_without_devobs_marker_fails(self):
        self.server.page_body = b"<!doctype html><html><body><h1>Different brand</h1></body></html>"
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("none of the accepted brand text", result.stdout + result.stderr)

    def test_contract_without_devobs_marker_fails_closed(self):
        self.contract.write_text(json.dumps({"required_text_any": ["AL-DALA MOBILE"]}), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Site contract must include the Devobs marker", result.stdout + result.stderr)

    def test_repository_contract_requires_devobs_marker(self):
        contract = json.loads((ROOT / "site-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(
            contract.get("required_text_any"),
            ["Devobs"],
            "site-contract.json must require the Devobs brand marker only",
        )

    def test_missing_site_url_does_not_fall_back_to_production_url(self):
        bash = require_bash(self)
        env = self.checker_environment()
        env.update({
            "VERCEL_PRODUCTION_URL": f"http://127.0.0.1:{self.server.server_port}",
            "EXPECTED_SHA": EXPECTED_SHA,
            "CONTRACT_FILE": str(self.contract),
            "ALLOW_INSECURE_LOCALHOST": "true",
        })
        env.pop("SITE_URL", None)
        result = subprocess.run(
            [bash, to_bash_path(self.checker_script)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Set SITE_URL to the preview deployment URL", result.stdout + result.stderr)

    def test_readme_returning_200_fails(self):
        self.server.private_statuses["/README.md"] = 200
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/README.md ended at HTTP 200", result.stdout + result.stderr)

    def test_all_private_paths_returning_404_passes(self):
        self.server.private_statuses = {path: 404 for path in PRIVATE_PATHS}
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_private_path_redirecting_to_login_200_fails(self):
        self.server.redirect_private_to_login = True
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("login or Deployment Protection response", result.stdout + result.stderr)

    def test_private_path_404_with_protection_body_fails(self):
        self.server.private_statuses["/README.md"] = 404
        self.server.protection_body = True
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("login or Deployment Protection response", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

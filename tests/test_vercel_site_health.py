from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest


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

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_checker(self, expected_sha=EXPECTED_SHA):
        env = os.environ.copy()
        env.update({
            "SITE_URL": f"http://127.0.0.1:{self.server.server_port}",
            "EXPECTED_SHA": expected_sha,
            "CONTRACT_FILE": str(self.contract),
            "ALLOW_INSECURE_LOCALHOST": "true",
            "MAX_ATTEMPTS": "1",
            "POLL_INTERVAL_SECONDS": "0",
        })
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "check_vercel_site.sh")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
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
        env = os.environ.copy()
        env.update({
            "VERCEL_PRODUCTION_URL": f"http://127.0.0.1:{self.server.server_port}",
            "EXPECTED_SHA": EXPECTED_SHA,
            "CONTRACT_FILE": str(self.contract),
            "ALLOW_INSECURE_LOCALHOST": "true",
        })
        env.pop("SITE_URL", None)
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "check_vercel_site.sh")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
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

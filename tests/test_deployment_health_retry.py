"""Offline behavioral tests for the bounded deployment-manifest retry.

The GitHub Pages health check is a bash program embedded in a workflow file.
These tests extract that exact program, point only its site URL at a loopback
mock server, and exercise the real curl/retry/validation path. No GitHub Pages
host, credential, deployment or paid service is contacted.

The retry applies to transport failures only. HTTP status handling, the exact
40-hex source-SHA check and the expected-SHA comparison must keep failing
closed, and nothing may be retried into a pass.
"""
from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deployment-health-check.yml"

# The single production URL line the harness replaces. If the workflow changes
# it, every behavioral test fails loudly instead of silently testing nothing.
URL_ANCHOR = 'SITE_URL="https://hamedonassar95.github.io/Devobs/"'
TEST_URL_LINE = 'SITE_URL="$TEST_SITE_URL"'

SAMPLE_SHA = "c3998b951d8fb6b829e93105e6b34388722b2a63"
OTHER_SHA = "a" * 40


def _find_bash() -> str | None:
    candidates = [shutil.which("bash")]
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")):
            if base:
                candidates.append(str(Path(base) / "Git" / "bin" / "bash.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def _probe(bash: str | None, command: str) -> bool:
    if not bash:
        return False
    try:
        result = subprocess.run([bash, "-s"], input=command, capture_output=True,
                                text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


BASH = _find_bash()
HAS_CURL = _probe(BASH, "command -v curl >/dev/null 2>&1")
HAS_JQ = _probe(BASH, "command -v jq >/dev/null 2>&1")
NO_BASH = None if BASH else "bash is not installed"
NO_CURL = None if HAS_CURL else "curl is not available inside bash"
NO_JQ = None if HAS_JQ else "jq is not available inside bash"


def extract_script() -> str:
    """Return the exact bash program of the 'Verify deployed site' step."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "- name: Verify deployed site":
            start = index
            break
    if start is None:
        raise AssertionError("verify step not found in deployment-health-check.yml")

    run_index = None
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "run: |":
            run_index = index
            break
        if stripped.startswith("- "):
            break
    if run_index is None:
        raise AssertionError("run block not found in the verify step")

    body: list[str] = []
    for line in lines[run_index + 1:]:
        if not line.strip():
            body.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < 10:
            break
        body.append(line[10:])
    while body and not body[-1]:
        body.pop()

    script = "\n".join(body) + "\n"
    if "set -euo pipefail" not in script or "manifest_url=" not in script:
        raise AssertionError("extracted block is not the expected verify script")
    return script


class _State:
    def __init__(self, mode: str, body: bytes, status: int) -> None:
        self.mode = mode
        self.body = body
        self.status = status
        self.manifest_requests = 0
        self.lock = threading.Lock()


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # the reset path is expected
        pass


def _make_handler(state: _State):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt, *args):  # keep test output quiet
            pass

        def finish(self):
            try:
                super().finish()
            except Exception:  # the reset path closes the socket on purpose
                pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in ("/", "/index.html"):
                self._send(200, b"<!doctype html><title>Devobs</title><h1>Devobs</h1>",
                           "text/html; charset=utf-8")
                return
            if path != "/deployment.json":
                self._send(404, b"", "text/plain")
                return
            with state.lock:
                state.manifest_requests += 1
                attempt = state.manifest_requests
            if state.mode == "reset" or (state.mode == "reset_once" and attempt == 1):
                self._reset()
                return
            if state.mode == "timeout":
                # Hold the response open so curl exits with its documented
                # timeout code (28) and exercises the retry bound.
                time.sleep(30)
                return
            if state.mode in ("partial", "partial_once"):
                truncated = b'{"schema_version":1,"source_sha":"'
                if state.mode == "partial" or attempt == 1:
                    self._send_partial(truncated)
                    return
            self._send(state.status, state.body, "application/json")

        def _reset(self) -> None:
            self.close_connection = True
            try:
                self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                           struct.pack("ii", 1, 0))
            except OSError:
                pass
            try:
                self.connection.close()
            except OSError:
                pass

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _send_partial(self, body: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            # Deliberately promise more bytes than are written so curl reports
            # exit 18 instead of producing a complete, parseable response.
            self.send_header("Content-Length", str(len(body) + 64))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True

    return Handler


class WorkflowContractTests(unittest.TestCase):
    """Guards that run without bash and protect the hardening invariants."""

    def setUp(self):
        self.script = extract_script()
        # Comments may legitimately name a forbidden flag, so only real code
        # lines are inspected for the hardening invariants.
        self.code = "\n".join(line for line in self.script.splitlines()
                              if not line.lstrip().startswith("#"))
        self.manifest = self.code[self.code.index("manifest_url="):]

    def test_retry_is_bounded_to_three_attempts(self):
        match = re.search(r"^manifest_max_attempts=(\d+)$", self.script, re.MULTILINE)
        self.assertIsNotNone(match, "a fixed attempt bound must be declared")
        self.assertEqual(match.group(1), "3")
        self.assertIn('sleep "$manifest_attempt"', self.code)
        self.assertIn("manifest_attempt=$(( manifest_attempt + 1 ))", self.code)

    def test_only_documented_transport_exit_codes_are_retried(self):
        retry_case = [line.strip() for line in self.code.splitlines()
                      if line.strip().startswith("6|7|")]
        self.assertEqual(retry_case, ["6|7|18|28|35|52|55|56|92) ;;"])
        self.assertNotIn("*) ;;", self.code)

    def test_manifest_fetch_is_a_bounded_read_only_get(self):
        self.assertIn("--connect-timeout 5", self.manifest)
        self.assertIn("--max-time 20", self.manifest)
        for forbidden in ("--data", "--form", "--upload-file", "-X ", "--request ",
                          "--retry", "-d "):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.manifest)

    def test_tls_verification_is_never_disabled(self):
        self.assertNotIn("--insecure", self.code)
        self.assertNotRegex(self.code, r"(?<![\w-])-k(?![\w-])")
        self.assertNotIn("--no-check-certificate", self.code)

    def test_retry_does_not_touch_sha_validation_rules(self):
        self.assertIn("jq -er 'select(.schema_version == 1) | .source_sha'", self.code)
        self.assertIn('=~ ^[0-9a-f]{40}$', self.code)
        self.assertIn('"$deployed_sha" != "$EXPECTED_SHA"', self.code)

    def test_no_secret_or_environment_dump(self):
        for forbidden in ("printenv", "set -x", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.code)


@unittest.skipIf(NO_BASH, NO_BASH or "")
@unittest.skipIf(NO_CURL, NO_CURL or "")
class ManifestRetryBehaviourTests(unittest.TestCase):
    def start(self, mode: str, body: bytes = b"", status: int = 200) -> str:
        self.state = _State(mode, body, status)
        self.server = _Server(("127.0.0.1", 0), _make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop)
        return f"http://127.0.0.1:{self.server.server_address[1]}/"

    def _stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_script(self, url: str, expected_sha: str = ""):
        script = extract_script()
        self.assertIn(URL_ANCHOR, script, "SITE_URL anchor changed; update the harness")
        script = script.replace(URL_ANCHOR, TEST_URL_LINE, 1)
        self.assertNotIn(URL_ANCHOR, script)
        work = Path(tempfile.mkdtemp(prefix="pages-retry-"))
        self.addCleanup(shutil.rmtree, work, True)
        output = work / "github_output"
        summary = work / "github_summary"
        output.write_text("", encoding="utf-8")
        summary.write_text("", encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "TEST_SITE_URL": url,
            "EXPECTED_SHA": expected_sha,
            "GITHUB_RUN_ID": "44401423814",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        })
        return subprocess.run([BASH, "-s"], input=script, cwd=str(work), env=env,
                              capture_output=True, text=True, timeout=180), output

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_connection_reset_then_success_is_retried(self):
        manifest = json.dumps({"schema_version": 1, "source_sha": SAMPLE_SHA}).encode()
        url = self.start("reset_once", manifest)
        proc, output = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.state.manifest_requests, 2)
        self.assertIn("Manifest fetch retry", proc.stdout)
        self.assertIn(f"source_sha={SAMPLE_SHA}", output.read_text(encoding="utf-8"))
        self.assertIn("Deployment health check passed", proc.stdout)

    def test_persistent_transport_failure_stops_after_three_attempts(self):
        url = self.start("reset")
        proc, _ = self.run_script(url)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.state.manifest_requests, 3)
        self.assertIn("Manifest fetch failed after all attempts", proc.stdout)
        self.assertNotIn("Deployment health check passed", proc.stdout)

    def test_transport_timeout_stops_after_three_attempts(self):
        url = self.start("timeout")
        proc, _ = self.run_script(url)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.state.manifest_requests, 3)
        self.assertIn("Manifest fetch failed after all attempts", proc.stdout)
        self.assertIn("Last curl exit 28.", proc.stdout)
        self.assertNotIn("Deployment health check passed", proc.stdout)

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_partial_response_recovers_on_second_attempt(self):
        manifest = json.dumps({"schema_version": 1, "source_sha": SAMPLE_SHA}).encode()
        url = self.start("partial_once", manifest)
        proc, output = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.state.manifest_requests, 2)
        self.assertIn("Manifest fetch retry (curl exit 18).", proc.stdout)
        self.assertIn(f"source_sha={SAMPLE_SHA}", output.read_text(encoding="utf-8"))

    def test_persistent_partial_response_fails_after_three_attempts(self):
        url = self.start("partial")
        proc, _ = self.run_script(url)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.state.manifest_requests, 3)
        self.assertIn("Manifest fetch failed after all attempts", proc.stdout)
        self.assertIn("Last curl exit 18.", proc.stdout)
        self.assertNotIn("Deployment health check passed", proc.stdout)

    def test_http_500_is_rejected_without_retry(self):
        url = self.start("status", b"", 500)
        proc, _ = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.state.manifest_requests, 1)
        self.assertIn("HTTP 500", proc.stdout)
        self.assertNotIn("Manifest fetch retry", proc.stdout)

    def test_http_404_with_required_expected_sha_fails_closed(self):
        url = self.start("status", b"", 404)
        proc, _ = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.state.manifest_requests, 1)
        self.assertIn("HTTP 404", proc.stdout)
        self.assertNotIn("legacy deployment", proc.stdout)

    def test_http_404_without_expected_sha_keeps_legacy_behaviour(self):
        url = self.start("status", b"", 404)
        proc, _ = self.run_script(url)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.state.manifest_requests, 1)
        self.assertIn("legacy deployment", proc.stdout)

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_invalid_manifest_fails_without_echoing_the_body(self):
        body = json.dumps({"schema_version": 1,
                           "source_sha": "LEAK_SENTINEL_not_a_sha"}).encode()
        url = self.start("status", body)
        proc, _ = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("invalid source SHA", proc.stdout)
        self.assertNotIn("LEAK_SENTINEL", proc.stdout + proc.stderr)

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_invalid_json_is_rejected_without_echoing_the_body(self):
        url = self.start("status", b"INVALID_JSON_SENTINEL")
        proc, _ = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.state.manifest_requests, 1)
        self.assertNotIn("INVALID_JSON_SENTINEL", proc.stdout + proc.stderr)
        self.assertNotIn("Deployment health check passed", proc.stdout)

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_incorrect_source_sha_is_rejected(self):
        body = json.dumps({"schema_version": 1, "source_sha": SAMPLE_SHA}).encode()
        url = self.start("status", body)
        proc, _ = self.run_script(url, expected_sha=OTHER_SHA)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not match expected commit", proc.stdout)
        self.assertIn(OTHER_SHA, proc.stdout)

    @unittest.skipIf(NO_JQ, NO_JQ or "")
    def test_successful_first_attempt_is_not_retried(self):
        body = json.dumps({"schema_version": 1, "source_sha": SAMPLE_SHA}).encode()
        url = self.start("status", body)
        proc, output = self.run_script(url, expected_sha=SAMPLE_SHA)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.state.manifest_requests, 1)
        self.assertNotIn("retrying", proc.stdout)
        self.assertIn(f"source_sha={SAMPLE_SHA}", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

"""Run the workflow's actual HTML check against a local HTTP fixture."""
import http.server
from pathlib import Path
import subprocess
import textwrap
import threading
import time
import unittest

from tests.platform_support import require_bash

ROOT = Path(__file__).resolve().parents[1]


class ContainerSmokeHtmlTests(unittest.TestCase):
    def check_page(self, body, *, status=200, truncated=False):
        bash = require_bash(self)
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(status)
                self.send_header('Content-Length', str(len(body) + (100 if truncated else 0)))
                self.end_headers()
                try:
                    self.wfile.write(body[:8192])
                    self.wfile.flush()
                    # Healthy responses can arrive over multiple network writes.
                    time.sleep(0.03)
                    self.wfile.write(body[8192:])
                except (BrokenPipeError, ConnectionResetError):
                    pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            workflow = (ROOT / '.github/workflows/ci.yml').read_text()
            start = workflow.index('          if ! curl --fail --silent --show-error http://127.0.0.1:18080/')
            end = workflow.index('      - name:', start)
            fragment = textwrap.dedent(workflow[start:end])
            fragment = fragment.replace('http://127.0.0.1:18080/', f'http://127.0.0.1:{server.server_port}/')
            return subprocess.run([bash, '-c', 'set -euo pipefail\n' + fragment],
                                  capture_output=True, text=True, timeout=5)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_valid_chunked_delivery_is_not_a_broken_pipe_failure(self):
        result = self.check_page((ROOT / 'index.html').read_bytes())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('healthy and served the expected HTML page', result.stdout)

    def test_non_html_and_http_errors_still_fail_closed(self):
        for body, status in [(b'not HTML', 200), (b'<!doctype html>error', 500)]:
            with self.subTest(status=status):
                self.assertNotEqual(self.check_page(body, status=status).returncode, 0)

    def test_incomplete_response_fails_even_if_doctype_was_received(self):
        self.assertNotEqual(self.check_page(b'<!doctype html>partial', truncated=True).returncode, 0)

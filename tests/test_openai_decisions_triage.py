import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from scripts import openai_decisions_triage as decisions


class _LocalDecisionsHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.server.request_count += 1
        content_length = int(self.headers["Content-Length"])
        self.server.request_body = json.loads(self.rfile.read(content_length))
        self.server.authorization = self.headers.get("Authorization")
        if self.path == "/redirect":
            host, port = self.server.server_address
            self.send_response(307)
            self.send_header("Location", f"http://{host}:{port}/redirect-target")
            self.end_headers()
            return
        if self.path == "/rate-limit":
            self.send_response(429)
            self.send_header("Retry-After", "17")
            self.end_headers()
            return
        response = json.dumps(response_body()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass


def response_body():
    return {
        "answers": [
            {"type": "predicate", "name": "confirmed_security_impact", "probability": 0.02},
            {
                "type": "choice",
                "name": "incident_category",
                "choice": "ci_cd",
                "confidence": 0.93,
                "probabilities": [
                    {"value": value, "probability": 0.94 if value == "ci_cd" else 0.01}
                    for value in decisions.CATEGORY_VALUES
                ],
            },
            {
                "type": "score",
                "name": "incident_severity",
                "score": 1.1,
                "confidence": 0.55,
                "probabilities": [
                    {
                        "value": index,
                        "label": label,
                        "probability": probability,
                    }
                    for index, (label, _) in enumerate(decisions.SEVERITY_LEVELS)
                    for probability in ([0.1, 0.7, 0.2, 0.0, 0.0][index],)
                ],
            },
        ]
    }


class OpenAIDecisionsTriageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = Path(self.temp_dir.name) / "incident.txt"
        self.input_path.write_text("Redacted incident: the deployment job failed.", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *extra_args):
        return decisions.main(["--input-file", str(self.input_path), *extra_args])

    def test_budget_gate_blocks_before_request_even_with_api_key(self):
        with patch.dict(os.environ, {"DEVOBS_AI_BUDGET_APPROVED": "false", "OPENAI_API_KEY": "test-key"}):
            with patch.object(decisions, "_send_request") as send_request:
                self.assertEqual(self.run_cli("--confirm-billable", "--confirm-data-redacted"), 2)
        send_request.assert_not_called()

    def test_each_explicit_confirmation_is_required(self):
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        with patch.dict(os.environ, environment):
            with patch.object(decisions, "_send_request") as send_request:
                self.assertEqual(self.run_cli("--confirm-data-redacted"), 2)
                self.assertEqual(self.run_cli("--confirm-billable"), 2)
        send_request.assert_not_called()

    def test_missing_api_key_blocks_without_request(self):
        with patch.dict(os.environ, {"DEVOBS_AI_BUDGET_APPROVED": "true"}, clear=True):
            with patch.object(decisions, "_send_request") as send_request:
                self.assertEqual(self.run_cli("--confirm-billable", "--confirm-data-redacted"), 2)
        send_request.assert_not_called()

    def test_success_uses_documented_endpoint_and_typed_questions(self):
        response = json.dumps(response_body()).encode("utf-8")
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        with patch.dict(os.environ, environment):
            with patch.object(decisions, "_send_request", return_value=response) as send_request:
                from contextlib import redirect_stderr, redirect_stdout
                from io import StringIO

                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = self.run_cli("--confirm-billable", "--confirm-data-redacted")

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn("test-key", stdout.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["advisory_only"])
        self.assertEqual(result["answers"]["incident_category"]["choice"], "ci_cd")

        request = send_request.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/decisions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "gpt-6-luna")
        self.assertEqual(payload["input"], "Redacted incident: the deployment job failed.")
        self.assertEqual([question["type"] for question in payload["questions"]], ["predicate", "choice", "score"])

    def test_cli_posts_once_to_a_local_mock_server_without_provider_access(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalDecisionsHandler)
        server.request_count = 0
        server.request_body = None
        server.authorization = None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/v1/decisions"
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        try:
            with patch.dict(os.environ, environment), patch.object(decisions, "DECISION_ENDPOINT", endpoint):
                from contextlib import redirect_stderr, redirect_stdout
                from io import StringIO

                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = self.run_cli("--confirm-billable", "--confirm-data-redacted")
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(server.request_count, 1)
            self.assertEqual(server.authorization, "Bearer test-key")
            self.assertEqual(server.request_body["model"], "gpt-6-luna")
            self.assertEqual(len(server.request_body["questions"]), 3)
            self.assertTrue(json.loads(stdout.getvalue())["advisory_only"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_redirect_is_rejected_without_forwarding_authentication(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalDecisionsHandler)
        server.request_count = 0
        server.request_body = None
        server.authorization = None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/redirect"
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        try:
            with patch.dict(os.environ, environment), patch.object(decisions, "DECISION_ENDPOINT", endpoint):
                from contextlib import redirect_stderr
                from io import StringIO

                stderr = StringIO()
                with redirect_stderr(stderr):
                    exit_code = self.run_cli("--confirm-billable", "--confirm-data-redacted")
            self.assertEqual(exit_code, 2)
            self.assertEqual(server.request_count, 1)
            self.assertNotIn("test-key", stderr.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_rate_limit_is_reported_without_retry_and_honors_retry_after(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalDecisionsHandler)
        server.request_count = 0
        server.request_body = None
        server.authorization = None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/rate-limit"
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        try:
            with patch.dict(os.environ, environment), patch.object(decisions, "DECISION_ENDPOINT", endpoint):
                from contextlib import redirect_stderr
                from io import StringIO

                stderr = StringIO()
                with redirect_stderr(stderr):
                    exit_code = self.run_cli("--confirm-billable", "--confirm-data-redacted")
            self.assertEqual(exit_code, 2)
            self.assertEqual(server.request_count, 1)
            self.assertIn("wait at least 17 seconds", stderr.getvalue())
            self.assertNotIn("test-key", stderr.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_refusal_and_invalid_typed_answer_fail_closed(self):
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        refusal = {"answers": [{"type": "refusal", "name": "confirmed_security_impact"}]}
        malformed = response_body()
        malformed["answers"][1]["choice"] = "execute_rollback"
        for body in (refusal, malformed):
            with patch.dict(os.environ, environment):
                with patch.object(decisions, "_send_request", return_value=json.dumps(body).encode("utf-8")):
                    self.assertEqual(self.run_cli("--confirm-billable", "--confirm-data-redacted"), 2)

    def test_input_limits_and_symlink_inputs_are_rejected(self):
        oversized = Path(self.temp_dir.name) / "oversized.txt"
        oversized.write_bytes(b"x" * (decisions.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(decisions.DecisionError, "byte limit"):
            decisions._read_input(str(oversized))

        symlink = Path(self.temp_dir.name) / "link.txt"
        symlink.symlink_to(self.input_path)
        with self.assertRaisesRegex(decisions.DecisionError, "symlink"):
            decisions._read_input(str(symlink))

    def test_credential_like_input_is_blocked_without_echo_or_request(self):
        marker = "Authorization: Bearer test-placeholder-for-local-unit-tests"
        self.input_path.write_text(f"Failed request\n{marker}\n", encoding="utf-8")
        environment = {"DEVOBS_AI_BUDGET_APPROVED": "true", "OPENAI_API_KEY": "test-key"}
        from contextlib import redirect_stderr
        from io import StringIO

        stderr = StringIO()
        with patch.dict(os.environ, environment), patch.object(decisions, "_send_request") as send_request:
            with redirect_stderr(stderr):
                exit_code = self.run_cli("--confirm-billable", "--confirm-data-redacted")
        self.assertEqual(exit_code, 2)
        self.assertIn("line(s) 2", stderr.getvalue())
        self.assertNotIn(marker, stderr.getvalue())
        send_request.assert_not_called()

    def test_explicit_redaction_marker_is_not_treated_as_a_secret(self):
        self.input_path.write_text("Authorization: Bearer <REDACTED>", encoding="utf-8")
        self.assertEqual(decisions._read_input(str(self.input_path)), "Authorization: Bearer <REDACTED>")


if __name__ == "__main__":
    unittest.main()

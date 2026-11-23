"""Behavioral tests for the read-only evaluation CLI.

Every test runs the CLI in-process against local fixtures and asserts exit codes
and JSON output. No network call, credential read or paid inference is involved.
"""

from __future__ import annotations

import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from devobs.ai_evaluation.cli import main
from devobs.ai_evaluation.models import FixtureSet

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples" / "ai_evaluation"
FIXTURES = EXAMPLES / "provider_cases.json"
PRICING = EXAMPLES / "pricing.json"


def _synthetic_token(letter: str) -> str:
    """Build a scanner-recognisable test token at runtime, never as a literal.

    The fragments are not a credential. Assembling the value at runtime keeps
    secret scanners from treating test data as a committed secret while the
    redaction code still sees a realistic credential-like token.
    """
    return "xai-" + letter * 24


def _run_with_stderr(*args: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


def _run(*args: str) -> tuple[int, str]:
    code, output, _ = _run_with_stderr(*args)
    return code, output


class CliTests(unittest.TestCase):
    def test_gate_cli_returns_zero_and_structured_pass(self) -> None:
        code, output = _run(
            "--fixtures", str(FIXTURES), "--pricing", str(PRICING), "--gate")
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(payload["schema_version"], "ai-eval-gate/1.0")
        self.assertEqual(payload["decision"], "PASS")
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["failures"], [])

    def test_report_cli_emits_offline_report(self) -> None:
        code, output = _run("--fixtures", str(FIXTURES), "--pricing", str(PRICING))
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertTrue(payload["offline"])
        self.assertEqual(payload["live_calls"], 0)
        self.assertEqual(len(payload["cases"]), 10)
        self.assertTrue(payload["routing"])
        self.assertEqual(len(payload["configs"]), 2)

    def test_missing_file_fails_closed(self) -> None:
        code, output = _run(
            "--fixtures", "does-not-exist.json", "--pricing", str(PRICING))
        payload = json.loads(output)
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "INVALID")
        self.assertLessEqual(len(payload["reason"]), 120)

    def test_malformed_json_fails_closed_without_echo(self) -> None:
        secret_like = _synthetic_token("A")
        malformed = '{"version":"x","note":"' + secret_like + '","cases":['
        original_read_text = pathlib.Path.read_text

        def _fixtures_read_text(path: pathlib.Path, *args: object, **kwargs: object) -> str:
            if path.name == "malformed.json":
                return malformed
            return original_read_text(path, *args, **kwargs)

        with patch.object(pathlib.Path, "read_text", _fixtures_read_text):
            code, output, errors = _run_with_stderr(
                "--fixtures", "malformed.json", "--pricing", str(PRICING))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["status"], "INVALID")
        self.assertNotIn(secret_like, output)
        self.assertNotIn(secret_like, errors)

    def test_unknown_scenario_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
            raw["cases"] = [dict(raw["cases"][0], scenario="send_email")]
            path = pathlib.Path(tmp) / "unknown.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            code, output = _run(
                "--fixtures", str(path), "--pricing", str(PRICING), "--gate")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["reason"], "invalid_scenario")

    def test_report_redacts_credential_like_prompt_content(self) -> None:
        secret_like = _synthetic_token("B")
        raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
        raw["cases"][0]["prompt"] = "Classify " + secret_like + " safely."
        redacted_fixture = FixtureSet.from_mapping(raw)
        with patch("devobs.ai_evaluation.cli.FixtureSet.from_mapping",
                   return_value=redacted_fixture):
            code, output, errors = _run_with_stderr(
                "--fixtures", str(FIXTURES), "--pricing", str(PRICING))
        self.assertEqual(code, 0)
        self.assertNotIn(secret_like, output)
        self.assertNotIn(secret_like, errors)
        self.assertIn("[REDACTED]", output)

    def test_gate_cli_reports_blocked_with_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
            raw["cases"][0]["expected_outcome"] = "TIMEOUT"
            path = pathlib.Path(tmp) / "mismatch.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            code, output = _run(
                "--fixtures", str(path), "--pricing", str(PRICING), "--gate")
        payload = json.loads(output)
        self.assertEqual(code, 1)
        self.assertEqual(payload["decision"], "BLOCKED")
        self.assertTrue(payload["failures"])


if __name__ == "__main__":
    unittest.main()

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
from contextlib import redirect_stdout
from unittest.mock import patch

from devobs.ai_evaluation.cli import main

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples" / "ai_evaluation"
FIXTURES = EXAMPLES / "provider_cases.json"
PRICING = EXAMPLES / "pricing.json"


def _run(*args: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(args))
    return code, buffer.getvalue()

_ORIGINAL_READ_TEXT = pathlib.Path.read_text


def _run_with_virtual_fixture(contents: str, filename: str) -> tuple[int, str]:
    """Feed synthetic JSON to the CLI without writing secret-shaped samples to disk."""
    virtual_path = pathlib.Path(filename)

    def read_text(path: pathlib.Path, *args: object, **kwargs: object) -> str:
        if path == virtual_path:
            return contents
        return _ORIGINAL_READ_TEXT(path, *args, **kwargs)

    with patch.object(pathlib.Path, "read_text", new=read_text):
        return _run("--fixtures", str(virtual_path), "--pricing", str(PRICING))


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
        secret_like = "xai-" + "A" * 24
        contents = '{"version":"x","note":"' + secret_like + '","cases":['
        code, output = _run_with_virtual_fixture(contents, "virtual-malformed.json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["status"], "INVALID")
        self.assertNotIn(secret_like, output)

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
        secret_like = "xai-" + "B" * 24
        raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
        raw["cases"][0]["prompt"] = "Classify " + secret_like + " safely."
        code, output = _run_with_virtual_fixture(
            json.dumps(raw), "virtual-redaction.json")
        self.assertEqual(code, 0)
        self.assertNotIn(secret_like, output)
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

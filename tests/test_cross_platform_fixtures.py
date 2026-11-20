"""Cross-platform contracts for byte-pinned repository fixtures."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]

BYTE_PINNED_FIXTURES = (
    "tests/fixtures/ai-evals/decisions-triage.jsonl",
    "tests/fixtures/intelligence_eval_cases.json",
    "tests/fixtures/intelligence_eval_cases_v2.json",
    "deploy/keycloak-hosted/render.yaml",
)


class CrossPlatformFixtureTests(unittest.TestCase):
    def test_byte_pinned_fixtures_are_checked_out_with_lf_eol(self) -> None:
        for relative in BYTE_PINNED_FIXTURES:
            with self.subTest(path=relative):
                result = subprocess.run(
                    ["git", "check-attr", "text", "eol", "--", relative],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("text: set", result.stdout)
                self.assertIn("eol: lf", result.stdout)

    def test_byte_pinned_fixtures_have_no_crlf_in_the_worktree(self) -> None:
        for relative in BYTE_PINNED_FIXTURES:
            with self.subTest(path=relative):
                raw = (ROOT / relative).read_bytes()
                self.assertNotIn(b"\r\n", raw)


if __name__ == "__main__":
    unittest.main()

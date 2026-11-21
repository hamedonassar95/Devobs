"""CLI behavior for the offline integration control plane."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devobs.integration_control.__main__ import main

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/integration_control
    import helpers as h


class ControlPlaneCliTests(unittest.TestCase):
    def _run(self, document: object, output_format: str = "json") -> tuple[int, str]:
        with tempfile.TemporaryDirectory(prefix="integration-control-cli-") as folder:
            path = Path(folder) / "snapshot.json"
            path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(["--input", str(path), "--format", output_format])
            return code, stream.getvalue()

    def test_valid_snapshot_exit_zero_and_json_report(self) -> None:
        code, output = self._run(h.snapshot())

        report = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(report["decision"], "PROCEED_TO_HUMAN_REVIEW")
        self.assertFalse(report["merge_authorized"])

    def test_malformed_document_fails_closed(self) -> None:
        code, output = self._run({"not": "a snapshot"})

        report = json.loads(output)
        self.assertEqual(code, 3)
        self.assertEqual(report["decision"], "INVALID")
        self.assertEqual(report["findings"][0]["code"], "invalid_snapshot_fields")

    def test_markdown_output_includes_separate_check_counts(self) -> None:
        _code, output = self._run(h.snapshot(), output_format="markdown")

        self.assertIn("## Checks", output)
        self.assertIn("Passed:", output)
        self.assertIn("Failed: none", output)
        self.assertIn("Skipped: none", output)


if __name__ == "__main__":
    unittest.main()

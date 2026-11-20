"""Regression coverage for Python source outside scripts/ and tests/."""
from collections import Counter
import os
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import patch

from scripts import assess_change

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


class PythonSourceCoverageTests(unittest.TestCase):
    def select(self, changed_path):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            summary = Path(directory) / "summary"
            with (
                patch.dict(os.environ, {
                    "GITHUB_OUTPUT": str(output),
                    "GITHUB_STEP_SUMMARY": str(summary),
                }, clear=True),
                patch.object(assess_change, "event_changed_paths", return_value=([changed_path], "a" * 40)),
                patch.object(assess_change, "changed_line_count", return_value=1),
                patch.object(assess_change, "recent_touch_counts", return_value=Counter()),
            ):
                assess_change.main()
            return dict(line.split("=", 1) for line in output.read_text().splitlines())

    def test_tools_python_file_is_classified_as_python(self):
        self.assertTrue(assess_change.is_python(PurePosixPath("tools/graphify/common.py")))

    def test_tools_only_change_selects_python_ci(self):
        result = self.select("tools/graphify/common.py")
        self.assertEqual(result["python_required"], "true")
        self.assertNotEqual(result["risk_level"], "high")

    def test_ci_compiles_and_scans_tools_directory(self):
        self.assertIn("'[\"scripts\", \"tests\", \"tools\"]'", WORKFLOW)
        self.assertIn("python3 -m bandit -r scripts tools", WORKFLOW)


if __name__ == "__main__":
    unittest.main()

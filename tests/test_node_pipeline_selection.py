"""Exercise CI outputs for fixture-only local intelligence changes."""
from collections import Counter
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import assess_change


class NodePipelineSelectionTests(unittest.TestCase):
    def selection(self, changed_path):
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

    def test_each_pipeline_fixture_selects_node_even_without_code_or_high_risk(self):
        for path in (
            "examples/integrations/synthetic-ci-events.jsonl",
            "tests/fixtures/intelligence_eval_cases.json",
        ):
            with self.subTest(path=path):
                result = self.selection(path)
                self.assertEqual(result["node_required"], "true")
                self.assertNotEqual(result["risk_level"], "high")
                self.assertEqual(result["console_required"], "false")

    def test_unrelated_document_does_not_select_node(self):
        self.assertEqual(self.selection("docs/AI_LOCAL_DASHBOARD.md")["node_required"], "false")


if __name__ == "__main__":
    unittest.main()

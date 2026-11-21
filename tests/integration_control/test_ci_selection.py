"""CI selection contract for integration-control source files."""

from __future__ import annotations

import unittest
from pathlib import Path, PurePosixPath

from scripts.assess_change import is_python

ROOT = Path(__file__).resolve().parents[2]


class CiSelectionTests(unittest.TestCase):
    def test_devobs_python_files_select_python_checks(self) -> None:
        self.assertTrue(is_python(PurePosixPath("devobs/integration_control/engine.py")))
        self.assertTrue(is_python(PurePosixPath("tests/integration_control/test_cli.py")))

    def test_workflow_compiles_and_scans_devobs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn('"devobs"]', workflow)
        self.assertIn("bandit -r scripts tools devobs", workflow)


if __name__ == "__main__":
    unittest.main()

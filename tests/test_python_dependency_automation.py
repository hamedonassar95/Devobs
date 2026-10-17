from pathlib import Path
import re
import unittest
from pathlib import PurePosixPath

from scripts.assess_change import is_python_dependency


ROOT = Path(__file__).resolve().parents[1]


class PythonDependencyAutomationTests(unittest.TestCase):
    def test_bandit_is_declared_and_used_by_ci(self):
        requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertRegex(requirements, r"(?m)^bandit==[0-9][^\s]*$")
        self.assertIn("cache-dependency-path: requirements-dev.txt", workflow)
        self.assertIn(
            "python3 -m pip install --disable-pip-version-check -r requirements-dev.txt",
            workflow,
        )
        self.assertIn("python3 -m bandit -r scripts -x scripts/check_site.py", workflow)

    def test_dependabot_updates_python_dependencies_weekly(self):
        config = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")

        self.assertRegex(
            config,
            re.compile(
                r'(?ms)^  - package-ecosystem: "pip"\s+'
                r'directory: "/"\s+'
                r'schedule:\s+interval: "weekly"(?:\s|$)'
            ),
        )

    def test_dependency_manifest_changes_select_python_ci(self):
        self.assertTrue(is_python_dependency(PurePosixPath("requirements-dev.txt")))


if __name__ == "__main__":
    unittest.main()

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
        self.assertRegex(requirements, r"(?m)^pip==[0-9][^\s]*$")
        self.assertIn("cache-dependency-path: requirements-dev.lock", workflow)
        self.assertIn(
            "python3 -m pip install --disable-pip-version-check --require-hashes -r requirements-dev.lock",
            workflow,
        )
        self.assertIn("python3 -m bandit -r scripts -x scripts/check_site.py", workflow)
        self.assertIn("pip-audit --requirement requirements-dev.lock", workflow)
        self.assertIn("pip-audit --requirement requirements-api.lock", workflow)

    def test_api_and_security_locks_cover_direct_dependencies_with_hashes(self):
        for source_name, lock_name in (
            ("requirements-api.txt", "requirements-api.lock"),
            ("requirements-dev.txt", "requirements-dev.lock"),
        ):
            with self.subTest(lock=lock_name):
                source = (ROOT / source_name).read_text(encoding="utf-8")
                lock = (ROOT / lock_name).read_text(encoding="utf-8")
                lock_entries = {
                    line.strip().rstrip("\\").strip().lower()
                    for line in lock.splitlines()
                    if line and not line.startswith(("#", " ", "\t"))
                }
                for line in source.splitlines():
                    match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s]+)$", line)
                    if match:
                        package = match.group(1).lower().replace("_", "-")
                        version = match.group(2)
                        self.assertIn(f"{package}=={version}", lock_entries)

                requirement_start = re.compile(r"^[A-Za-z0-9_.-]+==")
                lines = lock.splitlines()
                found = 0
                for index, line in enumerate(lines):
                    if not requirement_start.match(line):
                        continue
                    found += 1
                    stanza = []
                    for candidate in lines[index + 1:]:
                        if not candidate.strip() or requirement_start.match(candidate) or candidate.startswith("#"):
                            break
                        stanza.append(candidate)
                    self.assertRegex("\n".join(stanza), r"--hash=sha256:[0-9a-f]{64}")
                self.assertGreater(found, 0)

    def test_python_ci_consumes_hash_locked_files_and_dependency_changes_select_it(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        reusable = (ROOT / ".github/workflows/reusable-python-ci.yml").read_text(encoding="utf-8")
        self.assertIn("requirements_file: requirements-api.lock", ci)
        self.assertIn("requirements-api.lock", ci)
        self.assertIn("--require-hashes", reusable)
        for name in (
            "requirements-api.txt", "requirements-dev.txt",
            "requirements-api.lock", "requirements-dev.lock",
        ):
            with self.subTest(path=name):
                self.assertTrue(is_python_dependency(PurePosixPath(name)))

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

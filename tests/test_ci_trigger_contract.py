import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
EVENTS = WORKFLOW.split("\npermissions:", 1)[0]


class CITriggerContractTests(unittest.TestCase):
    def test_ci_runs_for_all_pushes_and_pull_requests(self):
        self.assertIn("on:\n  push:\n  pull_request:\n", EVENTS)
        self.assertNotIn("branches:", EVENTS)

    def test_production_release_remains_main_only(self):
        release = WORKFLOW.split("  production-release:\n", 1)[1].split("\n  controlled-incident-drill:", 1)[0]
        self.assertIn("github.ref == 'refs/heads/main'", release)
        self.assertIn("needs.validate.result == 'success'", release)


if __name__ == "__main__":
    unittest.main()

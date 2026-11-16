"""Contract tests for the opt-in read-only portfolio CI/AI-7 GitHub workflow."""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/portfolio-ai7-manual.yml"


def read_workflow():
    if yaml is not None:
        return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    ruby = shutil.which("ruby")
    if ruby is None:
        raise RuntimeError("A YAML parser is required (PyYAML or Ruby/Psych).")
    script = (
        'require "yaml"; require "json"; '
        'STDOUT.write(JSON.generate(YAML.load_file(ARGV.fetch(0), aliases: false)))'
    )
    result = subprocess.run(
        [ruby, "-e", script, str(WORKFLOW)],
        capture_output=True, text=True, check=True, timeout=8,
    )
    return json.loads(result.stdout)


class PublicPortfolioAI7WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_workflow()
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.job = cls.data["jobs"]["observe"]
        cls.steps = cls.job["steps"]

    def test_only_human_invoked_on_protected_main(self):
        self.assertEqual(self.data.get("on", self.data.get("true")), {"workflow_dispatch": {}})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.job["runs-on"], "ubuntu-24.04")
        self.assertEqual(str(self.job["timeout-minutes"]), "6")
        self.assertEqual(str(self.data["concurrency"]["cancel-in-progress"]).lower(), "false")

    def test_minimal_permissions_and_no_secret_or_provider_access(self):
        self.assertEqual(self.data["permissions"], {"contents": "read"})
        self.assertEqual(self.job["permissions"], {"contents": "read"})
        for forbidden in (
            "secrets.", "id-token:", "gh auth", "terraform apply", "workflow_run",
            "schedule:", "pull_request_target", "curl ", "repository_dispatch",
        ):
            self.assertNotIn(forbidden, self.source)
        self.assertTrue(all("github-script@" not in s.get("uses", "")
                            for s in self.steps))

    def test_actions_are_pinned_and_checkout_cannot_persist_credentials(self):
        pins = [
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1",
            "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9",
        ]
        uses = [s["uses"] for s in self.steps if "uses" in s]
        self.assertEqual(uses, pins)
        self.assertTrue(all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", p) for p in uses))
        self.assertEqual(str(self.steps[0]["with"]["persist-credentials"]).lower(), "false")
        self.assertEqual(self.steps[1]["with"]["node-version"], "24")

    def test_artifact_is_sanitized_and_incomplete_evidence_fails_closed(self):
        observer = next(s for s in self.steps if s.get("id") == "observe")
        run = observer["run"]
        self.assertIn("node scripts/portfolio_ci_ai7_live.mjs", run)
        self.assertIn("node scripts/portfolio_ai7_action_report.mjs", run)
        self.assertIn('if (( outcome > 1 )); then', run)
        self.assertIn('echo "valid_report=true"', run)
        upload = next(s for s in self.steps if "upload-artifact@" in s.get("uses", ""))
        self.assertEqual(upload["if"], "steps.observe.outputs.valid_report == 'true'")
        self.assertEqual(str(upload["with"]["retention-days"]), "7")
        self.assertEqual(upload["with"]["if-no-files-found"], "error")
        self.assertEqual(upload["with"]["path"], "${{ runner.temp }}/portfolio-public-ci-ai7.json")
        failed = self.steps[-1]
        self.assertIn("observation_exit != '0'", failed["if"])
        self.assertIn("exit 1", failed["run"])


if __name__ == "__main__":
    unittest.main()

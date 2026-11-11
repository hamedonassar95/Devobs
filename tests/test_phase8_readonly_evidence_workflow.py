"""Exercise the Phase 8 read-only workflow's incident-number handling."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - GitHub's Ubuntu runner includes Ruby/Psych.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/phase8-readonly-evidence.yml"


class Phase8ReadOnlyEvidenceWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if yaml is not None:
            cls.workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        else:
            ruby = shutil.which("ruby")
            if ruby is None:
                raise RuntimeError("A YAML parser is required: use PyYAML or runner-provided Ruby/Psych.")
            parser = (
                'require "yaml"; require "json"; '
                'data = YAML.load_file(ARGV.fetch(0), aliases: false); '
                'data["on"] = data.delete(true) if data.key?(true); '
                'STDOUT.write(JSON.generate(data))'
            )
            result = subprocess.run(
                [ruby, "-e", parser, str(WORKFLOW_PATH)],
                capture_output=True,
                text=True,
                check=True,
            )
            cls.workflow = json.loads(result.stdout)

        steps = cls.workflow["jobs"]["collect"]["steps"]
        evidence = next(step for step in steps if step.get("id") == "evidence")
        cls.evidence_script = evidence["with"]["script"]
        cls.evidence_env = evidence.get("env", {})

    def test_incident_number_is_passed_as_environment_data_not_script_source(self):
        self.assertEqual(self.evidence_env.get("INCIDENT_NUMBER"), "${{ inputs.incident_number }}")
        self.assertNotIn("${{ inputs.incident_number }}", self.evidence_script)
        self.assertIn("process.env.INCIDENT_NUMBER", self.evidence_script)
        self.assertIn("Number.isSafeInteger(Number(rawIssueNumber))", self.evidence_script)

    def _run_script(self, incident_number):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required to execute the workflow's github-script body.")
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment = {
                "PATH": str(Path(node).parent),
                "INCIDENT_NUMBER": incident_number,
                "GITHUB_WORKSPACE": temporary_directory,
            }
            harness = f"""
            const calls = [];
            let failure = null;
            const context = {{ repo: {{ owner: "hamedonassar95", repo: "Devobs" }} }};
            const github = {{
              rest: {{ issues: {{
                get: async (args) => {{ calls.push(args.issue_number); return {{ data: {{ body: "", title: "incident: synthetic", state: "open" }} }}; }},
                listComments: async () => ({{ data: [] }})
              }} }},
              paginate: async () => []
            }};
            const core = {{
              setFailed: (message) => {{ failure = message; }},
              summary: {{
                addHeading() {{ return this; }},
                addCodeBlock() {{ return this; }},
                addRaw() {{ return this; }},
                async write() {{ return undefined; }}
              }}
            }};
            (async () => {{
              try {{
                await (async () => {{
            {self.evidence_script}
                }})();
              }} catch (error) {{
                failure = `unexpected error: ${{error.message}}`;
              }}
              process.stdout.write(JSON.stringify({{
                failure,
                calls,
                injected: process.env.PWNED || null
              }}));
            }})();
            """
            result = subprocess.run(
                [node, "-e", harness],
                cwd=temporary_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = Path(temporary_directory) / "phase8-evidence.json"
            artifact_text = artifact.read_text(encoding="utf-8") if artifact.exists() else None
            return json.loads(result.stdout), artifact_text

    def test_valid_positive_integer_fetches_only_that_incident(self):
        result, artifact_text = self._run_script("42")
        self.assertIsNone(result["failure"])
        self.assertEqual(result["calls"], [42])
        self.assertEqual(json.loads(artifact_text)["issue_number"], 42)

    def test_expression_payload_is_rejected_before_api_access(self):
        payload = "${(() => { process.env.PWNED = 'yes'; return 42; })()}"
        result, artifact_text = self._run_script(payload)
        self.assertEqual(result["failure"], "incident_number must be a positive integer")
        self.assertEqual(result["calls"], [])
        self.assertIsNone(result["injected"])
        self.assertIsNone(artifact_text)

    def test_unsafe_integer_is_rejected_before_api_access(self):
        result, artifact_text = self._run_script("9007199254740992")
        self.assertEqual(result["failure"], "incident_number must be a positive integer")
        self.assertEqual(result["calls"], [])
        self.assertIsNone(artifact_text)


if __name__ == "__main__":
    unittest.main()

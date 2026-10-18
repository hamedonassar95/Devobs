"""Validate the manually dispatched Vercel staging workflow as YAML."""

from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

try:
    import yaml
except ImportError:  # pragma: no cover - GitHub's Ubuntu runner includes Ruby/Psych.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "vercel-stage-test.yml"


class VercelStageTestWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if yaml is not None:
            cls.workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
            return

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

    def test_only_workflow_dispatch_is_configured(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_dispatch"})
        inputs = self.workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(set(inputs), {"source_ref"})
        self.assertEqual(str(inputs["source_ref"]["required"]).lower(), "true")

    def test_staging_job_uses_the_dedicated_environment(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(len(jobs), 1)
        job = next(iter(jobs.values()))
        self.assertEqual(job["environment"]["name"], "vercel-staging")

    def test_source_ref_is_validated_as_a_full_sha(self):
        steps = next(iter(self.workflow["jobs"].values()))["steps"]
        commands = "\n".join(step.get("run", "") for step in steps)
        self.assertRegex(commands, re.compile(r"\^\[0-9a-f\]\{40\}\$"))

    def test_staging_flow_is_preview_only_and_uses_alternate_config(self):
        steps = next(iter(self.workflow["jobs"].values()))["steps"]
        cli_commands = [
            step.get("run", "")
            for step in steps
            if "npx --yes vercel@" in step.get("run", "")
        ]
        project_cli_commands = [command for command in cli_commands if " api " not in command]
        self.assertGreaterEqual(len(project_cli_commands), 3)
        self.assertTrue(all("--local-config deploy/vercel-staging.json" in command for command in project_cli_commands))
        self.assertTrue(any("deploy --prebuilt --local-config" in command for command in project_cli_commands))
        self.assertFalse(any(re.search(r"\bvercel(?:@[A-Za-z0-9._-]+)?\s+(?:promote|rollback)\b", c) for c in project_cli_commands))
        self.assertFalse(any(re.search(r"\bvercel(?:@[A-Za-z0-9._-]+)?\s+deploy\b[^\n]*\s--prod(?:\s|$)", c) for c in project_cli_commands))

    def test_api_preflight_resolves_the_project_account_context(self):
        steps = next(iter(self.workflow["jobs"].values()))["steps"]
        step = next(step for step in steps if step.get("name") == "Confirm Vercel API access to the configured project")
        command = step["run"]
        self.assertIn('/v9/projects/${VERCEL_PROJECT_ID}', command)
        self.assertNotIn('teamId=', command)
        self.assertIn('project.get("id") != expected_id', command)
        self.assertIn('account_id = project.get("accountId")', command)
        self.assertIn('output.write(f"org_id={account_id}', command)
        self.assertEqual(step.get("id"), "vercel_api")

    def test_vercel_secrets_are_not_in_job_level_environment(self):
        job = next(iter(self.workflow["jobs"].values()))
        env = job.get("env", {})
        secrets = {"VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID", "VERCEL_AUTOMATION_BYPASS_SECRET"}
        self.assertFalse(secrets.intersection(env))

    def test_each_vercel_cli_step_uses_step_scoped_staging_credentials(self):
        job = next(iter(self.workflow["jobs"].values()))
        required = {
            "VERCEL_TOKEN": "${{ secrets.VERCEL_TOKEN }}",
            "VERCEL_PROJECT_ID": "${{ secrets.VERCEL_PROJECT_ID }}",
        }
        cli_steps = [
            step for step in job["steps"]
            if "npx --yes vercel@" in step.get("run", "") and " api " not in step.get("run", "")
        ]
        self.assertGreaterEqual(len(cli_steps), 3)
        for step in cli_steps:
            self.assertEqual({key: step.get("env", {}).get(key) for key in required}, required)
            self.assertEqual(step.get("env", {}).get("VERCEL_ORG_ID"), "${{ steps.vercel_api.outputs.org_id }}")

    def test_alternate_config_defines_staging_build_and_output(self):
        config = json.loads((ROOT / "deploy" / "vercel-staging.json").read_text(encoding="utf-8"))
        self.assertEqual(config["outputDirectory"], "_site")
        self.assertEqual(
            config["buildCommand"],
            "python3 scripts/stage_site.py --source-dir candidate --output-dir _site",
        )

    def test_root_vercel_config_is_not_required(self):
        self.assertTrue((ROOT / "deploy" / "vercel-staging.json").is_file())
        self.assertFalse((ROOT / "vercel.json").exists())


if __name__ == "__main__":
    unittest.main()

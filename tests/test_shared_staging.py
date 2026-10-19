"""Behavioral contract for the shared Pages and Vercel staging output."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE_SCRIPT = ROOT / "scripts" / "stage_site.py"


class SharedStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = Path(self.temp_dir.name)
        self.source = self.workspace / "candidate"
        self.source.mkdir()
        (self.source / "index.html").write_text("<h1>fixture</h1>", encoding="utf-8")
        assets = self.source / "assets"
        assets.mkdir()
        (assets / "site.css").write_text("body{}", encoding="utf-8")
        (assets / ".private.css").write_text("hidden{}", encoding="utf-8")
        self.output = self.workspace / "_site"
        self.source_sha = "a" * 40

    def run_stage(self, source):
        env = os.environ.copy()
        env["GITHUB_WORKSPACE"] = str(self.workspace)
        return subprocess.run(
            [
                sys.executable,
                str(STAGE_SCRIPT),
                "--source-dir",
                str(source),
                "--output-dir",
                str(self.output),
                "--source-sha",
                self.source_sha,
            ],
            cwd=self.workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_stages_exact_file_list_and_source_sha(self):
        result = self.run_stage(self.source)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        files = {
            path.relative_to(self.output).as_posix()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        self.assertEqual(files, {"index.html", "assets/site.css", "deployment.json"})
        manifest = json.loads((self.output / "deployment.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_sha"], self.source_sha)

    def test_cli_fails_closed_for_missing_source(self):
        result = self.run_stage(self.workspace / "missing-candidate")

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Site staging failed:", result.stderr)
        self.assertFalse(self.output.exists())

    def test_pages_and_rollback_use_the_shared_validated_output(self):
        workflow = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

        self.assertEqual(workflow.count("python3 scripts/stage_site.py"), 2)
        self.assertEqual(workflow.count("SITE_ROOT=_site python3 scripts/check_site.py"), 2)
        self.assertEqual(workflow.count("path: _site"), 2)
        self.assertNotIn("cp index.html _site/index.html", workflow)


if __name__ == "__main__":
    unittest.main()

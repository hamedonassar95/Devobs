"""Behavioral contract for the shared Pages and Vercel staging output."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
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
        (self.source / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Fixture</title></head><body><main><h1>fixture</h1></main></body></html>",
            encoding="utf-8",
        )
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

    def run_site_check(self):
        env = os.environ.copy()
        env["SITE_ROOT"] = str(self.output)
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_site.py")],
            cwd=self.workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    def create_valid_staged_artifact(self):
        self.output.mkdir(exist_ok=True)
        (self.output / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Fixture</title></head><body><main><h1>fixture</h1></main></body></html>",
            encoding="utf-8",
        )
        (self.output / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "source_sha": self.source_sha}), encoding="utf-8"
        )
        (self.output / "assets").mkdir(exist_ok=True)
        (self.output / "assets" / "site.css").write_text("body{}", encoding="utf-8")

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
        check = self.run_site_check()
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("Page contract and HTTP smoke checks passed.", check.stdout)

    def test_cli_fails_closed_for_missing_source(self):
        result = self.run_stage(self.workspace / "missing-candidate")

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Site staging failed:", result.stderr)
        self.assertFalse(self.output.exists())

    def test_ci_site_contract_stages_validates_and_previews_the_same_output(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("  site-contract:\n", 1)[1].split("\n  container-build:", 1)[0]

        self.assertEqual(job.count("git rev-parse HEAD"), 1)
        self.assertIn("=~ ^[a-f0-9]{40}$", job)
        self.assertIn('echo "SITE_SOURCE_SHA=$commit_sha" >> "$GITHUB_ENV"', job)
        stage_command = (
            'python3 scripts/stage_site.py --source-dir . --output-dir _site '
            '--source-sha "$SITE_SOURCE_SHA"'
        )
        stage_at = job.index(stage_command)
        check_at = job.index("SITE_ROOT=_site python3 scripts/check_site.py")
        self.assertLess(job.index("git rev-parse HEAD"), stage_at)
        self.assertLess(stage_at, check_at)
        self.assertIn('path: _site/', job)
        self.assertNotIn("_preview", job)
        self.assertNotIn("cp index.html", job)

    def test_pages_and_rollback_use_the_shared_validated_output(self):
        workflow = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

        self.assertEqual(workflow.count("python3 scripts/stage_site.py"), 1)
        self.assertEqual(workflow.count("SITE_ROOT=_site python3 scripts/check_site.py"), 2)
        self.assertEqual(workflow.count("path: _site"), 3)
        self.assertNotIn("cp index.html _site/index.html", workflow)

    def test_main_pages_release_downloads_only_the_same_run_validated_artifact(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
        site_job = ci.split("  site-contract:\n", 1)[1].split("\n  container-build:", 1)[0]
        deploy_job = release.split("  deploy:\n", 1)[1].split("\n  verify:", 1)[0]

        artifact_name = "validated-site-main-${{ github.run_id }}"
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", site_job)
        self.assertIn(f"name: {artifact_name}", site_job)
        self.assertIn("path: _site/", site_job)
        self.assertIn("if-no-files-found: error", site_job)
        self.assertLess(
            site_job.index("SITE_ROOT=_site python3 scripts/check_site.py"),
            site_job.index("Upload validated staged site for main Pages release"),
        )
        self.assertIn(f"name: {artifact_name}", deploy_job)
        self.assertIn("path: _site", deploy_job)
        self.assertIn("actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333", deploy_job)
        self.assertNotIn("python3 scripts/stage_site.py", deploy_job)
        self.assertIn("needs.validate.result == 'success'", ci.split("  production-release:\n", 1)[1])

        normal_deploy = release.split("  deploy:\n", 1)[1].split("\n  verify:", 1)[0]
        rollback_deploy = release.split("  rollback-deploy:\n", 1)[1]
        self.assertIn("actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333", normal_deploy)
        self.assertIn("python3 scripts/stage_site.py", rollback_deploy)
        self.assertIn("SITE_ROOT=_site python3 scripts/check_site.py", normal_deploy)
        self.assertIn("SITE_ROOT=_site python3 scripts/check_site.py", rollback_deploy)

    def test_main_artifact_reference_survives_partial_and_full_reruns(self):
        staged = self.run_stage(self.source)
        self.assertEqual(staged.returncode, 0, staged.stdout + staged.stderr)
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        pages = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
        site_job = ci.split("  site-contract:\n", 1)[1].split("\n  container-build:", 1)[0]
        deploy_job = pages.split("  deploy:\n", 1)[1].split("\n  verify:", 1)[0]
        producer = site_job.split("      - name: Upload validated staged site for main Pages release\n", 1)[1].split(
            "      - name:", 1
        )[0]
        consumer = deploy_job.split("      - name: Download validated CI site artifact from this workflow run\n", 1)[1].split(
            "      - name:", 1
        )[0]

        def artifact_template(step):
            return next(line.strip().removeprefix("name: ") for line in step.splitlines() if "name: validated-site-main-" in line)

        def artifact_name(template, run_id, attempt):
            return template.replace("${{ github.run_id }}", str(run_id)).replace(
                "${{ github.run_attempt }}", str(attempt)
            )

        producer_template = artifact_template(producer)
        consumer_template = artifact_template(consumer)
        producer_attempt_1 = artifact_name(producer_template, 73142, 1)
        consumer_attempt_2 = artifact_name(consumer_template, 73142, 2)
        files = sorted(path.relative_to(self.output).as_posix() for path in self.output.rglob("*") if path.is_file())
        artifacts = {producer_attempt_1: files}

        # A partial rerun skips the successful producer but increments the consumer attempt.
        self.assertEqual(producer_attempt_1, consumer_attempt_2)
        self.assertEqual(artifacts[consumer_attempt_2], ["assets/site.css", "deployment.json", "index.html"])
        self.assertNotEqual(consumer_attempt_2, artifact_name(consumer_template, 73143, 2))
        with self.assertRaises(KeyError):
            {}[consumer_attempt_2]

        # A full rerun can replace the same run-scoped artifact instead of receiving a 409.
        self.assertNotIn("github.run_attempt", producer_template)
        self.assertNotIn("github.run_attempt", consumer_template)
        self.assertIn("overwrite: true", producer)
        self.assertIn("if-no-files-found: error", producer)
        self.assertIn("retention-days: 7", producer)
        self.assertNotIn("run-id:", consumer)
        self.assertNotIn("github-token:", consumer)
        full_rerun_name = artifact_name(producer_template, 73142, 2)
        self.assertEqual(full_rerun_name, producer_attempt_1)

        def upload(name, contents, overwrite):
            if name in artifacts and not overwrite:
                raise FileExistsError("artifact name collision (409)")
            artifacts[name] = contents

        upload(full_rerun_name, files, overwrite="overwrite: true" in producer)
        self.assertEqual(artifacts[producer_attempt_1], files)

    def test_downloaded_pages_artifact_validator_accepts_exact_staged_fixture(self):
        self.create_valid_staged_artifact()
        workflow = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Validate downloaded CI artifact\n", 1)[1].split(
            "      - name:", 1
        )[0]
        run_body = block.split("        run: |\n", 1)[1].split("          SITE_ROOT=_site python3 scripts/check_site.py", 1)[0]
        validator = textwrap.dedent("\n".join(line[10:] for line in run_body.splitlines() if line.startswith("          ")))
        self.assertIn("SITE_ROOT=_site python3 scripts/check_site.py", block)
        result = subprocess.run(
            ["bash", "-e", "-u", "-o", "pipefail", "-c", validator],
            cwd=self.workspace,
            env={**os.environ, "EXPECTED_SOURCE_SHA": self.source_sha},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        check = self.run_site_check()
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_downloaded_pages_artifact_validator_fails_closed_for_missing_or_wrong_artifact(self):
        workflow = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Validate downloaded CI artifact\n", 1)[1].split(
            "      - name:", 1
        )[0]
        run_body = block.split("        run: |\n", 1)[1].split("          SITE_ROOT=_site python3 scripts/check_site.py", 1)[0]
        validator = textwrap.dedent("\n".join(line[10:] for line in run_body.splitlines() if line.startswith("          ")))

        def run_validator():
            return subprocess.run(
                ["bash", "-e", "-u", "-o", "pipefail", "-c", validator],
                cwd=self.workspace,
                env={**os.environ, "EXPECTED_SOURCE_SHA": self.source_sha},
                capture_output=True,
                text=True,
                check=False,
            )

        missing = run_validator()
        self.assertNotEqual(missing.returncode, 0)

        self.output.mkdir()
        (self.output / "index.html").write_text("fixture", encoding="utf-8")
        (self.output / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "source_sha": "b" * 40}), encoding="utf-8"
        )
        wrong_sha = run_validator()
        self.assertNotEqual(wrong_sha.returncode, 0)

        (self.output / "deployment.json").write_text(
            json.dumps({"schema_version": 2, "source_sha": self.source_sha}), encoding="utf-8"
        )
        wrong_manifest = run_validator()
        self.assertNotEqual(wrong_manifest.returncode, 0)

        (self.output / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "source_sha": self.source_sha}), encoding="utf-8"
        )
        (self.output / "assets").write_text("not an assets directory", encoding="utf-8")
        invalid_assets_root = run_validator()
        self.assertNotEqual(invalid_assets_root.returncode, 0)
        (self.output / "assets").unlink()
        (self.output / "assets").mkdir()
        (self.output / "assets" / "site.css").write_text("body{}", encoding="utf-8")
        (self.output / "unexpected.py").write_text("print('not public site data')", encoding="utf-8")
        unexpected_file = run_validator()
        self.assertNotEqual(unexpected_file.returncode, 0)

        (self.output / "unexpected.py").unlink()
        (self.output / "assets" / ".private.css").write_text("hidden{}", encoding="utf-8")
        hidden_file = run_validator()
        self.assertNotEqual(hidden_file.returncode, 0)
        (self.output / "assets" / ".private.css").unlink()
        (self.output / "assets" / "outside-link").symlink_to(self.source / "index.html")
        symlink = run_validator()
        self.assertNotEqual(symlink.returncode, 0)
        (self.output / "assets" / "outside-link").unlink()

        executable_asset = self.output / "assets" / "script.js"
        executable_asset.write_text("/* fixture */", encoding="utf-8")
        executable_asset.chmod(0o755)
        executable = run_validator()
        self.assertNotEqual(executable.returncode, 0)
        executable_asset.unlink()

        (self.output / "index.html").write_text("not valid html", encoding="utf-8")
        invalid_site = self.run_site_check()
        self.assertNotEqual(invalid_site.returncode, 0)


if __name__ == "__main__":
    unittest.main()

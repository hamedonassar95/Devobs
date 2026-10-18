import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_site import stage_site


class StageSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "index.html").write_text("<h1>site</h1>", encoding="utf-8")
        (self.source / "assets").mkdir()
        (self.source / "assets" / "visible.css").write_text("body{}", encoding="utf-8")
        self.output = self.source / "_site"

    def test_stages_site_and_source_manifest(self):
        sha = "a" * 40
        stage_site(self.source, self.output, sha)
        self.assertEqual((self.output / "index.html").read_text(encoding="utf-8"), "<h1>site</h1>")
        self.assertEqual((self.output / "assets" / "visible.css").read_text(encoding="utf-8"), "body{}")
        self.assertEqual(
            json.loads((self.output / "deployment.json").read_text(encoding="utf-8")),
            {"schema_version": 1, "source_sha": sha},
        )

    def test_rejects_asset_symlink_that_points_outside_source(self):
        outside = self.root / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        (self.source / "assets" / "external.txt").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlinks are not allowed"):
            stage_site(self.source, self.output, "a" * 40)

    def test_hidden_files_and_directories_are_not_copied(self):
        (self.source / ".private").write_text("root hidden", encoding="utf-8")
        (self.source / "assets" / ".hidden").write_text("asset hidden", encoding="utf-8")
        hidden_dir = self.source / "assets" / ".cache"
        hidden_dir.mkdir()
        (hidden_dir / "secret.txt").write_text("hidden directory", encoding="utf-8")
        stage_site(self.source, self.output, "a" * 40)
        self.assertFalse((self.output / ".private").exists())
        self.assertFalse((self.output / "assets" / ".hidden").exists())
        self.assertFalse((self.output / "assets" / ".cache").exists())
        self.assertTrue((self.output / "assets" / "visible.css").is_file())

    def test_invalid_sha_fails(self):
        for sha in ("", "abc", "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(sha=sha), self.assertRaisesRegex(ValueError, "40 hexadecimal"):
                stage_site(self.source, self.output, sha)

    def test_empty_index_fails(self):
        (self.source / "index.html").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "index.html must not be empty"):
            stage_site(self.source, self.output, "a" * 40)

    def test_source_dir_option_rejects_path_outside_github_workspace(self):
        workspace = self.root / "workspace"
        workspace.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "index.html").write_text("<h1>candidate</h1>", encoding="utf-8")
        env = os.environ.copy()
        env["GITHUB_WORKSPACE"] = str(workspace)

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "stage_site.py"),
                "--source-dir",
                str(outside),
                "--output-dir",
                str(workspace / "_site"),
                "--source-sha",
                "a" * 40,
            ],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("inside GITHUB_WORKSPACE", result.stderr)

    def test_source_dir_option_rejects_symlink(self):
        workspace = self.root / "workspace"
        workspace.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "index.html").write_text("<h1>candidate</h1>", encoding="utf-8")
        (workspace / "candidate").symlink_to(outside, target_is_directory=True)
        env = os.environ.copy()
        env["GITHUB_WORKSPACE"] = str(workspace)

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "stage_site.py"),
                "--source-dir",
                "candidate",
                "--output-dir",
                str(workspace / "_site"),
                "--source-sha",
                "a" * 40,
            ],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("contains a symlink", result.stderr)

    def test_site_source_dir_environment_stages_candidate_without_overwriting_root(self):
        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "index.html").write_text("<h1>trusted root</h1>", encoding="utf-8")
        candidate = workspace / "candidate"
        candidate.mkdir()
        (candidate / "index.html").write_text("<h1>candidate data</h1>", encoding="utf-8")
        (candidate / "assets").mkdir()
        (candidate / "assets" / "app.css").write_text("body{}", encoding="utf-8")
        source_sha = "b" * 40
        env = os.environ.copy()
        env.update({
            "GITHUB_WORKSPACE": str(workspace),
            "SITE_SOURCE_DIR": "candidate",
            "SITE_SOURCE_SHA": source_sha,
        })

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "stage_site.py"),
                "--output-dir",
                "_site",
            ],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((workspace / "index.html").read_text(encoding="utf-8"), "<h1>trusted root</h1>")
        self.assertEqual((candidate / "index.html").read_text(encoding="utf-8"), "<h1>candidate data</h1>")
        self.assertEqual((workspace / "_site" / "index.html").read_text(encoding="utf-8"), "<h1>candidate data</h1>")
        self.assertEqual(
            json.loads((workspace / "_site" / "deployment.json").read_text(encoding="utf-8")),
            {"schema_version": 1, "source_sha": source_sha},
        )


if __name__ == "__main__":
    unittest.main()

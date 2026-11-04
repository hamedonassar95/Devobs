import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.lint_authored_workflows import list_authored_workflows, run_actionlint


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")


class ActionlintGateTests(unittest.TestCase):
    def test_selects_hand_authored_workflows_and_excludes_generated_locks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow_directory = root / ".github" / "workflows"
            workflow_directory.mkdir(parents=True)
            (workflow_directory / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            (workflow_directory / "release.yaml").write_text("name: Release\n", encoding="utf-8")
            (workflow_directory / "agent.lock.yml").write_text("name: Generated\n", encoding="utf-8")
            (workflow_directory / "agent.md").write_text("# Agent workflow\n", encoding="utf-8")
            nested_directory = workflow_directory / "nested"
            nested_directory.mkdir()
            (nested_directory / "ignored.yml").write_text("name: Nested\n", encoding="utf-8")

            self.assertEqual(
                list_authored_workflows(root),
                [".github/workflows/ci.yml", ".github/workflows/release.yaml"],
            )

    def test_fails_closed_when_workflow_directory_or_sources_are_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaises(FileNotFoundError):
                list_authored_workflows(root)

            (root / ".github" / "workflows").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "No hand-authored"):
                list_authored_workflows(root)

    def test_fails_closed_on_workflow_yaml_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow_directory = root / ".github" / "workflows"
            workflow_directory.mkdir(parents=True)
            (workflow_directory / "linked.yml").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                list_authored_workflows(root)

    def test_invokes_actionlint_with_exact_selected_paths_and_returns_its_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow_directory = root / ".github" / "workflows"
            workflow_directory.mkdir(parents=True)
            (workflow_directory / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            (workflow_directory / "agent.lock.yml").write_text("name: Generated\n", encoding="utf-8")
            captured = {}

            def fake_runner(command, *, cwd, check):
                captured.update(command=command, cwd=cwd, check=check)
                return subprocess.CompletedProcess(command, 7)

            result = run_actionlint("/tmp/actionlint", root, fake_runner)

            self.assertEqual(result, 7)
            self.assertEqual(
                captured["command"],
                ["/tmp/actionlint", "-color=false", ".github/workflows/ci.yml"],
            )
            self.assertEqual(captured["cwd"], root)
            self.assertFalse(captured["check"])

    def test_ci_runs_checksum_pinned_actionlint_only_on_pull_requests_in_security_job(self):
        self.assertIn("  security:\n", WORKFLOW)
        self.assertNotIn("\n  actionlint:\n", WORKFLOW)
        security_job = WORKFLOW.split("  security:\n", 1)[1].split("\n  site-contract:", 1)[0]
        self.assertIn("- name: Install pinned actionlint CLI\n", security_job)
        install_step = security_job.split("- name: Install pinned actionlint CLI\n", 1)[1].split(
            "- name: Lint authored GitHub Actions workflow files\n", 1
        )[0]
        lint_step = security_job.split("- name: Lint authored GitHub Actions workflow files\n", 1)[1].split(
            "- name: Validate AI agent inventory and guardrails\n", 1
        )[0]

        self.assertIn("if: github.event_name == 'pull_request'", install_step)
        self.assertIn('ACTIONLINT_VERSION: "1.7.12"', install_step)
        self.assertIn(
            'ACTIONLINT_SHA256: "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"',
            install_step,
        )
        self.assertIn("sha256sum --check", install_step)
        self.assertLess(install_step.index("sha256sum --check"), install_step.index("tar -xzf"))
        self.assertIn("if: github.event_name == 'pull_request'", lint_step)
        self.assertIn('python3 scripts/lint_authored_workflows.py "$RUNNER_TEMP/actionlint-bin"', lint_step)


if __name__ == "__main__":
    unittest.main()

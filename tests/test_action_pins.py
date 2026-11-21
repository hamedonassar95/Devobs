import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_action_pins
from scripts.check_action_pins import pull_request_target_references


class PullRequestTargetGuardTests(unittest.TestCase):
    def test_repository_workflows_do_not_use_pull_request_target(self):
        self.assertEqual(pull_request_target_references(), [])

    def test_detects_yaml_key_and_event_list_but_ignores_comments_and_markdown(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "active.yml").write_text(
                "on:\n  pull_request_target:\n    types: [opened]\n"
                "# on: [pull_request_target]\n",
                encoding="utf-8",
            )
            (root / "event-list.yaml").write_text(
                "on: [push, pull_request_target]\n",
                encoding="utf-8",
            )
            (root / "commented.yaml").write_text(
                "# pull_request_target:\nname: safe\n",
                encoding="utf-8",
            )
            (root / "example.md").write_text(
                "```yaml\npull_request_target:\n```\n",
                encoding="utf-8",
            )

            self.assertEqual(
                pull_request_target_references(root),
                [(root / "active.yml", 2), (root / "event-list.yaml", 1)],
            )

    def test_fails_closed_when_workflow_directory_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(FileNotFoundError):
                pull_request_target_references(Path(temporary_directory) / "missing")

    def test_checker_returns_failure_before_action_pin_checks(self):
        output = io.StringIO()
        with (
            patch.object(
                check_action_pins,
                "pull_request_target_references",
                return_value=[(Path(".github/workflows/example.yml"), 7)],
            ),
            patch.object(check_action_pins, "mutable_action_references") as pin_check,
            contextlib.redirect_stdout(output),
        ):
            result = check_action_pins.main()

        self.assertEqual(result, 1)
        self.assertIn("example.yml:7", output.getvalue())
        pin_check.assert_not_called()


class VersionCommentGuardTests(unittest.TestCase):
    CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    GITHUB_SCRIPT = "actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3"
    SETUP_NODE = "actions/setup-node@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"

    def test_repository_remote_actions_declare_versions(self):
        self.assertEqual(check_action_pins.missing_version_comments(), [])

    def test_detects_missing_and_non_version_comments_but_allows_exemptions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "missing.yml").write_text(
                f"steps:\n  - uses: {self.CHECKOUT}\n",
                encoding="utf-8",
            )
            (root / "non-version.yml").write_text(
                f"steps:\n  - uses: {self.GITHUB_SCRIPT} # pinned\n",
                encoding="utf-8",
            )
            (root / "valid.yml").write_text(
                "\n".join(
                    [
                        "steps:",
                        f"  - uses: {self.SETUP_NODE} # v7.1.0",
                        "  - uses: ./.github/workflows/reusable.yml",
                        "  - uses: docker://alpine@sha256:"
                        + "a" * 64,
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(
                check_action_pins.missing_version_comments(root),
                [
                    (root / "missing.yml", 2, self.CHECKOUT, ""),
                    (root / "non-version.yml", 2, self.GITHUB_SCRIPT, "pinned"),
                ],
            )

    def test_fails_closed_when_workflow_directory_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(FileNotFoundError):
                check_action_pins.missing_version_comments(
                    Path(temporary_directory) / "missing"
                )

    def test_checker_reports_missing_version_comments(self):
        output = io.StringIO()
        with (
            patch.object(
                check_action_pins,
                "pull_request_target_references",
                return_value=[],
            ),
            patch.object(
                check_action_pins,
                "mutable_action_references",
                return_value=[],
            ),
            patch.object(
                check_action_pins,
                "missing_version_comments",
                return_value=[
                    (
                        Path(".github/workflows/example.yml"),
                        7,
                        self.GITHUB_SCRIPT,
                        "",
                    )
                ],
            ),
            contextlib.redirect_stdout(output),
        ):
            result = check_action_pins.main()

        self.assertEqual(result, 1)
        self.assertIn("example.yml:7", output.getvalue())
        self.assertIn("same-line comment", output.getvalue())


if __name__ == "__main__":
    unittest.main()

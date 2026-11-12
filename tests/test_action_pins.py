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


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the offline advisory task-status report."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import agent_task_status_report as status_report  # noqa: E402

REPO = "hamedonassar95/Devobs"
SHA = "a" * 40
RESTRICTED = ("merge", "deploy", "billing", "production")


def task(task_id, **overrides):
    result = {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": "CODEX",
        "branch": "feature/" + task_id.lower(),
        "affected_files": ["scripts/" + task_id.lower() + ".py"],
        "dependencies": [],
        "status": "planned",
        "previous_status": "none",
        "source_sha": None,
        "verification": {"commands": [], "result": "PENDING", "evidence": ""},
        "pr_reference": None,
        "requested_actions": ["code_change"],
    }
    result.update(overrides)
    return result


def complete(task_id, **overrides):
    values = {
        "status": "complete",
        "previous_status": "evidence_ready",
        "source_sha": SHA,
        "verification": {
            "commands": ["python -m unittest discover -s tests -v"],
            "result": "PASS",
            "evidence": "local offline tests: 12 passed",
        },
        "pr_reference": "#123",
    }
    values.update(overrides)
    return task(task_id, **values)


def manifest(tasks, **overrides):
    result = {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {key: "pending_human" for key in RESTRICTED},
        "tasks": tasks,
    }
    result.update(overrides)
    return result


def write_manifest(root, data):
    path = root / "tasks.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class AgentTaskStatusReportTests(unittest.TestCase):
    def test_report_displays_all_required_fields_and_advisory_label(self):
        data = manifest([
            complete("TASK-001"),
            task("TASK-002", assigned_agent="OPENCODE",
                 dependencies=["TASK-001"], pr_reference="#124"),
        ])
        report = status_report.build_report(data, source_label="tasks.json")
        human = status_report.render_human(report)

        self.assertEqual(report["effective_decision"], "PASS")
        self.assertTrue(report["advisory"])
        for expected in (
            "ADVISORY LOCAL DATA", "TASK-001", "TASK-002", "CODEX", "OPENCODE",
            REPO, "feature/task-001", "feature/task-002", "Status:",
            "Dependencies:", "Blocked:", "PR reference:",
            "Verification evidence state:",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, human)
        self.assertEqual(report["summary"]["tasks"], 2)
        self.assertEqual(report["summary"]["pass_claims"], 1)

    def test_blocked_task_is_visible_even_when_validator_returns_pass(self):
        data = manifest([
            task("TASK-001"),
            task("TASK-002", status="blocked", previous_status="planned",
                 dependencies=["TASK-001"]),
        ])
        fake_validation = {
            "decision": "PASS", "errors": [], "blocked_tasks": [],
            "conflicts": [], "summary": {},
        }
        with patch.object(status_report, "evaluate", return_value=fake_validation):
            report = status_report.build_report(data, source_label="tasks.json")

        self.assertEqual(report["validator_decision"], "PASS")
        self.assertEqual(report["effective_decision"], "BLOCKED")
        blocked = {item["task_id"]: item for item in report["blocked_tasks"]}
        self.assertIn("TASK-002", blocked)
        self.assertIn("manifest_status_blocked", blocked["TASK-002"]["reasons"])
        self.assertIn("unresolved_dependencies", blocked["TASK-002"]["reasons"])
        self.assertEqual(blocked["TASK-002"]["unresolved_dependencies"], ["TASK-001"])
        human = status_report.render_human(report)
        self.assertIn("Blocked tasks:", human)
        self.assertIn("TASK-002", human)
        self.assertIn("unresolved_dependencies", human)

    def test_pass_claim_is_never_presented_as_verified(self):
        report = status_report.build_report(
            manifest([complete("TASK-001")]), source_label="tasks.json"
        )
        human = status_report.render_human(report)
        payload = json.dumps(report, ensure_ascii=True)

        self.assertEqual(report["tasks"][0]["evidence_state"],
                         status_report.UNVERIFIED_CLAIM_STATE)
        self.assertIn("PASS is an unverified local claim", human)
        self.assertIsNone(re.search(r"\bVERIFIED\b", human))
        self.assertIsNone(re.search(r"\bVERIFIED\b", payload))

    def test_untrusted_text_is_sanitized_in_human_and_json_output(self):
        payload_text = (
            "\x1b[31mlocal PASS\x1b[0m \u202eREVERSE\x1b]8;;url\x07link\x1b]8;;\x07"
        )
        report = status_report.build_report(
            manifest([complete("TASK-001", verification={
                "commands": ["python -m unittest"],
                "result": "PASS",
                "evidence": payload_text,
            })]),
            source_label="tasks\u202e.json",
        )
        human = status_report.render_human(report)
        encoded = json.dumps(status_report._json_safe(report), ensure_ascii=True)

        for forbidden in ("\x1b", "\u202e", "\\u001b", "\\u202e"):
            with self.subTest(forbidden=repr(forbidden)):
                self.assertNotIn(forbidden, human)
                self.assertNotIn(forbidden, encoded)
        self.assertIn("[ansi removed]", human)
        self.assertIn("[osc removed]", human)

    def test_missing_and_malformed_manifests_fail_closed(self):
        script = str(ROOT / "tools" / "agent_task_status_report.py")
        cases = [("absent.json", None), ("broken.json", "{broken")]
        for filename, content in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as folder:
                root = pathlib.Path(folder)
                if content is not None:
                    (root / filename).write_text(content, encoding="utf-8")
                run = subprocess.run(
                    [sys.executable, script, "--manifest", str(root / filename)],
                    capture_output=True, text=True,
                )
                self.assertEqual(run.returncode, 2, run.stderr)
                payload = json.loads(run.stderr)
                self.assertEqual(payload["effective_decision"], "FAIL")
                self.assertIn("invalid manifest file", json.dumps(payload))
                self.assertIn("ADVISORY LOCAL DATA", run.stdout)

    def test_default_output_and_json_only_mode(self):
        script = str(ROOT / "tools" / "agent_task_status_report.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            path = write_manifest(root, manifest([task("TASK-001")]))
            default = subprocess.run(
                [sys.executable, script, "--manifest", str(path)],
                capture_output=True, text=True,
            )
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertIn("ADVISORY LOCAL DATA", default.stdout)
            payload = json.loads(default.stderr)
            self.assertEqual(payload["effective_decision"], "PASS")

            json_only = subprocess.run(
                [sys.executable, script, "--manifest", str(path), "--json-only"],
                capture_output=True, text=True,
            )
            self.assertEqual(json_only.returncode, 0, json_only.stderr)
            self.assertEqual(json_only.stderr, "")
            self.assertEqual(json.loads(json_only.stdout)["report_type"],
                             status_report.REPORT_TYPE)

    def test_stored_commands_are_displayed_never_executed(self):
        script = str(ROOT / "tools" / "agent_task_status_report.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            marker = root / "SHOULD_NOT_EXIST"
            dangerous_command = (
                f"powershell -NoProfile -Command \"New-Item -Path '{marker}'\""
            )
            path = write_manifest(root, manifest([
                task("TASK-001", verification={
                    "commands": [dangerous_command],
                    "result": "PENDING", "evidence": "local advisory data",
                }),
            ]))
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(path), "--json-only"],
                capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertFalse(marker.exists())
            self.assertNotIn(dangerous_command, run.stdout)

    def test_module_does_not_import_network_or_process_launchers(self):
        source = (ROOT / "tools" / "agent_task_status_report.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "import subprocess", "import socket", "import urllib",
            "import http.client", "import requests", "shutil.which",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

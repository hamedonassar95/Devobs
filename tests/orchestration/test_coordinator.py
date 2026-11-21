"""End-to-end offline tests for the orchestration facade and approval binding."""
import copy
import importlib
import importlib.util
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "scripts", ROOT / "tools"):
    _path = str(_folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent_dispatch_preflight import build_preflight  # noqa: E402
from agent_task_status_report import build_report  # noqa: E402


def load_module(name):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise AssertionError("missing module: " + name)
    return importlib.import_module(name)


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


def manifest(*tasks):
    return {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {key: "pending_human" for key in RESTRICTED},
        "tasks": list(tasks),
    }


def coordinator_for(data, **kwargs):
    module = load_module("devobs.orchestration.coordinator")
    return module.Coordinator.from_manifest(data, **kwargs)


class CoordinatorTests(unittest.TestCase):
    def test_preview_is_read_only_deterministic_and_never_dispatches(self):
        data = manifest(task("TASK-001"), task("TASK-002", assigned_agent="OPENCODE"))
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
            before = sorted(str(path) for path in root.rglob("*"))
            with mock.patch.object(subprocess, "Popen") as popen, \
                    mock.patch.object(socket, "socket") as socket_class:
                first = coordinator_for(data).preview()
                second = coordinator_for(data).preview()
            after = sorted(str(path) for path in root.rglob("*"))
            self.assertEqual(first, second)
            self.assertEqual(before, after)
            popen.assert_not_called()
            socket_class.assert_not_called()
            self.assertEqual(first["mode"], "DRY_RUN")
            self.assertFalse(first["dispatched"])
            self.assertFalse(first["apply"])
            self.assertTrue(all(first["approval"][key] == "pending_human" for key in RESTRICTED))

    def test_plan_feeds_existing_preflight_and_status_report(self):
        data = manifest(task("TASK-001"), task("TASK-002", assigned_agent="OPENCODE"))
        coordinator = coordinator_for(data)
        preview = coordinator.preview()
        self.assertEqual(preview["decision"], "PASS")
        with tempfile.TemporaryDirectory() as folder:
            preflight = build_preflight(
                coordinator.manifest(),
                instructions_dir=pathlib.Path(folder) / "instructions",
                which=lambda name: f"/usr/local/bin/{name}",
            )
        report = build_report(coordinator.manifest())
        self.assertEqual(preflight["decision"], "PASS")
        self.assertFalse(preflight["dispatched"])
        self.assertEqual(report["effective_decision"], "PASS")
        self.assertEqual(preview["summary"]["assignments"], 2)

    def test_approval_is_bound_to_exact_plan_fingerprint_and_scope(self):
        data = manifest(task("TASK-001"), task("TASK-002", assigned_agent="OPENCODE"))
        coordinator = coordinator_for(data)
        preview = coordinator.preview()
        original = copy.deepcopy(preview)
        record = {
            "verification_status": "VERIFIED",
            "approval": "APPROVE",
            "approver_is_human": True,
            "approver_has_write": True,
            "pr_open": True,
            "pr_merged": False,
            "reviewed_sha": SHA,
            "scope_fingerprint": preview["fingerprint"],
            "approved_task_ids": ["TASK-001", "TASK-002"],
            "approved_actions": ["code_change"],
        }
        result = coordinator.approve(preview, record)
        self.assertTrue(result["authorized"])
        self.assertEqual(result["status"], "HUMAN_APPROVED")
        self.assertEqual(preview, original)

        for field, value in (
            ("scope_fingerprint", "0" * 64),
            ("reviewed_sha", "HEAD"),
            ("approved_task_ids", ["TASK-001"]),
            ("approved_actions", ["merge"]),
            ("pr_open", False),
        ):
            with self.subTest(field=field):
                changed = dict(record)
                changed[field] = value
                denied = coordinator.approve(preview, changed)
                self.assertFalse(denied["authorized"])
                self.assertNotEqual(denied["status"], "HUMAN_APPROVED")

    def test_preview_never_grants_restricted_actions(self):
        data = manifest(task("TASK-001"))
        preview = coordinator_for(data).preview()
        for key in RESTRICTED:
            self.assertEqual(preview["approval"][key], "pending_human")
        self.assertEqual(preview["safety"]["human_gate"], "PENDING HUMAN APPROVAL")

    def test_coordinator_has_no_execution_entry_point(self):
        module = load_module("devobs.orchestration.coordinator")
        for name in ("execute", "dispatch", "apply", "run", "merge", "deploy"):
            self.assertFalse(hasattr(module.Coordinator, name), name)


if __name__ == "__main__":
    unittest.main()

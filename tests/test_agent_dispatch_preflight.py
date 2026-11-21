"""Behavioral tests for the offline agent dispatch preflight."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_dispatch_preflight as preflight  # noqa: E402
from agent_dispatch_preflight import build_preflight, exit_code, main  # noqa: E402

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


def available_cli(name):
    return f"/usr/local/bin/{name}"


def fake_cli_path(root, names=("codex", "opencode")):
    """Create detectable-but-never-executed CLI stubs for deterministic CLI tests."""
    binary_dir = root / "bin"
    binary_dir.mkdir()
    for name in names:
        executable = binary_dir / name
        executable.write_text("stub", encoding="utf-8")
        executable.chmod(0o755)
        for suffix in (".exe", ".cmd"):
            stub = binary_dir / f"{name}{suffix}"
            stub.write_text("stub", encoding="utf-8")
            stub.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(binary_dir) + os.pathsep + environment.get("PATH", "")
    return environment


def create_directory_link(link_path, target_path):
    """Create a portable reparse-point fixture for the output-directory test."""
    target_path.mkdir()
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr or completed.stdout)
    else:
        os.symlink(target_path, link_path, target_is_directory=True)


class AgentDispatchPreflightTests(unittest.TestCase):
    def test_valid_manifest_prepares_instructions_without_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            result = build_preflight(
                manifest([task("TASK-001")]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )
            self.assertEqual(result["decision"], "PASS")
            self.assertEqual(result["mode"], "DRY_RUN")
            self.assertFalse(result["dispatched"])
            self.assertEqual(result["validator"]["decision"], "PASS")
            self.assertTrue((instructions_dir / "CODEX_instructions.md").is_file())
            self.assertTrue((instructions_dir / "OPENCODE_instructions.md").is_file())
            self.assertEqual(
                sorted(entry.name for entry in instructions_dir.iterdir()),
                ["CODEX_instructions.md", "OPENCODE_instructions.md"],
            )

    def test_exit_codes_are_exact_and_unknown_decisions_fail_closed(self):
        self.assertEqual(exit_code("PASS"), 0)
        self.assertEqual(exit_code("BLOCKED"), 1)
        self.assertEqual(exit_code("FAIL"), 2)
        self.assertEqual(exit_code("UNKNOWN"), 2)
        self.assertEqual(exit_code(None), 2)

    def test_result_names_exact_human_approval_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            result = build_preflight(
                manifest([task("TASK-001")]),
                instructions_dir=pathlib.Path(folder) / "instructions",
                which=available_cli,
            )
            actions = {item["id"]: item for item in result["human_approval_actions"]}
            self.assertEqual(
                set(actions),
                {
                    "REVIEW_INSTRUCTIONS",
                    "START_WORKERS_MANUALLY",
                    "KEEP_RESTRICTED_APPROVALS_PENDING",
                    "VERIFY_EVIDENCE",
                    "PHASE_8_APPROVAL",
                },
            )
            pending = actions["KEEP_RESTRICTED_APPROVALS_PENDING"]
            for key in RESTRICTED:
                self.assertEqual(pending[key], "pending_human")
            self.assertIn("check_two_agent_tasks.py", actions["VERIFY_EVIDENCE"]["action"])

    def test_missing_required_cli_blocks_without_instructions(self):
        def which(name):
            return None if name == "opencode" else "/usr/local/bin/codex"

        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            result = build_preflight(
                manifest([
                    task("TASK-001", assigned_agent="CODEX"),
                    task("TASK-002", assigned_agent="OPENCODE"),
                ]),
                instructions_dir=instructions_dir,
                which=which,
            )
            self.assertEqual(result["decision"], "BLOCKED")
            self.assertEqual(result["missing_clis"], ["OPENCODE"])
            self.assertEqual(result["cli_detection"]["OPENCODE"]["status"], "MISSING")
            self.assertFalse(instructions_dir.exists())

    def test_cli_defaults_to_dry_run_and_writes_result_json(self):
        script = str(ROOT / "scripts" / "agent_dispatch_preflight.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            manifest_path = root / "tasks.json"
            manifest_path.write_text(
                json.dumps(manifest([task("TASK-001")])), encoding="utf-8"
            )
            instructions_dir = root / "instructions"
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(manifest_path),
                 "--instructions-dir", str(instructions_dir)],
                capture_output=True,
                text=True,
                env=fake_cli_path(root),
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "PASS")
            self.assertEqual(payload["mode"], "DRY_RUN")
            self.assertFalse(payload["dispatched"])
            self.assertTrue((instructions_dir / "CODEX_instructions.md").is_file())

    def test_cli_fails_closed_on_invalid_manifest(self):
        script = str(ROOT / "scripts" / "agent_dispatch_preflight.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            manifest_path = root / "tasks.json"
            manifest_path.write_text("{broken", encoding="utf-8")
            instructions_dir = root / "instructions"
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(manifest_path),
                 "--instructions-dir", str(instructions_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 2, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "FAIL")
            self.assertIn("invalid manifest file", json.dumps(payload))
            self.assertFalse(instructions_dir.exists())

    def test_cli_returns_blocked_exit_code_without_instructions(self):
        script = str(ROOT / "scripts" / "agent_dispatch_preflight.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            manifest_path = root / "tasks.json"
            manifest_path.write_text(
                json.dumps(manifest([task("TASK-001", assigned_agent="OPENCODE")])),
                encoding="utf-8",
            )
            environment = fake_cli_path(root, names=("codex",))
            environment["PATH"] = str(root / "bin")
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(manifest_path)],
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(run.returncode, 1, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "BLOCKED")
            self.assertEqual(payload["missing_clis"], ["OPENCODE"])
            self.assertFalse((root / "agent_dispatch_instructions").exists())

    def test_cli_rejects_any_non_dry_run_mode(self):
        script = str(ROOT / "scripts" / "agent_dispatch_preflight.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            manifest_path = root / "tasks.json"
            manifest_path.write_text(
                json.dumps(manifest([task("TASK-001")])), encoding="utf-8"
            )
            run = subprocess.run(
                [sys.executable, script, "--manifest", str(manifest_path),
                 "--mode", "DISPATCH"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("DRY_RUN", run.stderr + run.stdout)

    def test_conflicts_and_unauthorized_tasks_are_rejected_without_instructions(self):
        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            conflict = build_preflight(
                manifest([
                    task("TASK-001", affected_files=["shared/module.py"]),
                    task("TASK-002", assigned_agent="OPENCODE",
                         affected_files=["shared/module.py"]),
                ]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )
            self.assertEqual(conflict["decision"], "BLOCKED")
            self.assertEqual(conflict["rejection_reason"], "validator_conflict")
            self.assertEqual(
                set(conflict["rejected_tasks"]), {"TASK-001", "TASK-002"}
            )
            self.assertFalse(instructions_dir.exists())

            unauthorized = build_preflight(
                manifest([task("TASK-001", requested_actions=["merge"])]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )
            self.assertEqual(unauthorized["decision"], "FAIL")
            self.assertEqual(unauthorized["rejection_reason"], "validator_contract_failure")
            self.assertFalse(instructions_dir.exists())

    def test_instructions_are_scoped_to_each_assigned_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            result = build_preflight(
                manifest([
                    task("TASK-001", assigned_agent="CODEX"),
                    task("TASK-002", assigned_agent="OPENCODE"),
                ]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )
            self.assertEqual(
                result["instruction_scope"],
                {"CODEX": ["TASK-001"], "OPENCODE": ["TASK-002"]},
            )
            codex_text = (instructions_dir / "CODEX_instructions.md").read_text(encoding="utf-8")
            opencode_text = (instructions_dir / "OPENCODE_instructions.md").read_text(encoding="utf-8")
            self.assertIn("TASK-001", codex_text)
            self.assertNotIn("TASK-002", codex_text)
            self.assertIn("TASK-002", opencode_text)
            self.assertNotIn("TASK-001", opencode_text)
            self.assertIn('- requested_actions: ["code_change"]', codex_text)

    def test_existing_output_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            instructions_dir.mkdir()
            existing = instructions_dir / "CODEX_instructions.md"
            existing.write_text("DO NOT OVERWRITE", encoding="utf-8")

            result = build_preflight(
                manifest([task("TASK-001")]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )

            self.assertEqual(result["decision"], "FAIL")
            self.assertEqual(result["rejection_reason"], "output_file_exists")
            self.assertEqual(existing.read_text(encoding="utf-8"), "DO NOT OVERWRITE")
            self.assertFalse((instructions_dir / "OPENCODE_instructions.md").exists())
            self.assertEqual(
                sorted(entry.name for entry in instructions_dir.iterdir()),
                ["CODEX_instructions.md"],
            )

    def test_symlink_output_directory_is_rejected_without_writing_through_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            target = root / "target"
            link = root / "instructions"
            create_directory_link(link, target)

            result = build_preflight(
                manifest([task("TASK-001")]),
                instructions_dir=link,
                which=available_cli,
            )

            self.assertEqual(result["decision"], "FAIL")
            self.assertEqual(result["rejection_reason"], "symlink_output_destination")
            self.assertEqual(list(target.iterdir()), [])

    def test_symlink_output_file_is_rejected_without_writing_through_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            instructions_dir = root / "instructions"
            instructions_dir.mkdir()
            target = root / "outside"
            link = instructions_dir / "OPENCODE_instructions.md"
            create_directory_link(link, target)

            result = build_preflight(
                manifest([task("TASK-001")]),
                instructions_dir=instructions_dir,
                which=available_cli,
            )

            self.assertEqual(result["decision"], "FAIL")
            self.assertEqual(result["rejection_reason"], "symlink_output_destination")
            self.assertEqual(list(target.iterdir()), [])
            self.assertFalse((instructions_dir / "CODEX_instructions.md").exists())

    def test_second_output_failure_removes_all_generated_files(self):
        with tempfile.TemporaryDirectory() as folder:
            instructions_dir = pathlib.Path(folder) / "instructions"
            real_link = preflight.os.link
            calls = []

            def fail_second_link(source, destination, *args, **kwargs):
                calls.append(pathlib.Path(destination).name)
                if len(calls) == 2:
                    raise OSError("simulated second output failure")
                return real_link(source, destination, *args, **kwargs)

            with mock.patch.object(preflight.os, "link", side_effect=fail_second_link):
                result = build_preflight(
                    manifest([task("TASK-001")]),
                    instructions_dir=instructions_dir,
                    which=available_cli,
                )

            self.assertEqual(result["decision"], "FAIL")
            self.assertEqual(result["rejection_reason"], "output_write_failed")
            self.assertFalse(instructions_dir.exists())

    def test_cli_collision_returns_fail_without_overwriting(self):
        script = str(ROOT / "scripts" / "agent_dispatch_preflight.py")
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            manifest_path = root / "tasks.json"
            manifest_path.write_text(
                json.dumps(manifest([task("TASK-001")])), encoding="utf-8"
            )
            instructions_dir = root / "instructions"
            instructions_dir.mkdir()
            existing = instructions_dir / "OPENCODE_instructions.md"
            existing.write_text("DO NOT OVERWRITE", encoding="utf-8")

            run = subprocess.run(
                [sys.executable, script, "--manifest", str(manifest_path),
                 "--instructions-dir", str(instructions_dir)],
                capture_output=True,
                text=True,
                env=fake_cli_path(root),
            )

            self.assertEqual(run.returncode, 2, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["decision"], "FAIL")
            self.assertEqual(payload["rejection_reason"], "output_file_exists")
            self.assertEqual(existing.read_text(encoding="utf-8"), "DO NOT OVERWRITE")
            self.assertFalse((instructions_dir / "CODEX_instructions.md").exists())


if __name__ == "__main__":
    unittest.main()

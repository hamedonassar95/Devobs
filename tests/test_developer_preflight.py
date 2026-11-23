"""Behavioral tests for the read-only developer environment preflight."""
import contextlib
import io
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
import developer_preflight as preflight  # noqa: E402

VERSIONS = {
    ("python", "--version"): "Python 3.12.10",
    ("python3", "--version"): "Python 3.11.9",
    ("node", "--version"): "v22.14.0",
    ("git", "--version"): "git version 2.45.2",
    ("docker", "--version"): "Docker version 28.0.1, build 0000000",
    ("terraform", "version"): "Terraform v1.9.8\non windows_amd64",
    ("npm", "--version"): "10.8.2",
}
ALL_PATHS = frozenset(
    path for spec in preflight.COMMAND_SPECS for path in spec["required_paths"]
)
ALL_TOOL_IDS = frozenset(spec["id"] for spec in preflight.TOOL_SPECS)


def fake_probe(argv):
    argv = tuple(str(arg) for arg in argv)
    executable = pathlib.PurePath(argv[0]).name.lower()
    for suffix in (".cmd", ".bat", ".exe"):
        if executable.endswith(suffix):
            executable = executable[:-len(suffix)]
            break
    normalized = (executable,) + argv[1:]
    if normalized not in preflight.ALLOWED_VERSION_PROBES:
        raise AssertionError("unexpected probe: " + repr(argv))
    return 0, VERSIONS.get(normalized, ""), ""


def fake_which(name):
    return f"/usr/local/bin/{name}"


def fake_distribution_version(name):
    if name != "bandit":
        raise AssertionError("unexpected distribution: " + name)
    return "1.9.4"


def fake_path_exists(relative):
    return relative in ALL_PATHS


def build(**overrides):
    kwargs = {
        "repo_root": pathlib.Path("/repo"),
        "which": fake_which,
        "run_version_probe": fake_probe,
        "distribution_version": fake_distribution_version,
        "path_exists": fake_path_exists,
        "platform_name": "Linux",
    }
    kwargs.update(overrides)
    return preflight.build_report(**kwargs)


class DeveloperPreflightTests(unittest.TestCase):
    def test_report_is_machine_readable_and_uses_only_allowed_statuses(self):
        report = build()
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["mode"], "READ_ONLY")
        self.assertFalse(report["commands_executed"])
        self.assertFalse(report["environment_values_read"])
        self.assertIn(report["overall_status"], preflight.STATUSES)
        entries = report["tools"] + report["documented_commands"]
        self.assertTrue(entries)
        for entry in entries:
            self.assertIn(entry["status"], preflight.STATUSES)
        self.assertEqual(
            report["summary"],
            {
                "verified": sum(e["status"] == "VERIFIED" for e in entries),
                "blocked": sum(e["status"] == "BLOCKED" for e in entries),
                "unverified": sum(e["status"] == "UNVERIFIED" for e in entries),
            },
        )

    def test_all_required_tool_families_are_checked_with_versions(self):
        report = build()
        tools = {item["id"]: item for item in report["tools"]}
        self.assertEqual(
            set(tools),
            {"python", "node", "git", "docker", "terraform", "npm", "bandit"},
        )
        expected_versions = {
            "python": "3.12.10",
            "node": "22.14.0",
            "git": "2.45.2",
            "docker": "28.0.1",
            "terraform": "1.9.8",
            "npm": "10.8.2",
            "bandit": "1.9.4",
        }
        for tool_id, version in expected_versions.items():
            self.assertEqual(tools[tool_id]["status"], "VERIFIED", tool_id)
            self.assertEqual(tools[tool_id]["version"], version, tool_id)
        self.assertEqual(tools["python"]["probe"], "python --version")
        self.assertEqual(tools["terraform"]["probe"], "terraform version")
        self.assertEqual(tools["bandit"]["probe"], "distribution:bandit")

    def test_python_falls_back_to_python3_without_hiding_the_probe(self):
        def which(name):
            if name == "python3":
                return "/usr/bin/python3"
            return None if name == "python" else fake_which(name)

        tools = {item["id"]: item for item in build(which=which)["tools"]}
        self.assertEqual(tools["python"]["status"], "VERIFIED")
        self.assertEqual(tools["python"]["probe"], "python3 --version")
        self.assertEqual(tools["python"]["version"], "3.11.9")

    def test_missing_executable_blocks_the_tool_and_dependent_commands(self):
        def which(name):
            return None if name == "terraform" else fake_which(name)

        report = build(which=which)
        tools = {item["id"]: item for item in report["tools"]}
        self.assertEqual(tools["terraform"]["status"], "BLOCKED")
        self.assertEqual(tools["terraform"]["reason"], "executable_not_found")
        commands = {item["id"]: item for item in report["documented_commands"]}
        for command_id in ("terraform_fmt_check", "terraform_validate"):
            self.assertEqual(commands[command_id]["status"], "BLOCKED", command_id)
            self.assertIn("terraform", commands[command_id]["missing_tools"])
        self.assertEqual(report["overall_status"], "BLOCKED")

    def test_failed_and_unexpected_version_probes_fail_closed(self):
        def failed_probe(argv):
            if pathlib.PurePath(argv[0]).name.lower() == "node":
                return 1, "", "permission denied"
            return fake_probe(argv)

        failed = {item["id"]: item for item in build(run_version_probe=failed_probe)["tools"]}
        self.assertEqual(failed["node"]["status"], "BLOCKED")
        self.assertEqual(failed["node"]["reason"], "version_probe_failed")
        self.assertNotIn("permission denied", json.dumps(failed))

        def strange_probe(argv):
            if pathlib.PurePath(argv[0]).name.lower() == "node":
                return 0, "SENSITIVE_OUTPUT_TOKEN", ""
            return fake_probe(argv)

        strange = {item["id"]: item for item in build(run_version_probe=strange_probe)["tools"]}
        self.assertEqual(strange["node"]["status"], "UNVERIFIED")
        self.assertEqual(strange["node"]["reason"], "unexpected_version_output")
        self.assertNotIn("SENSITIVE_OUTPUT_TOKEN", json.dumps(strange))

    def test_missing_bandit_distribution_blocks_bandit_command(self):
        def no_bandit(name):
            raise ValueError("not installed")

        report = build(distribution_version=no_bandit)
        tools = {item["id"]: item for item in report["tools"]}
        commands = {item["id"]: item for item in report["documented_commands"]}
        self.assertEqual(tools["bandit"]["status"], "BLOCKED")
        self.assertEqual(tools["bandit"]["reason"], "distribution_not_found")
        self.assertEqual(commands["bandit_scan"]["status"], "BLOCKED")
        self.assertNotIn("not installed", json.dumps(report))

    def test_missing_paths_block_commands_without_marking_them_verified(self):
        report = build(path_exists=lambda relative: False)
        commands = {item["id"]: item for item in report["documented_commands"]}
        self.assertTrue(commands)
        for command in commands.values():
            self.assertEqual(command["status"], "BLOCKED")
            self.assertEqual(command["reason"], "required_path_missing")
            self.assertTrue(command["missing_paths"])
        self.assertEqual(report["overall_status"], "BLOCKED")

    def test_available_prerequisites_remain_unverified_until_commands_run(self):
        report = build()
        commands = {item["id"]: item for item in report["documented_commands"]}
        self.assertTrue(commands)
        for command in commands.values():
            self.assertEqual(command["status"], "UNVERIFIED", command["id"])
            self.assertEqual(command["reason"], "not_executed_by_preflight")
            self.assertEqual(command["missing_paths"], [])
            self.assertEqual(command["missing_tools"], [])
        self.assertEqual(report["overall_status"], "UNVERIFIED")
        self.assertEqual(report["platform"], "Linux")

    def test_windows_platform_is_reported_without_platform_specific_commands(self):
        report = build(platform_name="Windows")
        self.assertEqual(report["platform"], "Windows")
        self.assertEqual(report["overall_status"], "UNVERIFIED")

    def test_documented_command_catalog_points_to_real_documented_commands(self):
        for spec in preflight.COMMAND_SPECS:
            source = ROOT / spec["source"]
            self.assertTrue(source.is_file(), spec["source"])
            text = source.read_text(encoding="utf-8")
            self.assertIn(spec["command"], text, spec["command"])
            self.assertEqual(spec["id"], spec["id"].strip())

    def test_default_version_probe_uses_fixed_allowlisted_no_shell_invocation(self):
        completed = subprocess.CompletedProcess(
            ["git", "--version"], 0, "git version 2.45.2", ""
        )
        with mock.patch.object(preflight.subprocess, "run", return_value=completed) as run:
            result = preflight.default_version_probe(("git", "--version"))
        self.assertEqual(result, (0, "git version 2.45.2", ""))
        args, kwargs = run.call_args
        self.assertEqual(pathlib.PurePath(args[0][0]).name, "git")
        self.assertEqual(args[0][1:], ["--version"])
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertTrue(kwargs["capture_output"])
        self.assertGreater(kwargs["timeout"], 0)
        self.assertNotIn("env", kwargs)
        with self.assertRaises(ValueError):
            preflight.default_version_probe(("docker", "run", "alpine"))

    def test_report_build_does_not_read_environment_values(self):
        class ExplodingEnviron(dict):
            def get(self, *args, **kwargs):
                raise AssertionError("environment value read")

            def __getitem__(self, key):
                raise AssertionError("environment value read")

        with mock.patch("os.environ", ExplodingEnviron()):
            report = build()
        self.assertEqual(report["overall_status"], "UNVERIFIED")
        self.assertTrue(report["tools"])

    def test_exit_codes_are_exact_and_unknown_status_fails_closed(self):
        self.assertEqual(preflight.exit_code({"overall_status": "UNVERIFIED"}), 0)
        self.assertEqual(preflight.exit_code({"overall_status": "BLOCKED"}), 1)
        self.assertEqual(preflight.exit_code({"overall_status": "VERIFIED"}), 2)
        self.assertEqual(preflight.exit_code({}), 2)

    def test_main_prints_only_json_and_returns_blocked_exit_code(self):
        report = {
            "schema_version": 1,
            "overall_status": "BLOCKED",
            "tools": [],
            "documented_commands": [],
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(preflight, "build_report", return_value=report):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = preflight.main(["--repo", str(ROOT)])
        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue()), report)

    def test_help_is_readable_and_succeeds(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                preflight.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("read-only", stdout.getvalue().lower())

    def test_cli_does_not_disclose_environment_secrets(self):
        sentinel = "PREFLIGHT_TEST_SENTINEL_DO_NOT_PRINT"
        environment = os.environ.copy()
        environment["PREFLIGHT_TEST_SECRET"] = sentinel
        environment["PATH"] = ""
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "developer_preflight.py"),
             "--repo", tempfile.gettempdir()],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        self.assertIn(run.returncode, (0, 1), run.stderr)
        payload = json.loads(run.stdout)
        self.assertIn(payload["overall_status"], preflight.STATUSES)
        self.assertNotIn(sentinel, run.stdout + run.stderr)
        self.assertTrue(payload["tools"])


if __name__ == "__main__":
    unittest.main()

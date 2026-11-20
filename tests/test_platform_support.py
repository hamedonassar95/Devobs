"""Contracts for shared test host-capability discovery."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.platform_support import (
    executable_mode_bit_supported,
    find_bash,
    has_secure_open_capability,
    symlink_creation_supported,
    to_bash_path,
    write_python_cli_shim,
    write_python3_shim,
)


class PlatformSupportTests(unittest.TestCase):
    def test_find_bash_returns_a_file_when_bash_is_available(self):
        bash = find_bash()
        if bash is None:
            self.skipTest("bash is not installed on this host")
        self.assertTrue(Path(bash).is_file(), bash)

    def test_secure_open_capability_reflects_the_host(self):
        self.assertIsInstance(has_secure_open_capability(), bool)

    def test_symlink_probe_does_not_leave_artifacts(self):
        self.assertIsInstance(symlink_creation_supported(), bool)

    def test_executable_mode_bit_probe_does_not_leave_artifacts(self):
        self.assertIsInstance(executable_mode_bit_supported(), bool)

    def test_windows_drive_paths_are_converted_for_bash(self):
        if os.name != "nt":
            self.skipTest("drive-letter conversion applies only to Windows")
        self.assertEqual(to_bash_path(r"C:\Temp\fixture"), "/c/Temp/fixture")

    def test_bash_paths_are_left_unchanged(self):
        self.assertEqual(to_bash_path("/tmp/fixture"), "/tmp/fixture")

    def test_python3_shim_runs_under_bash(self):
        bash = find_bash()
        if bash is None:
            self.skipTest("bash is not installed on this host")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_python3_shim(root)
            env = os.environ.copy()
            env["PATH"] = f"{to_bash_path(root)}:{env.get('PATH', '')}"
            result = subprocess.run(
                [bash, "-c", 'python3 -c "print(41 + 1)"'],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "42")

    def test_python_script_shim_runs_under_bash(self):
        bash = find_bash()
        if bash is None:
            self.skipTest("bash is not installed on this host")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "fixture.py"
            script.write_text("print('shim-ok')\n", encoding="utf-8")
            write_python_cli_shim(root, "fixture-cli", script)
            env = os.environ.copy()
            env["PATH"] = f"{to_bash_path(root)}:{env.get('PATH', '')}"
            result = subprocess.run(
                [bash, "-c", "fixture-cli"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "shim-ok")


if __name__ == "__main__":
    unittest.main()

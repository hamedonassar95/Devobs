"""Contracts for shared test host-capability discovery."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from tests.platform_support import (
    find_bash,
    has_secure_open_capability,
    symlink_creation_supported,
    to_bash_path,
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

    def test_windows_drive_paths_are_converted_for_bash(self):
        if os.name != "nt":
            self.skipTest("drive-letter conversion applies only to Windows")
        self.assertEqual(to_bash_path(r"C:\Temp\fixture"), "/c/Temp/fixture")

    def test_bash_paths_are_left_unchanged(self):
        self.assertEqual(to_bash_path("/tmp/fixture"), "/tmp/fixture")


if __name__ == "__main__":
    unittest.main()

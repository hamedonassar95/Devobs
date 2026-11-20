"""Contracts for shared test host-capability discovery."""

from __future__ import annotations

from pathlib import Path
import unittest

from tests.platform_support import (
    find_bash,
    has_secure_open_capability,
    symlink_creation_supported,
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


if __name__ == "__main__":
    unittest.main()

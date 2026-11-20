"""Behavioral tests for fail-closed Graphify wheel integrity."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify import repository_intelligence as ri  # noqa: E402
from tools.graphify import supply_chain  # noqa: E402


class SupplyChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-wheel-verify-")
        self.addCleanup(self.tmp.cleanup)
        self.wheel = pathlib.Path(self.tmp.name) / "graphifyy-0.9.113-py3-none-any.whl"
        self.wheel.write_bytes(b"synthetic wheel bytes")

    def test_pinned_digest_is_a_complete_64_character_sha256(self) -> None:
        self.assertRegex(supply_chain.PINNED_WHEEL_SHA256, r"^[0-9a-f]{64}$")

    def test_truncated_or_mismatched_digest_is_refused(self) -> None:
        with self.assertRaisesRegex(supply_chain.SupplyChainError, "must_be_64_hex"):
            supply_chain.verify_wheel_sha256(self.wheel, expected=supply_chain.PINNED_WHEEL_SHA256[:32])
        with self.assertRaisesRegex(supply_chain.SupplyChainError, "wheel_sha256_mismatch"):
            supply_chain.verify_wheel_sha256(self.wheel, expected="0" * 64)

    def test_matching_digest_is_accepted(self) -> None:
        expected = hashlib.sha256(self.wheel.read_bytes()).hexdigest()
        with mock.patch.object(supply_chain, "PINNED_WHEEL_SHA256", expected):
            self.assertEqual(supply_chain.verify_wheel_sha256(self.wheel), expected)

    def test_missing_wheel_is_refused(self) -> None:
        with self.assertRaisesRegex(supply_chain.SupplyChainError, "wheel_not_found"):
            supply_chain.verify_wheel_sha256(self.wheel.parent / "missing.whl")

    def test_cli_verify_wheel_accepts_a_matching_digest(self) -> None:
        expected = hashlib.sha256(self.wheel.read_bytes()).hexdigest()
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(supply_chain, "PINNED_WHEEL_SHA256", expected):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = ri.main(["verify-wheel", "--wheel", str(self.wheel)])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((report["status"], report["sha256"]), ("verified", expected))
        self.assertEqual(report["pinned_version"], "0.9.113")
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_verify_wheel_refuses_truncated_digest(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(supply_chain, "PINNED_WHEEL_SHA256", "abc123"):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = ri.main(["verify-wheel", "--wheel", str(self.wheel)])
        self.assertEqual(code, 2)
        self.assertIn("must_be_64_hex", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

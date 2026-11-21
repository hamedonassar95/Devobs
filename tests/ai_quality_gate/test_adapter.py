"""Offline advisory adapter tests."""

from __future__ import annotations

import unittest
from unittest import mock

from devobs.ai_quality_gate.adapter import (
    EXPLANATIONS,
    LocalExplanatoryAdapter,
)


class LocalExplanatoryAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = LocalExplanatoryAdapter()

    def test_explains_only_supplied_closed_codes(self):
        text = self.adapter.assess({
            "finding_codes": ["CONCURRENT_FILE_OWNERSHIP", "UNKNOWN_CODE"],
            "source_sha": "a" * 40,
        })
        self.assertIn("CONCURRENT_FILE_OWNERSHIP", text)
        self.assertIn(EXPLANATIONS["CONCURRENT_FILE_OWNERSHIP"], text)
        self.assertIn("UNKNOWN_CODE", text)
        self.assertLessEqual(len(text), 600)

    def test_contexts_without_codes_are_empty(self):
        self.assertEqual(self.adapter.assess({}), "")
        self.assertEqual(self.adapter.assess({"finding_codes": "not-a-list"}), "")
        self.assertEqual(self.adapter.assess(None), "")

    def test_output_is_bounded_and_deterministic(self):
        context = {
            "finding_codes": [f"CODE_{index:03d}" for index in range(200)]
        }
        first = self.adapter.assess(context)
        second = self.adapter.assess(context)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 600)

    def test_no_network_or_process_primitives_are_used(self):
        context = {"finding_codes": ["CI_FAILURE_CODE"]}
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("unexpected network call"),
        ), mock.patch(
            "subprocess.Popen",
            side_effect=AssertionError("unexpected process call"),
        ):
            text = self.adapter.assess(context)
        self.assertIn("CI_FAILURE_CODE", text)


if __name__ == "__main__":
    unittest.main()

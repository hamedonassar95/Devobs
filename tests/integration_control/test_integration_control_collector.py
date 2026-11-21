"""Tests for the offline repository state collector."""

from __future__ import annotations

import json
import unittest

from devobs.integration_control.collector import CollectionError, collect_repository_state
from devobs.integration_control.engine import evaluate_integration

from test_integration_control_plane import base_input


class CollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = base_input()
        self.request = {
            "repository": "hamedonassar95/Devobs",
            "pr_number": 10,
            "head_sha": "a" * 40,
        }

    def test_offline_snapshot_collects_and_evaluates(self) -> None:
        state = collect_repository_state(self.snapshot, self.request)
        self.assertEqual(state["pr"]["repository"], self.request["repository"])
        report = evaluate_integration(state)
        self.assertEqual(report["decision"], "READY_FOR_HUMAN_REVIEW")

    def test_callable_provider_is_supported(self) -> None:
        seen: list[dict] = []

        def provider(request):
            seen.append(dict(request))
            return self.snapshot

        state = collect_repository_state(provider, self.request)
        self.assertEqual(seen[0]["pr_number"], 10)
        self.assertEqual(state["pr"]["head_sha"], "a" * 40)

    def test_mismatched_identity_fails_closed(self) -> None:
        request = dict(self.request, pr_number=11)
        with self.assertRaises(CollectionError):
            collect_repository_state(self.snapshot, request)

    def test_provider_name_string_is_rejected(self) -> None:
        with self.assertRaises(CollectionError):
            collect_repository_state("github", self.request)

    def test_unavailable_provider_fails_closed(self) -> None:
        def provider(_request):
            raise RuntimeError("network disabled")

        with self.assertRaises(CollectionError) as ctx:
            collect_repository_state(provider, self.request)
        self.assertIn("provider unavailable", str(ctx.exception))
        self.assertNotIn("network disabled", str(ctx.exception))

    def test_collector_redacts_secrets(self) -> None:
        snapshot = base_input()
        snapshot["evidence"][0]["data"] = {"authorization": "Bearer abc.def.ghi"}
        state = collect_repository_state(snapshot, self.request)
        self.assertNotIn("abc.def.ghi", json.dumps(state))

    def test_collector_bounds_state(self) -> None:
        snapshot = base_input()
        snapshot["checks"] = [{"name": f"check-{i}", "status": "completed", "conclusion": "success"} for i in range(5001)]
        with self.assertRaises(CollectionError):
            collect_repository_state(snapshot, self.request)


if __name__ == "__main__":
    unittest.main()

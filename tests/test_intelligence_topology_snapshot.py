"""Offline contract tests for tenant- and source-bound topology snapshots."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot


def snapshot(**overrides):
    values = {
        "tenant": "alpha",
        "project": "platform",
        "services": ["api", "db", "web"],
        "edges": [("api", "db"), ("web", "api")],
        "source_sha": "a" * 40,
        "captured_at": "2026-11-02T00:00:00Z",
    }
    values.update(overrides)
    return ServiceTopologySnapshot(**values)


class ServiceTopologySnapshotTests(unittest.TestCase):
    def test_digest_is_canonical_and_binds_source_and_capture_time(self):
        first = snapshot()
        reordered = snapshot(services=["web", "db", "api"],
                            edges=[("web", "api"), ("api", "db")])
        self.assertEqual(first.snapshot_digest, reordered.snapshot_digest)
        self.assertEqual(first.snapshot_digest, snapshot(
            captured_at="2026-11-02T01:00:00+01:00").snapshot_digest)
        self.assertNotEqual(first.snapshot_digest,
                            snapshot(source_sha="b" * 40).snapshot_digest)
        self.assertNotEqual(first.snapshot_digest,
                            snapshot(captured_at="2026-11-02T00:01:00Z").snapshot_digest)

    def test_impact_query_requires_exact_tenant_and_project_scope(self):
        graph = snapshot()
        now = datetime(2026, 11, 2, 0, 5, tzinfo=timezone.utc)
        self.assertEqual(graph.affected_by("alpha", "platform", "db", now=now),
                         ("api", "db", "web"))
        with self.assertRaisesRegex(ContextError, "scope_mismatch"):
            graph.affected_by("beta", "platform", "db", now=now)
        with self.assertRaisesRegex(ContextError, "scope_mismatch"):
            graph.affected_by("alpha", "other", "db", now=now)

    def test_stale_future_and_invalid_clock_values_fail_closed(self):
        graph = snapshot()
        with self.assertRaisesRegex(ContextError, "stale_topology"):
            graph.affected_by("alpha", "platform", "db",
                              now=datetime(2026, 11, 2, 0, 16, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ContextError, "stale_topology"):
            graph.affected_by("alpha", "platform", "db",
                              now=datetime(2026, 11, 1, 23, 59, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ContextError, "invalid_query"):
            graph.affected_by("alpha", "platform", "db", now="2026-11-02T00:01:00Z")
        with self.assertRaisesRegex(ContextError, "invalid_query"):
            graph.affected_by("alpha", "platform", "db",
                              now=datetime(2026, 11, 2, 0, 1), max_age_seconds=0)

    def test_snapshot_rejects_missing_or_invalid_provenance_and_topology(self):
        for override in (
            {"source_sha": "short"},
            {"captured_at": "2026-11-02T00:00:00"},
            {"captured_at": "not-a-time"},
            {"source_sha": None},
            {"services": ["api", "api"]},
            {"edges": [("api", "missing")]},
        ):
            with self.subTest(override=override), self.assertRaises(ContextError):
                snapshot(**override)

    def test_json_record_round_trip_preserves_canonical_snapshot(self):
        original = snapshot()
        record = json.loads(json.dumps(original.to_record()))

        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["services"], ["api", "db", "web"])
        self.assertEqual(record["edges"], [["api", "db"], ["web", "api"]])
        restored = ServiceTopologySnapshot.from_record(record)
        self.assertEqual(restored, original)
        self.assertEqual(restored.snapshot_digest, original.snapshot_digest)

        record["services"].append("mutated")
        record["edges"][0].append("mutated")
        self.assertEqual(original.services, ("api", "db", "web"))
        self.assertEqual(original.edges, (("api", "db"), ("web", "api")))

    def test_json_record_rejects_unknown_schema_and_unexpected_fields(self):
        record = snapshot().to_record()
        for invalid in (
            {**record, "schema_version": True},
            {**record, "schema_version": 2},
            {**record, "unknown": "field"},
            {key: value for key, value in record.items() if key != "tenant"},
            {**record, "edges": [["api"], ["web", "api"]]},
            {**record, "services": "api,db,web"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ContextError):
                ServiceTopologySnapshot.from_record(invalid)

    def test_json_record_rejects_tampered_digest_and_content(self):
        record = snapshot().to_record()
        with self.assertRaisesRegex(ContextError, "snapshot_digest_mismatch"):
            ServiceTopologySnapshot.from_record({**record, "snapshot_digest": "0" * 64})

        with self.assertRaisesRegex(ContextError, "snapshot_digest_mismatch"):
            ServiceTopologySnapshot.from_record({**record, "source_sha": "b" * 40})

    def test_query_depth_and_service_bounds_remain_enforced(self):
        graph = snapshot()
        now = datetime(2026, 11, 2, 0, 1, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ContextError, "invalid_query"):
            graph.affected_by("alpha", "platform", "unknown", now=now)
        with self.assertRaisesRegex(ContextError, "invalid_query"):
            graph.affected_by("alpha", "platform", "db", now=now, depth=99)


if __name__ == "__main__":
    unittest.main()

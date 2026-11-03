"""Behavioral tests for offline, tenant-bound topology drift reports."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot
from devobs_intelligence.topology_drift import compare_topology_snapshots


def snapshot(*, services, edges, source_sha, captured_at,
             tenant="alpha", project="platform"):
    return ServiceTopologySnapshot(
        tenant, project, services, edges, source_sha, captured_at,
    )


class TopologyDriftTests(unittest.TestCase):
    def test_report_is_canonical_and_detects_added_nodes_edges_cycle_and_orphan(self):
        before = snapshot(
            services=["api", "db"], edges=[("api", "db")],
            source_sha="a" * 40, captured_at="2026-11-01T00:00:00Z",
        )
        after = snapshot(
            services=["worker", "web", "db", "api"],
            edges=[("web", "api"), ("db", "api"), ("api", "db")],
            source_sha="b" * 40, captured_at="2026-11-02T00:00:00Z",
        )
        reordered_after = snapshot(
            services=["api", "db", "web", "worker"],
            edges=[("api", "db"), ("web", "api"), ("db", "api")],
            source_sha="b" * 40, captured_at="2026-11-02T00:00:00Z",
        )

        record = compare_topology_snapshots(before, after).to_record()
        reordered_record = compare_topology_snapshots(
            before, reordered_after,
        ).to_record()
        self.assertEqual(record, reordered_record)
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["unverifiable_edges"], [
            {
                "edge": ["api", "db"],
                "status": "UNVERIFIABLE",
                "reason": "per_edge_source_metadata_absent",
            },
            {
                "edge": ["db", "api"],
                "status": "UNVERIFIABLE",
                "reason": "per_edge_source_metadata_absent",
            },
            {
                "edge": ["web", "api"],
                "status": "UNVERIFIABLE",
                "reason": "per_edge_source_metadata_absent",
            },
        ])
        self.assertEqual(record["added_services"], ["web", "worker"])
        self.assertEqual(record["added_edges"], [["db", "api"], ["web", "api"]])
        self.assertEqual(record["introduced_cycles"], [["api", "db"]])
        self.assertEqual(record["newly_isolated_services"], ["worker"])
        self.assertEqual(record["removed_services"], [])
        self.assertEqual(len(record["report_digest"]), 64)
        report_payload = {key: value for key, value in record.items()
                          if key != "report_digest"}
        expected_digest = hashlib.sha256(json.dumps(
            report_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")).hexdigest()
        self.assertEqual(record["report_digest"], expected_digest)

        record["added_services"].append("external-mutation")
        record["unverifiable_edges"][0]["edge"].append("external-mutation")
        self.assertEqual(compare_topology_snapshots(before, after).to_record(),
                         reordered_record)

    def test_report_detects_removed_edges_resolved_cycle_and_reconnected_service(self):
        before = snapshot(
            services=["api", "db", "worker"],
            edges=[("api", "db"), ("db", "api")],
            source_sha="a" * 40, captured_at="2026-11-01T00:00:00Z",
        )
        after = snapshot(
            services=["api", "db", "worker"],
            edges=[("api", "db"), ("worker", "api")],
            source_sha="a" * 40, captured_at="2026-11-02T00:00:00Z",
        )

        record = compare_topology_snapshots(before, after).to_record()
        self.assertEqual(record["removed_edges"], [["db", "api"]])
        self.assertEqual(record["resolved_cycles"], [["api", "db"]])
        self.assertEqual(record["reconnected_services"], ["worker"])
        self.assertEqual(record["introduced_cycles"], [])

    def test_empty_current_graph_has_no_unverifiable_edges(self):
        before = snapshot(
            services=["api"], edges=[], source_sha="a" * 40,
            captured_at="2026-11-01T00:00:00Z",
        )
        after = snapshot(
            services=["api"], edges=[], source_sha="b" * 40,
            captured_at="2026-11-02T00:00:00Z",
        )

        record = compare_topology_snapshots(before, after).to_record()
        self.assertEqual(record["unverifiable_edges"], [])

    def test_comparison_rejects_scope_mismatch_and_nonincreasing_time(self):
        before = snapshot(
            services=["api"], edges=[], source_sha="a" * 40,
            captured_at="2026-11-02T00:00:00Z",
        )
        for after, error in (
            (snapshot(services=["api"], edges=[], source_sha="b" * 40,
                      captured_at="2026-11-02T00:01:00Z", tenant="beta"),
             "topology_scope_mismatch"),
            (snapshot(services=["api"], edges=[], source_sha="b" * 40,
                      captured_at="2026-11-02T00:01:00Z", project="other"),
             "topology_scope_mismatch"),
            (snapshot(services=["api"], edges=[], source_sha="b" * 40,
                      captured_at="2026-11-02T00:00:00Z"),
             "invalid_topology_order"),
            (snapshot(services=["api"], edges=[], source_sha="b" * 40,
                      captured_at="2026-11-01T23:59:00Z"),
             "invalid_topology_order"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ContextError, error):
                compare_topology_snapshots(before, after)

    def test_comparison_revalidates_snapshot_instances_and_rejects_wrong_type(self):
        before = snapshot(
            services=["api"], edges=[], source_sha="a" * 40,
            captured_at="2026-11-01T00:00:00Z",
        )
        after = snapshot(
            services=["api"], edges=[], source_sha="b" * 40,
            captured_at="2026-11-02T00:00:00Z",
        )
        object.__setattr__(after, "snapshot_digest", "0" * 64)
        with self.assertRaisesRegex(ContextError, "invalid_topology_snapshot"):
            compare_topology_snapshots(before, after)
        with self.assertRaisesRegex(ContextError, "invalid_topology_snapshot"):
            compare_topology_snapshots(before, json.loads("{}"))


if __name__ == "__main__":
    unittest.main()

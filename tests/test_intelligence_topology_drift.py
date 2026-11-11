"""Behavioral tests for offline, tenant-bound topology drift reports."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot
from devobs_intelligence.topology_drift import (
    compare_attested_topology_snapshots,
    compare_topology_snapshots,
)
from devobs_intelligence.topology_attestation import RotatingTopologyKeyring

_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
_ATTESTATION_DOMAIN = b"devobs-topology-attestation-v1\n"


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

    def test_removed_isolated_service_is_not_reported_as_reconnected(self):
        before = snapshot(
            services=["api", "db", "retired"], edges=[("api", "db")],
            source_sha="a" * 40, captured_at="2026-11-01T00:00:00Z",
        )
        after = snapshot(
            services=["api", "db"], edges=[("api", "db")],
            source_sha="b" * 40, captured_at="2026-11-02T00:00:00Z",
        )

        report = compare_topology_snapshots(before, after)

        self.assertEqual(report.removed_services, ("retired",))
        self.assertEqual(report.reconnected_services, ())

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


class AttestedTopologyDriftTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.keyring = {("alpha", "platform", "collector-1"): public_key}

    def signed(self, topology):
        payload = {
            "schema_version": 1,
            "key_id": "collector-1",
            "snapshot": topology.to_record(),
        }
        signed_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        signature = self.private_key.sign(
            _ATTESTATION_DOMAIN + signed_bytes,
        ).hex()
        return {**payload, "signature": signature}

    def compare(self, before, after, **overrides):
        options = {
            "expected_tenant": "alpha",
            "expected_project": "platform",
            "expected_before_source_sha": "a" * 40,
            "expected_after_source_sha": "b" * 40,
            "now": _NOW,
            "max_age_seconds": 60,
        }
        options.update(overrides)
        return compare_attested_topology_snapshots(
            before, after, self.keyring, **options,
        )

    def pair(self):
        before = snapshot(
            services=["api", "db"], edges=[("api", "db")],
            source_sha="a" * 40,
            captured_at=(_NOW - timedelta(seconds=40)).isoformat(
                timespec="microseconds").replace("+00:00", "Z"),
        )
        after = snapshot(
            services=["api", "db", "worker"],
            edges=[("api", "db"), ("worker", "api")],
            source_sha="b" * 40,
            captured_at=(_NOW - timedelta(seconds=10)).isoformat(
                timespec="microseconds").replace("+00:00", "Z"),
        )
        return self.signed(before), self.signed(after)

    def test_valid_signed_pair_returns_deterministic_provenance_bound_report(self):
        before, after = self.pair()
        report = self.compare(before, after)
        record = report.to_record()

        self.assertEqual(report.before_key_id, "collector-1")
        self.assertEqual(report.after_key_id, "collector-1")
        self.assertEqual(record["drift"]["added_services"], ["worker"])
        self.assertEqual(record["drift"]["unverifiable_edges"][0]["status"],
                         "UNVERIFIABLE")
        self.assertEqual(record, self.compare(before, after).to_record())
        self.assertEqual(len(record["before_attestation"]["digest"]), 64)
        self.assertEqual(len(record["after_attestation"]["digest"]), 64)
        self.assertEqual(len(record["attested_report_digest"]), 64)
        self.assertNotIn("signature", json.dumps(record))
        self.assertNotIn("public_key", json.dumps(record))

    def test_both_signatures_and_each_expected_source_sha_are_required(self):
        before, after = self.pair()
        with self.assertRaisesRegex(ContextError, "^invalid_topology_attestation_signature$"):
            self.compare(before, {**after, "signature": "0" * 128})
        with self.assertRaisesRegex(ContextError, "^topology_source_sha_mismatch$"):
            self.compare(before, after, expected_after_source_sha="c" * 40)

    def test_both_snapshots_must_be_fresh_and_share_expected_scope(self):
        before, after = self.pair()
        stale_snapshot = snapshot(
            services=["api"], edges=[], source_sha="a" * 40,
            captured_at=(_NOW - timedelta(hours=2)).isoformat(
                timespec="microseconds").replace("+00:00", "Z"),
        )
        with self.assertRaisesRegex(ContextError, "^stale_topology$"):
            self.compare(self.signed(stale_snapshot), after)
        with self.assertRaisesRegex(ContextError, "^topology_scope_mismatch$"):
            self.compare(before, after, expected_project="other")

    def test_nonincreasing_attested_capture_time_is_rejected(self):
        before, after = self.pair()
        same_time = snapshot(
            services=["api", "db", "worker"],
            edges=[("api", "db"), ("worker", "api")],
            source_sha="b" * 40,
            captured_at=(_NOW - timedelta(seconds=40)).isoformat(
                timespec="microseconds").replace("+00:00", "Z"),
        )
        with self.assertRaisesRegex(ContextError, "^invalid_topology_order$"):
            self.compare(before, self.signed(same_time))

    def test_rotating_keyring_is_snapshotted_once_for_the_pair(self):
        before, after = self.pair()
        operator_key = Ed25519PrivateKey.generate()
        operator_public_key = operator_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        rotating = RotatingTopologyKeyring(
            self.keyring, operator_public_keys={"operator-1": operator_public_key},
        )

        with patch.object(rotating, "snapshot", wraps=rotating.snapshot) as snapshot:
            result = compare_attested_topology_snapshots(
                before, after, rotating,
                expected_tenant="alpha",
                expected_project="platform",
                expected_before_source_sha="a" * 40,
                expected_after_source_sha="b" * 40,
                now=_NOW,
                max_age_seconds=60,
            )

        self.assertEqual(snapshot.call_count, 1)
        self.assertEqual(result.before_key_id, "collector-1")
        self.assertEqual(result.after_key_id, "collector-1")


if __name__ == "__main__":
    unittest.main()

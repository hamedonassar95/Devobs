"""Behavioral topological correlation tests; no model or remote endpoints."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from devobs_intelligence.context import (
    ContextError, normalize_telemetry, ServiceTopology, ServiceTopologySnapshot,
    Telemetry,
)
from devobs_intelligence.incident_memory import IncidentRecord,IncidentMemory
from devobs_intelligence.correlation import correlate

NOW=datetime(2026,10,25,1,0,tzinfo=timezone.utc)


def data(service,metric,value,digest,tenant="alpha",sha="a"*40,age=0):
    return normalize_telemetry({
        "tenant":tenant,"project":"platform","service":service,
        "source_sha":sha,"observed_at":(NOW-timedelta(seconds=age)).isoformat(),
        "metric":metric,"value":value,"evidence_digest":digest*64
    })


def graph():
    return ServiceTopology("alpha","platform",["db","api","web"],
                           [("api","db"),("web","api")])


def snapshot(**overrides):
    values = {
        "tenant": "alpha",
        "project": "platform",
        "services": ["db", "api", "web"],
        "edges": [("api", "db"), ("web", "api")],
        "source_sha": "a" * 40,
        "captured_at": NOW.isoformat(),
    }
    values.update(overrides)
    return ServiceTopologySnapshot(**values)


def memory():
    return IncidentMemory([
        IncidentRecord("alpha","platform","db","high_error_rate",
                       "RB-SLO-01","resolved","f"*64),
        IncidentRecord("beta","platform","db","high_error_rate",
                       "RB-CAP-01","resolved","e"*64),
    ])


def provenanced_memory(recorded_at=NOW.isoformat()):
    return IncidentMemory([
        IncidentRecord("alpha", "platform", "db", "high_error_rate",
                       "RB-SLO-01", "resolved", "c" * 64,
                       "b" * 40, recorded_at),
    ])


class IncidentCorrelationTests(unittest.TestCase):
    def test_rank_and_topology_are_evidence_bound(self):
        report=correlate(graph(),[
            data("db","error_rate_pct",9,"b"),
            data("api","capacity_pct",91,"c"),
            data("web","capacity_pct",88,"d"),
        ],memory(),NOW)
        self.assertEqual(report.ranked_services,("db","api","web"))
        self.assertEqual(report.impacted_services,("api","db","web"))
        self.assertEqual(report.runbook_ids,("RB-SLO-01",))
        self.assertEqual(report.status,"PENDING_HUMAN_APPROVAL")
        self.assertFalse(report.model_used)
        self.assertFalse(report.calibrated)
        self.assertIsNone(report.topology_snapshot_digest)

    def test_fresh_snapshot_is_bound_to_correlation_result_provenance(self):
        topology = snapshot()
        report = correlate(topology, [data("db", "error_rate_pct", 9, "b")],
                           memory(), NOW)
        self.assertEqual(report.impacted_services, ("api", "db", "web"))
        self.assertEqual(report.topology_snapshot_digest, topology.snapshot_digest)
        self.assertEqual(report.topology_captured_at, topology.captured_at)

    def test_snapshot_rejects_stale_cross_scope_and_mismatched_source(self):
        stale = snapshot(captured_at=(NOW - timedelta(seconds=901)).isoformat())
        with self.assertRaisesRegex(ContextError, "stale_topology"):
            correlate(stale, [data("db", "error_rate_pct", 9, "b")], memory(), NOW)

        with self.assertRaisesRegex(ContextError, "invalid_incident_scope"):
            correlate(snapshot(tenant="beta"),
                      [data("db", "error_rate_pct", 9, "b")], memory(), NOW)

        with self.assertRaisesRegex(ContextError, "topology_source_sha_mismatch"):
            correlate(snapshot(source_sha="c" * 40),
                      [data("db", "error_rate_pct", 9, "b")], memory(), NOW)

    def test_snapshot_instances_are_revalidated_before_use(self):
        forged = snapshot()
        object.__setattr__(forged, "source_sha", "not-a-sha")
        with self.assertRaisesRegex(ContextError, "invalid_topology_snapshot"):
            correlate(forged, [data("db", "error_rate_pct", 9, "b")], memory(), NOW)

    def test_snapshot_provenance_is_returned_when_correlation_abstains(self):
        topology = snapshot()
        report = correlate(topology, [data("api", "capacity_pct", 15, "b")],
                           memory(), NOW)
        self.assertEqual(report.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(report.topology_snapshot_digest, topology.snapshot_digest)
        self.assertEqual(report.topology_captured_at, topology.captured_at)

    def test_snapshot_correlation_requires_explicit_memory_freshness(self):
        topology = snapshot()
        telemetry = [data("db", "error_rate_pct", 9, "b")]
        legacy = correlate(topology, telemetry, memory(), NOW)
        self.assertEqual(legacy.runbook_ids, ())
        self.assertEqual(legacy.memory_provenance, ())

        report = correlate(topology, telemetry, provenanced_memory(), NOW,
                           memory_max_age_seconds=60)
        self.assertEqual(report.runbook_ids, ("RB-SLO-01",))
        self.assertEqual(len(report.memory_provenance), 1)
        self.assertEqual(report.memory_provenance[0].source_sha, "b" * 40)
        self.assertEqual(report.memory_provenance[0].evidence_digest, "c" * 64)
        record_digest = getattr(report.memory_provenance[0], "record_digest", None)
        self.assertIsNotNone(record_digest, "findings must expose the exact memory record digest")
        expected_record = provenanced_memory().retrieve_provenanced(
            "alpha", "platform", "db", "high_error_rate", now=NOW,
            max_age_seconds=60,
        )[0]
        self.assertEqual(record_digest, expected_record.record_digest)

        stale = correlate(topology, telemetry,
                          provenanced_memory((NOW - timedelta(hours=1)).isoformat()),
                          NOW, memory_max_age_seconds=60)
        self.assertEqual(stale.runbook_ids, ())
        with self.assertRaisesRegex(ContextError, "invalid_query"):
            correlate(topology, telemetry, provenanced_memory(), NOW,
                      memory_max_age_seconds=0)

    def test_no_evidence_does_not_propose_false_root(self):
        report=correlate(graph(),[data("api","capacity_pct",15,"b")],memory(),NOW)
        self.assertEqual(report.status,"INSUFFICIENT_EVIDENCE")
        self.assertEqual(report.ranked_services,())

    def test_cross_tenant_evidence_rejected(self):
        with self.assertRaisesRegex(ContextError,"invalid_incident_scope"):
            correlate(graph(),[data("db","error_rate_pct",9,"b",tenant="beta")],memory(),NOW)

    def test_stale_or_future_evidence_rejected(self):
        for age in (901,-61):
            with self.subTest(age=age),self.assertRaisesRegex(ContextError,"stale_evidence"):
                correlate(graph(),[data("db","error_rate_pct",9,"b",age=age)],memory(),NOW)

    def test_mismatched_sha_and_duplicate_metrics_rejected(self):
        with self.assertRaisesRegex(ContextError,"mixed_source_sha"):
            correlate(graph(),[data("db","error_rate_pct",9,"b"),
                               data("api","error_rate_pct",8,"c",sha="c"*40)],memory(),NOW)
        with self.assertRaisesRegex(ContextError,"duplicate_evidence"):
            correlate(graph(),[data("db","capacity_pct",90,"b"),
                               data("db","capacity_pct",92,"c")],memory(),NOW)

    def test_graph_missing_service_rejected(self):
        with self.assertRaises(ContextError):
            correlate(graph(),[data("external","error_rate_pct",9,"b")],memory(),NOW)

    def test_directly_forged_telemetry_cannot_bypass_contract(self):
        forged=Telemetry("alpha","platform","db","a"*40,
                         "2026-10-25T01:00:00Z","capacity_pct",
                         float("nan"),"b"*64)
        with self.assertRaisesRegex(ContextError,"invalid_value"):
            correlate(graph(),[forged],memory(),NOW)

    def test_no_memorized_customer_data_is_shared(self):
        other=IncidentMemory([IncidentRecord("beta","platform","db",
                                             "high_error_rate","RB-SLO-01",
                                             "resolved","f"*64)])
        report=correlate(graph(),[data("db","error_rate_pct",6,"b")],other,NOW)
        self.assertEqual(report.runbook_ids,())

    def test_deployment_and_scaling_not_executable(self):
        report=correlate(graph(),[data("db","failed_checks",1,"b")],memory(),NOW)
        self.assertEqual(report.category,"ci_failure")
        self.assertNotIn("APPROVED",str(report))


if __name__=="__main__": unittest.main()

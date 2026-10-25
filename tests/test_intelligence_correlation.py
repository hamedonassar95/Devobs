"""Behavioral topological correlation tests; no model or remote endpoints."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from devobs_intelligence.context import ContextError,normalize_telemetry,ServiceTopology,Telemetry
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


def memory():
    return IncidentMemory([
        IncidentRecord("alpha","platform","db","high_error_rate",
                       "RB-SLO-01","resolved","f"*64),
        IncidentRecord("beta","platform","db","high_error_rate",
                       "RB-CAP-01","resolved","e"*64),
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

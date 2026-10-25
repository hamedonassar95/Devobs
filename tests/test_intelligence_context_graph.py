"""Offline behavioral tests: numeric telemetry, graph, isolation, bounded retrieval."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from devobs_intelligence.context import ContextError,normalize_telemetry,ServiceTopology
from devobs_intelligence.incident_memory import IncidentRecord,IncidentMemory


def sample(**overrides):
    value={"tenant":"alpha","project":"platform","service":"api",
           "source_sha":"a"*40,"observed_at":"2026-10-25T00:00:00Z",
           "metric":"error_rate_pct","value":8.0,"evidence_digest":"b"*64}
    value.update(overrides)
    return value


def memory(tenant="alpha",service="api",digest="c"*64,outcome="resolved"):
    return IncidentRecord(tenant,"platform",service,"high_error_rate",
                          "RB-SLO-01",outcome,digest)


class ContextTests(unittest.TestCase):
    def test_strict_telemetry_and_timestamp(self):
        p=normalize_telemetry(sample())
        self.assertEqual(p.source_sha,"a"*40)
        self.assertEqual(p.observed_at,"2026-10-25T00:00:00Z")

    def test_failed_check_counter_remains_integer_after_normalization(self):
        point=normalize_telemetry(sample(metric="failed_checks",value=2))
        self.assertEqual(point.value,2)
        self.assertIs(type(point.value),int)
        self.assertEqual(point,normalize_telemetry({
            "tenant":point.tenant,"project":point.project,"service":point.service,
            "source_sha":point.source_sha,"observed_at":point.observed_at,
            "metric":point.metric,"value":point.value,
            "evidence_digest":point.evidence_digest}))

    def test_unknown_unstructured_field_rejected(self):
        with self.assertRaisesRegex(ContextError,"invalid_fields"):
            normalize_telemetry(sample(raw_payload="unstructured"))
        with self.assertRaisesRegex(ContextError,"invalid_metric"):
            normalize_telemetry(sample(metric="arbitrary_text"))

    def test_bad_metrics_naive_time_and_sha_rejected(self):
        for override in ({"value":float("nan")},{"value":True},{"value":-1},
                         {"metric":"failed_checks","value":1.25},
                         {"observed_at":"2026-10-25T00:00:00"},
                         {"source_sha":"short"}):
            with self.subTest(value=override),self.assertRaises(ContextError):
                normalize_telemetry(sample(**override))

    def test_topology_transitive_impact_even_if_cyclic(self):
        graph=ServiceTopology("alpha","platform",["api","db","web","worker"],
                              [("api","db"),("web","api"),("db","api"),("worker","db")])
        self.assertEqual(graph.affected_by("db",0),("db",))
        self.assertEqual(graph.affected_by("db",3),("api","db","web","worker"))

    def test_unknown_topology_edges_and_duplicates_rejected(self):
        for edges in ([("api","missing")],[("api","api")],
                      [("api","db"),("api","db")]):
            with self.subTest(edges=edges),self.assertRaises(ContextError):
                ServiceTopology("alpha","platform",["api","db"],edges)

    def test_untrusted_unhashable_scope_objects_fail_closed(self):
        with self.assertRaisesRegex(ContextError,"invalid_topology"):
            ServiceTopology("alpha","platform",[{"not":"service"}],[])
        with self.assertRaisesRegex(ContextError,"invalid_memory"):
            IncidentRecord("alpha","platform","api","high_error_rate",
                           "RB-SLO-01",[], "c"*64)
        with self.assertRaisesRegex(ContextError,"invalid_query"):
            IncidentMemory([]).retrieve("alpha","platform","api",[])

    def test_memory_strict_tenant_project_and_positive_outcomes(self):
        m=IncidentMemory([memory(),memory("beta"),memory(digest="d"*64),
                          memory(digest="e"*64,outcome="false_positive")])
        found=m.retrieve("alpha","platform","api","high_error_rate")
        self.assertEqual(len(found),2)
        self.assertTrue(all(r.tenant=="alpha" for r in found))
        self.assertEqual(m.retrieve("beta","platform","api","high_error_rate")[0].tenant,"beta")
        self.assertEqual(m.retrieve("alpha","platform","db","high_error_rate"),())

    def test_memory_duplicates_and_freeform_runbooks_rejected(self):
        with self.assertRaises(ContextError):
            IncidentMemory([memory(),memory()])
        with self.assertRaises(ContextError):
            IncidentRecord("alpha","platform","api","high_error_rate",
                           "unreviewed note","resolved","c"*64)
        with self.assertRaises(ContextError):
            IncidentMemory([{"sample":"not-schema"}])

    def test_memory_results_are_bounded(self):
        m=IncidentMemory([memory(digest=chr(97+i)*64) for i in range(5)])
        self.assertEqual(len(m.retrieve("alpha","platform","api","high_error_rate",2)),2)
        with self.assertRaises(ContextError):
            m.retrieve("alpha","platform","api","high_error_rate",99)


if __name__=="__main__": unittest.main()

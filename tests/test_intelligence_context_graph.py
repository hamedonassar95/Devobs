"""Offline behavioral tests: numeric telemetry, graph, isolation, bounded retrieval."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
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


def provenanced_memory(*, tenant="alpha", digest="c"*64, source_sha="a"*40,
                       recorded_at="2026-10-25T00:00:00Z"):
    return IncidentRecord(tenant, "platform", "api", "high_error_rate",
                          "RB-SLO-01", "resolved", digest, source_sha, recorded_at)


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

    def test_memory_defensively_copies_input_and_returned_records(self):
        original = memory()
        store = IncidentMemory([original])
        object.__setattr__(original, "tenant", "beta")
        found = store.retrieve("alpha", "platform", "api", "high_error_rate")
        self.assertEqual(found[0].tenant, "alpha")
        object.__setattr__(found[0], "runbook_id", "RB-SEC-99")
        again = store.retrieve("alpha", "platform", "api", "high_error_rate")
        self.assertEqual(again[0].runbook_id, "RB-SLO-01")

    def test_provenanced_memory_requires_source_and_freshness_and_is_tenant_scoped(self):
        now = datetime(2026, 10, 25, 0, 5, tzinfo=timezone.utc)
        store = IncidentMemory([
            provenanced_memory(digest="c" * 64),
            provenanced_memory(digest="d" * 64, tenant="beta"),
            memory(digest="e" * 64),
            provenanced_memory(digest="f" * 64,
                               recorded_at=(now - timedelta(hours=2)).isoformat()),
            provenanced_memory(digest="1" * 64,
                               recorded_at=(now + timedelta(seconds=1)).isoformat()),
        ])
        fresh = store.retrieve_provenanced(
            "alpha", "platform", "api", "high_error_rate", now=now,
            max_age_seconds=600,
        )
        self.assertEqual([row.evidence_digest for row in fresh], ["c" * 64])
        self.assertEqual(fresh[0].source_sha, "a" * 40)
        self.assertEqual(fresh[0].recorded_at, "2026-10-25T00:00:00.000000Z")

    def test_memory_provenance_fields_are_an_all_or_nothing_valid_pair(self):
        for source_sha, recorded_at in (("a" * 40, None), (None, "2026-10-25T00:00:00Z"),
                                         ("short", "2026-10-25T00:00:00Z"),
                                         ("a" * 40, "2026-10-25T00:00:00")):
            with self.subTest(source_sha=source_sha, recorded_at=recorded_at):
                with self.assertRaises(ContextError):
                    provenanced_memory(source_sha=source_sha, recorded_at=recorded_at)

    def test_incident_record_wire_contract_roundtrips_legacy_and_provenanced_records(self):
        for original in (memory(), provenanced_memory()):
            with self.subTest(provenanced=original.source_sha is not None):
                to_record = getattr(original, "to_record", None)
                if not callable(to_record):
                    self.fail("IncidentRecord must expose a JSON-compatible record contract")
                wire_record = to_record()
                self.assertEqual(wire_record["schema_version"], 1)
                self.assertEqual(wire_record["record_digest"], original.record_digest)
                restored = IncidentRecord.from_record(json.loads(json.dumps(wire_record)))
                self.assertEqual(restored, original)

    def test_incident_record_wire_contract_rejects_tampering_and_unknown_shapes(self):
        original = provenanced_memory()
        record = original.to_record()
        for changed in (
                {**record, "runbook_id": "RB-SEC-01"},
                {**record, "schema_version": True},
                {**record, "unknown": "value"},
                {key: value for key, value in record.items() if key != "record_digest"},
                {**record, "schema_version": 2},
        ):
            with self.subTest(record=changed), self.assertRaises(ContextError):
                IncidentRecord.from_record(changed)

    def test_incident_memory_bundle_roundtrips_deterministically(self):
        records = [memory(digest="d" * 64), provenanced_memory(),
                   memory(tenant="beta", digest="e" * 64)]
        first = IncidentMemory(records).to_bundle()
        second = IncidentMemory(list(reversed(records))).to_bundle()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], 1)
        self.assertEqual(len(first["records"]), 3)
        restored = IncidentMemory.from_bundle(json.loads(json.dumps(first)))
        self.assertEqual(restored.to_bundle(), first)
        self.assertEqual(
            [row.evidence_digest for row in restored.retrieve(
                "alpha", "platform", "api", "high_error_rate")],
            ["c" * 64, "d" * 64],
        )
        noncanonical = json.loads(json.dumps(first))
        noncanonical["records"].reverse()
        payload = {"schema_version": noncanonical["schema_version"],
                   "records": noncanonical["records"]}
        noncanonical["bundle_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")).hexdigest()
        with self.assertRaisesRegex(ContextError, "noncanonical_memory_bundle"):
            IncidentMemory.from_bundle(noncanonical)

    def test_incident_memory_bundle_rejects_corruption_and_unknown_shapes(self):
        bundle = IncidentMemory([provenanced_memory()]).to_bundle()
        tampered = json.loads(json.dumps(bundle))
        tampered["records"][0]["outcome"] = "false_positive"
        with self.assertRaisesRegex(ContextError, "memory_record_digest_mismatch"):
            IncidentMemory.from_bundle(tampered)

        tampered = json.loads(json.dumps(bundle))
        tampered["bundle_digest"] = "0" * 64
        with self.assertRaisesRegex(ContextError, "memory_bundle_digest_mismatch"):
            IncidentMemory.from_bundle(tampered)

        for changed in (
                {**bundle, "unexpected": True},
                {**bundle, "schema_version": 2},
                {**bundle, "schema_version": True},
                {**bundle, "records": "not-a-list"},
        ):
            with self.subTest(bundle=changed), self.assertRaises(ContextError):
                IncidentMemory.from_bundle(changed)

    def test_incident_memory_bundle_rejects_invalid_or_duplicate_members_atomically(self):
        record = memory().to_record()
        for records in ([record, {"invalid": True}], [record, record]):
            payload = {"schema_version": 1, "records": records}
            bundle = {**payload, "bundle_digest": hashlib.sha256(json.dumps(
                payload, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")).hexdigest()}
            with self.subTest(records=records), self.assertRaises(ContextError):
                IncidentMemory.from_bundle(bundle)

        too_many = {"schema_version": 1, "records": [record] * 1001,
                    "bundle_digest": "0" * 64}
        with self.assertRaisesRegex(ContextError, "invalid_memory_bundle"):
            IncidentMemory.from_bundle(too_many)


if __name__=="__main__": unittest.main()

"""Behavioral tests for binding offline findings to the audit hash chain."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.audit_store import AuditError, AuditStore
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.correlation import IncidentFinding, correlate
from devobs_intelligence.context import normalize_telemetry, ServiceTopology
from devobs_intelligence.incident_memory import IncidentMemory


def event(*, project_ref="alpha/platform", source_sha="a" * 40,
          evidence_digest="b" * 64):
    return parse_event({
        "schema_version": 1, "event_id": "incident-01", "provider": "github",
        "project_ref": project_ref, "source_sha": source_sha, "kind": "incident",
        "observed_at": "2026-11-02T12:00:00Z",
        "evidence_digests": [evidence_digest],
    })


def finding(*, source_sha="a" * 40, tenant="alpha", project="platform",
            evidence_digest="b" * 64):
    topology = ServiceTopology(tenant, project, ["api"], [])
    point = normalize_telemetry({
        "tenant": tenant, "project": project, "service": "api",
        "source_sha": source_sha, "observed_at": "2026-11-02T12:00:00Z",
        "metric": "error_rate_pct", "value": 8.0,
        "evidence_digest": evidence_digest,
    })
    now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    return correlate(topology, [point], IncidentMemory([]), now)


def changed_category(result):
    record = result.to_record()
    record["category"] = "capacity_pressure"
    payload = {key: value for key, value in record.items() if key != "finding_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    record["finding_digest"] = hashlib.sha256(encoded).hexdigest()
    return IncidentFinding.from_record(record)


class IncidentFindingAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "audit.sqlite3")
        self.store = AuditStore(self.path)
        self.addCleanup(self.store.close)

    def test_finding_digest_is_bound_to_a_verified_audit_chain_entry(self):
        source = event()
        result = finding()

        entry = self.store.append_finding(source, result)

        self.assertEqual(entry.action, "read_evidence")
        self.assertEqual(entry.subject_digest, result.to_record()["finding_digest"])
        self.assertEqual(self.store.verify(), 1)
        self.assertEqual(self.store.summary()["record_count"], 1)
        self.assertNotIn("alpha/platform", str(entry))

    def test_finding_write_is_idempotent_but_rejects_changed_result(self):
        source = event()
        first = self.store.append_finding(source, finding())

        self.assertEqual(self.store.append_finding(source, finding()), first)
        changed = changed_category(finding())
        with self.assertRaisesRegex(AuditError, "duplicate_conflict"):
            self.store.append_finding(source, changed)

    def test_finding_must_match_project_source_and_evidence(self):
        result = finding()
        bad_events = (
            event(project_ref="beta/platform"),
            event(source_sha="c" * 40),
            event(evidence_digest="c" * 64),
        )
        for source in bad_events:
            with self.subTest(event=source):
                with self.assertRaisesRegex(AuditError, "invalid_finding_binding"):
                    self.store.append_finding(source, result)

    def test_generic_append_rejects_evaluation_for_a_different_action(self):
        source = event()
        from devobs_intelligence.policy import evaluate_action
        with self.assertRaisesRegex(AuditError, "invalid_entry"):
            self.store.append(source, evaluate_action(source, "read_evidence"), "deploy")

    def test_v1_database_migrates_without_invalidating_existing_hashes(self):
        legacy_path = str(Path(self.temp.name) / "legacy.sqlite3")
        previous = "0" * 64
        item = {
            "event_id": "legacy-01", "source_sha": "a" * 40,
            "policy_version": "devobs-policy-v1", "decision": "ALLOW_READ",
            "action": "read_evidence",
        }
        encoded = json.dumps(item, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True)
        record_hash = hashlib.sha256((previous + "\n" + encoded).encode()).hexdigest()
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            "CREATE TABLE audit (seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            "event_id TEXT NOT NULL,source_sha TEXT NOT NULL,policy_version TEXT NOT NULL,"
            "decision TEXT NOT NULL,action TEXT NOT NULL,previous_hash TEXT NOT NULL,"
            "record_hash TEXT NOT NULL,UNIQUE(event_id, action))")
        connection.execute(
            "INSERT INTO audit (event_id,source_sha,policy_version,decision,action,"
            "previous_hash,record_hash) VALUES (?,?,?,?,?,?,?)",
            (item["event_id"], item["source_sha"], item["policy_version"],
             item["decision"], item["action"], previous, record_hash))
        connection.commit()
        connection.close()
        migrated = AuditStore(legacy_path)
        self.addCleanup(migrated.close)

        self.assertEqual(migrated.verify(), 1)
        self.assertIsNone(migrated._entries()[0].subject_digest)

    def test_subject_digest_tampering_invalidates_hash_chain(self):
        source = event()
        self.store.append_finding(source, finding())
        self.store.connection.execute(
            "UPDATE audit SET subject_digest=? WHERE seq=1", ("c" * 64,))
        with self.assertRaisesRegex(AuditError, "chain_invalid"):
            self.store.verify()


if __name__ == "__main__":
    unittest.main()

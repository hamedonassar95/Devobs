"""Offline Ed25519 verification tests for curated incident-memory records."""
import hashlib
import json
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import (
    ContextError, ServiceTopologySnapshot, normalize_telemetry,
)
from devobs_intelligence.correlation import IncidentFinding, correlate
from devobs_intelligence.incident_memory import IncidentMemory, IncidentRecord
from devobs_intelligence.incident_memory_approval import IncidentMemoryApprovalRegistry

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds").replace("+00:00", "Z")


class IncidentMemoryApprovalTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.keyring = {("alpha", "platform", "curator-1"): self.public_key}
        self.registry = IncidentMemoryApprovalRegistry()

    def test_signed_import_requires_explicit_replay_registry(self):
        with self.assertRaisesRegex(ContextError,
                                    "invalid_memory_approval_registry"):
            IncidentMemory.from_approved_envelopes(
                [self.approval()], self.keyring, now=NOW,
                consumption_registry=None,
            )

    def test_approval_id_cannot_be_consumed_twice_by_one_registry(self):
        envelope = self.approval()
        self.load_memory([envelope])
        with self.assertRaisesRegex(ContextError, "replayed_memory_approval"):
            self.load_memory([envelope])

    def test_reissued_payload_cannot_reuse_a_consumed_approval_id(self):
        self.load_memory([self.approval()])
        reissued = self.approval(
            record=self.record(evidence_digest="d" * 64),
        )
        with self.assertRaisesRegex(ContextError, "replayed_memory_approval"):
            self.load_memory([reissued])

    def test_failed_batch_does_not_partially_consume_valid_approvals(self):
        first = self.approval(approval_id="1" * 32)
        second = self.approval(
            record=self.record(evidence_digest="d" * 64),
            approval_id="2" * 32,
        )
        malformed = {**second, "signature": "00" * 64}
        with self.assertRaises(ContextError):
            self.load_memory([first, malformed])
        self.load_memory([first])

    def test_registry_capacity_fails_closed_without_evicting_claims(self):
        registry = IncidentMemoryApprovalRegistry(max_entries=1)
        first = self.approval(approval_id="1" * 32)
        second = self.approval(
            record=self.record(evidence_digest="d" * 64),
            approval_id="2" * 32,
        )
        with self.assertRaisesRegex(ContextError, "memory_approval_registry_full"):
            self.load_memory([first, second], consumption_registry=registry)
        self.load_memory([first], consumption_registry=registry)
        with self.assertRaisesRegex(ContextError, "memory_approval_registry_full"):
            self.load_memory([second], consumption_registry=registry)
        with self.assertRaisesRegex(ContextError,
                                    "invalid_memory_approval_registry"):
            IncidentMemoryApprovalRegistry(max_entries=True)

    def test_concurrent_replay_has_exactly_one_successful_consumer(self):
        envelope = self.approval()
        barrier = Barrier(8)

        def consume_once(_):
            barrier.wait(timeout=5)
            try:
                self.load_memory([envelope])
                return "accepted"
            except ContextError as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(consume_once, range(8)))
        self.assertEqual(outcomes.count("accepted"), 1)
        self.assertEqual(outcomes.count("replayed_memory_approval"), 7)

    def record(self, **overrides):
        fields = {
            "tenant": "alpha", "project": "platform", "service": "db",
            "category": "high_error_rate", "runbook_id": "RB-SLO-01",
            "outcome": "resolved", "evidence_digest": "c" * 64,
            "source_sha": "a" * 40,
            "recorded_at": stamp(NOW - timedelta(minutes=5)),
        }
        fields.update(overrides)
        return IncidentRecord(**fields)

    def approval(self, *, record=None, approval_id="1" * 32,
                 approver_id="curator-1", approved_at=None, expires_at=None):
        payload = {
            "schema_version": 1,
            "approval_id": approval_id,
            "approver_id": approver_id,
            "approved_at": stamp(approved_at or NOW - timedelta(minutes=1)),
            "expires_at": stamp(expires_at or NOW + timedelta(hours=1)),
            "record": (record or self.record()).to_record(),
        }
        return {
            **payload,
            "signature": self.private_key.sign(canonical_bytes(payload)).hex(),
        }

    def load_memory(self, envelopes, keyring=None, *, now=NOW,
                    consumption_registry=None):
        if keyring is None:
            keyring = self.keyring
        if consumption_registry is None:
            consumption_registry = self.registry
        return IncidentMemory.from_approved_envelopes(
            envelopes, keyring, now=now,
            consumption_registry=consumption_registry,
        )

    def test_signed_records_load_atomically_and_keep_curator_provenance(self):
        envelope = self.approval()
        store = self.load_memory(
            [envelope], self.keyring, now=NOW,
        )
        row = store.retrieve_provenanced(
            "alpha", "platform", "db", "high_error_rate",
            now=NOW, max_age_seconds=600,
        )[0]
        approval = store.approval_provenance_for(row)
        self.assertEqual(approval.approval_id, "1" * 32)
        self.assertEqual(approval.approver_id, "curator-1")
        self.assertEqual(approval.record_digest, row.record_digest)
        self.assertEqual(len(approval.approval_digest), 64)

        topology = ServiceTopologySnapshot(
            "alpha", "platform", ["db"], [], "a" * 40, stamp(NOW),
        )
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": "a" * 40, "observed_at": stamp(NOW),
            "metric": "error_rate_pct", "value": 9.0,
            "evidence_digest": "b" * 64,
        })
        finding = correlate(
            topology, [telemetry], store, NOW, memory_max_age_seconds=600,
        )
        evidence = finding.memory_provenance[0]
        self.assertEqual(evidence.approval_id, approval.approval_id)
        self.assertEqual(evidence.approver_id, approval.approver_id)
        self.assertEqual(evidence.approval_digest, approval.approval_digest)

        wire_finding = finding.to_record()
        restored_finding = IncidentFinding.from_record(
            json.loads(json.dumps(wire_finding)),
        )
        self.assertEqual(restored_finding, finding)
        self.assertEqual(wire_finding["memory_provenance"][0]["approval_id"],
                         approval.approval_id)

    def test_signature_binds_record_identity_approval_and_expiry(self):
        original = self.approval()
        changes = []
        changed_record = json.loads(json.dumps(original))
        changed_record["record"]["runbook_id"] = "RB-SEC-01"
        unsigned = dict(changed_record["record"])
        unsigned.pop("record_digest")
        changed_record["record"]["record_digest"] = hashlib.sha256(
            canonical_bytes(unsigned)).hexdigest()
        changes.append(changed_record)
        changed_id = json.loads(json.dumps(original))
        changed_id["approval_id"] = "2" * 32
        changes.append(changed_id)
        changed_expiry = json.loads(json.dumps(original))
        changed_expiry["expires_at"] = stamp(NOW + timedelta(minutes=30))
        changes.append(changed_expiry)
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    ContextError, "invalid_memory_approval_signature"):
                self.load_memory(
                    [changed], self.keyring, now=NOW,
                )

    def test_untrusted_signer_malformed_keys_and_unknown_envelope_fields_fail_closed(self):
        with self.assertRaisesRegex(ContextError, "untrusted_memory_approver"):
            self.load_memory(
                [self.approval()],
                {("alpha", "platform", "different-curator"): self.public_key},
                now=NOW,
            )
        other_key = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        with self.assertRaisesRegex(ContextError, "invalid_memory_approval_signature"):
            self.load_memory(
                [self.approval()], {("alpha", "platform", "curator-1"): other_key},
                now=NOW,
            )
        with self.assertRaisesRegex(ContextError, "invalid_memory_keyring"):
            self.load_memory(
                [self.approval()], {("alpha", "platform", "curator-1"): b"short"},
                now=NOW,
            )
        malformed_signature = self.approval()
        malformed_signature["signature"] = "00"
        with self.assertRaisesRegex(ContextError, "invalid_memory_approval_signature"):
            self.load_memory(
                [malformed_signature], self.keyring, now=NOW,
            )
        for scope in (("beta", "platform", "curator-1"),
                      ("alpha", "different-project", "curator-1")):
            with self.subTest(scope=scope), self.assertRaisesRegex(
                    ContextError, "untrusted_memory_approver"):
                self.load_memory(
                    [self.approval()], {scope: self.public_key}, now=NOW,
                )
        changed = self.approval()
        changed["unexpected"] = True
        with self.assertRaisesRegex(ContextError, "invalid_memory_approval"):
            self.load_memory(
                [changed], self.keyring, now=NOW,
            )

    def test_expired_future_and_overlong_approvals_are_rejected(self):
        cases = (
            self.approval(approved_at=NOW - timedelta(days=2),
                          expires_at=NOW - timedelta(days=1)),
            self.approval(approved_at=NOW + timedelta(minutes=1),
                          expires_at=NOW + timedelta(hours=1)),
            self.approval(approved_at=NOW - timedelta(days=8),
                          expires_at=NOW + timedelta(minutes=1)),
        )
        for envelope in cases:
            with self.subTest(envelope=envelope), self.assertRaises(ContextError):
                self.load_memory(
                    [envelope], self.keyring, now=NOW,
                )

    def test_unsupported_versions_and_noncanonical_approval_times_are_rejected(self):
        unsupported = self.approval()
        unsupported["schema_version"] = 2
        with self.assertRaisesRegex(ContextError, "unsupported_memory_approval"):
            self.load_memory(
                [unsupported], self.keyring, now=NOW,
            )
        boolean_version = self.approval()
        boolean_version["schema_version"] = True
        with self.assertRaisesRegex(ContextError, "unsupported_memory_approval"):
            self.load_memory(
                [boolean_version], self.keyring, now=NOW,
            )
        noncanonical_time = self.approval()
        noncanonical_time["approved_at"] = (NOW - timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ContextError, "invalid_memory_approval_time"):
            self.load_memory(
                [noncanonical_time], self.keyring, now=NOW,
            )

    def test_batch_rejects_duplicate_approval_ids_duplicate_records_and_partial_imports(self):
        first = self.approval(approval_id="1" * 32)
        second_id = self.approval(approval_id="2" * 32)
        with self.assertRaisesRegex(ContextError, "duplicate_memory_approval"):
            self.load_memory(
                [first, first], self.keyring, now=NOW,
            )
        with self.assertRaisesRegex(ContextError, "duplicate_memory"):
            self.load_memory(
                [first, second_id], self.keyring, now=NOW,
            )
        malformed = json.loads(json.dumps(second_id))
        malformed["signature"] = "00" * 64
        with self.assertRaises(ContextError):
            self.load_memory(
                [first, malformed], self.keyring, now=NOW,
            )

    def test_only_resolved_records_with_source_and_time_are_approvable(self):
        cases = (
            self.record(outcome="unresolved"),
            IncidentRecord(
                "alpha", "platform", "db", "high_error_rate", "RB-SLO-01",
                "resolved", "d" * 64,
            ),
        )
        for record in cases:
            with self.subTest(record=record), self.assertRaises(ContextError):
                self.load_memory(
                    [self.approval(record=record)], self.keyring, now=NOW,
                )

    def test_provenanced_retrieval_requires_a_current_signature_when_requested(self):
        record = self.record()
        approved = self.load_memory(
            [self.approval(record=record)], self.keyring, now=NOW,
        )
        query = {
            "tenant": "alpha", "project": "platform", "service": "db",
            "category": "high_error_rate", "max_age_seconds": 86_400,
            "require_approval": True,
        }
        self.assertEqual(approved.retrieve_provenanced(**query, now=NOW), (record,))
        self.assertEqual(
            approved.retrieve_provenanced(**query, now=NOW + timedelta(hours=2)), (),
        )

        unsigned = IncidentMemory([record])
        self.assertEqual(unsigned.retrieve_provenanced(**query, now=NOW), ())


if __name__ == "__main__":
    unittest.main()

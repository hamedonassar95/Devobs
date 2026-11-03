"""Offline verification of signed memory approvals referenced by findings."""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot, normalize_telemetry
from devobs_intelligence.correlation import (
    correlate, verify_incident_finding_memory_provenance,
)
from devobs_intelligence.incident_memory import IncidentMemory, IncidentRecord
from devobs_intelligence.incident_memory_approval import (
    IncidentMemoryApprovalRegistry,
)

_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
_SOURCE_SHA = "a" * 40


def _canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds").replace("+00:00", "Z")


class FindingMemoryProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.trusted_keys = {
            ("alpha", "platform", "curator-1"): public_key,
        }
        self.record = self.make_record("alpha", "b" * 64)
        self.approval = self.sign(self.record)
        memory = IncidentMemory.from_approved_envelopes(
            [self.approval], self.trusted_keys, now=_NOW,
            consumption_registry=IncidentMemoryApprovalRegistry(),
        )
        topology = ServiceTopologySnapshot(
            "alpha", "platform", ["db"], [], _SOURCE_SHA, _stamp(_NOW),
        )
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": _SOURCE_SHA, "observed_at": _stamp(_NOW),
            "metric": "error_rate_pct", "value": 9,
            "evidence_digest": "c" * 64,
        })
        self.finding = correlate(
            topology, [telemetry], memory, _NOW, memory_max_age_seconds=600,
        )

    def make_record(self, tenant, evidence_digest):
        return IncidentRecord(
            tenant, "platform", "db", "high_error_rate", "RB-SLO-01",
            "resolved", evidence_digest, _SOURCE_SHA,
            _stamp(_NOW - timedelta(minutes=1)),
        )

    def sign(self, record, *, approval_id="1" * 32):
        payload = {
            "schema_version": 1,
            "approval_id": approval_id,
            "approver_id": "curator-1",
            "approved_at": _stamp(_NOW - timedelta(seconds=30)),
            "expires_at": _stamp(_NOW + timedelta(hours=1)),
            "record": record.to_record(),
        }
        return {
            **payload,
            "signature": self.private_key.sign(_canonical_json(payload)).hex(),
        }

    def validate(self, finding=None, envelopes=None, trusted_keys=None, now=_NOW):
        return verify_incident_finding_memory_provenance(
            (finding or self.finding).to_record(),
            [self.approval] if envelopes is None else envelopes,
            self.trusted_keys if trusted_keys is None else trusted_keys,
            now_utc=now,
        )

    def test_matching_active_approval_is_independently_verified(self):
        verified = self.validate()

        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0].approval_id, self.approval["approval_id"])
        self.assertEqual(verified[0].record, self.record)

    def test_signed_approval_for_another_tenant_does_not_match_finding(self):
        public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        beta_approval = self.sign(self.make_record("beta", "d" * 64))
        keyring = {
            **self.trusted_keys,
            ("beta", "platform", "curator-1"): public_key,
        }
        with self.assertRaisesRegex(
                ContextError, "incident_finding_memory_mismatch"):
            self.validate(envelopes=[beta_approval], trusted_keys=keyring)

    def test_missing_extra_or_invalid_approval_envelopes_fail_closed(self):
        extra = self.sign(
            self.make_record("alpha", "d" * 64), approval_id="2" * 32,
        )
        malformed = {**self.approval, "signature": "0" * 128}
        for envelopes, error in (
                ([], "incident_finding_memory_mismatch"),
                ([self.approval, extra], "incident_finding_memory_mismatch"),
                ([malformed], "invalid_memory_approval_signature")):
            with self.subTest(error=error), self.assertRaisesRegex(ContextError, error):
                self.validate(envelopes=envelopes)

    def test_findings_without_memory_require_no_approval_envelopes(self):
        topology = ServiceTopologySnapshot(
            "alpha", "platform", ["db"], [], _SOURCE_SHA, _stamp(_NOW),
        )
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": _SOURCE_SHA, "observed_at": _stamp(_NOW),
            "metric": "error_rate_pct", "value": 9,
            "evidence_digest": "c" * 64,
        })
        finding = correlate(topology, [telemetry], IncidentMemory([]), _NOW)

        self.assertEqual(self.validate(finding=finding, envelopes=[]), ())
        with self.assertRaisesRegex(
                ContextError, "incident_finding_memory_mismatch"):
            self.validate(finding=finding, envelopes=[self.approval])


if __name__ == "__main__":
    unittest.main()

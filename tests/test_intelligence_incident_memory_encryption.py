"""Offline tests for tenant-scoped, expiring incident-memory archives."""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import (
    ContextError, ServiceTopologySnapshot, normalize_telemetry,
)
from devobs_intelligence.correlation import correlate
from devobs_intelligence.incident_memory import IncidentMemory, IncidentRecord
from devobs_intelligence.incident_memory_approval import IncidentMemoryApprovalRegistry
from devobs_intelligence.incident_memory_encryption import (
    decrypt_approved_incident_memory_bundle,
    decrypt_incident_memory_bundle,
    encrypt_incident_memory_bundle,
)

_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
_KEY = bytes(range(32))


def incident_memory(*, tenant="alpha", project="platform", service="private-api",
                    evidence="a" * 64):
    return IncidentMemory([IncidentRecord(
        tenant, project, service, "high_error_rate", "RB-SLO-01", "resolved",
        evidence, "b" * 40,
        (_NOW - timedelta(minutes=1)).isoformat(
            timespec="microseconds").replace("+00:00", "Z"),
    )])


def signed_approval(memory, private_key, *, approval_id="1" * 32):
    record = memory.to_bundle()["records"][0]
    payload = {
        "schema_version": 1,
        "approval_id": approval_id,
        "approver_id": "curator-1",
        "approved_at": (_NOW - timedelta(seconds=30)).isoformat(
            timespec="microseconds").replace("+00:00", "Z"),
        "expires_at": (_NOW + timedelta(hours=1)).isoformat(
            timespec="microseconds").replace("+00:00", "Z"),
        "record": record,
    }
    message = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return {
        **payload,
        "signature": private_key.sign(message).hex(),
    }


class IncidentMemoryEncryptionTests(unittest.TestCase):
    def encrypt(self, memory=None, **overrides):
        options = {
            "tenant": "alpha",
            "project": "platform",
            "now": _NOW,
            "retention_seconds": 3600,
        }
        options.update(overrides)
        with patch(
                "devobs_intelligence.incident_memory_encryption.os.urandom",
                return_value=b"S" * 32):
            return encrypt_incident_memory_bundle(
                memory or incident_memory(), _KEY, **options,
            )

    def decrypt(self, envelope, *, key=_KEY, tenant="alpha", project="platform",
                now=_NOW):
        return decrypt_incident_memory_bundle(
            envelope, key, expected_tenant=tenant,
            expected_project=project, now=now,
        )

    def approved_decrypt(self, envelope, approvals, keyring, registry):
        return decrypt_approved_incident_memory_bundle(
            envelope, _KEY, expected_tenant="alpha",
            expected_project="platform", now=_NOW,
            approval_envelopes=approvals, trusted_public_keys=keyring,
            consumption_registry=registry,
        )

    def test_roundtrip_is_scoped_authenticated_and_does_not_expose_plaintext(self):
        memory = incident_memory()
        envelope = self.encrypt(memory)
        encoded = json.dumps(envelope, sort_keys=True)

        self.assertEqual(set(envelope), {
            "schema_version", "algorithm", "created_at", "expires_at",
            "salt", "ciphertext",
        })
        for private_value in ("alpha", "platform", "private-api", "a" * 64,
                              _KEY.hex()):
            self.assertNotIn(private_value, encoded)
        self.assertEqual(envelope["algorithm"], "AES-256-GCM")
        self.assertEqual(len(envelope["salt"]), 43)
        restored = self.decrypt(envelope)
        self.assertEqual(restored.to_bundle(), memory.to_bundle())
        self.assertEqual(restored.retrieve_provenanced(
            "alpha", "platform", "private-api", "high_error_rate",
            now=_NOW, max_age_seconds=3600, require_approval=True,
        ), ())

    def test_approved_restore_requires_fresh_matching_signed_approval(self):
        record_memory = incident_memory()
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        keyring = {("alpha", "platform", "curator-1"): public_key}
        approval = signed_approval(record_memory, private_key)
        source = IncidentMemoryApprovalRegistry().load_memory(
            [approval], keyring, now=_NOW,
        )
        envelope = self.encrypt(source)

        # Plain decryption intentionally strips approval provenance.
        plain = self.decrypt(envelope)
        query = {
            "tenant": "alpha", "project": "platform",
            "service": "private-api", "category": "high_error_rate",
            "now": _NOW, "max_age_seconds": 3600, "require_approval": True,
        }
        self.assertEqual(plain.retrieve_provenanced(**query), ())

        restored = self.approved_decrypt(
            envelope, [approval], keyring, IncidentMemoryApprovalRegistry(),
        )
        self.assertEqual(restored.retrieve_provenanced(**query),
                         record_memory.retrieve("alpha", "platform",
                                                "private-api", "high_error_rate"))

    def test_mismatched_approval_batch_does_not_consume_valid_approval(self):
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        keyring = {("alpha", "platform", "curator-1"): public_key}
        archived_memory = incident_memory(evidence="a" * 64)
        different_memory = incident_memory(evidence="c" * 64)
        archived_approval = signed_approval(
            archived_memory, private_key, approval_id="1" * 32,
        )
        different_approval = signed_approval(
            different_memory, private_key, approval_id="2" * 32,
        )
        envelope = self.encrypt(archived_memory)
        registry = IncidentMemoryApprovalRegistry()

        with self.assertRaisesRegex(
                ContextError, "memory_approval_archive_mismatch"):
            self.approved_decrypt(
                envelope, [archived_approval, different_approval],
                keyring, registry,
            )
        restored = self.approved_decrypt(
            envelope, [archived_approval], keyring, registry,
        )
        self.assertEqual(len(restored.retrieve_provenanced(
            "alpha", "platform", "private-api", "high_error_rate",
            now=_NOW, max_age_seconds=3600, require_approval=True,
        )), 1)

    def test_approved_archive_import_obeys_the_replay_registry(self):
        memory = incident_memory()
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        keyring = {("alpha", "platform", "curator-1"): public_key}
        approval = signed_approval(memory, private_key)
        envelope = self.encrypt(memory)
        registry = IncidentMemoryApprovalRegistry()

        self.approved_decrypt(envelope, [approval], keyring, registry)
        with self.assertRaisesRegex(ContextError, "replayed_memory_approval"):
            self.approved_decrypt(envelope, [approval], keyring, registry)

    def test_restored_approval_provenance_reaches_the_correlated_finding(self):
        memory = incident_memory(service="db")
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        keyring = {("alpha", "platform", "curator-1"): public_key}
        approval = signed_approval(memory, private_key)
        archive = self.encrypt(memory)
        restored = self.approved_decrypt(
            archive, [approval], keyring, IncidentMemoryApprovalRegistry(),
        )
        topology = ServiceTopologySnapshot(
            "alpha", "platform", ["api", "db"], [("api", "db")],
            "b" * 40, _NOW.isoformat(),
        )
        telemetry = [normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": "b" * 40,
            "observed_at": _NOW.isoformat(timespec="seconds"),
            "metric": "error_rate_pct", "value": 9,
            "evidence_digest": "d" * 64,
        })]

        finding = correlate(
            topology, telemetry, restored, _NOW, memory_max_age_seconds=3600,
        )

        self.assertEqual(finding.runbook_ids, ("RB-SLO-01",))
        self.assertEqual(len(finding.memory_provenance), 1)
        self.assertEqual(finding.memory_provenance[0].approval_id, "1" * 32)
        self.assertEqual(finding.memory_provenance[0].approver_id, "curator-1")
        self.assertEqual(finding.memory_provenance[0].source_sha, "b" * 40)

    def test_wrong_scope_key_salt_or_ciphertext_fails_closed(self):
        envelope = self.encrypt()
        with self.assertRaisesRegex(ContextError, "^invalid_encrypted_memory$"):
            self.decrypt(envelope, tenant="beta")
        with self.assertRaisesRegex(ContextError, "^invalid_encrypted_memory$"):
            self.decrypt(envelope, key=b"X" * 32)
        for field in ("salt", "ciphertext"):
            changed = dict(envelope)
            value = changed[field]
            changed[field] = ("A" if value[0] != "A" else "B") + value[1:]
            with self.subTest(field=field), self.assertRaisesRegex(
                    ContextError, "^invalid_encrypted_memory$"):
                self.decrypt(changed)

    def test_expiry_is_authenticated_and_enforced_at_the_boundary(self):
        envelope = self.encrypt(retention_seconds=60)
        with self.assertRaisesRegex(ContextError, "^future_encrypted_memory$"):
            self.decrypt(envelope, now=_NOW - timedelta(seconds=1))
        with self.assertRaisesRegex(ContextError, "^expired_encrypted_memory$"):
            self.decrypt(envelope, now=_NOW + timedelta(seconds=60))
        changed = {**envelope, "expires_at": "2026-11-03T13:00:01.000000Z"}
        with self.assertRaisesRegex(ContextError, "^invalid_encrypted_memory$"):
            self.decrypt(changed)

    def test_cross_scope_bundles_and_invalid_encryption_queries_are_rejected(self):
        mixed = IncidentMemory([
            incident_memory().retrieve(
                "alpha", "platform", "private-api", "high_error_rate",
            )[0],
            IncidentRecord(
                "beta", "platform", "other-api", "high_error_rate",
                "RB-SLO-01", "resolved", "c" * 64,
            ),
        ])
        with self.assertRaisesRegex(ContextError, "^memory_scope_mismatch$"):
            self.encrypt(mixed)
        for overrides in (
            {"retention_seconds": True},
            {"retention_seconds": 31_536_001},
            {"now": "2026-11-03T12:00:00Z"},
            {"now": datetime.max.replace(tzinfo=timezone.utc)},
            {"tenant": "not a tenant"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ContextError):
                self.encrypt(**overrides)
        with self.assertRaisesRegex(ContextError, "^invalid_memory_encryption_query$"):
            encrypt_incident_memory_bundle(
                incident_memory(), b"short",
                tenant="alpha", project="platform", now=_NOW,
                retention_seconds=60,
            )

    def test_unknown_shapes_versions_and_malformed_salts_are_rejected(self):
        envelope = self.encrypt()
        for changed in (
            {**envelope, "unexpected": True},
            {**envelope, "schema_version": True},
            {**envelope, "schema_version": 2},
            {**envelope, "algorithm": "AES-128-GCM"},
            {**envelope, "salt": "bad!"},
            {**envelope, "created_at": "not-a-time"},
        ):
            with self.subTest(envelope=changed), self.assertRaises(ContextError):
                self.decrypt(changed)

    def test_salt_separates_archive_keys(self):
        memory = incident_memory()
        with patch(
                "devobs_intelligence.incident_memory_encryption.os.urandom",
                side_effect=[b"A" * 32, b"B" * 32],
        ):
            first = encrypt_incident_memory_bundle(
                memory, _KEY, tenant="alpha", project="platform", now=_NOW,
                retention_seconds=3600,
            )
            second = encrypt_incident_memory_bundle(
                memory, _KEY, tenant="alpha", project="platform", now=_NOW,
                retention_seconds=3600,
            )
        self.assertNotEqual(first["salt"], second["salt"])
        self.assertNotEqual(first["ciphertext"], second["ciphertext"])
        self.assertEqual(self.decrypt(first).to_bundle(), memory.to_bundle())
        self.assertEqual(self.decrypt(second).to_bundle(), memory.to_bundle())


if __name__ == "__main__":
    unittest.main()

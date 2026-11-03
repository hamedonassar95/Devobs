"""Offline tests for signed topology metadata and caller-supplied trust."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot  # noqa: E402
from devobs_intelligence.topology_attestation import (  # noqa: E402
    verify_topology_attestation,
)
from devobs_intelligence import topology_attestation  # noqa: E402

_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
_DOMAIN = b"devobs-topology-attestation-v1\n"
_ROTATION_DOMAIN = b"devobs-topology-keyring-update-v1\n"


def snapshot(**overrides):
    values = {
        "tenant": "alpha",
        "project": "platform",
        "services": ["api", "db"],
        "edges": [("api", "db")],
        "source_sha": "a" * 40,
        "captured_at": (_NOW - timedelta(seconds=10)).isoformat(
            timespec="microseconds").replace("+00:00", "Z"),
    }
    values.update(overrides)
    return ServiceTopologySnapshot(**values)


def canonical_json(value):
    import json
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class TopologyAttestationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.keyring = {("alpha", "platform", "collector-1"): public_key}

    def envelope(self, topology=None, key_id="collector-1"):
        topology = topology or snapshot()
        payload = {
            "schema_version": 1,
            "key_id": key_id,
            "snapshot": topology.to_record(),
        }
        signature = self.private_key.sign(
            _DOMAIN + canonical_json(payload),
        ).hex()
        return {**payload, "signature": signature}

    def verify(self, value=None, **overrides):
        options = {
            "expected_tenant": "alpha",
            "expected_project": "platform",
            "expected_source_sha": "a" * 40,
            "now": _NOW,
            "max_age_seconds": 60,
        }
        options.update(overrides)
        return verify_topology_attestation(
            value or self.envelope(), self.keyring, **options,
        )

    def test_valid_signature_returns_snapshot_and_digest_only(self):
        topology = snapshot()
        result = self.verify(self.envelope(topology))

        self.assertEqual(result.snapshot, topology)
        self.assertEqual(result.key_id, "collector-1")
        self.assertEqual(len(result.attestation_digest), 64)
        self.assertNotIn("signature", result.__dict__)

    def test_signature_binds_exact_snapshot_content_and_source_sha(self):
        signed = self.envelope(snapshot())
        changed = snapshot(
            services=["api", "db", "worker"],
            edges=[("api", "db"), ("worker", "api")],
        )
        altered = {**signed, "snapshot": changed.to_record()}
        with self.assertRaisesRegex(
                ContextError, "^invalid_topology_attestation_signature$"):
            self.verify(altered)
        with self.assertRaisesRegex(
                ContextError, "^topology_source_sha_mismatch$"):
            self.verify(signed, expected_source_sha="b" * 40)

    def test_exact_scope_is_required(self):
        with self.assertRaisesRegex(ContextError, "^topology_scope_mismatch$"):
            self.verify(expected_tenant="beta")
        with self.assertRaisesRegex(ContextError, "^topology_scope_mismatch$"):
            self.verify(expected_project="other")

    def test_untrusted_signer_and_malformed_keyring_fail_closed(self):
        unsigned_trust = self.envelope(key_id="unknown")
        with self.assertRaisesRegex(ContextError, "^untrusted_topology_signer$"):
            self.verify(unsigned_trust)
        for keyring in (
            {},
            {("alpha", "platform", "collector-1"): b"short"},
            {("beta", "platform", "collector-1"): self.keyring[("alpha", "platform", "collector-1")]},
            None,
        ):
            with self.subTest(keyring=keyring), self.assertRaises(ContextError):
                verify_topology_attestation(
                    self.envelope(), keyring,
                    expected_tenant="alpha", expected_project="platform",
                    expected_source_sha="a" * 40, now=_NOW,
                )

    def test_tampered_and_malformed_signatures_are_rejected(self):
        signed = self.envelope()
        tampered = {**signed, "signature": "0" * 128}
        with self.assertRaisesRegex(
                ContextError, "^invalid_topology_attestation_signature$"):
            self.verify(tampered)
        for signature in ("not-a-signature", "0" * 126, None):
            with self.subTest(signature=signature), self.assertRaisesRegex(
                    ContextError, "^invalid_topology_attestation_signature$"):
                self.verify({**signed, "signature": signature})

    def test_stale_and_future_snapshots_are_rejected(self):
        stale = self.envelope(snapshot(captured_at=(
            _NOW - timedelta(hours=2)).isoformat(
                timespec="microseconds").replace("+00:00", "Z")))
        with self.assertRaisesRegex(ContextError, "^stale_topology$"):
            self.verify(stale)
        future = self.envelope(snapshot(captured_at=(
            _NOW + timedelta(minutes=1)).isoformat(
                timespec="microseconds").replace("+00:00", "Z")))
        with self.assertRaisesRegex(ContextError, "^stale_topology$"):
            self.verify(future)

    def test_unknown_fields_versions_and_noncanonical_records_are_rejected(self):
        signed = self.envelope()
        with self.assertRaisesRegex(ContextError, "^invalid_topology_attestation$"):
            self.verify({**signed, "unexpected": "value"})
        with self.assertRaisesRegex(ContextError, "^unsupported_topology_attestation$"):
            self.verify({**signed, "schema_version": 2})
        altered = {**signed, "snapshot": {**signed["snapshot"], "extra": "value"}}
        with self.assertRaisesRegex(ContextError, "^invalid_topology_snapshot$"):
            self.verify(altered)

    def test_invalid_query_bounds_fail_closed(self):
        for options in (
            {"expected_source_sha": "short"},
            {"expected_tenant": "bad tenant"},
            {"max_age_seconds": 0},
            {"max_age_seconds": True},
            {"now": "2026-11-03T12:00:00Z"},
        ):
            with self.subTest(options=options), self.assertRaisesRegex(
                    ContextError, "^invalid_topology_query$"):
                self.verify(**options)


class RotatingTopologyKeyringTests(unittest.TestCase):
    def setUp(self):
        self.old_private_key = Ed25519PrivateKey.generate()
        self.new_private_key = Ed25519PrivateKey.generate()
        self.operator_private_key = Ed25519PrivateKey.generate()
        self.scope = ("alpha", "platform", "collector-1")
        self.snapshot = snapshot()
        keyring_type = getattr(
            topology_attestation, "RotatingTopologyKeyring", None,
        )
        self.assertIsNotNone(
            keyring_type,
            "a rotating topology keyring must support reviewed local rotation",
        )
        self.keyring = keyring_type({
            self.scope: self.public_key(self.old_private_key),
        }, operator_public_keys={
            "operator-1": self.public_key(self.operator_private_key),
        })

    @staticmethod
    def public_key(private_key):
        return private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )

    def envelope(self, private_key, key_id):
        payload = {
            "schema_version": 1,
            "key_id": key_id,
            "snapshot": self.snapshot.to_record(),
        }
        signature = private_key.sign(
            _DOMAIN + canonical_json(payload),
        ).hex()
        return {**payload, "signature": signature}

    def verify(self, envelope):
        return verify_topology_attestation(
            envelope, self.keyring,
            expected_tenant="alpha", expected_project="platform",
            expected_source_sha="a" * 40, now=_NOW, max_age_seconds=60,
        )

    def update_envelope(self, keys, revision, *, signer=None, signer_id="operator-1"):
        entries = [
            {
                "tenant": scope[0],
                "project": scope[1],
                "key_id": scope[2],
                "public_key": public_key.hex(),
            }
            for scope, public_key in sorted(keys.items())
        ]
        payload = {
            "schema_version": 1,
            "revision": revision,
            "operator_key_id": signer_id,
            "keys": entries,
        }
        signer = signer or self.operator_private_key
        signature = signer.sign(_ROTATION_DOMAIN + canonical_json(payload)).hex()
        return {**payload, "signature": signature}

    def install(self, keys, revision):
        self.keyring.install_signed_update(
            self.update_envelope(keys, revision),
        )

    def test_rotation_keeps_overlap_then_revokes_removed_key(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        new_scope = ("alpha", "platform", "collector-2")
        new_envelope = self.envelope(self.new_private_key, "collector-2")

        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")
        self.install({
            self.scope: self.public_key(self.old_private_key),
            new_scope: self.public_key(self.new_private_key),
        }, revision=2)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")
        self.assertEqual(self.verify(new_envelope).key_id, "collector-2")

        self.install({
            new_scope: self.public_key(self.new_private_key),
        }, revision=3)
        self.assertEqual(self.verify(new_envelope).key_id, "collector-2")
        with self.assertRaisesRegex(
                ContextError, "^untrusted_topology_signer$"):
            self.verify(old_envelope)

    def test_stale_revision_cannot_replace_current_trust(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        new_scope = ("alpha", "platform", "collector-2")

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^stale_key_revision$"):
            self.install({
                new_scope: self.public_key(self.new_private_key),
            }, revision=1)

        self.assertEqual(self.keyring.revision, 1)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_snapshot_is_detached_from_internal_keyring(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        detached = self.keyring.snapshot()
        detached.clear()

        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_key_id_cannot_be_rebound_to_different_public_bytes(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^topology_key_id_reused$"):
            self.install({
                self.scope: self.public_key(self.new_private_key),
            }, revision=2)

        self.assertEqual(self.keyring.revision, 1)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_removed_key_id_cannot_be_reintroduced(self):
        new_scope = ("alpha", "platform", "collector-2")
        new_envelope = self.envelope(self.new_private_key, "collector-2")
        self.install({
            new_scope: self.public_key(self.new_private_key),
        }, revision=2)

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^revoked_topology_key_cannot_be_restored$"):
            self.install({
                self.scope: self.public_key(self.new_private_key),
                new_scope: self.public_key(self.new_private_key),
            }, revision=3)

        self.assertEqual(self.keyring.revision, 2)
        self.assertEqual(self.verify(new_envelope).key_id, "collector-2")

    def test_empty_update_revokes_all_keys(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        self.install({}, revision=2)

        self.assertEqual(self.keyring.snapshot(), {})
        with self.assertRaisesRegex(
                ContextError, "^untrusted_topology_signer$"):
            self.verify(old_envelope)

    def test_revocation_history_limit_rejects_update_atomically(self):
        second_scope = ("alpha", "platform", "collector-2")
        third_scope = ("alpha", "platform", "collector-3")
        second_envelope = self.envelope(self.new_private_key, "collector-2")
        second_public_key = self.public_key(self.new_private_key)

        self.install({
            second_scope: second_public_key,
        }, revision=2)
        with patch.object(topology_attestation, "_MAX_REVOKED_KEY_IDS", 1):
            with self.assertRaisesRegex(
                    topology_attestation.TopologyKeyringRotationRejected,
                    "^topology_revocation_history_full$"):
                self.install({
                    third_scope: second_public_key,
                }, revision=3)

        self.assertEqual(self.keyring.revision, 2)
        self.assertEqual(self.verify(second_envelope).key_id, "collector-2")

    def test_invalid_update_signature_does_not_change_trust(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        new_scope = ("alpha", "platform", "collector-2")
        update = self.update_envelope({
            new_scope: self.public_key(self.new_private_key),
        }, revision=2)
        update["revision"] = 3

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^invalid_topology_keyring_update_signature$"):
            self.keyring.install_signed_update(update)

        self.assertEqual(self.keyring.revision, 1)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_unknown_operator_key_cannot_rotate_topology_trust(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        unknown_operator = Ed25519PrivateKey.generate()
        new_scope = ("alpha", "platform", "collector-2")
        update = self.update_envelope({
            new_scope: self.public_key(self.new_private_key),
        }, revision=2, signer=unknown_operator, signer_id="operator-2")

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^untrusted_topology_update_signer$"):
            self.keyring.install_signed_update(update)

        self.assertEqual(self.keyring.revision, 1)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_rotation_manifest_requires_exact_sorted_key_entries(self):
        old_envelope = self.envelope(self.old_private_key, "collector-1")
        second_scope = ("alpha", "platform", "collector-2")
        update = self.update_envelope({
            self.scope: self.public_key(self.old_private_key),
            second_scope: self.public_key(self.new_private_key),
        }, revision=2)
        update["keys"].reverse()

        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^invalid_topology_keyring_update$"):
            self.keyring.install_signed_update(update)

        update = self.update_envelope({
            second_scope: self.public_key(self.new_private_key),
        }, revision=2)
        update["unexpected"] = "value"
        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^invalid_topology_keyring_update$"):
            self.keyring.install_signed_update(update)

        self.assertEqual(self.keyring.revision, 1)
        self.assertEqual(self.verify(old_envelope).key_id, "collector-1")

    def test_rotation_manifest_rejects_wrong_version_and_boolean_revision(self):
        new_scope = ("alpha", "platform", "collector-2")
        update = self.update_envelope({
            new_scope: self.public_key(self.new_private_key),
        }, revision=2)
        update["schema_version"] = 2
        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^unsupported_topology_keyring_update$"):
            self.keyring.install_signed_update(update)

        update = self.update_envelope({
            new_scope: self.public_key(self.new_private_key),
        }, revision=2)
        update["revision"] = True
        with self.assertRaisesRegex(
                topology_attestation.TopologyKeyringRotationRejected,
                "^invalid_topology_keyring_update$"):
            self.keyring.install_signed_update(update)

        self.assertEqual(self.keyring.revision, 1)


if __name__ == "__main__":
    unittest.main()

"""Offline tests for signed topology metadata and caller-supplied trust."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.context import ContextError, ServiceTopologySnapshot  # noqa: E402
from devobs_intelligence.topology_attestation import (  # noqa: E402
    verify_topology_attestation,
)

_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
_DOMAIN = b"devobs-topology-attestation-v1\n"


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


if __name__ == "__main__":
    unittest.main()

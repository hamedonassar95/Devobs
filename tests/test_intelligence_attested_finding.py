"""Offline acceptance for cryptographically attested impact findings."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.context import (  # noqa: E402
    ContextError, ServiceTopologySnapshot, normalize_telemetry,
)
from devobs_intelligence.correlation import (  # noqa: E402
    AttestedImpactFinding, IncidentFinding, correlate,
    validate_attested_impact_finding,
)
from devobs_intelligence.incident_memory import IncidentMemory  # noqa: E402
from devobs_intelligence.topology_attestation import (  # noqa: E402
    RotatingTopologyKeyring,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
SOURCE_SHA = "a" * 40
_DOMAIN = b"devobs-topology-attestation-v1\n"
_ROTATION_DOMAIN = b"devobs-topology-keyring-update-v1\n"


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def make_snapshot(*, edges=None, captured_at=None):
    return ServiceTopologySnapshot(
        "alpha", "platform", ["api", "cache", "db"],
        edges if edges is not None else [
            ("api", "db"), ("api", "cache"), ("cache", "db"),
        ],
        SOURCE_SHA,
        captured_at or (NOW - timedelta(seconds=10)).isoformat(
            timespec="microseconds").replace("+00:00", "Z"),
    )


class AttestedImpactFindingTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.operator_private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        operator_public_key = self.operator_private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.public_key = public_key
        self.keyring = RotatingTopologyKeyring({
            ("alpha", "platform", "collector-1"): public_key,
        }, operator_public_keys={"operator-1": operator_public_key})
        topology = make_snapshot()
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": SOURCE_SHA, "observed_at": NOW.isoformat(),
            "metric": "error_rate_pct", "value": 8,
            "evidence_digest": "b" * 64,
        })
        self.finding = correlate(
            topology, [telemetry], IncidentMemory([]), NOW,
        )
        self.snapshot = topology

    def envelope(self, topology=None, key_id="collector-1", private_key=None):
        payload = {
            "schema_version": 1,
            "key_id": key_id,
            "snapshot": (topology or self.snapshot).to_record(),
        }
        signer = private_key or self.private_key
        return {
            **payload,
            "signature": signer.sign(
                _DOMAIN + canonical_json(payload),
            ).hex(),
        }

    def keyring_update(self, keys, revision):
        entries = [
            {
                "tenant": scope[0],
                "project": scope[1],
                "key_id": scope[2],
                "public_key": key.hex(),
            }
            for scope, key in sorted(keys.items())
        ]
        payload = {
            "schema_version": 1,
            "revision": revision,
            "operator_key_id": "operator-1",
            "keys": entries,
        }
        signature = self.operator_private_key.sign(
            _ROTATION_DOMAIN + canonical_json(payload),
        ).hex()
        return {**payload, "signature": signature}

    def validate(self, finding=None, attestation=None, **overrides):
        options = {
            "expected_tenant": "alpha",
            "expected_project": "platform",
            "expected_source_sha": SOURCE_SHA,
            "now_utc": NOW,
            "max_age_seconds": 60,
        }
        options.update(overrides)
        return validate_attested_impact_finding(
            (finding or self.finding).to_record(),
            attestation or self.envelope(), self.keyring, **options,
        )

    def test_valid_signature_and_exact_snapshot_return_auditable_result(self):
        result = self.validate()

        self.assertIsInstance(result, AttestedImpactFinding)
        self.assertEqual(result.finding, self.finding)
        self.assertEqual(result.topology_key_id, "collector-1")
        self.assertEqual(len(result.topology_attestation_digest), 64)
        self.assertEqual(
            result.topology_snapshot_digest, self.snapshot.snapshot_digest,
        )

    def test_finding_gate_accepts_rotated_key_and_rejects_revoked_key(self):
        new_private_key = Ed25519PrivateKey.generate()
        new_public_key = new_private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        old_scope = ("alpha", "platform", "collector-1")
        new_scope = ("alpha", "platform", "collector-2")
        self.keyring.install_signed_update(self.keyring_update({
            old_scope: self.public_key,
            new_scope: new_public_key,
        }, revision=2))

        new_envelope = self.envelope(
            key_id="collector-2", private_key=new_private_key,
        )
        result = self.validate(attestation=new_envelope)
        self.assertEqual(result.topology_key_id, "collector-2")

        self.keyring.install_signed_update(self.keyring_update({
            new_scope: new_public_key,
        }, revision=3))
        with self.assertRaisesRegex(ContextError, "^untrusted_topology_signer$"):
            self.validate()

    def test_untrusted_signer_is_rejected(self):
        with self.assertRaisesRegex(ContextError, "^untrusted_topology_signer$"):
            self.validate(attestation=self.envelope(key_id="unknown"))

    def test_signed_but_different_snapshot_is_rejected(self):
        other_snapshot = make_snapshot(edges=[("api", "db"), ("cache", "db")])

        with self.assertRaisesRegex(
                ContextError, "^incident_finding_topology_mismatch$"):
            self.validate(attestation=self.envelope(other_snapshot))

    def test_forged_path_is_rejected_after_valid_signature_verification(self):
        altered = self.finding.to_record()
        altered["impact_paths"][0]["path_services"] = ["api", "cache", "db"]
        payload = {key: value for key, value in altered.items()
                   if key != "finding_digest"}
        altered["finding_digest"] = hashlib.sha256(
            canonical_json(payload),
        ).hexdigest()
        forged_finding = IncidentFinding.from_record(altered)

        with self.assertRaisesRegex(
                ContextError, "^incident_finding_impact_paths_mismatch$"):
            self.validate(finding=forged_finding)

    def test_stale_signed_snapshot_is_rejected(self):
        stale_snapshot = make_snapshot(captured_at=(
            NOW - timedelta(hours=1)).isoformat(
                timespec="microseconds").replace("+00:00", "Z"))

        with self.assertRaisesRegex(ContextError, "^stale_topology$"):
            self.validate(attestation=self.envelope(stale_snapshot))

    def test_external_scope_and_source_expectations_are_required(self):
        with self.assertRaisesRegex(ContextError, "^topology_scope_mismatch$"):
            self.validate(expected_tenant="other")
        with self.assertRaisesRegex(ContextError, "^topology_source_sha_mismatch$"):
            self.validate(expected_source_sha="c" * 40)

    def test_insufficient_evidence_is_verified_without_inventing_paths(self):
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": SOURCE_SHA, "observed_at": NOW.isoformat(),
            "metric": "capacity_pct", "value": 10,
            "evidence_digest": "c" * 64,
        })
        abstention = correlate(
            self.snapshot, [telemetry], IncidentMemory([]), NOW,
        )

        result = self.validate(finding=abstention)

        self.assertEqual(result.finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.finding.impact_paths, ())


if __name__ == "__main__":
    unittest.main()

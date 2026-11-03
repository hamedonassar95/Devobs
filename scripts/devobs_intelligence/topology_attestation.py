"""Offline Ed25519 verification for scope- and source-bound topology snapshots."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .context import ContextError, ServiceTopologySnapshot

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
_PUBLIC_KEY_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = frozenset({"schema_version", "key_id", "snapshot", "signature"})
_KEYRING_UPDATE_FIELDS = frozenset({
    "schema_version", "revision", "operator_key_id", "keys", "signature",
})
_KEYRING_UPDATE_ENTRY_FIELDS = frozenset({
    "tenant", "project", "key_id", "public_key",
})
_VERSION = 1
_DOMAIN = b"devobs-topology-attestation-v1\n"
_ROTATION_DOMAIN = b"devobs-topology-keyring-update-v1\n"
_MAX_KEYRING_ENTRIES = 100
_MAX_OPERATOR_KEYS = 100
_MAX_REVOKED_KEY_IDS = 10_000


@dataclass(frozen=True)
class VerifiedTopologyAttestation:
    """A verified snapshot and the configured signer identity."""

    snapshot: ServiceTopologySnapshot
    key_id: str
    attestation_digest: str


def _canonical_json(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _validated_keyring(value: object, *, allow_empty: bool = False
                       ) -> dict[tuple[str, str, str], bytes]:
    min_entries = 0 if allow_empty else 1
    if (type(value) is not dict
            or not min_entries <= len(value) <= _MAX_KEYRING_ENTRIES):
        raise ContextError("invalid_topology_keyring")
    keys = {}
    for scope, public_key in value.items():
        if (type(scope) is not tuple or len(scope) != 3
                or any(type(part) is not str or _ID.fullmatch(part) is None
                       for part in scope)
                or type(public_key) is not bytes or len(public_key) != 32):
            raise ContextError("invalid_topology_keyring")
        keys[scope] = public_key
    return keys


class TopologyKeyringRotationRejected(ValueError):
    """Fixed, non-sensitive error for an invalid local trust-set update."""


def _validated_operator_keys(value: object) -> dict[str, bytes]:
    if (type(value) is not dict
            or not 1 <= len(value) <= _MAX_OPERATOR_KEYS):
        raise TopologyKeyringRotationRejected("invalid_topology_update_trust")
    keys = {}
    for key_id, public_key in value.items():
        if (type(key_id) is not str or _ID.fullmatch(key_id) is None
                or type(public_key) is not bytes or len(public_key) != 32):
            raise TopologyKeyringRotationRejected("invalid_topology_update_trust")
        keys[key_id] = public_key
    return keys


class RotatingTopologyKeyring:
    """Process-local atomic rotation for operator-verified public keys.

    Operator public keys are trust anchors supplied at construction and must
    come from protected configuration. Each update must carry an Ed25519
    signature from one of those anchors. The revision and removed-key
    tombstones are memory-only; they do not prevent rollback after restart or
    synchronize updates across workers. Tombstones are bounded to avoid
    unbounded process memory growth; rotation fails closed at that bound.
    """

    def __init__(self, trusted_public_keys: dict[tuple[str, str, str], bytes],
                 *, operator_public_keys: dict[str, bytes], revision: int = 1):
        if type(revision) is not int or not 1 <= revision <= 2**31 - 1:
            raise TopologyKeyringRotationRejected("invalid_key_revision")
        self._current = _validated_keyring(trusted_public_keys)
        self._operator_keys = _validated_operator_keys(operator_public_keys)
        self._revoked: set[tuple[str, str, str]] = set()
        self._revision = revision
        self._lock = Lock()

    def snapshot(self) -> dict[tuple[str, str, str], bytes]:
        """Return a detached snapshot for one verification attempt."""
        with self._lock:
            return dict(self._current)

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def install_signed_update(self, update: object) -> None:
        """Verify an operator-signed update, then atomically replace the set.

        The operator public-key map is a trust anchor supplied at construction
        and must itself come from protected configuration. The signed update
        binds the revision and complete, sorted scoped-key set.
        """
        if (type(update) is not dict
                or set(update) != _KEYRING_UPDATE_FIELDS):
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_update")
        if (type(update["schema_version"]) is not int
                or update["schema_version"] != _VERSION):
            raise TopologyKeyringRotationRejected(
                "unsupported_topology_keyring_update")
        revision = update["revision"]
        operator_key_id = update["operator_key_id"]
        entries = update["keys"]
        signature_hex = update["signature"]
        if (type(revision) is not int or not 1 <= revision <= 2**31 - 1
                or type(operator_key_id) is not str
                or _ID.fullmatch(operator_key_id) is None
                or type(entries) is not list
                or len(entries) > _MAX_KEYRING_ENTRIES
                or type(signature_hex) is not str
                or _SIGNATURE.fullmatch(signature_hex) is None):
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_update")

        candidate = {}
        previous_scope = None
        for entry in entries:
            if (type(entry) is not dict
                    or set(entry) != _KEYRING_UPDATE_ENTRY_FIELDS):
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_update")
            scope = (entry["tenant"], entry["project"], entry["key_id"])
            public_key_hex = entry["public_key"]
            if (any(type(part) is not str or _ID.fullmatch(part) is None
                    for part in scope)
                    or type(public_key_hex) is not str
                    or _PUBLIC_KEY_HEX.fullmatch(public_key_hex) is None
                    or (previous_scope is not None and scope <= previous_scope)):
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_update")
            candidate[scope] = bytes.fromhex(public_key_hex)
            previous_scope = scope

        operator_public_key = self._operator_keys.get(operator_key_id)
        if operator_public_key is None:
            raise TopologyKeyringRotationRejected(
                "untrusted_topology_update_signer")
        payload = {key: update[key] for key in _KEYRING_UPDATE_FIELDS
                   if key != "signature"}
        try:
            Ed25519PublicKey.from_public_bytes(operator_public_key).verify(
                bytes.fromhex(signature_hex),
                _ROTATION_DOMAIN + _canonical_json(payload),
            )
        except (InvalidSignature, ValueError):
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_update_signature") from None

        with self._lock:
            if revision <= self._revision:
                raise TopologyKeyringRotationRejected("stale_key_revision")

            reintroduced = set(candidate).intersection(self._revoked)
            if reintroduced:
                raise TopologyKeyringRotationRejected(
                    "revoked_topology_key_cannot_be_restored")
            reused_ids = {
                scope for scope in set(self._current).intersection(candidate)
                if self._current[scope] != candidate[scope]
            }
            if reused_ids:
                raise TopologyKeyringRotationRejected(
                    "topology_key_id_reused")

            newly_revoked = set(self._current).difference(candidate)
            if len(self._revoked) + len(newly_revoked) > _MAX_REVOKED_KEY_IDS:
                raise TopologyKeyringRotationRejected(
                    "topology_revocation_history_full")

            self._revoked.update(newly_revoked)
            self._current = candidate
            self._revision = revision


def verify_topology_attestation(
        value: object,
        trusted_public_keys: dict[tuple[str, str, str], bytes]
        | RotatingTopologyKeyring, *,
        expected_tenant: str,
        expected_project: str,
        expected_source_sha: str,
        now: datetime,
        max_age_seconds: int = 900) -> VerifiedTopologyAttestation:
    """Verify one strict signed topology envelope against caller-supplied trust.

    The public-key map must come from protected configuration. This function
    does not authenticate key enrollment or prove that the signer observed the
    source commit named by the snapshot.
    """
    if type(value) is not dict or set(value) != _FIELDS:
        raise ContextError("invalid_topology_attestation")
    if type(value["schema_version"]) is not int or value["schema_version"] != _VERSION:
        raise ContextError("unsupported_topology_attestation")
    if type(value["key_id"]) is not str or _ID.fullmatch(value["key_id"]) is None:
        raise ContextError("invalid_topology_attestation")
    if (type(expected_tenant) is not str or _ID.fullmatch(expected_tenant) is None
            or type(expected_project) is not str
            or _ID.fullmatch(expected_project) is None
            or type(expected_source_sha) is not str
            or _SHA.fullmatch(expected_source_sha) is None
            or type(now) is not datetime or now.tzinfo is None
            or now.utcoffset() is None or type(max_age_seconds) is not int
            or not 1 <= max_age_seconds <= 86_400):
        raise ContextError("invalid_topology_query")

    try:
        snapshot = ServiceTopologySnapshot.from_record(value["snapshot"])
    except (ContextError, TypeError, ValueError):
        raise ContextError("invalid_topology_snapshot") from None
    if snapshot.to_record() != value["snapshot"]:
        raise ContextError("noncanonical_topology_snapshot")
    if (snapshot.tenant, snapshot.project) != (expected_tenant, expected_project):
        raise ContextError("topology_scope_mismatch")
    if snapshot.source_sha != expected_source_sha:
        raise ContextError("topology_source_sha_mismatch")
    snapshot.validate(
        expected_tenant, expected_project, now=now,
        max_age_seconds=max_age_seconds,
    )

    keyring = (trusted_public_keys.snapshot()
               if isinstance(trusted_public_keys, RotatingTopologyKeyring)
               else trusted_public_keys)
    keys = _validated_keyring(keyring, allow_empty=True)
    public_key = keys.get((expected_tenant, expected_project, value["key_id"]))
    if public_key is None:
        raise ContextError("untrusted_topology_signer")
    signature_hex = value["signature"]
    if type(signature_hex) is not str or _SIGNATURE.fullmatch(signature_hex) is None:
        raise ContextError("invalid_topology_attestation_signature")

    payload = {
        "schema_version": _VERSION,
        "key_id": value["key_id"],
        "snapshot": snapshot.to_record(),
    }
    signed_bytes = _DOMAIN + _canonical_json(payload)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            bytes.fromhex(signature_hex), signed_bytes,
        )
    except (InvalidSignature, ValueError):
        raise ContextError("invalid_topology_attestation_signature") from None

    signed_envelope = {**payload, "signature": signature_hex}
    digest = hashlib.sha256(_DOMAIN + _canonical_json(signed_envelope)).hexdigest()
    return VerifiedTopologyAttestation(snapshot, value["key_id"], digest)

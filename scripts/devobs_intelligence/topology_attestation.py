"""Offline Ed25519 verification for scope- and source-bound topology snapshots."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .context import ContextError, ServiceTopologySnapshot

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
_PUBLIC_KEY_HEX = re.compile(r"[0-9a-f]{64}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
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
_MAX_PERSISTED_STATE_BYTES = 3_000_000


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


def _keyring_state_record(
        revision: int,
        current: dict[tuple[str, str, str], bytes],
        revoked: set[tuple[str, str, str]]) -> dict:
    return {
        "schema_version": 1,
        "revision": revision,
        "keys": [
            {
                "tenant": scope[0], "project": scope[1],
                "key_id": scope[2], "public_key": public_key.hex(),
            }
            for scope, public_key in sorted(current.items())
        ],
        "revoked": [list(scope) for scope in sorted(revoked)],
    }


def _decode_keyring_state(
        state_json: object, state_digest: object
        ) -> tuple[int, dict[tuple[str, str, str], bytes],
                   set[tuple[str, str, str]]]:
    """Validate local persisted state; the digest detects corruption, not a
    privileged actor who can rewrite both the database and its digest.
    """
    try:
        if (type(state_json) is not str
                or len(state_json.encode("utf-8")) > _MAX_PERSISTED_STATE_BYTES
                or type(state_digest) is not str
                or _DIGEST.fullmatch(state_digest) is None):
            raise ValueError
        record = json.loads(state_json)
        if (type(record) is not dict
                or set(record) != {"schema_version", "revision", "keys", "revoked"}
                or type(record["schema_version"]) is not int
                or record["schema_version"] != 1
                or type(record["revision"]) is not int
                or not 1 <= record["revision"] <= 2**31 - 1
                or type(record["keys"]) is not list
                or len(record["keys"]) > _MAX_KEYRING_ENTRIES
                or type(record["revoked"]) is not list
                or len(record["revoked"]) > _MAX_REVOKED_KEY_IDS
                or _canonical_json(record).decode("utf-8") != state_json
                or hashlib.sha256(_canonical_json(record)).hexdigest()
                != state_digest):
            raise ValueError

        current = {}
        previous_scope = None
        for entry in record["keys"]:
            if (type(entry) is not dict
                    or set(entry) != {"tenant", "project", "key_id", "public_key"}):
                raise ValueError
            scope = (entry["tenant"], entry["project"], entry["key_id"])
            public_key = entry["public_key"]
            if (any(type(part) is not str or _ID.fullmatch(part) is None
                    for part in scope)
                    or type(public_key) is not str
                    or _PUBLIC_KEY_HEX.fullmatch(public_key) is None
                    or (previous_scope is not None and scope <= previous_scope)):
                raise ValueError
            current[scope] = bytes.fromhex(public_key)
            previous_scope = scope

        revoked = set()
        previous_scope = None
        for item in record["revoked"]:
            if (type(item) is not list or len(item) != 3
                    or any(type(part) is not str or _ID.fullmatch(part) is None
                           for part in item)):
                raise ValueError
            scope = tuple(item)
            if previous_scope is not None and scope <= previous_scope:
                raise ValueError
            revoked.add(scope)
            previous_scope = scope
        if set(current).intersection(revoked):
            raise ValueError
        return record["revision"], current, revoked
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise TopologyKeyringRotationRejected(
            "invalid_topology_keyring_store") from None


class RotatingTopologyKeyring:
    """Atomic rotation for operator-verified public keys.

    Operator public keys are trust anchors supplied at construction and must
    come from protected configuration. Each update must carry an Ed25519
    signature from one of those anchors. With ``state_path``, revision,
    active public keys and removed-key tombstones are kept in a local SQLite
    transaction and shared by instances using that database. This survives
    process restart, but restoring an older database file can still roll state
    back; external trust-anchor custody and rollback-resistant storage remain
    necessary for deployment. Tombstones are bounded; rotation fails closed
    at that bound. Private keys are never persisted.
    """

    def __init__(self, trusted_public_keys: dict[tuple[str, str, str], bytes],
                 *, operator_public_keys: dict[str, bytes], revision: int = 1,
                 state_path: str | None = None):
        if type(revision) is not int or not 1 <= revision <= 2**31 - 1:
            raise TopologyKeyringRotationRejected("invalid_key_revision")
        self._current = _validated_keyring(trusted_public_keys)
        self._operator_keys = _validated_operator_keys(operator_public_keys)
        self._revoked: set[tuple[str, str, str]] = set()
        self._revision = revision
        self._lock = Lock()
        if state_path is not None:
            self._state_path = self._validate_state_path(state_path)
            self._initialize_state_store()
        else:
            self._state_path = None

    @staticmethod
    def _validate_state_path(path: object) -> str:
        if (type(path) is not str or not path or path == ":memory:"
                or path.startswith("file:")
                or "\x00" in path):
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_store")
        try:
            requested_path = Path(path)
            if requested_path.is_symlink() or (
                    requested_path.exists() and not requested_path.is_file()):
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_store")
        except (OSError, RuntimeError):
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_store") from None
        return path

    def _connect_state_store(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self._state_path, timeout=2.0, isolation_level=None,
            )
            connection.execute("PRAGMA busy_timeout=2000")
            return connection
        except sqlite3.Error:
            raise TopologyKeyringRotationRejected(
                "topology_keyring_store_unavailable") from None

    def _read_state(self, connection: sqlite3.Connection
                    ) -> tuple[int, dict[tuple[str, str, str], bytes],
                               set[tuple[str, str, str]]]:
        try:
            columns = tuple(row[1] for row in connection.execute(
                "PRAGMA table_info(topology_keyring_state)").fetchall())
            if columns != ("singleton", "state_json", "state_digest"):
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_store")
            row = connection.execute(
                "SELECT state_json, state_digest FROM topology_keyring_state "
                "WHERE singleton = 1 AND length(state_json) <= ?",
                (_MAX_PERSISTED_STATE_BYTES,),
            ).fetchone()
            if row is None:
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_store")
            return _decode_keyring_state(row[0], row[1])
        except TopologyKeyringRotationRejected:
            raise
        except sqlite3.Error:
            raise TopologyKeyringRotationRejected(
                "invalid_topology_keyring_store") from None

    @staticmethod
    def _write_state(connection: sqlite3.Connection, revision: int,
                     current: dict[tuple[str, str, str], bytes],
                     revoked: set[tuple[str, str, str]]) -> None:
        record = _keyring_state_record(revision, current, revoked)
        state_json = _canonical_json(record).decode("utf-8")
        state_digest = hashlib.sha256(_canonical_json(record)).hexdigest()
        connection.execute(
            "INSERT INTO topology_keyring_state "
            "(singleton, state_json, state_digest) VALUES (1, ?, ?) "
            "ON CONFLICT(singleton) DO UPDATE SET "
            "state_json=excluded.state_json, state_digest=excluded.state_digest",
            (state_json, state_digest),
        )

    def _initialize_state_store(self) -> None:
        connection = self._connect_state_store()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS topology_keyring_state ("
                "singleton INTEGER PRIMARY KEY CHECK (singleton = 1), "
                "state_json TEXT NOT NULL, state_digest TEXT NOT NULL)"
            )
            connection.execute("BEGIN IMMEDIATE")
            columns = tuple(row[1] for row in connection.execute(
                "PRAGMA table_info(topology_keyring_state)").fetchall())
            if columns != ("singleton", "state_json", "state_digest"):
                raise TopologyKeyringRotationRejected(
                    "invalid_topology_keyring_store")
            row = connection.execute(
                "SELECT state_json, state_digest FROM topology_keyring_state "
                "WHERE singleton = 1 AND length(state_json) <= ?",
                (_MAX_PERSISTED_STATE_BYTES,),
            ).fetchone()
            if row is None:
                self._write_state(
                    connection, self._revision, self._current, self._revoked,
                )
            else:
                self._revision, self._current, self._revoked = (
                    _decode_keyring_state(row[0], row[1]))
            connection.execute("COMMIT")
        except TopologyKeyringRotationRejected:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.Error:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise TopologyKeyringRotationRejected(
                "topology_keyring_store_unavailable") from None
        finally:
            connection.close()

    def _refresh_from_store(self) -> None:
        connection = self._connect_state_store()
        try:
            revision, current, revoked = self._read_state(connection)
            self._revision, self._current, self._revoked = (
                revision, current, revoked,
            )
        finally:
            connection.close()

    @staticmethod
    def _validate_rotation(
            revision: int, current_revision: int,
            candidate: dict[tuple[str, str, str], bytes],
            current: dict[tuple[str, str, str], bytes],
            revoked: set[tuple[str, str, str]]) -> set[tuple[str, str, str]]:
        if revision <= current_revision:
            raise TopologyKeyringRotationRejected("stale_key_revision")
        if set(candidate).intersection(revoked):
            raise TopologyKeyringRotationRejected(
                "revoked_topology_key_cannot_be_restored")
        reused_ids = {
            scope for scope in set(current).intersection(candidate)
            if current[scope] != candidate[scope]
        }
        if reused_ids:
            raise TopologyKeyringRotationRejected("topology_key_id_reused")
        newly_revoked = set(current).difference(candidate)
        if len(revoked) + len(newly_revoked) > _MAX_REVOKED_KEY_IDS:
            raise TopologyKeyringRotationRejected(
                "topology_revocation_history_full")
        return revoked.union(newly_revoked)

    def snapshot(self) -> dict[tuple[str, str, str], bytes]:
        """Return a detached snapshot for one verification attempt."""
        with self._lock:
            if self._state_path is not None:
                self._refresh_from_store()
            return dict(self._current)

    @property
    def revision(self) -> int:
        with self._lock:
            if self._state_path is not None:
                self._refresh_from_store()
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
            if self._state_path is None:
                next_revoked = self._validate_rotation(
                    revision, self._revision, candidate,
                    self._current, self._revoked,
                )
                self._revoked = next_revoked
                self._current = candidate
                self._revision = revision
                return

            connection = self._connect_state_store()
            try:
                connection.execute("BEGIN IMMEDIATE")
                current_revision, current, revoked = self._read_state(connection)
                next_revoked = self._validate_rotation(
                    revision, current_revision, candidate, current, revoked,
                )
                self._write_state(connection, revision, candidate, next_revoked)
                connection.execute("COMMIT")
                self._revision, self._current, self._revoked = (
                    revision, candidate, next_revoked,
                )
            except TopologyKeyringRotationRejected:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            except sqlite3.Error:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise TopologyKeyringRotationRejected(
                    "topology_keyring_store_unavailable") from None
            finally:
                connection.close()


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

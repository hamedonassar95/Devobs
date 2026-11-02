"""Offline Ed25519 approvals for curated, provenance-bound incident memories."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .context import ContextError, _id
from .incident_memory import IncidentRecord, _canonical_json

_APPROVAL_ID = re.compile(r"[0-9a-f]{32}\Z")
_SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
_FIELDS = frozenset({
    "schema_version", "approval_id", "approver_id", "approved_at",
    "expires_at", "record", "signature",
})
_SCHEMA_VERSION = 1
_MAX_APPROVAL_TTL_SECONDS = 7 * 24 * 60 * 60
_MAX_KEYRING_ENTRIES = 100
_MAX_BATCH_SIZE = 1000


@dataclass(frozen=True)
class VerifiedIncidentMemoryApproval:
    """A signature-verified approval and the exact record it authorizes."""

    record: IncidentRecord
    approval_id: str
    approver_id: str
    approved_at: str
    expires_at: str
    approval_digest: str

    @property
    def record_digest(self) -> str:
        return self.record.record_digest


def _parse_canonical_utc(value: object) -> datetime:
    if type(value) is not str or len(value) > 35:
        raise ContextError("invalid_memory_approval_time")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError
        instant = instant.astimezone(timezone.utc)
        canonical = instant.isoformat(timespec="microseconds").replace("+00:00", "Z")
    except (ValueError, OverflowError):
        raise ContextError("invalid_memory_approval_time") from None
    if value != canonical:
        raise ContextError("invalid_memory_approval_time")
    return instant


def _validate_keyring(
        trusted_public_keys: object) -> dict[tuple[str, str, str], bytes]:
    if (type(trusted_public_keys) is not dict
            or not 1 <= len(trusted_public_keys) <= _MAX_KEYRING_ENTRIES):
        raise ContextError("invalid_memory_keyring")
    keys = {}
    for scope, public_key in trusted_public_keys.items():
        if (type(scope) is not tuple or len(scope) != 3
                or not all(_id(part) for part in scope)
                or type(public_key) is not bytes
                or len(public_key) != 32):
            raise ContextError("invalid_memory_keyring")
        keys[scope] = public_key
    return keys


def verify_incident_memory_approval(
        value: object,
        trusted_public_keys: dict[tuple[str, str, str], bytes], *,
        now: datetime) -> VerifiedIncidentMemoryApproval:
    """Verify one exact Ed25519 envelope against an externally trusted keyring.

    The public-key map is a trust input and must come from protected configuration;
    this function does not authenticate key enrollment or the person holding a key.
    """
    if type(value) is not dict or set(value) != _FIELDS:
        raise ContextError("invalid_memory_approval")
    if (type(value["schema_version"]) is not int
            or value["schema_version"] != _SCHEMA_VERSION):
        raise ContextError("unsupported_memory_approval")
    if (type(value["approval_id"]) is not str
            or _APPROVAL_ID.fullmatch(value["approval_id"]) is None
            or not _id(value["approver_id"])):
        raise ContextError("invalid_memory_approval")

    try:
        record = IncidentRecord.from_record(value["record"])
    except ContextError:
        raise ContextError("invalid_memory_approval_record") from None
    if (record.to_record() != value["record"] or record.outcome != "resolved"
            or record.source_sha is None or record.recorded_at is None):
        raise ContextError("unapprovable_memory_record")

    keys = _validate_keyring(trusted_public_keys)
    key_scope = (record.tenant, record.project, value["approver_id"])
    public_key = keys.get(key_scope)
    if public_key is None:
        raise ContextError("untrusted_memory_approver")

    approved_at = _parse_canonical_utc(value["approved_at"])
    expires_at = _parse_canonical_utc(value["expires_at"])
    if (expires_at <= approved_at
            or (expires_at - approved_at).total_seconds() > _MAX_APPROVAL_TTL_SECONDS):
        raise ContextError("invalid_memory_approval_window")
    if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
        raise ContextError("invalid_memory_approval_time")
    instant = now.astimezone(timezone.utc)
    if instant < approved_at:
        raise ContextError("future_memory_approval")
    if instant >= expires_at:
        raise ContextError("expired_memory_approval")

    signature_hex = value["signature"]
    if type(signature_hex) is not str or _SIGNATURE.fullmatch(signature_hex) is None:
        raise ContextError("invalid_memory_approval_signature")
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "approval_id": value["approval_id"],
        "approver_id": value["approver_id"],
        "approved_at": value["approved_at"],
        "expires_at": value["expires_at"],
        "record": record.to_record(),
    }
    signature = bytes.fromhex(signature_hex)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, _canonical_json(payload),
        )
    except (InvalidSignature, ValueError):
        raise ContextError("invalid_memory_approval_signature") from None

    complete = {**payload, "signature": signature_hex}
    return VerifiedIncidentMemoryApproval(
        record=record,
        approval_id=value["approval_id"],
        approver_id=value["approver_id"],
        approved_at=value["approved_at"],
        expires_at=value["expires_at"],
        approval_digest=hashlib.sha256(_canonical_json(complete)).hexdigest(),
    )


def verify_incident_memory_approvals(
        values: object,
        trusted_public_keys: dict[tuple[str, str, str], bytes], *,
        now: datetime) -> tuple[VerifiedIncidentMemoryApproval, ...]:
    """Verify a complete bounded batch; reject duplicates without partial results."""
    if type(values) is not list or len(values) > _MAX_BATCH_SIZE:
        raise ContextError("invalid_memory_approval_batch")
    verified = tuple(
        verify_incident_memory_approval(
            value, trusted_public_keys, now=now,
        )
        for value in values
    )
    approval_ids = [item.approval_id for item in verified]
    record_ids = [
        (item.record.tenant, item.record.project, item.record.evidence_digest)
        for item in verified
    ]
    if len(set(approval_ids)) != len(approval_ids):
        raise ContextError("duplicate_memory_approval")
    if len(set(record_ids)) != len(record_ids):
        raise ContextError("duplicate_memory")
    return verified

"""Offline authenticated encryption for bounded tenant-scoped memory bundles."""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .context import ContextError, _id
from .incident_memory import IncidentMemory

_SCHEMA_VERSION = 1
_ALGORITHM = "AES-256-GCM"
_DOMAIN = b"devobs-incident-memory-archive-v1\n"
_KDF_INFO = b"devobs-incident-memory-archive-key-v1\n"
_NONCE = b"\x00" * 12
_FIELDS = frozenset({
    "schema_version", "algorithm", "created_at", "expires_at", "salt",
    "ciphertext",
})
_B64URL = re.compile(r"[A-Za-z0-9_-]+\Z")
_MAX_BUNDLE_BYTES = 2 * 1024 * 1024
_MAX_CIPHERTEXT_BYTES = _MAX_BUNDLE_BYTES + 16
_MAX_CIPHERTEXT_TEXT = (_MAX_CIPHERTEXT_BYTES * 4 + 2) // 3
_MAX_RETENTION_SECONDS = 31_536_000


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _validate_key_and_scope(
    key: object, tenant: object, project: object,
) -> tuple[bytes, str, str]:
    if (type(key) is not bytes or len(key) != 32
            or not _id(tenant) or not _id(project)):
        raise ContextError("invalid_memory_encryption_query")
    return key, tenant, project


def _utc_now(value: object) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ContextError("invalid_memory_encryption_time")
    try:
        offset = value.utcoffset()
        if offset is None:
            raise ValueError
        return value.astimezone(timezone.utc)
    except (OverflowError, TypeError, ValueError):
        raise ContextError("invalid_memory_encryption_time") from None


def _format_time(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) > 35:
        raise ContextError("invalid_encrypted_memory")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        normalized = parsed.astimezone(timezone.utc)
    except (OverflowError, TypeError, ValueError):
        raise ContextError("invalid_encrypted_memory") from None
    if _format_time(normalized) != value:
        raise ContextError("invalid_encrypted_memory")
    return normalized


def _associated_data(
    tenant: str, project: str, created_at: str, expires_at: str, salt: str,
) -> bytes:
    return _DOMAIN + _canonical_json({
        "schema_version": _SCHEMA_VERSION,
        "algorithm": _ALGORITHM,
        "tenant": tenant,
        "project": project,
        "created_at": created_at,
        "expires_at": expires_at,
        "salt": salt,
    })


def _derive_archive_key(key: bytes, salt: bytes) -> bytes:
    return HKDF(
        algorithm=SHA256(), length=32, salt=salt, info=_KDF_INFO,
    ).derive(key)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: object, *, max_text: int) -> bytes:
    if (type(value) is not str or not 1 <= len(value) <= max_text
            or _B64URL.fullmatch(value) is None):
        raise ContextError("invalid_encrypted_memory")
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True,
        )
    except (binascii.Error, ValueError):
        raise ContextError("invalid_encrypted_memory") from None
    if _encode(decoded) != value:
        raise ContextError("invalid_encrypted_memory")
    return decoded


def encrypt_incident_memory_bundle(
    memory: IncidentMemory,
    key: bytes,
    *,
    tenant: str,
    project: str,
    now: datetime,
    retention_seconds: int,
) -> dict:
    """Encrypt one exact-tenant/project bundle with a caller-held 256-bit key.

    The key is neither generated nor retained here. Expiry is authenticated and
    enforced when decrypting; this function cannot delete a file or enforce an
    external retention policy.
    """
    key, tenant, project = _validate_key_and_scope(key, tenant, project)
    instant = _utc_now(now)
    if (type(memory) is not IncidentMemory
            or type(retention_seconds) is not int
            or not 1 <= retention_seconds <= _MAX_RETENTION_SECONDS):
        raise ContextError("invalid_memory_encryption_query")

    bundle = memory.to_bundle()
    if any((row["tenant"], row["project"]) != (tenant, project)
           for row in bundle["records"]):
        raise ContextError("memory_scope_mismatch")
    plaintext = _canonical_json(bundle)
    if len(plaintext) > _MAX_BUNDLE_BYTES:
        raise ContextError("memory_bundle_too_large")

    created_at = _format_time(instant)
    try:
        expires_at = _format_time(
            instant + timedelta(seconds=retention_seconds),
        )
    except OverflowError:
        raise ContextError("invalid_memory_encryption_time") from None
    try:
        salt = os.urandom(32)
        if type(salt) is not bytes or len(salt) != 32:
            raise ValueError
        encoded_salt = _encode(salt)
        ciphertext = AESGCM(_derive_archive_key(key, salt)).encrypt(
            _NONCE, plaintext,
            _associated_data(
                tenant, project, created_at, expires_at, encoded_salt,
            ),
        )
    except (OSError, OverflowError, TypeError, ValueError):
        raise ContextError("memory_encryption_unavailable") from None

    return {
        "schema_version": _SCHEMA_VERSION,
        "algorithm": _ALGORITHM,
        "created_at": created_at,
        "expires_at": expires_at,
        "salt": encoded_salt,
        "ciphertext": _encode(ciphertext),
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_json_constant(_value: str):
    raise ValueError


def decrypt_incident_memory_bundle(
    envelope: object,
    key: bytes,
    *,
    expected_tenant: str,
    expected_project: str,
    now: datetime,
) -> IncidentMemory:
    """Authenticate and decrypt one archive for the caller's exact scope.

    Imported records regain no curator-approval provenance: archives preserve
    incident records only. Callers requiring approved retrieval must separately
    verify the original signed approvals.
    """
    key, expected_tenant, expected_project = _validate_key_and_scope(
        key, expected_tenant, expected_project,
    )
    instant = _utc_now(now)
    if type(envelope) is not dict or set(envelope) != _FIELDS:
        raise ContextError("invalid_encrypted_memory")
    if (type(envelope["schema_version"]) is not int
            or envelope["schema_version"] != _SCHEMA_VERSION
            or type(envelope["algorithm"]) is not str
            or envelope["algorithm"] != _ALGORITHM):
        raise ContextError("unsupported_encrypted_memory")

    created = _parse_time(envelope["created_at"])
    expires = _parse_time(envelope["expires_at"])
    if (expires <= created
            or (expires - created).total_seconds() > _MAX_RETENTION_SECONDS):
        raise ContextError("invalid_encrypted_memory")
    salt = _decode(envelope["salt"], max_text=43)
    ciphertext = _decode(envelope["ciphertext"], max_text=_MAX_CIPHERTEXT_TEXT)
    if len(salt) != 32 or not 16 <= len(ciphertext) <= _MAX_CIPHERTEXT_BYTES:
        raise ContextError("invalid_encrypted_memory")
    encoded_salt = envelope["salt"]
    associated_data = _associated_data(
        expected_tenant, expected_project,
        envelope["created_at"], envelope["expires_at"], encoded_salt,
    )
    try:
        plaintext = AESGCM(_derive_archive_key(key, salt)).decrypt(
            _NONCE, ciphertext, associated_data,
        )
    except (InvalidTag, OverflowError, TypeError, ValueError):
        raise ContextError("invalid_encrypted_memory") from None
    if len(plaintext) > _MAX_BUNDLE_BYTES:
        raise ContextError("invalid_encrypted_memory")
    if instant < created:
        raise ContextError("future_encrypted_memory")
    if instant >= expires:
        raise ContextError("expired_encrypted_memory")

    try:
        bundle = json.loads(
            plaintext.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
        memory = IncidentMemory.from_bundle(bundle)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError,
            TypeError, ValueError):
        raise ContextError("invalid_encrypted_memory") from None
    if any((row["tenant"], row["project"])
           != (expected_tenant, expected_project)
           for row in memory.to_bundle()["records"]):
        raise ContextError("memory_scope_mismatch")
    return memory


def decrypt_approved_incident_memory_bundle(
    envelope: object,
    key: bytes,
    *,
    expected_tenant: str,
    expected_project: str,
    now: datetime,
    approval_envelopes: object,
    trusted_public_keys: object,
    consumption_registry: object,
) -> IncidentMemory:
    """Restore approved records only when signed approvals match the archive.

    Signed approval envelopes are supplied separately and contain incident
    records themselves. Callers must keep them protected and pass them directly
    to this function; this API does not persist or transport them. Approval IDs
    are consumed only after the complete verified record set exactly matches
    the decrypted archive. Replay protection remains process-local.
    """
    from .incident_memory_approval import (
        IncidentMemoryApprovalRegistry, verify_incident_memory_approvals,
    )

    if type(consumption_registry) is not IncidentMemoryApprovalRegistry:
        raise ContextError("invalid_memory_approval_registry")
    archived = decrypt_incident_memory_bundle(
        envelope, key, expected_tenant=expected_tenant,
        expected_project=expected_project, now=now,
    )
    verified = verify_incident_memory_approvals(
        approval_envelopes, trusted_public_keys, now=now,
    )
    approval_records = IncidentMemory(
        [approval.record for approval in verified],
    )
    if approval_records.to_bundle() != archived.to_bundle():
        raise ContextError("memory_approval_archive_mismatch")
    return consumption_registry.load_memory(
        approval_envelopes, trusted_public_keys, now=now,
    )

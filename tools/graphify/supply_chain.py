"""Fail-closed integrity checks for the approved Graphify wheel.

This module performs local verification only. It never downloads, installs or
executes a package. A truncated or non-hexadecimal digest is rejected before a
file is opened, so an unavailable or malformed pin can never be treated as a
passing integrity check.
"""

from __future__ import annotations

import hashlib
import hmac
import pathlib
import re

from .common import PINNED_WHEEL_SHA256

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHUNK_SIZE = 1024 * 1024


class SupplyChainError(Exception):
    """A package identity or integrity check failed and must stop the run."""


def validate_sha256_digest(digest: object, *, label: str = "digest") -> str:
    """Require a complete 64-character lowercase hexadecimal SHA-256 digest."""
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SupplyChainError(f"{label}_must_be_64_hex")
    return digest


def verify_wheel_sha256(
    wheel: pathlib.Path | str,
    expected: str | None = None,
) -> str:
    """Verify a local wheel against the approved full SHA-256 digest."""
    pinned = validate_sha256_digest(
        PINNED_WHEEL_SHA256 if expected is None else expected,
        label="expected_sha256",
    )
    path = pathlib.Path(wheel).resolve()
    if not path.is_file():
        raise SupplyChainError("wheel_not_found")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if not hmac.compare_digest(actual, pinned):
        raise SupplyChainError("wheel_sha256_mismatch")
    return actual

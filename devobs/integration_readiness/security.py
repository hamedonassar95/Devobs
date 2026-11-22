"""Redaction, path safety, license, and approval policy for readiness catalogs."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from scripts.ci_failure_intelligence import redact_secrets

from .models import MAX_SHORT_STRING, MAX_STRING, CatalogError

_SECRET_KEY_PARTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey", "private_key",
    "client_secret", "authorization", "credential", "access_key",
)
_FORBIDDEN_CONFIG_KEYS = frozenset({"command", "cmd", "exec", "script", "shell", "run"})
_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LICENSE_RE = re.compile(r"^[A-Za-z0-9.+-]+$")

APPROVED_LICENSES = frozenset({
    "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MIT", "MPL-2.0",
    "Python-2.0", "Unlicense", "Zlib",
})
RESTRICTED_LICENSES = frozenset({
    "AGPL-3.0-only", "AGPL-3.0-or-later", "BUSL-1.1", "CC-BY-NC-4.0",
    "Commons-Clause", "Elastic-2.0", "GPL-3.0-only", "GPL-3.0-or-later",
    "SSPL-1.0",
})


def redact_text(value: Any, limit: int = MAX_STRING) -> str:
    """Return a bounded, redacted string safe for reports."""
    text = redact_secrets("" if value is None else str(value)).strip()
    text = text.replace("\r", " ").replace("\n", " ")
    if len(text) > limit:
        return text[:limit] + "[TRUNCATED]"
    return text


def is_secret_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def redact_value(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact mappings and sequences without exposing secret values."""
    if _depth > 6:
        return "[TRUNCATED]"
    if isinstance(value, str):
        return redact_text(value, MAX_SHORT_STRING)
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if value is None:
        return None
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in list(value.items())[:50]:
            safe_key = redact_text(key, MAX_SHORT_STRING)
            result[safe_key] = "[REDACTED]" if is_secret_key(key) else redact_value(item, _depth=_depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_value(item, _depth=_depth + 1) for item in list(value)[:50]]
    return "[UNSUPPORTED_VALUE]"


def unsafe_config_keys(config: Any) -> list[str]:
    """Return forbidden command-like keys without inspecting their values."""
    if not isinstance(config, dict):
        return []
    return sorted(str(key) for key in config if isinstance(key, str) and key.lower() in _FORBIDDEN_CONFIG_KEYS)


def config_secret_keys(config: Any) -> list[str]:
    """Return secret-like key names only; values are never returned."""
    if not isinstance(config, dict):
        return []
    return sorted(str(key) for key in config if is_secret_key(key))


def safe_relative_path(value: Any, field: str = "path") -> str:
    """Normalize a catalog path and reject traversal or absolute paths."""
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"invalid_{field}")
    path = value.strip().replace("\\", "/")
    if "\x00" in path or path.startswith("/") or ":" in path or ".." in path.split("/"):
        raise CatalogError(f"unsafe_{field}")
    if not _PATH_RE.fullmatch(path):
        raise CatalogError(f"unsafe_{field}")
    parts = [part for part in path.split("/") if part not in {"", "."}]
    normalized = "/".join(parts)
    if not normalized:
        raise CatalogError(f"unsafe_{field}")
    return normalized


def valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA_RE.fullmatch(value.lower()))


def valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def classify_license(value: Any) -> str:
    """Classify an SPDX license string under this offline policy."""
    if not isinstance(value, str) or not _LICENSE_RE.fullmatch(value):
        return "unknown"
    if value in APPROVED_LICENSES:
        return "approved"
    if value in RESTRICTED_LICENSES:
        return "restricted"
    return "unknown"


def validate_approval(approval: Any, scope_sha: str) -> tuple[bool, str]:
    """Return (accepted, stable_reason) for a human approval record."""
    if not isinstance(approval, dict):
        return False, "missing_human_approval"
    approved_by = approval.get("approved_by")
    if not isinstance(approved_by, str) or not approved_by.strip():
        return False, "approval_identity_missing"
    lowered = approved_by.lower()
    if any(marker in lowered for marker in ("bot", "agent", "automation", "ai-", "llm")):
        return False, "approval_not_human"
    if not valid_date(approval.get("approved_at")):
        return False, "approval_date_invalid"
    if not valid_sha(approval.get("scope_sha")):
        return False, "approval_scope_invalid"
    if approval["scope_sha"].lower() != scope_sha.lower():
        return False, "approval_scope_stale"
    return True, "accepted"


__all__ = [
    "APPROVED_LICENSES",
    "RESTRICTED_LICENSES",
    "classify_license",
    "config_secret_keys",
    "is_secret_key",
    "redact_text",
    "redact_value",
    "safe_relative_path",
    "unsafe_config_keys",
    "valid_date",
    "valid_identifier",
    "valid_sha",
    "validate_approval",
]

"""Bounded, offline input and redaction controls."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.ci_failure_intelligence import redact_secrets

from .models import ControlError, Finding, BLOCKER

MAX_DOCUMENT_BYTES = 512 * 1024
MAX_RESPONSE_BYTES = 128 * 1024
MAX_ITEMS = 100
MAX_STRING = 4096
MAX_EXCERPT = 512

ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{2,63}$")
RUN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^(?:feature|fix|docs|chore)/[A-Za-z0-9._/-]{1,180}$")
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("ascii")).hexdigest()


def redact(value: Any, limit: int = MAX_STRING) -> tuple[str, bool]:
    """Return bounded redacted text and whether secret material was detected."""
    if value is None:
        return "", False
    if not isinstance(value, str):
        raise ControlError("invalid_string")
    original = value.strip()
    redacted = redact_secrets(original)
    safe = redacted[:limit]
    return safe, redacted != original


def _reject_constant(value: str) -> Any:
    raise ControlError("invalid_json_constant")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ControlError("duplicate_json_key")
        result[key] = value
    return result


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ControlError("invalid_json") from exc


def load_document(path: str | Path) -> Any:
    """Read one bounded local UTF-8 JSON document. No network or shell is used."""
    try:
        candidate = Path(path)
        if candidate.is_symlink():
            raise ControlError("invalid_input_path")
        if candidate.stat().st_size > MAX_DOCUMENT_BYTES:
            raise ControlError("input_too_large")
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ControlError("input_unreadable") from exc
    if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ControlError("input_too_large")
    return strict_json_loads(text)


def require_keys(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ControlError(code)
    return value


def bounded_text(value: Any, code: str, *, limit: int = MAX_STRING) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ControlError(code)
    return value.strip()


def safe_source(value: Any) -> str:
    text = bounded_text(value, "invalid_evidence_source", limit=MAX_STRING)
    candidate = text.replace("\\", "/")
    if "\x00" in candidate or re.match(r"^[A-Za-z]:", candidate) or candidate.startswith("/"):
        raise ControlError("invalid_evidence_source")
    parts = candidate.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ControlError("invalid_evidence_source")
    if not candidate.startswith(("local:", "fixture:", "github:", "coordination:")):
        raise ControlError("invalid_evidence_source")
    return candidate


def compare_redaction(original: Any, safe: str) -> bool:
    """True when canonical redaction changed the supplied text."""
    return isinstance(original, str) and redact(original)[0] != original.strip()


def secret_finding(source: str) -> Finding:
    return Finding("SECRET_MATERIAL_DETECTED", BLOCKER, source)

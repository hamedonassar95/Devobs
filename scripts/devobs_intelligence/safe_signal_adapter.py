"""Offline metadata-only safety boundary for selected log and trace outcomes.

This is NOT an OTLP receiver, log-redaction engine, authentication check,
or production storage boundary. Reject payloads with raw bodies or attributes.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_OPERATIONS = frozenset({"ci.check", "http.request", "deploy.change", "agent.review"})
_STATUSES = frozenset({"ok", "error", "unknown"})
_MAX_RECORDS = 32
_MAX_AGE_NS = 900 * 1_000_000_000
_MAX_FUTURE_NS = 60 * 1_000_000_000
_MIN_TIMESTAMP_NS = 1_577_836_800_000_000_000
_MAX_TIMESTAMP_NS = 4_102_444_800_000_000_000


class SafeSignalError(ValueError):
    """Fixed, non-sensitive error code. Input values are never echoed."""


@dataclass(frozen=True)
class SafeSignal:
    tenant: str
    project: str
    source_sha: str
    service: str
    kind: str
    operation: str
    status: str
    observed_at: str
    duration_ms: int | None
    evidence_digest: str


def _safe_id(value: object) -> bool:
    return (type(value) is str and len(value) <= 64
            and _ID.fullmatch(value) is not None)


def from_trusted_safe_signals(
    records: list[dict], *, tenant: str, project: str,
    source_sha: str, now_utc: datetime,
) -> tuple[SafeSignal, ...]:
    """Return only closed-vocabulary metadata; reject whole batch on any error.

    Scope, exact SHA, source authenticity, and UTC clock must be provided by a
    separately authenticated upstream component. No raw logs or prompt bodies.
    """
    if (type(records) is not list or not 1 <= len(records) <= _MAX_RECORDS
            or not _safe_id(tenant) or not _safe_id(project)
            or type(source_sha) is not str or _SHA.fullmatch(source_sha) is None
            or type(now_utc) is not datetime or now_utc.tzinfo is None
            or now_utc.utcoffset() is None):
        raise SafeSignalError("invalid_signal_batch")
    now = now_utc.astimezone(timezone.utc)
    now_ns = int(now.timestamp()) * 1_000_000_000 + now.microsecond * 1000
    results: list[tuple[int, SafeSignal]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for record in records:
        if type(record) is not dict:
            raise SafeSignalError("invalid_signal_fields")
        kind = record.get("kind")
        if type(kind) is not str or kind not in ("trace", "log"):
            raise SafeSignalError("invalid_signal_fields")
        expected = {"kind", "resource", "operation", "status", "time_unix_nano"}
        if kind == "trace":
            expected.add("duration_ms")
        if set(record) != expected:
            raise SafeSignalError("invalid_signal_fields")
        resource = record["resource"]
        if (type(resource) is not dict or set(resource) != {"service.name"}
                or not _safe_id(resource["service.name"])):
            raise SafeSignalError("invalid_signal_fields")
        operation, status = record["operation"], record["status"]
        if (type(operation) is not str or operation not in _OPERATIONS
                or type(status) is not str or status not in _STATUSES):
            raise SafeSignalError("invalid_signal_fields")
        stamp = record["time_unix_nano"]
        if (type(stamp) is not int
                or not _MIN_TIMESTAMP_NS <= stamp <= _MAX_TIMESTAMP_NS):
            raise SafeSignalError("invalid_signal_timestamp")
        if not -_MAX_FUTURE_NS <= now_ns - stamp <= _MAX_AGE_NS:
            raise SafeSignalError("stale_signal")
        duration = record.get("duration_ms")
        if kind == "trace" and (type(duration) is not int or not 0 <= duration <= 600_000):
            raise SafeSignalError("invalid_signal_duration")
        identity = (kind, resource["service.name"], operation, stamp)
        if identity in seen:
            raise SafeSignalError("duplicate_signal")
        seen.add(identity)
        observed = datetime.fromtimestamp(stamp // 1_000_000_000,
                                          tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        safe = {"tenant": tenant, "project": project, "source_sha": source_sha,
                "service": resource["service.name"], "kind": kind,
                "operation": operation, "status": status,
                "observed_at": observed, "time_unix_nano": stamp,
                "duration_ms": duration}
        digest = hashlib.sha256(json.dumps(safe, sort_keys=True,
                                            separators=(",", ":"),
                                            ensure_ascii=True).encode("ascii")).hexdigest()
        results.append((stamp, SafeSignal(tenant, project, source_sha,
                            resource["service.name"], kind, operation,
                            status, observed, duration, digest)))
    return tuple(item for _, item in sorted(results,
                    key=lambda pair: (pair[0], pair[1].kind,
                                      pair[1].service, pair[1].operation)))

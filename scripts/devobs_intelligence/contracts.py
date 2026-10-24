"""Strict, offline evidence contract. Raw project identifiers never leave this boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

_FIELDS = frozenset({"schema_version", "event_id", "provider", "project_ref", "source_sha", "kind", "observed_at", "evidence_digests"})
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_SOURCES = frozenset({"github", "gitlab"})
_KINDS = frozenset({"workflow_run", "pipeline", "incident", "pull_request"})


class EvidenceError(ValueError):
    """Error messages are fixed non-sensitive codes."""


@dataclass(frozen=True)
class EventEnvelopeV1:
    schema_version: int
    event_id: str
    provider: str
    project_digest: str
    source_sha: str
    kind: str
    observed_at: str
    evidence_digests: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise EvidenceError(reason)


def parse_event(payload: dict[str, Any]) -> EventEnvelopeV1:
    _require(type(payload) is dict, "invalid_object")
    _require(set(payload) == _FIELDS, "invalid_fields")
    try:
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise EvidenceError("invalid_encoding") from None
    _require(len(encoded) <= 16_384, "oversized_event")
    _require(type(payload["schema_version"]) is int and payload["schema_version"] == 1, "unsupported_schema")
    event_id = payload["event_id"]
    _require(isinstance(event_id, str) and _ID.fullmatch(event_id) is not None, "invalid_event_id")
    provider = payload["provider"]
    _require(type(provider) is str and provider in _SOURCES, "unsupported_provider")
    kind = payload["kind"]
    _require(type(kind) is str and kind in _KINDS, "unsupported_kind")
    project_ref = payload["project_ref"]
    _require(type(project_ref) is str and 1 <= len(project_ref) <= 256 and not project_ref.isspace(), "invalid_project_ref")
    sha = payload["source_sha"]
    _require(type(sha) is str and _SHA.fullmatch(sha) is not None, "invalid_source_sha")
    raw_date = payload["observed_at"]
    _require(type(raw_date) is str and 1 <= len(raw_date) <= 35, "invalid_timestamp")
    try:
        parsed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        parsed = parsed.astimezone(timezone.utc)
    except ValueError:
        raise EvidenceError("invalid_timestamp") from None
    digests = payload["evidence_digests"]
    _require(type(digests) is list and 1 <= len(digests) <= 32, "invalid_evidence")
    _require(all(type(d) is str and _DIGEST.fullmatch(d) for d in digests), "invalid_evidence")
    _require(len(set(digests)) == len(digests), "duplicate_evidence")
    return EventEnvelopeV1(
        schema_version=1, event_id=event_id, provider=provider,
        project_digest=hashlib.sha256(project_ref.encode("utf-8")).hexdigest(),
        source_sha=sha, kind=kind,
        observed_at=parsed.isoformat(timespec="seconds").replace("+00:00", "Z"),
        evidence_digests=tuple(sorted(digests)),
    )


def parse_events(payloads: list[dict[str, Any]]) -> tuple[EventEnvelopeV1, ...]:
    _require(type(payloads) is list and 1 <= len(payloads) <= 100, "invalid_batch")
    events = tuple(parse_event(payload) for payload in payloads)
    _require(len({(item.provider, item.event_id) for item in events}) == len(events), "duplicate_event_id")
    return events

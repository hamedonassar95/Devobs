"""Deterministic, offline ingestion for structured and sanitized incident data."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from devobs.incident_intelligence.analyzer import (
    AIProvider,
    analyze_signals,
    analyze_workflow_run,
)
from scripts.ci_failure_intelligence import (
    FINDING_INFERRED,
    FINDING_UNVERIFIED,
    FINDING_VERIFIED,
    normalize_log,
    redact_secrets,
    signature_id,
)

from .models import (
    SUPPORTED_SEVERITIES,
    SEVERITY_MEDIUM,
    Evidence,
    IncidentRecord,
    IngestionError,
)

KIND_GITHUB_ACTIONS = "github_actions_failure"
KIND_SANITIZED_CI_LOG = "sanitized_ci_log"
KIND_FAILED_TEST_SUMMARY = "failed_test_summary"
KIND_DEPLOYMENT_HEALTH = "deployment_health_evidence"
KIND_OPERATIONAL_INCIDENT = "operational_incident_report"
SUPPORTED_KINDS = frozenset({
    KIND_GITHUB_ACTIONS,
    KIND_SANITIZED_CI_LOG,
    KIND_FAILED_TEST_SUMMARY,
    KIND_DEPLOYMENT_HEALTH,
    KIND_OPERATIONAL_INCIDENT,
})

MAX_PAYLOAD_BYTES = 131_072
MAX_ITEMS = 100
MAX_TEXT_CHARS = 20_000
MAX_EXCERPT_CHARS = 2_000
MAX_FIELD_CHARS = 256
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_EVIDENCE_CONFIDENCES = frozenset({FINDING_VERIFIED, FINDING_INFERRED, FINDING_UNVERIFIED})
_TEXT_KEYS = ("logs", "log", "summary", "description", "detail", "message", "text", "failed_tests")
_NESTED_TEXT_KEYS = ("message", "detail", "text", "excerpt", "name")


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise IngestionError(code)


def _safe(value: Any, limit: int, code: str = "invalid_text") -> str:
    _require(type(value) is str, code)
    text = redact_secrets(value).strip()
    return text[:limit] + ("[TRUNCATED]" if len(text) > limit else "")


def _payload_size(payload: Mapping[str, Any]) -> int:
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        raise IngestionError("invalid_encoding") from None
    return len(encoded.encode("utf-8"))


def _normalize_evidence(raw: Any, source: str) -> tuple[Evidence, ...]:
    if raw is None:
        return ()
    _require(type(raw) is list and len(raw) <= MAX_ITEMS, "invalid_evidence")
    items: list[Evidence] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(raw):
        if type(entry) is str:
            evidence_source = source
            excerpt = _safe(entry, MAX_EXCERPT_CHARS, "invalid_evidence_excerpt")
            confidence = FINDING_UNVERIFIED
        elif isinstance(entry, Mapping):
            raw_source = entry.get("source", source)
            _require(type(raw_source) is str, "invalid_evidence_source")
            evidence_source = _safe(raw_source, MAX_FIELD_CHARS, "invalid_evidence_source")
            value_key = next((key for key in ("excerpt", "text", "log") if key in entry), "")
            _require(bool(value_key), "invalid_evidence_excerpt")
            excerpt = _safe(entry[value_key], MAX_EXCERPT_CHARS, "invalid_evidence_excerpt")
            confidence = entry.get("confidence", FINDING_UNVERIFIED)
            _require(confidence in _EVIDENCE_CONFIDENCES, "invalid_evidence_confidence")
        else:
            raise IngestionError("invalid_evidence_entry")
        _require(bool(excerpt), "empty_evidence")
        digest = hashlib.sha256(f"{evidence_source}\x00{excerpt}".encode("utf-8")).hexdigest()[:16]
        base = f"ev-{digest}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        items.append(Evidence(
            id=base if count == 0 else f"{base}-{count + 1}",
            source=evidence_source,
            excerpt=excerpt,
            confidence=str(confidence),
        ))
        _require(index < MAX_ITEMS, "too_many_evidence_items")
    return tuple(items)


def _collect_text(payload: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    values: list[str] = []
    warnings: list[str] = []
    for key in _TEXT_KEYS:
        raw = payload.get(key)
        if raw is None:
            continue
        if type(raw) is str:
            if raw.strip():
                values.append(_safe(raw, MAX_TEXT_CHARS))
            continue
        _require(type(raw) is list and len(raw) <= MAX_ITEMS, f"invalid_{key}")
        for entry in raw:
            if type(entry) is str:
                if entry.strip():
                    values.append(_safe(entry, MAX_TEXT_CHARS))
            elif isinstance(entry, Mapping):
                for nested in _NESTED_TEXT_KEYS:
                    nested_value = entry.get(nested)
                    if type(nested_value) is str and nested_value.strip():
                        values.append(_safe(nested_value, MAX_TEXT_CHARS))
            else:
                warnings.append("invalid_log_entry_ignored")
    return tuple(values), tuple(warnings)


def _normalize_metadata(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    _require(isinstance(raw, Mapping), "invalid_metadata")
    result: dict[str, str] = {}
    for key, value in raw.items():
        _require(type(key) is str and bool(key.strip()), "invalid_metadata_key")
        if type(value) in (str, int, float, bool):
            result[_safe(key, MAX_FIELD_CHARS, "invalid_metadata_key")] = _safe(
                str(value), MAX_FIELD_CHARS, "invalid_metadata_value")
        else:
            result[_safe(key, MAX_FIELD_CHARS, "invalid_metadata_key")] = "[UNSUPPORTED_VALUE]"
    return result


def _nested_evidence(report: Any) -> tuple[Evidence, ...]:
    raw = getattr(report, "evidence", ())
    if not isinstance(raw, (list, tuple)):
        return ()
    items: list[Evidence] = []
    for entry in raw[:MAX_ITEMS]:
        if not all(hasattr(entry, name) for name in ("id", "source", "excerpt", "confidence")):
            continue
        confidence = getattr(entry, "confidence")
        if confidence not in _EVIDENCE_CONFIDENCES:
            continue
        items.append(Evidence(
            id=_safe(str(entry.id), MAX_FIELD_CHARS),
            source=_safe(str(entry.source), MAX_FIELD_CHARS),
            excerpt=_safe(str(entry.excerpt), MAX_EXCERPT_CHARS),
            confidence=str(confidence),
        ))
    return tuple(items)


def _nested_report(
    payload: Mapping[str, Any],
    kind: str,
    ai_provider: AIProvider | None,
) -> tuple[tuple[Evidence, ...], tuple[str, ...], str]:
    """Reuse existing analyzers for GitHub and strict-envelope health signals."""
    report = None
    if kind == KIND_GITHUB_ACTIONS and isinstance(payload.get("run"), Mapping) and isinstance(payload.get("jobs"), Mapping):
        report = analyze_workflow_run(dict(payload["run"]), dict(payload["jobs"]), ai_provider=ai_provider)
    elif isinstance(payload.get("envelope"), Mapping) and isinstance(payload.get("signals"), Mapping):
        report = analyze_signals(dict(payload["envelope"]), dict(payload["signals"]), ai_provider=ai_provider)
    if report is None:
        return (), (), "disabled"
    warnings = tuple(_safe(item, MAX_FIELD_CHARS) for item in getattr(report, "warnings", ()))
    provider_status = _safe(str(getattr(getattr(report, "ai_provider", None), "status", "disabled")), MAX_FIELD_CHARS)
    return _nested_evidence(report), warnings, provider_status


def _derive_id(payload: Mapping[str, Any], text: tuple[str, ...], evidence: tuple[Evidence, ...]) -> str:
    canonical = json.dumps({
        "kind": payload.get("kind"),
        "timestamp": payload.get("timestamp") or payload.get("observed_at") or "UNKNOWN",
        "text": list(text),
        "evidence": [item.id for item in evidence],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "inc-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def ingest_incident(payload: Any, *, ai_provider: AIProvider | None = None) -> IncidentRecord:
    """Validate, redact and normalize one offline incident payload."""
    _require(isinstance(payload, Mapping), "invalid_object")
    _require(_payload_size(payload) <= MAX_PAYLOAD_BYTES, "payload_too_large")

    kind = payload.get("kind")
    _require(type(kind) is str and kind in SUPPORTED_KINDS, "unsupported_kind")
    severity = payload.get("severity", SEVERITY_MEDIUM)
    _require(type(severity) is str and severity in SUPPORTED_SEVERITIES, "invalid_severity")

    raw_timestamp = payload.get("timestamp") or payload.get("observed_at") or ""
    _require(type(raw_timestamp) is str and len(raw_timestamp) <= 35, "invalid_timestamp")
    timestamp = raw_timestamp or "UNKNOWN"

    text, warnings = _collect_text(payload)
    metadata = _normalize_metadata(payload.get("metadata"))
    evidence = _normalize_evidence(payload.get("evidence"), kind)
    nested_evidence, nested_warnings, provider_status = _nested_report(payload, kind, ai_provider)
    evidence += nested_evidence
    warnings += nested_warnings

    for item in evidence:
        if item.excerpt and item.excerpt not in text:
            text += (item.excerpt,)

    if not evidence:
        evidence = (Evidence(
            id="ev-no-evidence",
            source=kind,
            excerpt="No sanitized evidence supplied.",
            confidence=FINDING_UNVERIFIED,
        ),)
        warnings += ("missing_evidence",)

    supplied_id = payload.get("incident_id")
    if supplied_id is None:
        incident_id = _derive_id(payload, text, evidence)
    else:
        _require(type(supplied_id) is str and _ID.fullmatch(supplied_id) is not None, "invalid_incident_id")
        incident_id = supplied_id

    title = _safe(str(payload.get("title") or ""), MAX_FIELD_CHARS) or kind
    signature_ids = tuple(sorted({signature_id(normalize_log(item)) for item in text}))
    return IncidentRecord(
        incident_id=incident_id,
        kind=kind,
        timestamp=timestamp,
        severity=severity,
        title=title,
        evidence=evidence,
        text=text,
        metadata=metadata,
        warnings=tuple(dict.fromkeys(warnings)),
        signature_ids=signature_ids,
        provider_status=provider_status,
    )


__all__ = [
    "KIND_DEPLOYMENT_HEALTH",
    "KIND_FAILED_TEST_SUMMARY",
    "KIND_GITHUB_ACTIONS",
    "KIND_OPERATIONAL_INCIDENT",
    "KIND_SANITIZED_CI_LOG",
    "SUPPORTED_KINDS",
    "ingest_incident",
]

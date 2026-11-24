#!/usr/bin/env python3
"""Offline OTLP/JSON logs/traces subset to Devobs' SafeSignal contract.

This is a local file/stdin converter, not a network receiver or redaction tool.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from devobs_intelligence.safe_signal_adapter import (  # noqa: E402
    SafeSignalError,
    from_trusted_safe_signals,
)

MAX_INPUT_BYTES = 1_048_576
MAX_RECORDS = 32
UINT64_MAX = (1 << 64) - 1
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,19})\Z")
_HEX = re.compile(r"[0-9a-fA-F]+\Z")
_ERROR_CODES = frozenset({
    "invalid_arguments", "input_required", "input_unavailable", "input_too_large",
    "invalid_utf8", "invalid_json", "duplicate_json_key", "invalid_otlp_structure",
    "invalid_otlp_resource", "invalid_otlp_scope", "invalid_otlp_record",
    "invalid_otlp_attributes", "invalid_timestamp", "invalid_signal_batch",
    "invalid_signal_fields", "invalid_signal_timestamp", "invalid_signal_duration",
    "stale_signal", "duplicate_signal",
})


class OtlpAdapterError(ValueError):
    """Fixed diagnostic code; never includes submitted field values."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _reject(code: str) -> None:
    raise OtlpAdapterError(code)


def _is_object(value: Any) -> bool:
    return type(value) is dict


def _exact(value: Any, fields: set[str]) -> bool:
    return _is_object(value) and set(value) == fields


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _reject("duplicate_json_key")
        result[key] = value
    return result


def _invalid_json_constant(_value: str) -> None:
    _reject("invalid_json")


def _uint64(value: Any) -> int:
    if type(value) is str:
        if not _DECIMAL.fullmatch(value):
            _reject("invalid_timestamp")
        parsed = int(value)
    elif type(value) is int and 0 <= value <= UINT64_MAX:
        parsed = value
    else:
        _reject("invalid_timestamp")
    if parsed > UINT64_MAX:
        _reject("invalid_timestamp")
    return parsed


def _trace_identifier(value: Any, length: int, *, allow_empty: bool = False) -> bool:
    if allow_empty and value == "":
        return True
    return (type(value) is str and len(value) == length
            and _HEX.fullmatch(value) is not None
            and any(character != "0" for character in value))


def _attribute_map(value: Any, expected: set[str], error_code: str) -> dict[str, str]:
    if type(value) is not list or len(value) != len(expected):
        _reject(error_code)
    result: dict[str, str] = {}
    for pair in value:
        if not _exact(pair, {"key", "value"}) or type(pair["key"]) is not str:
            _reject(error_code)
        key = pair["key"]
        if key not in expected or key in result:
            _reject(error_code)
        typed_value = pair["value"]
        if not _exact(typed_value, {"stringValue"}) or type(typed_value["stringValue"]) is not str:
            _reject(error_code)
        result[key] = typed_value["stringValue"]
    if set(result) != expected:
        _reject(error_code)
    return result


def _log_timestamp(record: dict[str, Any]) -> int:
    allowed = {"attributes", "timeUnixNano", "observedTimeUnixNano"}
    if not {"attributes"}.issubset(record) or not set(record).issubset(allowed):
        _reject("invalid_otlp_record")
    time_value = _uint64(record["timeUnixNano"]) if "timeUnixNano" in record else 0
    observed_value = (
        _uint64(record["observedTimeUnixNano"])
        if "observedTimeUnixNano" in record else 0
    )
    timestamp = time_value or observed_value
    if timestamp == 0:
        _reject("invalid_timestamp")
    return timestamp


def _extract_signals(document: Any) -> list[dict[str, Any]]:
    if not _exact(document, {"resourceLogs"}) or type(document["resourceLogs"]) is not list:
        _reject("invalid_otlp_structure")
    resource_logs = document["resourceLogs"]
    if not 1 <= len(resource_logs) <= MAX_RECORDS:
        _reject("invalid_otlp_structure")

    signals: list[dict[str, Any]] = []
    for resource_log in resource_logs:
        if not _exact(resource_log, {"resource", "scopeLogs"}):
            _reject("invalid_otlp_structure")
        resource = resource_log["resource"]
        if not _exact(resource, {"attributes"}):
            _reject("invalid_otlp_resource")
        resource_attributes = _attribute_map(
            resource["attributes"], {"service.name"}, "invalid_otlp_resource"
        )
        scopes = resource_log["scopeLogs"]
        if type(scopes) is not list or not 1 <= len(scopes) <= MAX_RECORDS:
            _reject("invalid_otlp_scope")
        for scope in scopes:
            if not _exact(scope, {"scope", "logRecords"}) or not _exact(scope["scope"], set()):
                _reject("invalid_otlp_scope")
            records = scope["logRecords"]
            if type(records) is not list or not records:
                _reject("invalid_otlp_record")
            for record in records:
                if not _is_object(record):
                    _reject("invalid_otlp_record")
                stamp = _log_timestamp(record)
                attributes = _attribute_map(
                    record["attributes"],
                    {"devobs.operation", "devobs.status"},
                    "invalid_otlp_attributes",
                )
                signals.append({
                    "kind": "log",
                    "resource": {"service.name": resource_attributes["service.name"]},
                    "operation": attributes["devobs.operation"],
                    "status": attributes["devobs.status"],
                    "time_unix_nano": stamp,
                })
                if len(signals) > MAX_RECORDS:
                    _reject("invalid_signal_batch")
    return signals


def _extract_trace_signals(document: Any) -> list[dict[str, Any]]:
    if not _exact(document, {"resourceSpans"}) or type(document["resourceSpans"]) is not list:
        _reject("invalid_otlp_structure")
    resource_spans = document["resourceSpans"]
    if not 1 <= len(resource_spans) <= MAX_RECORDS:
        _reject("invalid_otlp_structure")

    signals: list[dict[str, Any]] = []
    required_span_fields = {
        "traceId", "spanId", "name", "startTimeUnixNano", "endTimeUnixNano",
    }
    optional_span_fields = {"parentSpanId", "kind", "status"}
    for resource_span in resource_spans:
        if not _exact(resource_span, {"resource", "scopeSpans"}):
            _reject("invalid_otlp_structure")
        resource = resource_span["resource"]
        if not _exact(resource, {"attributes"}):
            _reject("invalid_otlp_resource")
        resource_attributes = _attribute_map(
            resource["attributes"], {"service.name"}, "invalid_otlp_resource"
        )
        scopes = resource_span["scopeSpans"]
        if type(scopes) is not list or not 1 <= len(scopes) <= MAX_RECORDS:
            _reject("invalid_otlp_scope")
        for scope in scopes:
            if not _exact(scope, {"scope", "spans"}) or not _exact(scope["scope"], set()):
                _reject("invalid_otlp_scope")
            spans = scope["spans"]
            if type(spans) is not list or not spans:
                _reject("invalid_otlp_record")
            for span in spans:
                if (not _is_object(span)
                        or not required_span_fields.issubset(span)
                        or not set(span).issubset(required_span_fields | optional_span_fields)):
                    _reject("invalid_otlp_record")
                if (not _trace_identifier(span["traceId"], 32)
                        or not _trace_identifier(span["spanId"], 16)):
                    _reject("invalid_otlp_record")
                if "parentSpanId" in span and not _trace_identifier(
                    span["parentSpanId"], 16, allow_empty=True
                ):
                    _reject("invalid_otlp_record")
                if "kind" in span and (
                    type(span["kind"]) is not int or not 0 <= span["kind"] <= 5
                ):
                    _reject("invalid_otlp_record")

                status = span.get("status", {})
                if not _exact(status, set()) and not _exact(status, {"code"}):
                    _reject("invalid_otlp_record")
                status_code = status.get("code", 0)
                status_map = {0: "unknown", 1: "ok", 2: "error"}
                if type(status_code) is not int or status_code not in status_map:
                    _reject("invalid_otlp_record")

                start = _uint64(span["startTimeUnixNano"])
                end = _uint64(span["endTimeUnixNano"])
                if end < start:
                    _reject("invalid_timestamp")
                signals.append({
                    "kind": "trace",
                    "resource": {"service.name": resource_attributes["service.name"]},
                    "operation": span["name"],
                    "status": status_map[status_code],
                    "time_unix_nano": end,
                    "duration_ms": (end - start) // 1_000_000,
                })
                if len(signals) > MAX_RECORDS:
                    _reject("invalid_signal_batch")
    return signals


def convert_text(
    raw: str,
    *,
    tenant: str,
    project: str,
    source_sha: str,
    now_utc: datetime,
) -> tuple[Any, ...]:
    """Normalize a strict, metadata-only OTLP/JSON subset without I/O."""
    if type(raw) is not str:
        _reject("invalid_json")
    try:
        byte_length = len(raw.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        _reject("invalid_utf8")
    if byte_length > MAX_INPUT_BYTES:
        _reject("input_too_large")
    try:
        document = json.loads(
            raw,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_invalid_json_constant,
        )
    except OtlpAdapterError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        _reject("invalid_json")

    if _exact(document, {"resourceLogs"}):
        safe_records = _extract_signals(document)
    elif _exact(document, {"resourceSpans"}):
        safe_records = _extract_trace_signals(document)
    else:
        _reject("invalid_otlp_structure")
    try:
        return from_trusted_safe_signals(
            safe_records,
            tenant=tenant,
            project=project,
            source_sha=source_sha,
            now_utc=now_utc,
        )
    except SafeSignalError as error:
        code = str(error)
        _reject(code if code in _ERROR_CODES else "invalid_signal_batch")


def _read_bounded_input(path: str) -> str:
    if path == "-":
        if sys.stdin.isatty():
            _reject("input_required")
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            _reject("input_unavailable")
        descriptor = -1
        try:
            descriptor = os.open(path, os.O_RDONLY | nofollow)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _reject("input_unavailable")
            if metadata.st_size > MAX_INPUT_BYTES:
                _reject("input_too_large")
            with os.fdopen(descriptor, "rb", closefd=True) as stream:
                descriptor = -1
                data = stream.read(MAX_INPUT_BYTES + 1)
        except OtlpAdapterError:
            raise
        except OSError:
            _reject("input_unavailable")
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    if len(data) > MAX_INPUT_BYTES:
        _reject("input_too_large")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _reject("invalid_utf8")


def _arguments(argv: list[str]) -> dict[str, str] | None:
    if argv == ["--help"]:
        sys.stdout.write(
            "Usage: python3 scripts/integrations/otlp_logs_traces_adapter.py "
            "--input <file|-> --tenant <id> --project <id> --source-sha <sha>\n"
        )
        return None
    allowed = {"--input", "--tenant", "--project", "--source-sha"}
    if len(argv) != 8:
        _reject("invalid_arguments")
    parsed: dict[str, str] = {}
    for index in range(0, len(argv), 2):
        name, value = argv[index], argv[index + 1]
        if name not in allowed or name in parsed or not value or value.startswith("--"):
            _reject("invalid_arguments")
        parsed[name] = value
    if set(parsed) != allowed:
        _reject("invalid_arguments")
    return parsed


def main(argv: list[str] | None = None) -> int:
    try:
        args = _arguments(sys.argv[1:] if argv is None else argv)
        if args is None:
            return 0
        signals = convert_text(
            _read_bounded_input(args["--input"]),
            tenant=args["--tenant"],
            project=args["--project"],
            source_sha=args["--source-sha"],
            now_utc=datetime.now(timezone.utc),
        )
        output = "".join(
            json.dumps(asdict(signal), sort_keys=True, separators=(",", ":")) + "\n"
            for signal in signals
        )
        sys.stdout.write(output)
        return 0
    except OtlpAdapterError as error:
        code = error.code if error.code in _ERROR_CODES else "internal_error"
        sys.stderr.write(f"otlp-adapter: {code}\n")
        return 2
    except Exception:
        sys.stderr.write("otlp-adapter: internal_error\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

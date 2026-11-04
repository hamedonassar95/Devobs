"""Read-only WSGI API contract; does not start an HTTP server or deploy."""
from __future__ import annotations

import json
import math
import re
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from threading import BoundedSemaphore, Lock
from typing import Callable

from .oidc_tokens import AccessTokenVerifier, AuthenticationError
from .openai_error_diagnosis import (
    DiagnosticInputError,
    DiagnosticProviderError,
    MAX_ERROR_LOG_BYTES,
    validate_error_log,
)

_CI_PATH = re.compile(r"/v1/tenants/([^/]+)/projects/([^/]+)/ci\Z")
_SERVICE_AUTH_PATH = re.compile(
    r"/v1/tenants/([^/]+)/projects/([^/]+)/services/([^/]+)/authorization\Z"
)
_DIAGNOSIS_PATH = re.compile(
    r"/v1/tenants/([^/]+)/projects/([^/]+)/services/([^/]+)/diagnostics\Z"
)
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_STATES = frozenset({"success","failed","pending","running","stale","missing","skipped","canceled","manual","scheduled"})
_MAX_DIAGNOSIS_BODY_BYTES = MAX_ERROR_LOG_BYTES * 4


def reject_request_body(environ, start_response, *, allow_body=False,
                        max_body_bytes=_MAX_DIAGNOSIS_BODY_BYTES):
    """Reject unbounded bodies at the WSGI boundary; only diagnosis accepts JSON."""
    content_length = environ.get("CONTENT_LENGTH", "")
    transfer_encoding = environ.get("HTTP_TRANSFER_ENCODING", "")
    input_terminated = environ.get("wsgi.input_terminated")
    if (content_length in ("", "0") and transfer_encoding in ("", None)
            and not input_terminated):
        return None
    if allow_body:
        if transfer_encoding not in ("", None):
            return _reply(start_response, "400 Bad Request", {"error": "invalid_content_length"})
        if (type(content_length) is not str or not content_length.isascii()
                or not content_length.isdigit() or int(content_length) < 1):
            return _reply(start_response, "400 Bad Request", {"error": "invalid_content_length"})
        if int(content_length) > max_body_bytes:
            return _reply(start_response, "413 Content Too Large", {"error": "request_too_large"})
        return None
    return _reply(start_response, "400 Bad Request",
                  {"error": "request_body_not_allowed"})


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _diagnosis_request(environ):
    content_type = environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ValueError("invalid_request")
    try:
        length = int(environ.get("CONTENT_LENGTH", ""))
        stream = environ["wsgi.input"]
        raw = stream.read(length)
    except (KeyError, TypeError, ValueError, OSError):
        raise ValueError("invalid_request") from None
    if len(raw) != length or len(raw) > _MAX_DIAGNOSIS_BODY_BYTES:
        raise ValueError("invalid_request")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise ValueError("invalid_request") from None
    if (type(payload) is not dict or set(payload) != {"error_log", "data_redacted"}
            or payload["data_redacted"] is not True):
        raise ValueError("redacted_log_required")
    return validate_error_log(payload["error_log"])


@dataclass
class _RateWindow:
    timestamps: deque[float] = field(default_factory=deque)
    last_seen: float = 0.0


class _SubjectTenantRateLimiter:
    """Bounded process-local sliding window; a gateway is still needed globally."""

    def __init__(self, requests_per_window: int, window_seconds: int,
                 max_tracked_principals: int, clock: Callable[[], float]):
        for name, value in (("requests_per_window", requests_per_window),
                            ("window_seconds", window_seconds),
                            ("max_tracked_principals", max_tracked_principals)):
            if type(value) is not int or value < 1:
                raise ValueError(f"invalid_{name}")
        if not callable(clock):
            raise ValueError("invalid_clock")
        self._limit = requests_per_window
        self._window = window_seconds
        self._max_subjects = max_tracked_principals
        self._clock = clock
        self._entries: OrderedDict[tuple[str, str], _RateWindow] = OrderedDict()
        self._lock = Lock()

    def retry_after(self, subject: str, tenant: str) -> int | None:
        now = self._clock()
        key = (subject, tenant)
        with self._lock:
            # Entries are ordered by last use, so expire old identifiers promptly.
            while self._entries:
                oldest_key, oldest = next(iter(self._entries.items()))
                if oldest.last_seen + self._window > now:
                    break
                self._entries.pop(oldest_key)
            entry = self._entries.get(key)
            if entry is None:
                if len(self._entries) >= self._max_subjects:
                    self._entries.popitem(last=False)
                entry = _RateWindow()
                self._entries[key] = entry
            else:
                self._entries.move_to_end(key)
            while entry.timestamps and entry.timestamps[0] <= now - self._window:
                entry.timestamps.popleft()
            entry.last_seen = now
            if len(entry.timestamps) >= self._limit:
                return max(1, math.ceil(entry.timestamps[0] + self._window - now))
            entry.timestamps.append(now)
            return None


def make_app(verifier: AccessTokenVerifier, tenant_gate: object, *, diagnostician=None,
             requests_per_window: int = 60, window_seconds: int = 60,
             diagnostic_requests_per_window: int = 5,
             max_tracked_principals: int = 4096, max_in_flight: int = 8,
             clock: Callable[[], float] = time.monotonic) -> Callable:
    """Bounded authenticated API: read GETs plus opt-in advisory model diagnosis."""
    limiter = _SubjectTenantRateLimiter(requests_per_window, window_seconds,
                                        max_tracked_principals, clock)
    diagnostic_limiter = _SubjectTenantRateLimiter(
        diagnostic_requests_per_window, window_seconds, max_tracked_principals, clock)
    if type(max_in_flight) is not int or max_in_flight < 1:
        raise ValueError("invalid_max_in_flight")
    in_flight = BoundedSemaphore(max_in_flight)

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        route = None
        match = None
        if type(path) is str and len(path) <= 256:
            match = _CI_PATH.fullmatch(path)
            if match is not None:
                route = "ci"
            else:
                match = _SERVICE_AUTH_PATH.fullmatch(path)
                if match is not None:
                    route = "service_authorization"
                else:
                    match = _DIAGNOSIS_PATH.fullmatch(path)
                    if match is not None:
                        route = "diagnosis"
        rejected = reject_request_body(
            environ, start_response,
            allow_body=route == "diagnosis" and method == "POST",
        )
        if rejected is not None:
            return rejected
        if route is None or match is None:
            return _reply(start_response, "404 Not Found", {"error":"not_found"})
        if method != ("POST" if route == "diagnosis" else "GET"):
            return _reply(start_response, "405 Method Not Allowed", {"error":"method_not_allowed"},
                          [("Allow", "POST" if route == "diagnosis" else "GET")])
        if not in_flight.acquire(blocking=False):
            return _reply(start_response, "503 Service Unavailable", {"error":"backend_busy"},
                          [("Retry-After", "1")])
        try:
            authorization = environ.get("HTTP_AUTHORIZATION", "")
            if type(authorization) is not str or not authorization.startswith("Bearer "):
                return _reply(start_response, "401 Unauthorized", {"error":"invalid_token"},
                              [("WWW-Authenticate", 'Bearer error="invalid_token"')])
            try:
                principal = verifier.verify(authorization[7:])
            except AuthenticationError:
                return _reply(start_response, "401 Unauthorized", {"error":"invalid_token"},
                              [("WWW-Authenticate", 'Bearer error="invalid_token"')])
            tenant_id, project_id = match.groups()[:2]
            if route == "diagnosis" and "devobs.ai.diagnose" not in principal.scopes:
                return _reply(start_response, "403 Forbidden", {"error": "access_denied"})
            try:
                retry_after = limiter.retry_after(principal.subject, tenant_id)
            except Exception:
                return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
            if retry_after is not None:
                return _reply(start_response, "429 Too Many Requests", {"error":"rate_limited"},
                              [("Retry-After", str(retry_after))])
            if route == "diagnosis":
                try:
                    allowed = tenant_gate.authorize_service(
                        principal.subject, tenant_id, project_id, match.group(3))
                except ValueError:
                    return _reply(start_response, "403 Forbidden", {"error": "access_denied"})
                except Exception:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "backend_unavailable"})
                if type(allowed) is not bool:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "backend_unavailable"})
                if not allowed:
                    return _reply(start_response, "403 Forbidden", {"error": "access_denied"})
                if diagnostician is None:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "ai_not_configured"})
                try:
                    diagnostic_retry = diagnostic_limiter.retry_after(principal.subject, tenant_id)
                except Exception:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "backend_unavailable"})
                if diagnostic_retry is not None:
                    return _reply(start_response, "429 Too Many Requests",
                                  {"error": "rate_limited"},
                                  [("Retry-After", str(diagnostic_retry))])
                try:
                    error_log = _diagnosis_request(environ)
                except DiagnosticInputError as error:
                    return _reply(start_response, "400 Bad Request",
                                  {"error": str(error)})
                except ValueError as error:
                    return _reply(start_response, "400 Bad Request",
                                  {"error": str(error)})
                started = clock()
                try:
                    result = diagnostician.diagnose(error_log)
                    if type(result) is not dict or set(result) != {
                        "diagnosis", "recommendation", "severity", "confidence"
                    }:
                        raise DiagnosticProviderError("provider_invalid_response")
                    model = diagnostician.model
                    if (type(model) is not str or len(model) > 128
                            or any(type(result[field]) is not str or not result[field]
                                   or len(result[field]) > 1200
                                   for field in ("diagnosis", "recommendation"))
                            or result["severity"] not in {
                                "low", "medium", "high", "critical", "unknown"
                            }
                            or result["confidence"] not in {"low", "medium", "high"}):
                        raise DiagnosticProviderError("provider_invalid_response")
                except DiagnosticProviderError:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "ai_unavailable"})
                except Exception:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error": "ai_unavailable"})
                response = dict(result)
                response["model"] = model
                response["latency_ms"] = max(0, int((clock() - started) * 1000))
                return _reply(start_response, "200 OK", response)
            if route == "service_authorization":
                try:
                    allowed = tenant_gate.authorize_service(
                        principal.subject, tenant_id, project_id, match.group(3))
                except ValueError:
                    return _reply(start_response, "403 Forbidden", {"error":"access_denied"})
                except Exception:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error":"backend_unavailable"})
                if type(allowed) is not bool:
                    return _reply(start_response, "503 Service Unavailable",
                                  {"error":"backend_unavailable"})
                if not allowed:
                    return _reply(start_response, "403 Forbidden", {"error":"access_denied"})
                return _no_content(start_response)
            try:
                status = tenant_gate.read_status(principal.subject, tenant_id, project_id)
            except ValueError:
                return _reply(start_response, "403 Forbidden", {"error":"access_denied"})
            except Exception:
                return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
            if (type(status) is not dict or set(status) != {"ci_state", "source_sha"}
                    or type(status["ci_state"]) is not str or status["ci_state"] not in _STATES
                    or type(status["source_sha"]) is not str
                    or _SHA.fullmatch(status["source_sha"]) is None):
                return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
            return _reply(start_response, "200 OK", status)
        finally:
            in_flight.release()
    return app


def _reply(start, status: str, obj: dict, extra: list[tuple[str,str]] | None = None):
    body = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
               ("Content-Length", str(len(body)))] + (extra or [])
    start(status, headers)
    return [body]


def _no_content(start):
    start("204 No Content", [("Cache-Control", "no-store"),
                             ("X-Content-Type-Options", "nosniff"),
                             ("Content-Length", "0")])
    return [b""]

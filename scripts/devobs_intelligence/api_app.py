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

_PATH = re.compile(r"/v1/tenants/([^/]+)/projects/([^/]+)/ci\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_STATES = frozenset({"success","failed","pending","running","stale","missing","skipped","canceled","manual","scheduled"})


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


def make_app(verifier: AccessTokenVerifier, tenant_gate: object, *,
             requests_per_window: int = 60, window_seconds: int = 60,
             max_tracked_principals: int = 4096, max_in_flight: int = 8,
             clock: Callable[[], float] = time.monotonic) -> Callable:
    """A bounded, process-local GET path including token verification and storage reads."""
    limiter = _SubjectTenantRateLimiter(requests_per_window, window_seconds,
                                        max_tracked_principals, clock)
    if type(max_in_flight) is not int or max_in_flight < 1:
        raise ValueError("invalid_max_in_flight")
    in_flight = BoundedSemaphore(max_in_flight)

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        match = _PATH.fullmatch(path) if type(path) is str and len(path) <= 256 else None
        if match is None:
            return _reply(start_response, "404 Not Found", {"error":"not_found"})
        if method != "GET":
            return _reply(start_response, "405 Method Not Allowed", {"error":"method_not_allowed"},
                          [("Allow", "GET")])
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
            tenant_id, project_id = match.groups()
            try:
                retry_after = limiter.retry_after(principal.subject, tenant_id)
            except Exception:
                return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
            if retry_after is not None:
                return _reply(start_response, "429 Too Many Requests", {"error":"rate_limited"},
                              [("Retry-After", str(retry_after))])
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

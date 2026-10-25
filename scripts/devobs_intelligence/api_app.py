"""Read-only WSGI API contract; does not start an HTTP server or deploy."""
from __future__ import annotations

import json
import re
from typing import Callable

from .oidc_tokens import AccessTokenVerifier, AuthenticationError

_PATH = re.compile(r"/v1/tenants/([^/]+)/projects/([^/]+)/ci\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_STATES = frozenset({"success","failed","pending","running","stale","missing","skipped","canceled","manual","scheduled"})


def make_app(verifier: AccessTokenVerifier, tenant_gate: object) -> Callable:
    """A pure in-process WSGI callable, not a production deployment."""
    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        match = _PATH.fullmatch(path) if type(path) is str and len(path) <= 256 else None
        if match is None:
            return _reply(start_response, "404 Not Found", {"error":"not_found"})
        if method != "GET":
            return _reply(start_response, "405 Method Not Allowed", {"error":"method_not_allowed"},
                          [("Allow", "GET")])
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
            status = tenant_gate.read_status(principal.subject, tenant_id, project_id)
        except ValueError:
            return _reply(start_response, "403 Forbidden", {"error":"access_denied"})
        except Exception:
            return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
        if (type(status) is not dict or set(status) != {"ci_state", "source_sha"}
                or type(status["ci_state"]) is not str or status["ci_state"] not in _STATES
                or type(status["source_sha"]) is not str or _SHA.fullmatch(status["source_sha"]) is None):
            return _reply(start_response, "503 Service Unavailable", {"error":"backend_unavailable"})
        return _reply(start_response, "200 OK", status)
    return app


def _reply(start, status: str, obj: dict, extra: list[tuple[str,str]] | None = None):
    body = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
               ("Content-Length", str(len(body)))] + (extra or [])
    start(status, headers)
    return [body]

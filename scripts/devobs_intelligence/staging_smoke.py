"""Operator-triggered, read-only DevObs Staging HTTPS contract checks.

No discovery, redirects, mutation, provider provisioning or secret printing.
Only exact operator-pinned Render onrender.com hosts are allowed in this gate.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from urllib import error, parse, request

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+onrender\.com\Z")
_STATES = {"success", "failed", "pending", "running", "stale",
           "missing", "skipped", "canceled", "manual", "scheduled"}
_BODY_LIMIT = 2048


class SmokeFailure(Exception):
    """Fixed, non-sensitive failure code. Never include URLs or credentials."""


@dataclass(frozen=True)
class SmokeSettings:
    base_url: str
    expected_host: str
    tenant: str
    project: str
    denied_tenant: str
    bearer_token: str
    denied_tenant_token: str

    def validate(self) -> str:
        url = self.base_url
        if type(url) is not str or len(url) > 256 or not url.isascii():
            raise SmokeFailure("invalid_staging_target")
        try:
            parsed = parse.urlsplit(url)
            host = parsed.hostname
            if (parsed.scheme != "https" or not host
                    or parsed.username or parsed.password or parsed.port is not None
                    or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                    or url not in ("https://" + host, "https://" + host + "/")
                    or _HOST.fullmatch(host) is None
                    or type(self.expected_host) is not str
                    or host != self.expected_host):
                raise SmokeFailure("invalid_staging_target")
        except ValueError:
            raise SmokeFailure("invalid_staging_target") from None
        for item in (self.tenant, self.project, self.denied_tenant):
            if type(item) is not str or _ID.fullmatch(item) is None:
                raise SmokeFailure("invalid_staging_scope")
        if self.tenant == self.denied_tenant:
            raise SmokeFailure("invalid_staging_scope")
        for token in (self.bearer_token, self.denied_tenant_token):
            if (type(token) is not str or not 40 <= len(token) <= 8192
                    or not token.isascii() or token.count(".") != 2):
                raise SmokeFailure("invalid_staging_credentials")
        if self.bearer_token == self.denied_tenant_token:
            raise SmokeFailure("invalid_staging_credentials")
        return "https://" + host


class _RejectRedirects(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_https(url: str, token: str | None) -> tuple[int, dict[str, str], bytes]:
    # Only called after SmokeSettings validates the URL origin and path.
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    opener = request.build_opener(_RejectRedirects)
    try:
        req = request.Request(url, headers=headers, method="GET")
        try:
            response = opener.open(req, timeout=5)
        except error.HTTPError as exc:
            response = exc
        with response:
            status = response.status if hasattr(response, "status") else response.code
            reply_headers = {k.lower(): v for k, v in response.headers.items()}
            body = response.read(_BODY_LIMIT + 1)
        if len(body) > _BODY_LIMIT:
            raise SmokeFailure("oversized_response")
        return (status, reply_headers, body)
    except SmokeFailure:
        raise
    except Exception:
        # Do not accidentally output error URLs, HTTP bodies, or Authorization.
        raise SmokeFailure("network_failure") from None


def run_smoke(settings: SmokeSettings, fetch=fetch_https) -> None:
    origin = settings.validate()
    api = ("/v1/tenants/" + settings.tenant +
           "/projects/" + settings.project + "/ci")

    def check(name, path, bearer, expected_status):
        status, headers, body = fetch(origin + path, bearer)
        if type(status) is not int or status != expected_status:
            raise SmokeFailure(name + "_status")
        cache = headers.get("cache-control", "")
        if (type(cache) is not str or
                "no-store" not in {v.strip().lower() for v in cache.split(",")}):
            raise SmokeFailure(name + "_cache")
        if expected_status == 204:
            if body:
                raise SmokeFailure(name + "_body")
            return None
        if len(body) > _BODY_LIMIT or not headers.get(
                "content-type", "").lower().startswith("application/json"):
            raise SmokeFailure(name + "_format")
        try:
            obj = json.loads(body)
        except (ValueError, UnicodeDecodeError, TypeError):
            raise SmokeFailure(name + "_format") from None
        if type(obj) is not dict:
            raise SmokeFailure(name + "_format")
        return obj

    check("liveness", "/healthz", None, 204)
    check("readiness", "/readyz", None, 204)
    missing = check("anonymous", api, None, 401)
    if missing != {"error": "invalid_token"}:
        raise SmokeFailure("anonymous_response")
    allowed = check("allowed", api, settings.bearer_token, 200)
    def valid_ci_status(value):
        return (type(value) is dict
                and set(value) == {"ci_state", "source_sha"}
                and type(value["ci_state"]) is str
                and value["ci_state"] in _STATES
                and type(value["source_sha"]) is str
                and _SHA.fullmatch(value["source_sha"]) is not None)

    if not valid_ci_status(allowed):
        raise SmokeFailure("allowed_response")
    denied_path = ("/v1/tenants/" + settings.denied_tenant +
                   "/projects/" + settings.project + "/ci")
    # Prove the synthetic project exists for the other tenant before checking
    # that our original tenant identity cannot read it (avoid false 403s).
    fixture = check("denied_fixture", denied_path, settings.denied_tenant_token, 200)
    if not valid_ci_status(fixture):
        raise SmokeFailure("denied_fixture_response")
    denied = check("tenant_isolation", denied_path, settings.bearer_token, 403)
    if denied != {"error": "access_denied"}:
        raise SmokeFailure("tenant_isolation_response")


def main() -> int:
    cfg = SmokeSettings(
        base_url=os.getenv("DEVOBS_STAGING_BASE_URL", ""),
        expected_host=os.getenv("DEVOBS_STAGING_EXPECTED_HOST", ""),
        tenant=os.getenv("DEVOBS_STAGING_TENANT", ""),
        project=os.getenv("DEVOBS_STAGING_PROJECT", ""),
        denied_tenant=os.getenv("DEVOBS_STAGING_DENIED_TENANT", ""),
        bearer_token=os.getenv("DEVOBS_STAGING_TOKEN", ""),
        denied_tenant_token=os.getenv("DEVOBS_STAGING_DENIED_TENANT_TOKEN", ""),
    )
    try:
        run_smoke(cfg)
    except SmokeFailure as exc:
        print("DevObs staging smoke: FAIL (" + str(exc) + ")", file=sys.stderr)
        return 1
    print("DevObs staging smoke: PASS (read-only verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

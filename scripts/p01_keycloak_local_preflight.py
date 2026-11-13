#!/usr/bin/env python3
"""Read-only local Keycloak OIDC discovery and public-JWKS preflight.

The CLI contacts only http://127.0.0.1:8080. Its HTTP result is intentionally
not suitable as Devobs production OIDC configuration: the production issuer
policy requires HTTPS and this tool never validates a signed access token.
"""
from __future__ import annotations

import base64
import binascii
import http.client
import json
import re
import sys
from urllib.parse import urlsplit


LOCAL_ORIGIN = "http://127.0.0.1:8080"
REALM = "devobs-local"
DISCOVERY_PATH = f"/realms/{REALM}/.well-known/openid-configuration"
JWKS_PATH = f"/realms/{REALM}/protocol/openid-connect/certs"
DISCOVERY_LIMIT = 16 * 1024
JWKS_LIMIT = 64 * 1024
HEADER_COUNT_LIMIT = 64
HEADER_BYTES_LIMIT = 16 * 1024
REQUEST_TIMEOUT_SECONDS = 4
MAX_KEYS = 10
_KID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_B64URL = re.compile(r"[A-Za-z0-9_-]+\Z")
_PRIVATE_JWK_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})


class PreflightError(ValueError):
    """Fixed-code failure; never includes response data or exception details."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("invalid_json_constant")


def _parse_origin(origin: str) -> tuple[str, int]:
    if type(origin) is not str or len(origin) > 128:
        raise PreflightError("invalid_local_origin")
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        raise PreflightError("invalid_local_origin") from None
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or port is None or not 1 <= port <= 65535):
        raise PreflightError("invalid_local_origin")
    canonical = f"http://127.0.0.1:{port}"
    if origin not in (canonical, canonical + "/"):
        raise PreflightError("invalid_local_origin")
    return canonical, port


def _decode_base64url_integer(value: object, *, maximum_chars: int) -> int:
    if (type(value) is not str or not 1 <= len(value) <= maximum_chars
            or not _B64URL.fullmatch(value)):
        raise PreflightError("invalid_public_rsa_key")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error):
        raise PreflightError("invalid_public_rsa_key") from None
    if not raw or base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value:
        raise PreflightError("invalid_public_rsa_key")
    return int.from_bytes(raw, "big")


def _signing_key_count(jwks: object) -> int:
    if type(jwks) is not dict or type(jwks.get("keys")) is not list:
        raise PreflightError("invalid_jwks_document")
    keys = jwks["keys"]
    if not 1 <= len(keys) <= MAX_KEYS:
        raise PreflightError("invalid_jwks_document")

    kids: set[str] = set()
    signing_keys = 0
    for key in keys:
        if type(key) is not dict:
            raise PreflightError("invalid_jwks_document")
        if _PRIVATE_JWK_FIELDS.intersection(key):
            raise PreflightError("private_jwk_material_rejected")
        # Ignore unrelated public encryption keys, but fail closed on any key
        # that advertises itself as an RS256 or signing key.
        if key.get("use") != "sig" and key.get("alg") != "RS256":
            continue
        kid = key.get("kid")
        if (key.get("kty") != "RSA" or key.get("use") != "sig"
                or key.get("alg") != "RS256" or type(kid) is not str
                or not _KID.fullmatch(kid) or kid in kids):
            raise PreflightError("invalid_public_rsa_key")
        if "key_ops" in key and key["key_ops"] != ["verify"]:
            raise PreflightError("invalid_public_rsa_key")
        modulus = _decode_base64url_integer(key.get("n"), maximum_chars=2048)
        exponent = _decode_base64url_integer(key.get("e"), maximum_chars=16)
        modulus_bits = modulus.bit_length()
        if (not 2048 <= modulus_bits <= 8192 or exponent < 3
                or exponent % 2 == 0):
            raise PreflightError("invalid_public_rsa_key")
        kids.add(kid)
        signing_keys += 1
    if signing_keys == 0:
        raise PreflightError("no_compatible_public_signing_key")
    return signing_keys


def _fetch_json(port: int, path: str, limit: int) -> object:
    connection = http.client.HTTPConnection(
        "127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        # HTTPConnection does not follow redirects and bypasses proxy settings.
        connection.request("GET", path, headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Connection": "close",
        })
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise PreflightError("redirect_rejected")
        if response.status != 200:
            raise PreflightError("local_endpoint_http_error")
        headers = response.getheaders()
        if (len(headers) > HEADER_COUNT_LIMIT
                or sum(len(name) + len(value) for name, value in headers)
                > HEADER_BYTES_LIMIT):
            raise PreflightError("response_headers_too_large")
        media_type = response.getheader("Content-Type", "")
        if media_type.split(";", 1)[0].strip().lower() != "application/json":
            raise PreflightError("invalid_response_content_type")
        content_encoding = response.getheader("Content-Encoding", "identity")
        if content_encoding.lower() not in ("", "identity"):
            raise PreflightError("unsupported_response_encoding")
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            if not content_length.isdecimal():
                raise PreflightError("invalid_response_length")
            if int(content_length) > limit:
                raise PreflightError("response_body_too_large")
        try:
            body = response.read(limit + 1)
        except (OSError, http.client.HTTPException):
            raise PreflightError("local_http_request_failed") from None
        if len(body) > limit:
            raise PreflightError("response_body_too_large")
    except PreflightError:
        raise
    except (OSError, http.client.HTTPException, ValueError):
        raise PreflightError("local_http_request_failed") from None
    finally:
        connection.close()

    try:
        document = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise PreflightError("invalid_json_response") from None
    if type(document) is not dict:
        raise PreflightError("invalid_json_response")
    return document


def run_preflight(origin: str = LOCAL_ORIGIN) -> dict[str, object]:
    """Check only the fixed realm endpoints on an exact IPv4 loopback origin."""
    canonical_origin, port = _parse_origin(origin)
    discovery = _fetch_json(port, DISCOVERY_PATH, DISCOVERY_LIMIT)
    expected_issuer = f"{canonical_origin}/realms/{REALM}"
    expected_jwks_uri = f"{expected_issuer}/protocol/openid-connect/certs"
    if discovery.get("issuer") != expected_issuer:
        raise PreflightError("issuer_mismatch")
    if discovery.get("jwks_uri") != expected_jwks_uri:
        raise PreflightError("jwks_uri_mismatch")

    jwks = _fetch_json(port, JWKS_PATH, JWKS_LIMIT)
    key_count = _signing_key_count(jwks)
    return {
        "result": "LOCAL_OIDC_PREFLIGHT_PASS",
        "origin": canonical_origin,
        "realm": REALM,
        "discovery": "PASS",
        "issuer_match": "PASS",
        "jwks_uri_match": "PASS",
        "public_rs256_signing_keys": key_count,
        "https_only_issuer_policy": "NOT_COMPATIBLE_WITH_LOCAL_HTTP",
        "readiness_claim": "NOT_ESTABLISHED",
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--help"]:
        print("Usage: python3 scripts/p01_keycloak_local_preflight.py")
        print("Checks only the local http://127.0.0.1:8080 devobs-local realm.")
        return 0
    if args:
        print("PREFLIGHT_BLOCKED: unsupported_arguments", file=sys.stderr)
        return 2
    try:
        result = run_preflight()
    except PreflightError as exc:
        result = {
            "result": "LOCAL_OIDC_PREFLIGHT_BLOCKED",
            "error": exc.code,
            "readiness_claim": "NOT_ESTABLISHED",
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

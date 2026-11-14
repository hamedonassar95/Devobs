#!/usr/bin/env python3
"""Certificate-verified, loopback-only Keycloak discovery/JWKS preflight.

This tool never reads TLS private keys or obtains OAuth tokens. A successful
result establishes only HTTPS discovery and public-JWKS compatibility; it is
not a signed-token, database-readiness, staging, or production acceptance.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

from devobs_intelligence.oidc_metadata import (
    IssuerConfigurationError,
    trusted_oidc_verifier,
)


HOST = "localhost"
PORT = 443
REALM = "devobs-local"
ISSUER = f"https://{HOST}/realms/{REALM}"
DISCOVERY_PATH = f"/realms/{REALM}/.well-known/openid-configuration"
JWKS_PATH = f"/realms/{REALM}/protocol/openid-connect/certs"
JWKS_URI = f"https://{HOST}{JWKS_PATH}"
DISCOVERY_LIMIT = 16 * 1024
JWKS_LIMIT = 64 * 1024
HEADER_COUNT_LIMIT = 64
HEADER_BYTES_LIMIT = 16 * 1024
REQUEST_TIMEOUT_SECONDS = 4
MAX_KEYS = 10
NOT_TESTED_STATUS = "NOT_TESTED"


class PreflightError(ValueError):
    """Fixed, sanitized failure category."""

    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("invalid_json_constant")


def _build_tls_context(ca_certificate: str | Path) -> ssl.SSLContext:
    """Trust only the operator-supplied public CA; never accepts a key path."""
    try:
        ca_path = Path(ca_certificate)
        if not ca_path.is_file():
            raise PreflightError("public_ca_unavailable")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(cafile=str(ca_path))
    except PreflightError:
        raise
    except (OSError, ssl.SSLError, TypeError, ValueError):
        raise PreflightError("public_ca_invalid") from None
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise PreflightError("tls_verification_not_enabled")
    return context


def _resolve_loopback_addresses() -> tuple[tuple[int, int, int, tuple], ...]:
    """Resolve only the hard-coded localhost endpoint and reject non-loopback."""
    try:
        infos = socket.getaddrinfo(HOST, PORT, type=socket.SOCK_STREAM)
    except (OSError, socket.gaierror):
        raise PreflightError("loopback_resolution_failed") from None
    if not infos:
        raise PreflightError("loopback_resolution_failed")

    addresses: list[tuple[int, int, int, tuple]] = []
    seen: set[tuple] = set()
    for family, socktype, protocol, _canonical_name, sockaddr in infos:
        try:
            ip_text = sockaddr[0].split("%", 1)[0]
            address = ipaddress.ip_address(ip_text)
        except (IndexError, ValueError, TypeError):
            raise PreflightError("loopback_resolution_failed") from None
        if not address.is_loopback or len(sockaddr) < 2 or sockaddr[1] != PORT:
            raise PreflightError("non_loopback_address_rejected")
        candidate = (family, socktype, protocol, sockaddr)
        if candidate not in seen:
            seen.add(candidate)
            addresses.append(candidate)
    if not addresses:
        raise PreflightError("loopback_resolution_failed")
    return tuple(addresses)


class _PinnedLoopbackHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection pinned to prevalidated loopback addresses."""

    def __init__(self, addresses: tuple[tuple[int, int, int, tuple], ...],
                 context: ssl.SSLContext):
        super().__init__(HOST, PORT, timeout=REQUEST_TIMEOUT_SECONDS, context=context)
        self._pinned_addresses = addresses
        self._tls_context = context

    def connect(self) -> None:
        for family, socktype, protocol, sockaddr in self._pinned_addresses:
            raw_socket = socket.socket(family, socktype, protocol)
            raw_socket.settimeout(self.timeout)
            try:
                raw_socket.connect(sockaddr)
                self.sock = self._tls_context.wrap_socket(
                    raw_socket, server_hostname=HOST)
                return
            except ssl.SSLCertVerificationError:
                raw_socket.close()
                raise PreflightError("tls_certificate_rejected") from None
            except ssl.SSLError:
                raw_socket.close()
                raise PreflightError("tls_handshake_failed") from None
            except OSError:
                raw_socket.close()
        raise PreflightError("loopback_connection_failed")


def _response_body(response: http.client.HTTPResponse, limit: int) -> bytes:
    if 300 <= response.status < 400:
        raise PreflightError("redirect_rejected")
    if response.status != 200:
        raise PreflightError("endpoint_http_error")
    try:
        headers = response.getheaders()
        if (len(headers) > HEADER_COUNT_LIMIT
                or sum(len(name) + len(value) for name, value in headers)
                > HEADER_BYTES_LIMIT):
            raise PreflightError("response_headers_too_large")
        media_type = response.getheader("Content-Type", "")
        if media_type.split(";", 1)[0].strip().lower() != "application/json":
            raise PreflightError("invalid_response_content_type")
        encoding = response.getheader("Content-Encoding", "identity")
        if encoding.lower() not in ("", "identity"):
            raise PreflightError("unsupported_response_encoding")
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            if not content_length.isdecimal():
                raise PreflightError("invalid_response_length")
            if int(content_length) > limit:
                raise PreflightError("response_body_too_large")
        body = response.read(limit + 1)
    except PreflightError:
        raise
    except (OSError, http.client.HTTPException, AttributeError, TypeError):
        raise PreflightError("response_read_failed") from None
    if len(body) > limit:
        raise PreflightError("response_body_too_large")
    return body


def _decode_document(body: bytes) -> dict[str, object]:
    try:
        document = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise PreflightError("invalid_json_response") from None
    if type(document) is not dict:
        raise PreflightError("invalid_json_response")
    return document


def _fetch_json(context: ssl.SSLContext,
                addresses: tuple[tuple[int, int, int, tuple], ...],
                path: str, limit: int) -> dict[str, object]:
    if path not in (DISCOVERY_PATH, JWKS_PATH):
        raise PreflightError("unexpected_local_path")
    connection = _PinnedLoopbackHTTPSConnection(addresses, context)
    try:
        connection.request("GET", path, headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Connection": "close",
        })
        response = connection.getresponse()
        body = _response_body(response, limit)
    except PreflightError:
        raise
    except ssl.SSLError:
        raise PreflightError("tls_handshake_failed") from None
    except (OSError, http.client.HTTPException, ValueError):
        raise PreflightError("local_https_request_failed") from None
    finally:
        connection.close()
    return _decode_document(body)


def _validate_jwks_uri(discovery: object) -> None:
    if type(discovery) is not dict:
        raise PreflightError("invalid_discovery_document")
    if discovery.get("issuer") != ISSUER:
        raise PreflightError("issuer_mismatch")

    jwks_uri = discovery.get("jwks_uri")
    if type(jwks_uri) is not str or len(jwks_uri) > 512 or not jwks_uri.isascii():
        raise PreflightError("invalid_jwks_uri")
    try:
        parsed = urlsplit(jwks_uri)
        port = parsed.port
    except ValueError:
        raise PreflightError("invalid_jwks_uri") from None
    if (parsed.scheme != "https" or parsed.hostname != HOST or port not in (None, 443)
            or parsed.username is not None or parsed.password is not None
            or parsed.path != JWKS_PATH or parsed.query or parsed.fragment
            or jwks_uri != JWKS_URI):
        raise PreflightError("jwks_uri_mismatch")


def _validate_documents(discovery: object, jwks: object) -> int:
    _validate_jwks_uri(discovery)
    if type(jwks) is not dict or type(jwks.get("keys")) is not list:
        raise PreflightError("invalid_jwks_document")
    keys = jwks["keys"]
    if not 1 <= len(keys) <= MAX_KEYS:
        raise PreflightError("no_compatible_public_signing_key")
    try:
        # Reuse the production trust-bound metadata/JWKS contract. The fetched
        # documents have already passed bounded HTTPS transport validation; no
        # token is created or verified by this preflight.
        trusted_oidc_verifier(
            ISSUER, "devobs-api", "devobs-local-preflight", discovery, jwks)
    except (IssuerConfigurationError, TypeError, ValueError):
        raise PreflightError("incompatible_public_jwks") from None
    return len(keys)


def run_preflight(ca_certificate: str | Path, *, fetch_json=None,
                  context_factory=_build_tls_context) -> dict[str, object]:
    """Perform bounded local HTTPS discovery and public-JWKS validation."""
    context = context_factory(ca_certificate)
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise PreflightError("tls_verification_not_enabled")
    if fetch_json is None:
        addresses = _resolve_loopback_addresses()

        def fetch_json(path: str, limit: int) -> dict[str, object]:
            return _fetch_json(context, addresses, path, limit)

    discovery = fetch_json(DISCOVERY_PATH, DISCOVERY_LIMIT)
    # Validate issuer and URI before contacting JWKS. This keeps requests on
    # the one expected local origin even if discovery is malicious.
    _validate_jwks_uri(discovery)
    jwks = fetch_json(JWKS_PATH, JWKS_LIMIT)
    key_count = _validate_documents(discovery, jwks)
    return {
        "result": "LOCAL_HTTPS_OIDC_PREFLIGHT_PASS",
        "origin": f"https://{HOST}",
        "realm": REALM,
        "certificate_verification": "PASS",
        "discovery_http_status": 200,
        "issuer_match": "PASS",
        "jwks_uri_match": "PASS",
        "public_rs256_signing_keys": key_count,
        "signed_token_acceptance": NOT_TESTED_STATUS,
        "readiness_claim": "NOT_ESTABLISHED",
    }


def _json_output(result: dict[str, object]) -> None:
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--help"]:
        print("Usage: python3 scripts/p01_keycloak_https_preflight.py --ca-cert PUBLIC_CA_PEM")
        print("Checks HTTPS discovery and public JWKS only at https://localhost (TCP 443).")
        return 0
    if len(args) != 2 or args[0] != "--ca-cert":
        _json_output({
            "result": "LOCAL_HTTPS_OIDC_PREFLIGHT_BLOCKED",
            "failure_category": "public_ca_required_or_invalid_arguments",
            "readiness_claim": "NOT_ESTABLISHED",
        })
        return 2
    try:
        result = run_preflight(args[1])
    except PreflightError as exc:
        _json_output({
            "result": "LOCAL_HTTPS_OIDC_PREFLIGHT_BLOCKED",
            "failure_category": exc.category,
            "readiness_claim": "NOT_ESTABLISHED",
        })
        return 2
    _json_output(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

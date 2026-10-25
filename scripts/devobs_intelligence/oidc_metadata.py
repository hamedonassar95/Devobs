"""Trust-bound OIDC metadata validation; no network or automatic key discovery.

Only operator-verified, securely fetched issuer metadata/JWKS may be passed here.
All incoming responses/LLM content are untrusted unless verified out of band.
"""
from __future__ import annotations

import json
from urllib.parse import urlsplit

from .oidc_tokens import AccessTokenVerifier


class IssuerConfigurationError(ValueError):
    """Uniform, non-sensitive provider configuration failure."""


def _https_origin(url: object) -> tuple[str, str, int] | None:
    if type(url) is not str or len(url) > 512 or not url.isascii():
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.query or parsed.fragment or parsed.hostname.endswith("."):
            return None
        if parsed.port not in (None, 443):
            return None
        return ("https", parsed.hostname.lower(), 443)
    except ValueError:
        return None


def trusted_oidc_verifier(issuer: str, audience: str, client_id: str,
                          metadata: dict, jwks: dict) -> AccessTokenVerifier:
    """Construct a verifier from *already authenticated* OIDC documents.

    This does not retrieve metadata, validate TLS certificates, register clients,
    manage provider revocations or rotate keys automatically.
    """
    if (_https_origin(issuer) is None
            or type(metadata) is not dict or len(metadata) > 100
            or metadata.get("issuer") != issuer
            or _https_origin(metadata.get("jwks_uri")) != _https_origin(issuer)
            or type(metadata.get("jwks_uri")) is not str
            or not urlsplit(metadata["jwks_uri"]).path.startswith("/")
            or type(jwks) is not dict):
        raise IssuerConfigurationError("invalid_oidc_metadata")
    try:
        if len(json.dumps(metadata, allow_nan=False)) > 16384 or len(
                json.dumps(jwks, allow_nan=False)) > 65536:
            raise IssuerConfigurationError("invalid_oidc_metadata")
        return AccessTokenVerifier(issuer, audience, client_id, jwks)
    except (ValueError, TypeError, OverflowError):
        raise IssuerConfigurationError("invalid_oidc_metadata") from None

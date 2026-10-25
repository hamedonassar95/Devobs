"""Validate OAuth JWT access tokens with an operator-pinned public RSA JWKS.

An ID Token is NOT an API access token (RFC 9068); no remote JWKS URL,
credentials, private keys, or network activity in this module.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import jwt

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class AuthenticationError(ValueError):
    """Fixed error: never echo credentials or identity data."""


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    scopes: frozenset[str]


class AccessTokenVerifier:
    def __init__(self, issuer: str, audience: str, client_id: str, jwks: dict):
        if not isinstance(issuer, str) or len(issuer) > 512:
            raise ValueError("invalid_auth_config")
        parsed = urlparse(issuer)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ValueError("invalid_auth_config")
        if any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in (audience, client_id)):
            raise ValueError("invalid_auth_config")
        if type(jwks) is not dict or set(jwks) != {"keys"} or type(jwks["keys"]) is not list or not 1 <= len(jwks["keys"]) <= 10:
            raise ValueError("invalid_auth_config")
        keys = {}
        for candidate in jwks["keys"]:
            if (type(candidate) is not dict or candidate.get("kty") != "RSA"
                    or candidate.get("alg") != "RS256" or candidate.get("use") != "sig"
                    or type(candidate.get("kid")) is not str or not _ID.fullmatch(candidate["kid"])
                    or type(candidate.get("n")) is not str or type(candidate.get("e")) is not str
                    or candidate["kid"] in keys):
                raise ValueError("invalid_auth_config")
            try:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(candidate))
                if public_key.key_size < 2048:
                    raise ValueError("weak_rsa_key")
                keys[candidate["kid"]] = public_key
            except (jwt.PyJWTError, ValueError, TypeError, KeyError):
                raise ValueError("invalid_auth_config") from None
        self._keys = keys
        self._issuer = issuer
        self._audience = audience
        self._client = client_id

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if (type(token) is not str or len(token) > 8192 or len(token) < 40
                or token.count(".") != 2 or not token.isascii()):
            raise AuthenticationError("invalid_token")
        try:
            header = jwt.get_unverified_header(token)
            if (header.get("alg") != "RS256" or header.get("typ") not in ("at+jwt", "application/at+jwt")
                    or type(header.get("kid")) is not str):
                raise AuthenticationError("invalid_token")
            trusted_key = self._keys.get(header["kid"])
            if trusted_key is None:
                raise AuthenticationError("invalid_token")
            claims = jwt.decode(
                token, trusted_key, algorithms=["RS256"], issuer=self._issuer,
                audience=self._audience,
                options={"require": ["iss", "aud", "sub", "exp", "iat", "jti", "client_id"],
                         "strict_aud": True, "verify_signature": True},
                leeway=0,
            )
            subject = claims.get("sub")
            if (type(subject) is not str or not _ID.fullmatch(subject)
                    or type(claims.get("client_id")) is not str or claims["client_id"] != self._client
                    or type(claims.get("iat")) is not int or type(claims.get("exp")) is not int
                    or claims["exp"] <= claims["iat"] or claims["exp"] - claims["iat"] > 900
                    or type(claims.get("jti")) is not str or not 1 <= len(claims["jti"]) <= 128):
                raise AuthenticationError("invalid_token")
            scope = claims.get("scope")
            if type(scope) is not str or len(scope) > 512 or "devobs.read" not in scope.split():
                raise AuthenticationError("invalid_token")
            return AuthenticatedPrincipal(subject, frozenset(scope.split()))
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, OverflowError):
            raise AuthenticationError("invalid_token") from None

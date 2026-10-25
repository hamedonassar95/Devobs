"""Operator-verified OIDC key-set rotation; no network fetch or key auto-trust.

Signing-key changes require authenticated provider metadata/JWKS supplied by a
trusted deployment operator, never JWT headers, logs or model output. Updates
are swapped atomically for this process only (not distributed across workers).
"""
from __future__ import annotations

from threading import Lock

from .oidc_metadata import trusted_oidc_verifier


class RotationRejected(ValueError):
    """Fixed non-sensitive update error."""


class RotatingOIDCVerifier:
    """Validate JWT access tokens with an explicitly installed trusted key set.

    A long-lived server needs an independently authenticated rotation delivery
    mechanism. This object is only the validation + local atomic swap primitive.
    """

    def __init__(self, issuer: str, audience: str, client_id: str,
                 metadata: dict, jwks: dict, *, revision: int = 1):
        if type(revision) is not int or not 1 <= revision <= 2**31 - 1:
            raise RotationRejected("invalid_key_revision")
        self._issuer = issuer
        self._audience = audience
        self._client_id = client_id
        self._current = trusted_oidc_verifier(
            issuer, audience, client_id, metadata, jwks)
        self._revision = revision
        self._lock = Lock()

    def verify(self, token: str):
        # Acquiring a copy avoids modifying an in-flight verification while
        # preserving atomic key-set replacement for subsequent requests.
        with self._lock:
            verifier = self._current
        return verifier.verify(token)

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def install_operator_verified(self, metadata: dict, jwks: dict, *,
                                  revision: int) -> None:
        """Install preauthenticated public JWKS, fail closed on stale revisions.

        Caller MUST authenticate origin, TLS, authorized operator and revision
        before invoking. No network, update endpoint or provider credential
        management exists here. Do not expose this method over public HTTP.
        """
        if type(revision) is not int or not 1 <= revision <= 2**31 - 1:
            raise RotationRejected("invalid_key_revision")
        candidate = trusted_oidc_verifier(
            self._issuer, self._audience, self._client_id, metadata, jwks)
        with self._lock:
            if revision <= self._revision:
                raise RotationRejected("stale_key_revision")
            self._current = candidate
            self._revision = revision

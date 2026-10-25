"""Render staging WSGI entrypoint; deny startup on missing trust configuration.

This module NEVER fetches OIDC metadata, migrates the database, or provisions
cloud resources. Operators must supply authenticated metadata/JWKS and a
restricted, TLS-verified PostgreSQL connection string through a secret store.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Callable

from psycopg import Error as PsycopgError
from psycopg.conninfo import conninfo_to_dict

from .api_app import make_app
from .oidc_rotation import RotatingOIDCVerifier
from .postgres_store import PostgresTenantStore


class StagingConfigurationError(ValueError):
    """Non-sensitive startup error with a fixed public code."""


def _decode_document(settings: Mapping[str, str], name: str, limit: int) -> dict:
    value = settings.get(name)
    if type(value) is not str or not 1 <= len(value) <= limit or not value.isascii():
        raise StagingConfigurationError("invalid_staging_config")
    try:
        obj = json.loads(value)
    except (ValueError, TypeError):
        raise StagingConfigurationError("invalid_staging_config") from None
    if type(obj) is not dict:
        raise StagingConfigurationError("invalid_staging_config")
    return obj


def _database_dsn(settings: Mapping[str, str]) -> str:
    dsn = settings.get("DEVOBS_PG_DSN")
    if type(dsn) is not str or not 1 <= len(dsn) <= 4096:
        raise StagingConfigurationError("invalid_staging_config")
    try:
        cfg = conninfo_to_dict(dsn)
    except (ValueError, TypeError, PsycopgError):
        raise StagingConfigurationError("invalid_staging_config") from None
    # Supabase supports verify-full with a trusted CA file installed by operator.
    # Runtime identity must be a dedicated non-owner, never the postgres admin.
    role = cfg.get("user", "")
    if (cfg.get("sslmode") != "verify-full"
            or not cfg.get("sslrootcert") or not cfg.get("host")
            or not cfg.get("dbname") or not cfg.get("password")
            or not role or role == "postgres" or role.startswith("postgres.")):
        raise StagingConfigurationError("invalid_staging_config")
    return dsn


def build_app(settings: Mapping[str, str]) -> Callable:
    """Construct scoped read API; no network/database call until a request arrives."""
    try:
        issuer = settings["DEVOBS_OIDC_ISSUER"]
        audience = settings["DEVOBS_OIDC_AUDIENCE"]
        client_id = settings["DEVOBS_OIDC_CLIENT_ID"]
        metadata = _decode_document(settings, "DEVOBS_OIDC_METADATA_JSON", 16384)
        jwks = _decode_document(settings, "DEVOBS_OIDC_JWKS_JSON", 65536)
        verifier = RotatingOIDCVerifier(issuer, audience, client_id, metadata, jwks)
        store = PostgresTenantStore(_database_dsn(settings))
        api = make_app(verifier, store)
    except (KeyError, ValueError, TypeError):
        raise StagingConfigurationError("invalid_staging_config") from None

    def application(environ, start_response):
        path = environ.get("PATH_INFO")
        if path == "/healthz":
            if environ.get("REQUEST_METHOD") != "GET":
                start_response("405 Method Not Allowed", [("Allow", "GET"),
                                                           ("Content-Length", "0"),
                                                           ("Cache-Control", "no-store")])
            else:
                # Liveness only: not a proof of Postgres reachability/tenant safety.
                start_response("204 No Content", [("Cache-Control", "no-store"),
                                                   ("Content-Length", "0")])
            return [b""]
        if path == "/readyz":
            if environ.get("REQUEST_METHOD") != "GET":
                start_response("405 Method Not Allowed", [("Allow", "GET"),
                                                           ("Cache-Control", "no-store"),
                                                           ("Content-Length", "0")])
                return [b""]
            try:
                ready = store.probe_readiness() is True
            except Exception:
                ready = False
            # Do not leak DB configuration, SQL errors or identity information.
            start_response("204 No Content" if ready else "503 Service Unavailable",
                           [("Cache-Control", "no-store"),
                            ("X-Content-Type-Options", "nosniff"),
                            ("Content-Length", "0")])
            return [b""]
        return api(environ, start_response)

    return application


# Gunicorn loads this only in an explicitly configured staging service.
# Missing or unsafe credentials fail startup; no default demo/anonymous mode.
application = build_app(os.environ)

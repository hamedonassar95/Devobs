"""Render staging WSGI entrypoint; deny startup on missing trust configuration.

This module NEVER fetches OIDC metadata, migrates the database, or provisions
cloud resources. Operators must supply authenticated metadata/JWKS and a
restricted PostgreSQL connection through a secret store. The default database
mode requires TLS certificate verification; a separate explicit Render-internal
mode requires TLS encryption but cannot verify Render's self-signed peer cert.
"""
from __future__ import annotations

import atexit
import json
import os
from collections.abc import Mapping
from typing import Callable

from psycopg import Error as PsycopgError
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from .api_app import make_app, reject_request_body
from .gemini_error_diagnosis import GeminiErrorLogDiagnostician
from .local_model_error_diagnosis import LocalModelErrorLogDiagnostician
from .oidc_rotation import RotatingOIDCVerifier
from .openai_error_diagnosis import DEFAULT_MODEL, OpenAIErrorLogDiagnostician
from .otel_metrics import create_local_metrics
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
    # Runtime identity must be a dedicated non-owner, never the postgres admin.
    role = cfg.get("user", "")
    if (not cfg.get("host") or not cfg.get("dbname") or not cfg.get("password")
            or not role or role == "postgres" or role.startswith("postgres.")):
        raise StagingConfigurationError("invalid_staging_config")
    tls_mode = settings.get("DEVOBS_PG_TLS_MODE", "verify-full")
    if tls_mode == "verify-full":
        if cfg.get("sslmode") != "verify-full" or not cfg.get("sslrootcert"):
            raise StagingConfigurationError("invalid_staging_config")
        return dsn
    if tls_mode == "render-internal-require":
        # Render documents that its same-region internal Postgres connection
        # supports TLS with sslmode=require, but not peer-certificate
        # verification because its internal certificate is self-signed. This
        # weaker mode is permitted only for a Render web service and must be
        # selected explicitly in its Blueprint; all other environments retain
        # verify-full as the default.
        if settings.get("RENDER") != "true" or settings.get("RENDER_SERVICE_TYPE") != "web":
            raise StagingConfigurationError("invalid_staging_config")
        if cfg.get("sslmode") not in (None, "require"):
            raise StagingConfigurationError("invalid_staging_config")
        try:
            return make_conninfo(dsn, sslmode="require")
        except (ValueError, TypeError):
            raise StagingConfigurationError("invalid_staging_config") from None
    raise StagingConfigurationError("invalid_staging_config")


def build_app(settings: Mapping[str, str]) -> Callable:
    """Construct scoped API; model inference is disabled unless explicitly configured."""
    try:
        issuer = settings["DEVOBS_OIDC_ISSUER"]
        audience = settings["DEVOBS_OIDC_AUDIENCE"]
        client_id = settings["DEVOBS_OIDC_CLIENT_ID"]
        metadata = _decode_document(settings, "DEVOBS_OIDC_METADATA_JSON", 16384)
        jwks = _decode_document(settings, "DEVOBS_OIDC_JWKS_JSON", 65536)
        verifier = RotatingOIDCVerifier(issuer, audience, client_id, metadata, jwks)
        store = PostgresTenantStore(_database_dsn(settings))
        enabled = settings.get("DEVOBS_AI_DIAGNOSTICS_ENABLED", "false")
        if enabled not in {"true", "false"}:
            raise StagingConfigurationError("invalid_staging_config")
        diagnostician = None
        if enabled == "true":
            provider = settings.get("DEVOBS_AI_PROVIDER", "openai")
            if provider in {"ollama", "localai"}:
                if (settings.get("DEVOBS_AI_LOCAL_INFERENCE_APPROVED") != "true"
                        or settings.get("RENDER") == "true"):
                    raise StagingConfigurationError("invalid_staging_config")
                diagnostician = LocalModelErrorLogDiagnostician(
                    provider,
                    model=settings.get("DEVOBS_LOCAL_MODEL", ""),
                    api_key=settings.get("LOCALAI_API_KEY", "") if provider == "localai" else "",
                )
            elif provider == "openai":
                if settings.get("DEVOBS_AI_BUDGET_APPROVED") != "true":
                    raise StagingConfigurationError("invalid_staging_config")
                diagnostician = OpenAIErrorLogDiagnostician(
                    settings.get("OPENAI_API_KEY", ""),
                    model=settings.get("DEVOBS_AI_MODEL", DEFAULT_MODEL),
                )
            elif provider == "gemini":
                if (settings.get("DEVOBS_AI_BUDGET_APPROVED") != "true"
                        or settings.get("DEVOBS_AI_GEMINI_DATA_POLICY_APPROVED") != "true"):
                    raise StagingConfigurationError("invalid_staging_config")
                diagnostician = GeminiErrorLogDiagnostician(
                    settings.get("GEMINI_API_KEY", ""),
                    model=settings.get("DEVOBS_GEMINI_MODEL", ""),
                )
            else:
                raise StagingConfigurationError("invalid_staging_config")
        api = make_app(verifier, store, diagnostician=diagnostician)
        local_metrics = create_local_metrics(settings)
    except (KeyError, ValueError, TypeError):
        raise StagingConfigurationError("invalid_staging_config") from None

    def application(environ, start_response):
        path = environ.get("PATH_INFO")
        if path == "/healthz":
            rejected = reject_request_body(environ, start_response)
            if rejected is not None:
                return rejected
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
            rejected = reject_request_body(environ, start_response)
            if rejected is not None:
                return rejected
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

    if local_metrics is not None:
        atexit.register(local_metrics.shutdown)
        application = local_metrics.instrument(application)

    return application


# Gunicorn loads this only in an explicitly configured staging service.
# Missing or unsafe credentials fail startup; no default demo/anonymous mode.
application = build_app(os.environ)

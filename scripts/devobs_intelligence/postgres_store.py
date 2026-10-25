"""PostgreSQL tenant-scoped *read-only* adapter for DevObs's existing WSGI API.

Trusted application identity is passed separately; the DB has NO bearer-token
parser. A new connection and transaction are used for every read. No user SQL.
"""
from __future__ import annotations

import re

import psycopg

from .tenant_scope import AccessDenied

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class StorageUnavailable(RuntimeError):
    """Safe fixed code for unexpected storage/security failures."""


class PostgresTenantStore:
    def __init__(self, dsn: str):
        if type(dsn) is not str or not dsn or len(dsn) > 4096:
            raise ValueError("invalid_database_config")
        self._dsn = dsn

    def read_status(self, subject: str, tenant: str, project: str) -> dict[str, str]:
        if any(type(v) is not str or _ID.fullmatch(v) is None
               for v in (subject, tenant, project)):
            raise AccessDenied("access_denied")
        try:
            # autocommit=True prevents nested long-lived implicit transactions.
            # conn.transaction() scopes both identity variables to ONE request.
            with psycopg.connect(self._dsn, autocommit=True, connect_timeout=5) as conn:
                with conn.transaction():
                    conn.execute("SET TRANSACTION READ ONLY")
                    role = conn.execute(
                        """SELECT rolsuper, rolbypassrls,
                                  pg_has_role(current_user, 'devobs_ai_reader', 'USAGE')
                             FROM pg_roles WHERE rolname = current_user"""
                    ).fetchone()
                    if role is None or role[0] or role[1] or not role[2]:
                        raise StorageUnavailable("unsafe_database_role")
                    conn.execute(
                        """SELECT set_config('devobs_ai.tenant_id', %s, true),
                                  set_config('devobs_ai.subject_id', %s, true)""",
                        (tenant, subject),
                    )
                    row = conn.execute(
                        """SELECT ci_state, source_sha
                             FROM devobs_ai.project_ci
                            WHERE tenant_id = %s AND project_id = %s""",
                        (tenant, project),
                    ).fetchone()
            if row is None:
                raise AccessDenied("access_denied")
            return {"ci_state": row[0], "source_sha": row[1]}
        except (AccessDenied, StorageUnavailable):
            raise
        except (psycopg.Error, OSError, UnicodeError):
            raise StorageUnavailable("storage_unavailable") from None

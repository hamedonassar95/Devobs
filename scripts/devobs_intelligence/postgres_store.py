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

    def probe_readiness(self) -> bool:
        """Check a live DB connection, non-bypass reader role, and forced RLS.

        Uses only system catalogs, a short read-only transaction and no tenant
        records. Never treat a successful TCP connection as proof of safety.
        """
        try:
            with psycopg.connect(self._dsn, autocommit=True, connect_timeout=2) as conn:
                with conn.transaction():
                    conn.execute("SET TRANSACTION READ ONLY")
                    conn.execute("SET LOCAL statement_timeout = '1500ms'")
                    role = conn.execute(
                        """SELECT rolsuper, rolbypassrls,
                                  pg_has_role(current_user, 'devobs_ai_reader', 'USAGE')
                             FROM pg_roles WHERE rolname = current_user"""
                    ).fetchone()
                    if role != (False, False, True):
                        raise StorageUnavailable("unsafe_database_role")
                    tables = conn.execute(
                        """SELECT COUNT(*),
                                  COALESCE(BOOL_AND(
                                      c.relrowsecurity AND c.relforcerowsecurity
                                      AND row_security_active(c.oid)
                                      AND c.relowner <> current_user::regrole
                                      AND has_table_privilege(current_user, c.oid, 'SELECT')
                                      AND NOT has_table_privilege(
                                          current_user, c.oid,
                                          'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                                  ), FALSE)
                             FROM pg_class AS c
                             JOIN pg_namespace AS n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'devobs_ai'
                              AND c.relname IN ('project_ci', 'memberships')
                              AND c.relkind = 'r'"""
                    ).fetchone()
                    if tables != (2, True):
                        raise StorageUnavailable("unsafe_database_schema")
                    # PostgreSQL permissive SELECT policies are OR-combined.
                    # RLS enabled+forced is insufficient when an extra policy
                    # grants all rows. Require the reviewed policy inventory.
                    policies = conn.execute(
                        """SELECT tablename::text, policyname::text,
                                  permissive, cmd, roles
                             FROM pg_policies
                            WHERE schemaname = 'devobs_ai'
                              AND tablename IN ('project_ci', 'memberships')"""
                    ).fetchall()
                    found = {
                        (table, name, mode, cmd, tuple(roles or []))
                        for table, name, mode, cmd, roles in policies
                    }
                    expected = {
                        ("memberships", "devobs_membership_self", "PERMISSIVE",
                         "SELECT", ("devobs_ai_reader",)),
                        ("project_ci", "devobs_project_member_read", "PERMISSIVE",
                         "SELECT", ("devobs_ai_reader",)),
                    }
                    if len(policies) != len(expected) or found != expected:
                        raise StorageUnavailable("unsafe_database_schema")
            return True
        except StorageUnavailable:
            raise
        except (psycopg.Error, OSError, UnicodeError):
            raise StorageUnavailable("storage_unavailable") from None

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

"""PostgreSQL tenant-scoped *read-only* adapter for DevObs's existing WSGI API.

Trusted application identity is passed separately; the DB has NO bearer-token
parser. A new connection and transaction are used for every read. No user SQL.
"""
from __future__ import annotations

import re

import psycopg

from .tenant_scope import AccessDenied

# Reviewed PostgreSQL 17 policy-expression contract, captured from the clean
# deploy/postgres/001_tenant_rls.sql on disposable PG 17.11 in CI.
# Comparison intentionally fails closed on major-version / deparser drift.
# Never take the expected policy body from the same live database.
_PG17_POLICY_QUALS = {
    ("memberships", "devobs_membership_self"): (
        "((tenant_id = NULLIF(current_setting('devobs_ai.tenant_id'::text, true), "
        "''::text)) AND (subject_id = NULLIF(current_setting("
        "'devobs_ai.subject_id'::text, true), ''::text)))"
    ),
    ("project_ci", "devobs_project_member_read"): (
        "((tenant_id = NULLIF(current_setting('devobs_ai.tenant_id'::text, true), "
        "''::text)) AND (EXISTS ( SELECT 1\n"
        "   FROM devobs_ai.memberships m\n"
        "  WHERE ((m.tenant_id = project_ci.tenant_id) "
        "AND (m.project_id = project_ci.project_id) "
        "AND (m.subject_id = NULLIF(current_setting("
        "'devobs_ai.subject_id'::text, true), ''::text))))))"
    ),
}

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
                    # PostgreSQL deparser output is versioned: unknown major
                    # versions must be separately reviewed instead of trusted.
                    version = conn.execute("SHOW server_version_num").fetchone()
                    if (version is None or not version[0].isdigit()
                            or not 170000 <= int(version[0]) < 180000):
                        raise StorageUnavailable("unsafe_database_schema")
                    policies = conn.execute(
                        """SELECT tablename::text, policyname::text,
                                  permissive, cmd, roles, qual, with_check
                             FROM pg_policies
                            WHERE schemaname = 'devobs_ai'
                              AND tablename IN ('project_ci', 'memberships')"""
                    ).fetchall()
                    # Compare full approved predicates, not just policy names:
                    # PostgreSQL OR-combines permissive policies, and ALTER
                    # POLICY may widen a predicate without changing its name.
                    observed = {
                        (table, name): (mode, cmd, tuple(roles or []), qual, check)
                        for table, name, mode, cmd, roles, qual, check in policies
                    }
                    expected = {
                        identity: ("PERMISSIVE", "SELECT",
                                   ("devobs_ai_reader",), qual, None)
                        for identity, qual in _PG17_POLICY_QUALS.items()
                    }
                    if len(policies) != len(expected) or observed != expected:
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

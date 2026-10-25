"""Offline tenant-scoped SQLite read boundary; not a production database."""
import re
import sqlite3

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")


class TenantDenied(ValueError):
    """Uniform access denial."""


def _valid(value):
    return type(value) is str and _ID.fullmatch(value) is not None


class OfflineTenantStore:
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE records (
                tenant TEXT NOT NULL, project TEXT NOT NULL,
                sha TEXT NOT NULL, ci_state TEXT NOT NULL,
                PRIMARY KEY (tenant,project));
            CREATE TABLE memberships (
                tenant TEXT NOT NULL, project TEXT NOT NULL,
                subject TEXT NOT NULL,
                PRIMARY KEY (tenant,project,subject),
                FOREIGN KEY (tenant,project) REFERENCES records(tenant,project));
        """)

    def add_project(self, tenant, project, sha, state):
        if (not _valid(tenant) or not _valid(project)
                or type(sha) is not str or _SHA.fullmatch(sha) is None
                or state not in {"success","failed","stale","pending","missing"}):
            raise ValueError("invalid_project")
        with self._conn:
            self._conn.execute("INSERT INTO records VALUES (?,?,?,?)",
                               (tenant,project,sha,state))

    def grant_read(self, tenant, project, subject):
        if not all(_valid(v) for v in (tenant,project,subject)):
            raise ValueError("invalid_membership")
        with self._conn:
            self._conn.execute("INSERT INTO memberships VALUES (?,?,?)",
                               (tenant,project,subject))

    def read_status(self, subject, tenant, project):
        if not all(_valid(v) for v in (subject,tenant,project)):
            raise TenantDenied("access_denied")
        row = self._conn.execute("""
            SELECT r.ci_state, r.sha FROM records AS r JOIN memberships AS m
            ON r.tenant=m.tenant AND r.project=m.project
            WHERE r.tenant=? AND r.project=? AND m.subject=?
        """, (tenant,project,subject)).fetchone()
        if row is None:
            raise TenantDenied("access_denied")
        return {"ci_state":row[0],"source_sha":row[1]}

    def close(self):
        self._conn.close()

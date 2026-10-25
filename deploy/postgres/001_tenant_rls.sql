-- DevObs read-only multi-tenant reference schema (PostgreSQL 17+).
-- Apply exactly once using a migration owner/admin; never using the runtime role.
-- No customer data or credentials. Production deployments require separate approval.
CREATE ROLE devobs_ai_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE SCHEMA devobs_ai;
REVOKE ALL ON SCHEMA devobs_ai FROM PUBLIC;

CREATE TABLE devobs_ai.project_ci (
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    project_id TEXT NOT NULL CHECK (project_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    source_sha TEXT NOT NULL CHECK (source_sha ~ '^([0-9a-f]{40}|[0-9a-f]{64})$'),
    ci_state TEXT NOT NULL CHECK (ci_state IN
        ('success','failed','pending','running','stale','missing','skipped','canceled','manual','scheduled')),
    PRIMARY KEY (tenant_id, project_id)
);

CREATE TABLE devobs_ai.memberships (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL CHECK (subject_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    PRIMARY KEY (tenant_id, project_id, subject_id),
    FOREIGN KEY (tenant_id, project_id)
        REFERENCES devobs_ai.project_ci(tenant_id, project_id)
        ON DELETE CASCADE
);

REVOKE ALL ON ALL TABLES IN SCHEMA devobs_ai FROM PUBLIC;
GRANT USAGE ON SCHEMA devobs_ai TO devobs_ai_reader;
GRANT SELECT ON devobs_ai.project_ci, devobs_ai.memberships TO devobs_ai_reader;

ALTER TABLE devobs_ai.project_ci ENABLE ROW LEVEL SECURITY;
ALTER TABLE devobs_ai.project_ci FORCE ROW LEVEL SECURITY;
ALTER TABLE devobs_ai.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE devobs_ai.memberships FORCE ROW LEVEL SECURITY;

-- Missing identity context = default deny. No UPDATE/INSERT/DELETE policy exists.
CREATE POLICY devobs_membership_self ON devobs_ai.memberships
    FOR SELECT TO devobs_ai_reader
    USING (
        tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '')
        AND subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')
    );

CREATE POLICY devobs_project_member_read ON devobs_ai.project_ci
    FOR SELECT TO devobs_ai_reader
    USING (
        tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '')
        AND EXISTS (
            SELECT 1 FROM devobs_ai.memberships AS m
             WHERE m.tenant_id = project_ci.tenant_id
               AND m.project_id = project_ci.project_id
               AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')
        )
    );

-- Runtime roles must never be table owners or have SUPERUSER/BYPASSRLS.
-- Direct DB access, untrusted arbitrary SQL and connection-string injection are forbidden.

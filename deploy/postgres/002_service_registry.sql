-- DevObs tenant/project/service registry (PostgreSQL 17+).
-- Apply once after 001_tenant_rls.sql, using a migration owner/admin only.
-- This reference migration is for an empty, separately approved schema; it
-- does not provision resources or authorize production use.
BEGIN;

CREATE TABLE devobs_ai.service_registry (
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    project_id TEXT NOT NULL CHECK (project_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    service_id TEXT NOT NULL CHECK (service_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    PRIMARY KEY (tenant_id, project_id, service_id),
    FOREIGN KEY (tenant_id, project_id)
        REFERENCES devobs_ai.project_ci(tenant_id, project_id)
        ON DELETE CASCADE
);

REVOKE ALL ON TABLE devobs_ai.service_registry FROM PUBLIC;
GRANT SELECT ON TABLE devobs_ai.service_registry TO devobs_ai_reader;

ALTER TABLE devobs_ai.service_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE devobs_ai.service_registry FORCE ROW LEVEL SECURITY;

CREATE POLICY devobs_service_member_read ON devobs_ai.service_registry
    FOR SELECT TO devobs_ai_reader
    USING (
        tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '')
        AND EXISTS (
            SELECT 1 FROM devobs_ai.memberships AS m
             WHERE m.tenant_id = service_registry.tenant_id
               AND m.project_id = service_registry.project_id
               AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')
        )
    );

COMMIT;

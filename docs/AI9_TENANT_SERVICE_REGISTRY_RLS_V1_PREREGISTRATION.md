# AI-9 Tenant Service Registry under PostgreSQL RLS — Preregistration v1

**Status:** preregistered design; implementation and database tests have not started.
**Recorded:** 2026-10-30 UTC.
**Base:** `main` at `c778fe4e7ff9f26e7cd2d7f4b9bba1623bc9de6f`.
**Policy version:** `ai9-tenant-service-registry-rls-v1`.

## Purpose

Add a read-only PostgreSQL authorization lookup that binds an authenticated subject to an explicitly registered service inside the same tenant and project. This closes the repository-level gap identified by `docs/AI9_AUTH_SERVICE_INTEGRATION_AUDIT.md`: the existing JavaScript confirmation adapter accepts a service authorization callback, but there is no trusted service registry or application call site.

This is an offline/CI data-boundary increment only. It does not create an AI-9 endpoint, connect the JavaScript adapter to Python, change detector behavior, score AI-9, authorize a deployment, or provision a database.

## Frozen implementation contract

1. Keep `deploy/postgres/001_tenant_rls.sql` immutable. Add a separate one-time migration, `deploy/postgres/002_service_registry.sql`, to be applied after migration 001 only to a fresh, separately approved schema.
2. Create `devobs_ai.service_registry` with non-null `tenant_id`, `project_id`, and `service_id`; validate each identifier with the existing `[A-Za-z0-9][A-Za-z0-9_-]{0,63}` format; use `(tenant_id, project_id, service_id)` as the primary key and a cascading composite foreign key to `project_ci(tenant_id, project_id)`. Equal service IDs in different tenants are allowed.
3. Grant the existing `devobs_ai_reader` role `SELECT` only on the new table. Enable and force RLS. Add exactly one permissive SELECT policy, `devobs_service_member_read`, requiring the transaction-local tenant setting and an RLS-visible membership matching tenant, project, and transaction-local subject. No write policy is added.
4. Add `PostgresTenantStore.authorize_service(subject, tenant, project, service_id) -> bool`. Validate all four identifiers before connecting. Use a short read-only transaction, the existing fixed lock/role/schema checks, transaction-local `set_config`, and a parameterized exact service tuple lookup. Return `True` only for the registered tuple visible to that subject; return `False` for an absent tuple or non-member. Invalid scope remains `access_denied`; database, role, or schema failures remain fixed `StorageUnavailable` codes. Never accept identity from SQL input, HTTP headers, or service metadata.
5. Extend the readiness/schema contract to cover all three RLS tables and the exact reviewed policy predicate. Lock all three tables before checking and querying. Unrecognized PostgreSQL major versions, role/grant drift, disabled or unforced RLS, extra policies, and changed policy bodies fail closed.
6. Apply the new migration and seed only synthetic fixtures in the disposable PostgreSQL 17 CI service. Tests must include the same project and service identifiers across two tenants; matching and mismatching subject/tenant/project/service cases; malformed identifiers; runtime write denial; RLS/readiness and policy/grant drift; and access-share locking for the new table.
7. Update `docs/POSTGRES_RLS_STAGING.md` and `STATE.md` to describe the added reference contract and its limits. Do not change P01 owner decisions or imply a live database exists.

## Frozen verification and reporting

- Focused database gate: `python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v`, on the disposable PostgreSQL 17 service in GitHub Actions.
- Repository gate: the existing required CI/`validate` workflow and CodeQL on the exact PR head; inspect the exact run before merge.
- If a safe local PostgreSQL 17 fixture is unavailable, do not substitute mocks for the database integration gate; report local unavailability and rely on the real CI service before merging.
- Record exact PR head SHA and the final check runs. Keep this increment separate from future API/Node protocol work.

## Explicit non-goals and unchanged gates

- No AI-9 evaluation, new seeds, production data, or performance claim is part of this work. Existing AI-9 remains **FAIL**.
- No new API route, network listener, Node/Python protocol, provider identity, background ingestion, or service registration workflow is added.
- No live database, cloud resource, credential, deployment, or external service is used. The USD 100 total hard-stop remains unproven; P01 remains **NO-GO / BLOCKED**.
- Do not weaken or edit any existing gate, threshold, owner decision, token verification, or production detector behavior.


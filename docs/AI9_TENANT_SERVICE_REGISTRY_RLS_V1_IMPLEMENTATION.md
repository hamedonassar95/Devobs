# AI-9 Tenant Service Registry under PostgreSQL RLS — Implementation v1

**Policy version:** `ai9-tenant-service-registry-rls-v1`.
**Preregistration:** [frozen design](AI9_TENANT_SERVICE_REGISTRY_RLS_V1_PREREGISTRATION.md), commit `843ce6c62a571caa1e89bffc2f9a7207a712283a`.
**Base:** `main` at `c778fe4e7ff9f26e7cd2d7f4b9bba1623bc9de6f`.
**Gate status:** AI-9 **FAIL**; P01 **NO-GO / BLOCKED**.

## Change

- Added `deploy/postgres/002_service_registry.sql`, a one-time additive reference migration after `001_tenant_rls.sql`. It creates `(tenant_id, project_id, service_id)` as the key, checks identifier syntax, references the existing tenant/project tuple, grants `SELECT` only to `devobs_ai_reader`, forces RLS, and adds `devobs_service_member_read`.
- Added `PostgresTenantStore.authorize_service(subject, tenant, project, service_id)`. It validates IDs before connecting, opens a read-only transaction, sets identity only from the trusted caller using transaction-local settings, and returns a boolean for the exact registered tuple. Invalid identifiers return the existing fixed `access_denied`; database/security failures fail closed with fixed `StorageUnavailable` codes.
- Extended the role/schema/policy readiness check and ACCESS SHARE locking to all three reference tables. It rejects missing SELECT, any write privilege, disabled/unforced RLS, PostgreSQL versions outside the reviewed PG17 range, added policies, and changes to any of the three exact policy predicates.
- Added disposable PostgreSQL integration cases for same-name projects and services across tenants, exact subject/project/service matching, unknown membership/tuple denial, malformed input, read-only grants, RLS and policy drift, and DDL locking.
- Updated [the staging RLS guide](POSTGRES_RLS_STAGING.md). The service lookup is not routed from the WSGI API or Node confirmation adapter and no service write/registration workflow was added.

## Verification

The focused integration suite was run against a local disposable official `postgres:17` container, bound only to loopback, reporting PostgreSQL `17.11`. It used synthetic fixture rows and trust authentication only inside that temporary test container; the container is not a staging or production service.

```text
PG_TEST_ADMIN_DSN=postgresql://postgres@127.0.0.1:55432/postgres \
PG_TEST_READER_DSN=postgresql://devobs_ci_reader@127.0.0.1:55432/postgres \
python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v
Ran 21 tests in 0.797s
OK
```

The complete Python unit suite passed after installing the repository's hash-locked `requirements-dev.lock` in a temporary venv. The PostgreSQL test class was intentionally excluded there because that run had no test DSN; its separate run above used the disposable PostgreSQL service.

```text
python3 -m unittest discover -s tests -v
Ran 543 tests in 13.917s
OK (skipped=21)
```

TDD record: after writing the integration contract, the first run correctly failed because migration 002 was absent; after adding the migration, the next run exposed the missing `authorize_service` method and the readiness/lock checks ignoring the third table. The final focused run passed all 21 tests. The first full-suite attempt lacked both PyYAML and Ruby in this environment; installing the existing hash-locked development dependencies resolved the environment issue without changing repository dependencies.

Other local checks passed: Bandit reported no issues, the action-pin check covered 39 workflow/template files, agent-spec validation covered seven specs and five workflow budget gates, the synthetic AI-fixture validator returned `production_gate: false`, and staged-site HTTP smoke checks passed.

## Limits

- These are local source and disposable-PostgreSQL CI-fixture results, not a hosted staging test or production evidence.
- No route, service identity provider, API registration path, Node/Python protocol, real telemetry, or AI-9 evaluator was exercised.
- No detector, threshold, gate, AI-9 result, P01 decision, cloud setting, or deployment changed. No live service, real data, or secret was used.

## Hosted checks and merge evidence

- PR #306 passed CI in [run 41075077622](https://github.com/hamedonassar95/Devobs/actions/runs/41075077622) on exact head `c59f88e3db4b44c991152f931c4ab2875ff75c42`. Its PostgreSQL RLS, Python, security, image, site-contract, and required `validate` checks passed; CodeQL passed in [run 41075072434](https://github.com/hamedonassar95/Devobs/actions/runs/41075072434), and the Vercel preview check passed.
- PR #306 merged as `83f729b6aa2fff0f617e6a38a1a6bfc0c5315c26`. Main CI passed in [run 41075299391](https://github.com/hamedonassar95/Devobs/actions/runs/41075299391), including the disposable PostgreSQL RLS suite and static Pages publication plus `verify-production`. Main CodeQL passed in [run 41075298698](https://github.com/hamedonassar95/Devobs/actions/runs/41075298698).
- These results establish repository CI and static-site publication only. They do not establish a hosted P01 database, a real authentication integration, service ingestion, AI-9 quality, or production SaaS readiness.

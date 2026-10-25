# DevObs PostgreSQL RLS: real database integration gate

**Scope:** Original repository `hamedonassar95/Devobs`. Feature branch only. No deployment, cloud resources, external database, stored credentials, real account data or customer onboarding.

## What is actually implemented

- `deploy/postgres/001_tenant_rls.sql`: additive, single-use PostgreSQL 17+ schema `devobs_ai`, status records, tenant/project memberships, non-login `devobs_ai_reader` role.
- The role has SELECT and schema USAGE only; no table ownership, superuser, BYPASSRLS, INSERT, UPDATE or DELETE permissions. Both tables use `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
- Membership policies require exact server-authenticated subject and tenant; a project's CI state is visible only when membership and tenant match. Missing transaction identity gives zero rows by default.
- `PostgresTenantStore` in `scripts/devobs_intelligence/postgres_store.py` creates a new connection, starts an explicit read-only transaction, checks the active DB role, uses parameterized `set_config(..., true)` and parameterized SELECT. The client-supplied bearer token is **never forwarded to PostgreSQL**.
- The existing, signed access-token WSGI API can accept this adapter as its `tenant_gate` without additional permissions.
- The existing GitHub `validate` check now requires a **real PostgreSQL service-container isolation integration suite** on normal checks, not merely SQLite mocks. Rollback compatibility deliberately skips this extra gate, retaining the existing rollback test contract.

## Ephemeral test-only authentication

The integration service image uses `POSTGRES_HOST_AUTH_METHOD=trust` strictly inside a disposable GitHub Actions runner with no customer data or persistent storage. This must NEVER be copied to a real deployment. Test roles are created on the disposable instance and have no production credentials. Exposing such a service publicly would be unsafe.

## Runbook: staging adoption (NOT executed here)

1. Obtain owner approval for the target environment, region, infrastructure costs, incident response path and private network layout.
2. Configure a **separate** migration/DDL identity, and a runtime **non-owner, non-BYPASSRLS, non-superuser** database identity with read-only grants via role membership.
3. Secure all DB communications using TLS and limited-network ingress. Supply the DB connection via a secret manager in the running service, never via repository files.
4. Apply `deploy/postgres/001_tenant_rls.sql` **once**, in a reviewed migration transaction on an empty, separately approved database. It creates roles and schema; it is NOT a generic repeatable migration.
5. Connect the existing API with `PostgresTenantStore(injected_connection_string)`, after validating the OAuth issuer/JWKS using a trusted, operator-managed discovery lifecycle. Never accept a tenant/subject identity from unverified headers or user SQL.
6. Run cross-tenant tests with a true runtime role; verify missed membership, stale identity context, different tenants with equal project names, failed DB operations and denial of writes.
7. Before hosted SaaS, independently verify point-in-time restore, token/JWKS rotation, key compromise response, tenant deletion/privacy policy, rate limits, audits, data retention and least-privilege infrastructure.

**Important trust boundary:** custom PostgreSQL settings are application-controlled. A client with arbitrary SQL execution or direct access to the runtime DB role can spoof these settings. Therefore the database must not be accessible from untrusted clients, and all queries must be parameterized and fixed-shape. This demo does **not** establish production RLS against malicious direct SQL clients. Future stronger approaches include credentials scoped per tenant or securely signed tenant session context.

## Reproducible checks

```bash
# Standard unit tests without PostgreSQL (RLS suite will skip):
python3 -m unittest discover -s tests -v

# With an EMPTY, disposable PostgreSQL 17+ instance only:
# Set PG_TEST_ADMIN_DSN and PG_TEST_READER_DSN to disposable CI test roles.
python3 -m pip install -r requirements-api.txt
python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v
```

The GitHub `CI` workflow runs this against its own disposable service container and checks the result through the protected `validate` job; no manually supplied credentials or deployed server required. Check the exact PR commit status before merging.

## Outstanding blockers — not claimed implemented

- Deployed staging/prod PostgreSQL, customer identity provider, reverse proxy, domain/TLS, persistent backups/restore tests, on-call alerting, tenant usage isolation under concurrent loads, real data minimization, terms and privacy approval, commercial billing, external security audit, and customer access.
- Full SaaS platform and financial suitability are **not** established by a successful CI RLS test.
- `psycopg` uses LGPL-3.0-only; confirm how obligations apply to the intended distribution and any bundled binaries before commercial resale.

## References verified

- PostgreSQL RLS roles/forced policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL `CREATE POLICY`: https://www.postgresql.org/docs/current/sql-createpolicy.html
- `set_config` transaction scope: https://www.postgresql.org/docs/current/functions-admin.html
- Psycopg transactions: https://www.psycopg.org/psycopg3/docs/basic/transactions.html
- GitHub PostgreSQL service container CI: https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers

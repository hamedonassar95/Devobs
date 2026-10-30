# DevObs PostgreSQL RLS: real database integration gate

**Scope:** Original repository `hamedonassar95/Devobs`. Feature branch only. No deployment, cloud resources, external database, stored credentials, real account data or customer onboarding.

## What is actually implemented

- `deploy/postgres/001_tenant_rls.sql` creates the PostgreSQL 17+ reference schema `devobs_ai`, CI status records, tenant/project memberships, and the non-login `devobs_ai_reader` role. `deploy/postgres/002_service_registry.sql` adds the service registry as a separate one-time migration.
- The runtime role has SELECT and schema USAGE only; no table ownership, superuser, BYPASSRLS, INSERT, UPDATE or DELETE permissions. `project_ci`, `memberships`, and `service_registry` all use `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
- Membership policies require exact server-authenticated subject and tenant; CI status and service-registry rows are visible only when tenant, project, and subject membership match. Missing transaction identity gives zero rows by default. Service IDs may repeat across tenants because the primary key includes tenant and project.
- `PostgresTenantStore` in `scripts/devobs_intelligence/postgres_store.py` creates a new connection, starts an explicit read-only transaction, checks the active DB role and all three tables/policies, locks their schema for the transaction, and uses parameterized `set_config(..., true)` and fixed-shape SELECTs. `authorize_service(subject, tenant, project, service_id)` returns a boolean for an exact registered tuple. The client-supplied bearer token is **never forwarded to PostgreSQL**.
- `authorize_service` is a storage contract only. It is not called by the WSGI API or Node confirmation adapter, and this work adds no endpoint or service-registration/write path.
- The existing, signed access-token WSGI API can accept this adapter as its `tenant_gate` without additional permissions.
- `oidc_metadata.py` validates already authenticated issuer metadata against a configured HTTPS issuer and same-origin JWKS URI, then constructs the existing signature-verifying access-token reader. No arbitrary remote requests, unsigned token acceptance, runtime key rotation or live provider onboarding are enabled.
- The existing GitHub `validate` check now requires a **real PostgreSQL service-container isolation integration suite** on normal checks, not merely SQLite mocks. Rollback compatibility deliberately skips this extra gate, retaining the existing rollback test contract.

## Ephemeral test-only authentication

The integration service image uses `POSTGRES_HOST_AUTH_METHOD=trust` strictly inside a disposable GitHub Actions runner with no customer data or persistent storage. This must NEVER be copied to a real deployment. Test roles are created on the disposable instance and have no production credentials. Exposing such a service publicly would be unsafe.

## Independent OIDC provider readiness

The issuer-metadata validator deliberately consumes **already trusted, operator-verified metadata and JWKS**; it does not fetch remote content or verify HTTPS provenance itself. In staging an authorized operator must choose the IdP, verify its official issuer and key distribution over HTTPS, define rotation/revocation behavior and test actual JWT claims before onboarding users. The extra unit tests exercise generated ephemeral RSA public keys and reject mismatched issuers/JWKS origins and unsigned tokens. Never treat arbitrary discovery documents or a language-model suggestion as a signing authority.

## Runbook: staging adoption (NOT executed here)

1. Obtain owner approval for the target environment, region, infrastructure costs, incident response path and private network layout.
2. Configure a **separate** migration/DDL identity, and a runtime **non-owner, non-BYPASSRLS, non-superuser** database identity with read-only grants via role membership.
3. Secure all DB communications using TLS and limited-network ingress. Supply the DB connection via a secret manager in the running service, never via repository files.
4. Apply `deploy/postgres/001_tenant_rls.sql` once, then `deploy/postgres/002_service_registry.sql` once, using a separately approved migration identity on an empty, separately approved database. These reference migrations are not generic repeatable migrations; migration 002 requires migration 001.
5. Connect the existing API with `PostgresTenantStore(injected_connection_string)`, after validating the OAuth issuer/JWKS using a trusted, operator-managed discovery lifecycle. Never accept a tenant/subject identity from unverified headers or user SQL.
6. The current offline integration suite tests registered service lookups with a true runtime role, including equal project and service IDs across tenants. Before exposing service authorization through an API, add an authenticated call path and an owner-controlled registration process; neither exists in this increment.
7. Run cross-tenant tests with a true runtime role; verify missing membership, stale identity context, different tenants with equal project/service names, failed DB operations and denial of writes.
8. Before hosted SaaS, independently verify point-in-time restore, token/JWKS rotation, key compromise response, tenant deletion/privacy policy, rate limits, audits, data retention and least-privilege infrastructure.

**Important trust boundary:** custom PostgreSQL settings are application-controlled. A client with arbitrary SQL execution or direct access to the runtime DB role can spoof these settings. Therefore the database must not be accessible from untrusted clients, and all queries must be parameterized and fixed-shape. This demo does **not** establish production RLS against malicious direct SQL clients. Future stronger approaches include credentials scoped per tenant or securely signed tenant session context.

## Reproducible checks

```bash
# Standard unit tests without PostgreSQL (RLS suite will skip):
python3 -m unittest discover -s tests -v

# With an EMPTY, disposable PostgreSQL 17+ instance only:
# Set PG_TEST_ADMIN_DSN and PG_TEST_READER_DSN to disposable CI test roles.
python3 -m pip install --require-hashes -r requirements-api.lock
python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v
```

The GitHub `CI` workflow runs this against its own disposable service container and checks the result through the protected `validate` job; no manually supplied credentials or deployed server required. Check the exact PR commit status before merging.

## Outstanding blockers — not claimed implemented

- Deployed staging/prod PostgreSQL, service-registration administration, an API call site for `authorize_service`, a decision on where AI-9 confirmation state runs, customer identity provider, reverse proxy, domain/TLS, persistent backups/restore tests, on-call alerting, tenant usage isolation under concurrent loads, real data minimization, terms and privacy approval, commercial billing, external security audit, and customer access.
- Full SaaS platform and financial suitability are **not** established by a successful CI RLS test.
- `psycopg` uses LGPL-3.0-only; confirm how obligations apply to the intended distribution and any bundled binaries before commercial resale.

## References verified

- PostgreSQL RLS roles/forced policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL `CREATE TABLE` constraints and foreign keys: https://www.postgresql.org/docs/current/ddl-constraints.html
- PostgreSQL `CREATE POLICY`: https://www.postgresql.org/docs/current/sql-createpolicy.html
- `set_config` transaction scope: https://www.postgresql.org/docs/current/functions-admin.html
- Psycopg transactions: https://www.psycopg.org/psycopg3/docs/basic/transactions.html
- GitHub PostgreSQL service container CI: https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers

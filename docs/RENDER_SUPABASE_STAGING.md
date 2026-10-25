# DevObs managed Staging — Render + Supabase (proposal, not deployed)

**Scope:** Original `hamedonassar95/Devobs`, [master execution issue #233](https://github.com/hamedonassar95/Devobs/issues/233), phase [#221](https://github.com/hamedonassar95/Devobs/issues/221). This document and `render.yaml` only prepare a Staging deployment; they DO NOT create a service, enter secrets, migrate a customer database, enable billing, or certify readiness.

## Implementation delivered in this branch

- `scripts/devobs_intelligence/staging_app.py` wires the existing read-only WSGI API, pretrusted OIDC metadata and pinned JWKS, and `PostgresTenantStore` using a runtime configuration that fails closed.
- `render.yaml` chooses a proposed Frankfurt Starter web service with **`autoDeployTrigger: off`** and no preview services. **Applying the Blueprint is a separately authorized action and may incur charges.** The region, paid tier and any data residency terms require operator approval before applying.
- Health check `GET /healthz` returns liveness only (204); it **does not** check the database or guarantee readiness. Authenticated end-to-end API and RLS checks are additional gates.
- `tests/test_intelligence_staging_app.py` covers missing identity/DB settings, unsafe TLS and admin role names, method and bearer-token boundaries. No real credentials or external server are used.

## External prerequisites and approval gates

1. Choose and authorize the Render workspace, billing plan, region and maximum monthly spend. Do not import `render.yaml` without reviewing these fields. Keep auto-deploy off.
2. Create an **independent** staging Supabase project only with appropriate account authority. Obtain **operator-specific** connection information from Dashboard → Connect. Supabase's direct endpoint may require IPv6 or an IPv4 add-on; a persistent IPv4-only runtime can use **session pooler** mode. Do not guess a pooler host. Avoid admin `postgres` credentials as the runtime identity.
3. Use distinct migration and runtime identities. Apply `deploy/postgres/001_tenant_rls.sql` to an **empty approved staging DB**, reviewing its role/schema assumptions first. Grant only the minimum read permissions; production requires stronger tenant/session authorization and negative tenant/SQL-isolation testing.
4. Enable Supabase SSL enforcement, obtain the verified CA certificate through the authenticated dashboard and make it available to the Render runtime through an approved secret/mount method. Supply a `DEVOBS_PG_DSN` that uses `sslmode=verify-full` and `sslrootcert` pointing to that trusted certificate; neither the certificate nor a connection string belongs in source control. **A CA provisioning mechanism on Render still needs design and real testing before deployment.**
5. Choose an OIDC provider issuing appropriately typed `RS256` API access tokens with the required issuer, audience, client ID, `devobs.read` scope, `jti`, `iat` and `exp` claims. Supply metadata/JWKS only after independently authenticating their official source. Runtime JWKS refresh, revocation and key-rotation safety are still **BLOCKED**; static environment JSON is not a production key lifecycle.
6. Configure the `sync: false` Render variables during the approved initial Blueprint creation; for existing Blueprints, variables must be configured by an operator in the provider interface. Do not enter real tokens or passwords in GitHub Issues or Codex prompts.
7. Execute tests against a real staged identity and runtime role: valid read, invalid ID token, bad signature, different tenant, expired JWKS, stale source SHA, DB downtime, pooled connection switch, rate limiting, request sizing, redacted logs and recovery. Report actual results and exact staging SHA.
8. Enable a separate protected production environment only after managed database backup **restore rehearsal**, authenticated approvals, provider-side budgets, security review, privacy/legal review and monitored SLOs. Never auto-promote from a synthetic CI test.

## Required variable names (values set out of band)

| Variable | Meaning |
| --- | --- |
| `DEVOBS_PG_DSN` | dedicated non-admin runtime Postgres DSN with TLS verification and CA path |
| `DEVOBS_OIDC_ISSUER` | pinned HTTPS issuer |
| `DEVOBS_OIDC_AUDIENCE` | intended API audience |
| `DEVOBS_OIDC_CLIENT_ID` | accepted OAuth client ID |
| `DEVOBS_OIDC_METADATA_JSON` | *authenticated* provider metadata JSON |
| `DEVOBS_OIDC_JWKS_JSON` | *authenticated* public RSA JWKS JSON; no private signing keys |

## Local checks

```bash
python3 -m pip install -r requirements-api.txt
python3 -m unittest discover -s tests -p 'test_intelligence_staging_app.py' -v
python3 -m unittest discover -s tests -v
```

## Verified provider references

- Render Blueprint fields, manual deployment and secret prompts: https://render.com/docs/blueprint-spec
- Supabase connection options, dedicated runtime roles, session pooler, SSL/verify-full: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase enforced SSL: https://supabase.com/docs/guides/platform/ssl-enforcement

**Current decision:** managed services selected, but provider account connection, paid plan, tenant identity and user-authorized Staging remain **not configured**, so no real Staging/Production is claimed.

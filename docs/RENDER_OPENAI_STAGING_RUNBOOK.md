# Render + OpenAI synthetic staging runbook

## Render source commit drift preflight — 2026-11-18

**VERIFIED (read-only GitHub/Render connectors):** GitHub canonical `main` and the successfully synchronized GitLab `main` both pointed to `468addb459b79158f74dc2230a4336f81ac7c344` when inspected on 2026-11-18. The latest Render Free web-service deployment `dep-dbs9uo5g1s2s73ejsgj0` still reports `update_failed` at **different source** `1f1fd774f02579a500c07bd667865e51ed187948` (2026-11-14). Render's official [list deploys API](https://api-docs.render.com/reference/list-deploys) exposes `deploy.commit.id`, which is the source for the **reviewed, manually supplied** deploy SHA in this offline evidence snapshot. This is a point-in-time observation, not continuous monitoring.

**New offline gate (proposed in this PR, not deployed):** `scripts/check_free_staging_health.py` now accepts exact v3 evidence including `render.canonical_main_commit` and `render.web_last_deploy_commit` and reports `RENDER_DEPLOY_SOURCE_OUTDATED` when they differ, independently of status. A source SHA match alone cannot prove a working deployment; `RENDER_LATEST_DEPLOY_NOT_LIVE`, missing hosted identity/tenant acceptance, and all production gates remain separate. The updated `docs/p01/free-staging-inventory.json` captures **only** reviewed public commit SHAs and safe provider metadata. Old schema v2 and missing/non-lowercase SHA evidence fail closed instead of silently passing. Do not put branch credentials or any secret values in the evidence file.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

**Scope:** offline/free/local only; this does not poll GitHub or Render or change any cloud state. No permission to trigger Render, fix live OIDC values, generate credentials, change the disposable database, activate paid resources, or publish a release. Existing `invalid_staging_config stage=oidc` has **no confirmed individual missing/invalid name**. The operator's next step remains the existing name-only OIDC inventory, privately validated issuer/metadata/JWKS, and separate exact-scope approval before any deployment or ingress test. **P01 BLOCKED / NO-GO; AI-9 BLOCKED; Codex runtime OPEN.**

## 2026-11-18 owner checkpoint — disposable data and OIDC recovery

**VERIFIED (owner decision, 2026-11-18):** The owner explicitly classified data in the **existing** Render Free PostgreSQL `devobs-ai-staging-db` as **synthetic/disposable**, with no requirement to preserve its current contents. This is a *retention decision only*, **not** approval to delete/empty the database, export it, upgrade, provision a replacement or change the production backup requirements. Real customer data still requires separately reviewed backup and tested restore before P01 GO.

**VERIFIED (read-only Render metadata/logs):** Existing Free PostgreSQL 17 was `available` in Frankfurt and has an expiration timestamp of `2026-12-05T10:33:24.202776Z`. The web service's latest recorded deployment `dep-dbs9uo5g1s2s73ejsgj0`, source `1f1fd774f02579a500c07bd667865e51ed187948`, ended `update_failed`. A filtered Render log records `devobs-startup: invalid_staging_config stage=oidc`, but **does not identify a particular invalid name or value**. The latest canonical GitHub `main` at this checkpoint was `804324d4880fc5d16578b868df043a0c11fe1800`; successful source CI does **not** mean this newer code was deployed. No provider values, environment definitions or secrets were inspected.

**Already implemented:** [presence-only P01 triage](P01_STARTUP_TRIAGE.md) and `scripts/p01_startup_triage.py` accept manually marked `present`, `missing` or `not_checked` states. Presence-only triage now deliberately emits **nonzero exit code `5`** even when every required name is marked `present`: this signifies `PRESENT_BUT_VALIDITY_UNVERIFIED`, **not a successful readiness check**. The current source also categorizes OIDC startup errors without echoing values; the Render failure above was from older code and therefore does not reliably disclose `reason`. Do **not** create a second duplicate validator or a blind deploy.

### Authorized next diagnostic (names only, no deployment)

1. In the owner's **existing** Render web-service dashboard, examine only whether the five required OIDC *names* are configured: `DEVOBS_OIDC_ISSUER`, `DEVOBS_OIDC_AUDIENCE`, `DEVOBS_OIDC_CLIENT_ID`, `DEVOBS_OIDC_METADATA_JSON`, and `DEVOBS_OIDC_JWKS_JSON`. Do not copy any actual values, URLs, JWKS, tokens or screenshots of values into ChatGPT, GitHub or CI. Compare with the [name-only inventory](P01_STARTUP_TRIAGE.md).
2. The authorized identity-provider operator must **privately** verify that the issuer is HTTPS, registered client and intended audience are correct, metadata issuer matches exactly, `jwks_uri` has the expected HTTPS origin, and public JWKS passes the existing signed-token verifier policy. The startup verifier **does not fetch** metadata or JWKS automatically. Do not construct fake production keys or trust unreviewed metadata.
3. Record only non-sensitive outcomes such as `MISSING_REQUIRED_NAME`, `VALUE_VALIDITY_UNVERIFIED`, or `PROVIDER_METADATA_REVIEW_REQUIRED` in a separate review. A name marked `present` is not proof that its value is valid; stage `oidc` also says nothing about the database stage.
4. Any later configuration change, manual Render deploy or staging ingress test needs **separate approval** of its exact scope, a verified zero-paid-resource plan, and a fresh code SHA. Render's [Environment documentation](https://render.com/docs/configure-environment-variables) distinguishes **Save only** from save-and-deploy; do not accidentally choose a deployment option while preparing an audit.
5. After an authorized future attempt, require hosted `/healthz`, database-backed `/readyz`, signed-token acceptance and negative cross-tenant tests. If a check fails, keep **P01 BLOCKED / NO-GO**. Do not enable model inference, anonymous auth, provider auto-discovery or a replacement database as a workaround.

**Disposal/expiry boundary:** The owner does not need a backup of the current *synthetic* rows, but expiration can still make the service unusable. Do not automatically create new resources, change spending limits, delete the instance or claim hosted availability. Render's [Free policy](https://render.com/docs/free) says free Postgres is temporary and lacks managed backups. AI-9 remains **BLOCKED**, Codex runtime **OPEN**.

## Latest bounded diagnostic attempt — 2026-11-14

PR [#616](https://github.com/hamedonassar95/Devobs/pull/616) merged at
`1f1fd774f02579a500c07bd667865e51ed187948`. GitHub CI on the merge
[43623219682](https://github.com/hamedonassar95/Devobs/actions/runs/43623219682)
passed; the Render runtime result is separate.

The two non-secret paid-AI flags were merged as false without reading or replacing
other environment values. Render automatically started
`dep-dbs9uo5g1s2s73ejsgj0` on that source SHA; no duplicate deploy was dispatched.
Its terminal status was `update_failed`. A server-side text-filtered log query
returned only the safe startup diagnostic:

```text
devobs-startup: invalid_staging_config stage=oidc
```

The hosted configuration currently fails OIDC construction. This does not
identify a specific missing/invalid field, prove the validity of any later stage,
or justify weakening token validation. The actual issuer, registered public
client, authenticated metadata/public JWKS and restricted runtime connection
must be provisioned through an operator-managed secret/configuration interface.
Do not fabricate those values or publish them from a secret store.

The database remains temporary and backup/restore plus independent hosted
isolation are still unproven. Real independently labeled incident evidence is
also absent. P01 and AI-9 remain BLOCKED; this diagnostic attempt is not GO.

## Pre-deploy metadata snapshot — 2026-11-14 (metadata and owner attestation)

- In the owner-confirmed Render workspace, the existing `devobs-ai-staging`
  service is still Free in Frankfurt, on `main`, with automatic deploy disabled.
  Its only listed deploy is `update_failed` at source
  `5b75be633b4fd5c797d9e4fdc1e960fd0d68e07e` from 2026-11-05.
- The existing Free PostgreSQL database is `available` and expires on
  **2026-12-05**. That status does not prove schema, runtime-role, TLS or backup
  correctness. No second service or database was created.
- Bounded unauthenticated GETs to `/healthz` and `/readyz` timed out after
  15 seconds. This is absence of a successful probe, not proof of a specific
  missing configuration value or of the cause of the timeout.
- A read-only catalog query through the provider connector returned connection/TLS
  errors and no SQL result. No network allowlist was broadened and no schema or
  tenant-isolation claim was made from that attempt.
- The owner confirmed that this workspace has **no payment method**. This is an
  owner attestation, not an independent billing-account inspection. Render's
  [Free-service policy](https://render.com/docs/free) and
  [bandwidth policy](https://render.com/docs/outbound-bandwidth) say that Free
  services without a payment method are suspended when included usage is
  exhausted, rather than billed for overages. This supports a bounded Free-only
  diagnostic attempt; it does not authorize paid resources or model inference,
  establish another provider's billing policy, or satisfy the remaining P01 gates.

### Value-free startup diagnosis

**New offline source improvement (not a hosted deployment):** the fixed allowlisted
startup diagnostic now includes a safe `reason` classification alongside the
stage. It distinguishes `missing_required_configuration` (a required name is
absent) from `invalid_configuration` (a supplied document or setting is
invalid). An unknown/untrusted reason is normalized to `unclassified`.
Only these fixed literals are printed; raw field names, DSNs, credentials,
issuer URLs, metadata, JWKS, tokens and nested exception strings are never
included. Importantly, a `missing_required_configuration` result identifies
a **category**, not the individual environment-variable name.

The previously recorded **2026-11-14** Render diagnostic showed only
`stage=oidc` because it ran older code. Its exact reason remains
**UNVERIFIED**. No provider environment value was inspected, no hosted
redeployment was triggered, and existing hosted failures must not be relabeled
as missing/invalid without a newly authorized deploy.

The WSGI entrypoint preserves the fixed `invalid_staging_config` error and
fail-closed startup. For **new code**, a configuration rejection emits a single
bounded stderr line (synthetic example):

```text
devobs-startup: invalid_staging_config stage=oidc reason=missing_required_configuration
```

The stage is one of `oidc`, `database`, `diagnostics`, `api`, `telemetry`, or
`unclassified`. The reason is strictly allowlisted as above. It identifies a
category only; it never prints supplied values, a DSN, credentials, raw
metadata/JWKS or a nested exception message.
Successful startup emits no configuration diagnostic. An OIDC-stage failure is
not proof that the database or later stages are ready, because construction stops
at the first failure. Do not remove authentication/TLS validation to obtain a
successful process start.

The existing [presence-only inventory](P01_STARTUP_TRIAGE.md), if used by the
operator, remains separate and cannot prove the validity of any value. Identity
metadata/public signing keys and the restricted runtime connection must come
from an authenticated, operator-managed configuration source; do not copy
credentials into chat or Git. Live tenant-denial, TLS, backup/restore, independent
AI-9 incident labels and owner release evidence remain required before GO.

## Current verified runtime checkpoint — 2026-11-10 (read-only)

**VERIFIED from the connected Render workspace:** the resources have already been created. The existing [devobs-ai-staging web service](https://dashboard.render.com/web/srv-dbm5msu1egvs73be46lg) and [devobs-ai-staging-db PostgreSQL 17](https://dashboard.render.com/d/dpg-dbm5msu1egvs73be46og-a) are in Frankfurt. The web service targets `main`, with automatic deploy disabled. Its only recorded deployment, `dep-dbm5mtm1egvs73be49a0`, built successfully but failed to start on 2026-11-05, at source SHA `5b75be633b4fd5c797d9e4fdc1e960fd0d68e07e`. Logs end with `devobs_intelligence.staging_app.StagingConfigurationError: invalid_staging_config` and exit code 1. This fixed, non-sensitive error does **not** identify which required value is absent/invalid; do not assume a specific missing secret.

**VERIFIED deviation:** the actual PostgreSQL external access allowlist includes a `temporary-migration` entry, while reviewed `render.yaml` specifies `ipAllowList: []`. Never publish the address in GitHub. Determine whether that migration access is still required, then remove it by a separately approved operator action and verify the result. Database status `available` is not a readiness, schema, backup or isolation test.

**Verified boundary:** no successful hosted API request or live model call has been verified. The existing service has not passed `/readyz`, OIDC, least-privilege runtime-role, cross-tenant, recovery, or financial-cap checks. **P01 remains NO-GO / BLOCKED.** Do not import the Blueprint again, provision a second database, turn on paid inference, change Render environment/secrets, or redeploy based solely on this report.

## What the disposable CI integration proves

The existing `postgres-rls` CI job uses an ephemeral PostgreSQL 17 service and the repository's synthetic schema, restricted reader role, and tenant fixtures. `tests/test_postgres_rls_integration.py` now builds the real `devobs_intelligence.staging_app.build_app()` with an in-memory synthetic RSA key, public JWKS, compatible synthetic OIDC metadata, and short-lived test tokens. It exercises `/healthz`, database-backed `/readyz`, authenticated and cross-tenant reads, anonymous/invalid-token rejection, RLS-policy and runtime-role drift, fixed error redaction, invalid bootstrap settings, and the disabled-diagnostics response.

The test validates a `verify-full` DSN shape during application startup, then patches only the exact synthetic staging DSN at the `psycopg.connect` test boundary to use the disposable loopback reader DSN. That fixture has no verified-CA setup, so this patch does not prove TLS or certificate identity. Production `_database_dsn()` and TLS validation remain unchanged. A CI result proves only that the tested source revision passed against the synthetic disposable database; it says nothing about the current Render environment, database, OIDC provider, network, or recovery configuration.

**Previously verified CI baseline:** PR #600 merged at `12b857f1a5eec80fe605c34f08dd5b795fb7dc7a`; post-merge CI [43521549308](https://github.com/hamedonassar95/Devobs/actions/runs/43521549308) and the `postgres-rls` job succeeded on that exact SHA. That run predates the `build_app()` integration extension in this change and must not be presented as its test result.

## Secure operator actions before any future approved deployment

The CI fixture is not a deployment checklist. Before an owner-approved hosted attempt, the operator must recheck the current resource metadata without sharing credentials; reconcile the database's external allowlist; verify the reviewed exact SHA and startup settings through the provider's secret interface; confirm the runtime role is separate from the owner and has neither write grants nor `BYPASSRLS`; verify actual RLS policies and a trusted TLS certificate path; authenticate the OIDC issuer/JWKS and use synthetic identities; keep AI diagnostics disabled until separately approved budget and data-policy controls exist; and prove encrypted backup plus restore. Confirm the provider's total-cost boundary and rollback plan, then obtain explicit owner approval tied to the reviewed SHA. The recorded Render `render-internal-require` mode does not verify peer identity and does not meet the canonical P01 `verify-full` requirement without a separately approved exception.

CI success does not authorize P01 GO: it cannot establish hosted runtime state, network/TLS protections, real identity configuration, financial ceilings, backup/restore, or owner approval. P01 remains **NO-GO / BLOCKED** and AI-9 remains **BLOCKED**. No Render/Supabase runtime, credentials, paid inference, or deployment settings were accessed or changed for this integration proof.

**Historical preparation note (2026-11-05):** the following proposal preceded resource creation. The service/database now exist, but the intended fail-closed configuration and human approval boundaries remain in force.

**Historical preparation status (2026-11-05):** The owner selected Render for staging and OpenAI for diagnosis. The Blueprint and runbook describe intended controls, not proof of a working API. PR #440 and the staging preparation have been merged into the source history; live deployment was subsequently attempted and failed as documented above. No successful hosted API request or live model call has been verified. P01 remains NO-GO / BLOCKED until the remaining controls below are verified.

The draft uses one Render Free Python web service and one private Render Free PostgreSQL database in Frankfurt. Scope: synthetic data only. The API stays disabled by default. The database is for a temporary synthetic test only: Render Free Postgres has a 1 GB limit and expires after 30 days; it has no durable staging guarantee. Render Free web services sleep after 15 minutes without traffic, and workspace build-pipeline/outbound-bandwidth limits are not an all-in invoice cap. Do not use customer logs or real tenant data.

## Limits and trust boundaries in the draft

- The endpoint accepts at most **8 KiB of UTF-8 error log** and rejects request bodies larger than **32 KiB**.
- The OpenAI adapter makes one HTTPS Responses API request, with a 20-second network timeout, no retry, no redirect, `store: false`, no tools, and at most 512 output tokens. The Gunicorn worker timeout is 30 seconds.
- The endpoint allows at most **5 diagnoses per subject and tenant per minute**, plus **5 total valid diagnoses per process per minute**. The Render Blueprint uses one Gunicorn worker. These are in-memory burst limits; restarts reset them. They are not a monthly quota or a provider-enforced spending cap.
- The current draft model is `gpt-6-luna`; the owner chose OpenAI as provider but did not separately approve a model or a dollar budget. Check current [model details and pricing](https://developers.openai.com/api/docs/models/gpt-6-luna) before enabling calls.
- The only key source for this endpoint is the Render runtime environment variable `OPENAI_API_KEY`. There is no key in the Blueprint or repository. Never put the value in Git, a command, a ticket, or logs.
- Render documents that same-region internal Postgres connections can require TLS with `sslmode=require`, but that its self-signed internal certificates do not support `verify-full`. The explicit `render-internal-require` mode is limited to a Render web runtime. TLS is encrypted, but server-certificate identity is not verified. This differs from the canonical P01 `verify-full` requirement and remains a P01 blocker until the owner accepts the tradeoff or a compatible verified-TLS database path is selected and tested.
- Render's `fromDatabase` would expose the database's default connection identity. The Blueprint deliberately does **not** wire that admin identity into the API. The runtime DSN must use a separate login role that inherits `devobs_ai_reader`.
- OIDC documents/JWKS are operator-pinned, not fetched or rotated by the service. The runtime token must be RS256, contain the required claims and `devobs.ai.diagnose` scope, and use a `sub` matching `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. A compatible issuer and token are not configured or verified yet.

## Owner's manual setup, in order

1. **Do not import the Blueprint again.** The Render service and database already exist (see current verified checkpoint above). Use the two existing dashboard records to confirm the branch, the deployed SHA, the failed deployment, region and disabled auto-deploy. Do **not** create a duplicate resource or redeploy until the owner approves a reviewed exact SHA, the intended synthetic data scope, and the associated operational/cost risks. If account state differs from the checkpoint, stop and re-verify rather than recreating resources.

2. **Inspect the existing temporary synthetic database before any change.** Render reported it available, but its `temporary-migration` external allowlist entry differs from the reviewed private-only Blueprint; obtain separate owner approval to retire that entry after confirming it is unused. Check whether the schema or runtime role was already created; **never blindly re-run migrations**. If the database is verified empty and an operator separately approves migrations, use the official Render CLI from an exact reviewed checkout and run each migration exactly once against that new empty database:

   ```sh
   render psql devobs-ai-staging-db -- -v ON_ERROR_STOP=1 -f deploy/postgres/001_tenant_rls.sql
   render psql devobs-ai-staging-db -- -v ON_ERROR_STOP=1 -f deploy/postgres/002_service_registry.sql
   ```

   These commands change the remote database. They are not part of CI and have not been run here. Do not run them on an existing or customer database. The migrations create the reference schema and read-only NOLOGIN role; they do not insert tenant or service records.

3. **Create a separate runtime login in an interactive `render psql` session.** On this new database only, run once:

   ```sql
   CREATE ROLE devobs_staging_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
   GRANT devobs_ai_reader TO devobs_staging_runtime;
   \password devobs_staging_runtime
   ```

   `\password` prompts without echoing the password. Never use the database owner/admin connection in the API. If role creation or membership fails, stop; do not work around it by using the admin role.

4. **Configure an OIDC test identity before enabling the endpoint.** For a review-only candidate and synthetic compatibility matrix, consult [P01 Keycloak OIDC profile](P01_KEYCLOAK_OIDC_PROFILE.md); it does not create or approve an issuer.  Choose an issuer that can issue an access token with header `alg=RS256` and `typ=at+jwt`, plus the exact issuer/audience/client ID, `sub`, `jti`, `iat`, `exp` (lifetime no more than 15 minutes), and scopes `devobs.read devobs.ai.diagnose`. The `sub` must satisfy the identifier pattern stated above. Independently verify the issuer metadata and same-origin HTTPS JWKS, including the matching public RSA `kid`, then add `DEVOBS_OIDC_ISSUER`, `DEVOBS_OIDC_AUDIENCE`, `DEVOBS_OIDC_CLIENT_ID`, `DEVOBS_OIDC_METADATA_JSON`, and `DEVOBS_OIDC_JWKS_JSON` in the Render service's **Environment** page. Only public metadata and public JWKS belong in these settings; never include a private signing key. The service does not auto-discover or rotate keys.

5. **Prepare one synthetic tenant fixture.** Through the database admin session, insert the following fixture exactly once, replacing `staging-smoke` only if the chosen issuer cannot issue that safe `sub`. Make the test token's `sub` match the row. This uses synthetic values only; the API has no public row-creation endpoint.

   ```sql
   BEGIN;
   INSERT INTO devobs_ai.project_ci
       (tenant_id, project_id, source_sha, ci_state)
   VALUES ('demo', 'repair', repeat('0', 40), 'success');
   INSERT INTO devobs_ai.memberships (tenant_id, project_id, subject_id)
   VALUES ('demo', 'repair', 'staging-smoke');
   INSERT INTO devobs_ai.service_registry (tenant_id, project_id, service_id)
   VALUES ('demo', 'repair', 'api');
   COMMIT;
   ```

   If any insert fails, roll back and inspect the new empty database rather than retrying partial statements. Do not include the fixture or token in public issue/PR text.

6. **Add the runtime DSN to Render Environment.** Build it from the database's **internal** connection information, but use `devobs_staging_runtime` and its own password, not the admin user. Keep `DEVOBS_PG_TLS_MODE=render-internal-require` as set by the Blueprint. Add the DSN only in the Render dashboard; never add it to Git, local logs, or this repository. The code forces TLS and fails closed unless Render identifies the service as a web service. After separate owner approval for exact SHA and settings, the operator can redeploy manually and check `GET /readyz` returns `204`. That only proves the reviewed DB readiness contract, not OIDC login or AI behavior.

7. **Add the OpenAI key manually.** In the Render service, open **Environment → Add Environment Variable**; set the key name to exactly `OPENAI_API_KEY`, mark/store it as a secret, paste the value directly in Render, then save and deploy. Do not send the key to Codex or put it in a shell command, `.env`, Blueprint, report, or log. This repository cannot verify the account's billing limits. Configure and confirm the OpenAI project/account spending controls yourself before allowing any request.

8. **Enable the diagnosis route last.** Only after synthetic-only scope, account spending controls, the OIDC test identity, runtime database role, and `readyz` have been checked, set `DEVOBS_AI_BUDGET_APPROVED=true` and then `DEVOBS_AI_DIAGNOSTICS_ENABLED=true` in Render Environment. The budget flag is an operator acknowledgment, **not** an enforced budget. If you cannot establish the approved all-in USD 100 monthly cap, keep both flags false and P01 blocked.

9. **Run the five-case live probe only after the endpoint is enabled.** Set the endpoint URL (not a credential) and use the short-lived test access token when prompted; the prompt hides input. Save the report outside the repository:

   ```sh
   DEVOBS_DIAGNOSIS_ENDPOINT='https://<your-service>.onrender.com/v1/tenants/demo/projects/repair/services/api/diagnostics' \
     python3 scripts/devobs_intelligence/run_live_diagnosis_cases.py \
       --output /tmp/devobs-staging-diagnosis-2026-11-05.json
   ```

   This sends exactly five synthetic requests, makes no retries, and may incur OpenAI usage. The client timeout is 120 seconds to allow for a Free service cold start; the API's OpenAI socket timeout remains 20 seconds and Gunicorn remains 30 seconds. The report records each synthetic input, returned output, HTTP status, and client/server latency in a new mode-0600 file; it refuses to overwrite an existing report. A failed request is recorded as failed. Do not call the endpoint live before you are ready to incur up to five model requests.

## What must still be proven before P01 can leave NO-GO

- Render account/workspace eligibility, actual region, resource creation, startup, TLS ingress and egress, `readyz`, and the database's actual role/policies.
- Render Free Postgres expires after 30 days and lacks durable backups. A recovery or paid-plan decision is required before treating this as persistent staging.
- The Render internal DB's TLS mode does not satisfy the roadmap's certificate-verification requirement. Get explicit owner acceptance of this test-only tradeoff or use a verified-TLS database endpoint with a safe ingress policy.
- The USD 100 all-in cap remains unproven. Render build/bandwidth and OpenAI model usage are separate spend surfaces; per-minute request limits do not cap total monthly spend.
- A compatible live OIDC issuer/JWKS, key-rotation procedure, compliant token subject, authenticated request, cross-tenant denial, rate-limit evidence, sanitized logs, and deletion/rollback evidence.
- The five-case script has not run, and there has been no hosted API request or live OpenAI model call from this work.

## Official references

- [Render Free services and Postgres limits](https://render.com/docs/free)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render Postgres connectivity and TLS behavior](https://render.com/docs/postgresql-creating-connecting)
- [Render CLI `psql`](https://render.com/docs/cli-reference)
- [Render default environment variables](https://render.com/docs/environment-variables)
- [OpenAI GPT-6 Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)

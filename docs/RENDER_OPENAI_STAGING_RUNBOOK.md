# Render + OpenAI synthetic staging runbook

## Current verified runtime checkpoint — 2026-11-10 (read-only)

**VERIFIED from the connected Render workspace:** the resources have already been created. The existing [devobs-ai-staging web service](https://dashboard.render.com/web/srv-dbm5msu1egvs73be46lg) and [devobs-ai-staging-db PostgreSQL 17](https://dashboard.render.com/d/dpg-dbm5msu1egvs73be46og-a) are in Frankfurt. The web service targets `main`, with automatic deploy disabled. Its only recorded deployment, `dep-dbm5mtm1egvs73be49a0`, built successfully but failed to start on 2026-11-05, at source SHA `5b75be633b4fd5c797d9e4fdc1e960fd0d68e07e`. Logs end with `devobs_intelligence.staging_app.StagingConfigurationError: invalid_staging_config` and exit code 1. This fixed, non-sensitive error does **not** identify which required value is absent/invalid; do not assume a specific missing secret.

**VERIFIED deviation:** the actual PostgreSQL external access allowlist includes a `temporary-migration` entry, while reviewed `render.yaml` specifies `ipAllowList: []`. Never publish the address in GitHub. Determine whether that migration access is still required, then remove it by a separately approved operator action and verify the result. Database status `available` is not a readiness, schema, backup or isolation test.

**Verified boundary:** no successful hosted API request or live model call has been verified. The existing service has not passed `/readyz`, OIDC, least-privilege runtime-role, cross-tenant, recovery, or financial-cap checks. **P01 remains NO-GO / BLOCKED.** Do not import the Blueprint again, provision a second database, turn on paid inference, change Render environment/secrets, or redeploy based solely on this report.

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

4. **Configure an OIDC test identity before enabling the endpoint.** Choose an issuer that can issue an access token with header `alg=RS256` and `typ=at+jwt`, plus the exact issuer/audience/client ID, `sub`, `jti`, `iat`, `exp` (lifetime no more than 15 minutes), and scopes `devobs.read devobs.ai.diagnose`. The `sub` must satisfy the identifier pattern stated above. Independently verify the issuer metadata and same-origin HTTPS JWKS, including the matching public RSA `kid`, then add `DEVOBS_OIDC_ISSUER`, `DEVOBS_OIDC_AUDIENCE`, `DEVOBS_OIDC_CLIENT_ID`, `DEVOBS_OIDC_METADATA_JSON`, and `DEVOBS_OIDC_JWKS_JSON` in the Render service's **Environment** page. Only public metadata and public JWKS belong in these settings; never include a private signing key. The service does not auto-discover or rotate keys.

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

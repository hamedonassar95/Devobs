# Devobs free staging — cross-provider read-only checkpoint (2026-11-17)

**VERIFIED provider metadata / READ ONLY / P01 NO-GO.** This page documents only the public or redacted read-only metadata observed through the existing Render and Supabase connections. It is **not** proof of functioning hosted authentication, tenant isolation, payment limits, backups or production readiness.

## What is available without new spending

| Surface | Current observation | Boundary |
| --- | --- | --- |
| GitHub | Protected `main` with passing [CI #44040183553](https://github.com/hamedonassar95/Devobs/actions/runs/44040183553); Pages serves a static site | Public-repo standard GitHub-hosted Actions usage is [free](https://docs.github.com/en/actions/concepts/billing-and-usage); static Pages is not a hosted multi-tenant API |
| Render web | Existing `devobs-ai-staging` uses the **free** plan, Frankfurt, attached to Devobs GitHub `main`; automatic deployment disabled | Provider record indicates no suspension, but does **not** prove healthy `/readyz`; web ingress currently permits public networks; no hosted authorization test was made |
| Render latest deploy | The last known `devobs-ai-staging` deploy for Git commit `1f1fd774f02579a500c07bd667865e51ed187948` finished `update_failed` on 2026-11-14. The prior 2026-11-05 deploy also finished `update_failed` | Failures verified through read-only provider deployment metadata. They do not prove the exact root cause or whether an older instance is still serving. The **v2** readiness snapshot must report a `RENDER_LATEST_DEPLOY_NOT_LIVE` blocker. Never silently treat a failed deploy as production readiness. [Render deploy statuses](https://api-docs.render.com/reference/retrieve-deploy) |
| Render PostgreSQL | Existing `devobs-ai-staging-db` uses **free** PostgreSQL 17 in Frankfurt; provider metadata says available | **Expires 2026-12-05 10:33:24 UTC**, no replicas or verified backups; no changes made. The [Free policy](https://render.com/docs/free) specifies 30-day expiry and no managed backups |
| Supabase Devobs | Existing project status **INACTIVE**, not serving new connected database checks | The official [free-project pause guide](https://supabase.com/docs/guides/platform/free-project-pausing) describes manual project resumption. This audit did not resume it or read rows |
| Phone Repair Assistant v2 Supabase | Separate connected project reported **ACTIVE_HEALTHY** | **Not a Devobs resource.** Its database, credentials, tenancy and data must never be reused for this integration |
| GitLab | Imported Devobs repository exists, branch `main` remains behind canonical GitHub | GitLab parity and Git safety checks already exist. No mirror, branch write or CI update was performed |
| GitBook | Private documentation Git Sync is configured | No new public site or publication authorized |

## Repeatable zero-cost local checkpoint

The dated inventory is a **strictly redacted source snapshot** at `docs/p01/free-staging-inventory.json`. It contains no project IDs, provider credentials, connection strings, email addresses, internal hostnames, or raw health responses. Do not add these fields.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

- Exit **1 / `REVIEW_REQUIRED`** with independently classified blockers; this is the expected outcome. No remote calls or automatic action happen. The checker can never assert production GO from provider metadata alone.
- Exit **2 / `INVALID_SNAPSHOT`** for malformed, cross-project, paid-tier, or unexpected evidence. Duplicate keys, symlinks and added secret fields fail closed.
- The observation date expires after **7 days**. Stale metadata is a blocker even when the snapshot previously showed an available instance.
- Verify `Render` and `Supabase` status again through an **authorized read-only** provider connection before updating this source file in a new reviewed PR. Changing the snapshot does not trigger a service restart, hosted migration, token refresh or billable API.

## Owner decisions still required

**Owner decision, 2026-11-18:** the owner explicitly classified the **existing** Render Free PostgreSQL data as synthetic/disposable and said it need not be preserved. This resolves only the *current test-data retention decision*, not the service availability/deletion decision or production backup-and-restore acceptance. The database still expires on **2026-12-05 10:33:24 UTC**. No delete, empty-table operation, paid upgrade, export, replacement, migration or automatic service action was authorized. **Latest Render failure:** read-only logs for the 2026-11-14 `update_failed` deploy identify the startup stage `oidc`, but not which value/name failed. Follow the [OIDC operator recovery checklist](RENDER_OPENAI_STAGING_RUNBOOK.md#2026-11-18-owner-checkpoint--disposable-data-and-oidc-recovery) using only variable-name presence observations; actual OIDC values and provider identities remain owner/operator-managed and unverified. Render's [environment configuration documentation](https://render.com/docs/configure-environment-variables) distinguishes save-only from deploy actions; do not make settings changes or trigger deploys during this read-only phase. Devobs Supabase project resumption, provider network/identity configuration, billing constraints and hosted integration acceptance remain separate owner-gated operations. Do not use the active phone-repair project as a shortcut.

**Open gates:** P01 BLOCKED/NO-GO, AI-9 BLOCKED and Codex runtime OPEN. Existing free components allow CI, demonstrations and offline tests; they cannot meet full hosted SaaS production acceptance without independent evidence.

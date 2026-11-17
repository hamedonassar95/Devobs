# Devobs free staging — cross-provider read-only checkpoint (2026-11-17)

**VERIFIED provider metadata / READ ONLY / P01 NO-GO.** This page documents only the public or redacted read-only metadata observed through the existing Render and Supabase connections. It is **not** proof of functioning hosted authentication, tenant isolation, payment limits, backups or production readiness.

## What is available without new spending

| Surface | Current observation | Boundary |
| --- | --- | --- |
| GitHub | Protected `main` with passing [CI #44040183553](https://github.com/hamedonassar95/Devobs/actions/runs/44040183553); Pages serves a static site | Public-repo standard GitHub-hosted Actions usage is [free](https://docs.github.com/en/actions/concepts/billing-and-usage); static Pages is not a hosted multi-tenant API |
| Render web | Existing `devobs-ai-staging` uses the **free** plan, Frankfurt, attached to Devobs GitHub `main`; automatic deployment disabled | Provider record indicates no suspension, but does **not** prove healthy `/readyz`; web ingress currently permits public networks; no hosted authorization test was made |
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

The Render free database is expiring; data-retention needs, source access, lawful backups and restore must be decided by the owner **before 2026-12-05**. Do not assume the post-expiry grace period keeps it queryable, and do not automatically upgrade, delete or export it. Devobs Supabase project resumption, provider network/identity configuration, billing constraints and hosted integration acceptance are separate owner-gated operations. Do not use the active phone-repair project as a shortcut.

**Open gates:** P01 BLOCKED/NO-GO, AI-9 BLOCKED and Codex runtime OPEN. Existing free components allow CI, demonstrations and offline tests; they cannot meet full hosted SaaS production acceptance without independent evidence.

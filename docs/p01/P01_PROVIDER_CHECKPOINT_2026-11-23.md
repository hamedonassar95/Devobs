# P01 provider inventory checkpoint — 2026-11-23

**Status:** VERIFIED metadata observations; P01 remains **BLOCKED / NO-GO**.
**Canonical source:** GitHub `main` at `4771071dd4cde67fec175d2b671e54a170a11ab0`.
**Evidence collected:** 2026-11-23 UTC using connected read-only Render and Supabase inventory actions.
**Scope:** Existing Devobs resources only; no data, credentials, environment values, database connections, hosted app probes, deployments, or spend.

## Current verified observations

| Surface | Provider metadata | Evidence boundary |
| --- | --- | --- |
| GitHub repository | `main` at `4771071dd4cde67fec175d2b671e54a170a11ab0`; main CI [#45186604047](https://github.com/hamedonassar95/Devobs/actions/runs/45186604047) succeeded. | Repository CI is not a hosted API readiness test. |
| Render web service `devobs-ai-staging` | Free, Frankfurt; `main` source branch, auto-deploy off, not suspended; latest recorded deployment `update_failed` (2026-11-14) at `1f1fd774f02579a500c07bd667865e51ed187948`. Build succeeded but process exited nonzero. | No successful `/readyz` result, signed OIDC flow, TLS/network acceptance or runtime connection was observed. Current ingress configuration permits public traffic; the policy has not been accepted for P01. |
| Render PostgreSQL `devobs-ai-staging-db` | Free, PostgreSQL 17, Frankfurt, provider status `available`, expires `2026-12-05T10:33:24.202776Z`. A named external allowlist entry still exists; omit its address from this public report. | No SQL, data classification, live consumers, backup, or restore was verified. |
| Supabase organization `Devobs AI Intelligence` | Its connected Free project was listed as `INACTIVE` in `us-east-1`. | No resume, SQL, authorization, or hosted tenant-denial test was performed. A separate phone-repair project is outside Devobs scope. |

## Deadline and risk

- The reported Render Free PostgreSQL expiry is **2026-12-05 10:33 UTC** (**13:33 Asia/Amman**).
- Render states Free PostgreSQL expires after 30 days; after expiry it cannot be accessed without a paid upgrade, followed by a 14-day paid-upgrade grace interval before deletion. The Free plan has no Render-managed backups: [Free tier](https://render.com/docs/free), [backup and recovery](https://render.com/docs/postgresql-backups).
- A grace interval **does not** provide continued free access, a data-preservation guarantee, or approval to incur charges.
- The older deployment SHA is not the latest GitHub main SHA. The provider inventory is not proof of which specific OIDC field, if any, blocked runtime startup.

## Required owner decision before expiry

1. Reconfirm, without exposing rows or credentials, whether all data are synthetic/disposable and whether any external service or person depends on this database.
2. Select a separately reviewed **preserve** or **retire** path in [issue #713](https://github.com/hamedonassar95/Devobs/issues/713); no action is selected by silence.
3. Any future irreversible, paid, or hosted operation needs a new exact-resource / source-SHA / UTC-window / impact authorization. **This checkpoint does not authorize either option.**
4. Do not import the existing Blueprint, activate auto-deploy, start AI inference, create paid services, run migrations, export data, or delete/suspend the instance under this PR.

## Existing controls reused

- [Owner-gated retirement plan](../plans/2026-11-19-render-free-postgres-retirement-plan.md)
- [P01 activation readiness](../P01_ACTIVATION_READINESS.md)
- `scripts/check_free_staging_health.py` and `scripts/check_render_free_expiry.py` (offline, fail-closed, not provider probes)
- [P01 NO-GO decision](P01_NO_GO_DECISION_2026-11-19.md)

**Open acceptance gates:** P01 **BLOCKED / NO-GO**; AI-9 **BLOCKED**; Codex runtime **OPEN**.

# Render Free PostgreSQL expiry decision — 2026-11-24

**Status: PENDING HUMAN APPROVAL.** This is a read-only, owner-gated decision record. This task authorizes neither preservation nor retirement, and it does not approve accepting provider expiry by silence.

## Verified baseline

- **VERIFIED (GitHub):** PR [#775](https://github.com/hamedonassar95/Devobs/pull/775) merged exact head `e12915ea1f053b4c240c11170eb201e4db45d3d5` as `main` SHA `7f23f5635fecdbdc342dfaada259e4cc0c2adc3f`. Exact-head CI [45306060923](https://github.com/hamedonassar95/Devobs/actions/runs/45306060923), merge-SHA CI [45355683819](https://github.com/hamedonassar95/Devobs/actions/runs/45355683819), and merge-SHA [Push on main](https://github.com/hamedonassar95/Devobs/actions/runs/45355682459) completed successfully.
- **VERIFIED (read-only Render metadata, 2026-11-24):** PostgreSQL resource `devobs-ai-staging-db` / `dpg-dbm5msu1egvs73be46og-a` is `available`, Free, PostgreSQL 17, Frankfurt, and reports expiry `2026-12-05T10:33:24.202776Z`. The associated web service `devobs-ai-staging` / `srv-dbm5msu1egvs73be46lg` exists on `main`, has auto-deploy off, and is not suspended. Only resource metadata was retained; no environment values, connection details, logs, database sessions, rows, billing settings, or service probes were read.
- **Deadline:** Render reports `2026-12-05 10:33:24.202776 UTC`, which is `2026-12-05 13:33:24.202776 Asia/Amman (UTC+03:00)`. This is the provider-reported expiry, not permission to delete, upgrade, migrate, or intentionally lose data.
- **VERIFIED (provider documentation):** [Render Free](https://render.com/docs/free) says Free PostgreSQL becomes inaccessible after expiry without a paid upgrade and documents a 14-day upgrade grace interval before eventual deletion. [Render PostgreSQL backups](https://render.com/docs/postgresql-backups) says Free databases do not have Render-managed backups. The grace period is not free continued access or a recovery guarantee; the exact eventual deletion time and any exception are unverified.

## Existing decision and dependency evidence

- **VERIFIED (owner direction, Issue [#713](https://github.com/hamedonassar95/Devobs/issues/713), 2026-11-19):** the owner approved preparing the existing retirement plan only. The latest issue update on 2026-11-23 still requires an explicit choice and data/dependency attestations. Issue #713 remains open. Planning approval is not execution authorization.
- **VERIFIED (source):** [`render.yaml`](../../render.yaml) declares the staging service and database. `scripts/devobs_intelligence/staging_app.py` constructs `PostgresTenantStore` from the configured `DEVOBS_PG_DSN` and wires its readiness probe. This is a source-level dependency; it does **not** prove a live connection or consumer. Re-importing the Blueprint is not part of either option and could attempt resource creation.
- **VERIFIED (bounded prior search recorded in Issue #713):** no explicit target database identifier was found in the other searched repository sources at that time. This does not establish that external services, local users, jobs, sessions, or unindexed repositories do not depend on the database.
- **VERIFIED (historical owner statement, 2026-11-18):** the current rows were classified as synthetic/disposable with no current-content preservation requirement. **UNVERIFIED:** actual row contents, current classification, legal/contractual retention duties, external consumers, and any owner responsible for those dependencies; no rows were inspected here.
- **VERIFIED (provider policy):** Render-managed Free backups are unavailable. **UNVERIFIED:** any separately held backup, whether it can be restored, and its approved retention destination. No backup/export or recovery test has been performed for this resource.

## Decision matrix

| Option | Impact and risk | Costs and recovery | Current decision state |
| --- | --- | --- | --- |
| **A. Preserve the existing database/data** | Keeping the current Free resource does not guarantee access after the deadline. Preserving access may require a paid upgrade; preserving data elsewhere would require a separately approved export and destination. | Exact plan price, total cost, and an enforceable budget cap were not checked or approved. No verified backup or restore exists. Any preservation method needs an owner-approved recovery destination and tested restore plan. | **BLOCKED — not selected or authorized.** |
| **B. Retire the disposable staging database** | Explicit deletion or deliberate acceptance of expiry may irreversibly remove data. The source has a PostgreSQL readiness dependency; service impact is possible, while current runtime dependence is unknown. Recreating an empty database is not rollback. | No backup is verified. Outage, replacement, and recovery costs are unknown; no paid service is approved. | **BLOCKED — not selected or authorized.** |
| **C. Remain BLOCKED pending owner approval** | Leave provider resources unchanged during this review. The provider expiry still approaches; this state does not preserve the database and does not mean the owner accepts expiry or data loss. | No cost or recovery claim is made. If no decision is made, access may end at expiry and data may later be deleted under provider policy. | **Current fail-closed review disposition only; not an owner-selected data path.** |

No option is selected by this task. In particular, the prior classification of data as disposable and the earlier planning approval do not authorize retirement, upgrade, backup/export, migration, or intentional expiration.

## Owner sign-off required for either action path

Before any future live change, the owner must approve a separate, exact-scope action record that states:

1. **Exact resources:** database `devobs-ai-staging-db` (`dpg-dbm5msu1egvs73be46og-a`) and affected service `devobs-ai-staging` (`srv-dbm5msu1egvs73be46lg`). Recheck provider metadata immediately before action.
2. **One intended action:** preserve access/data, explicitly retire/delete, or separately acknowledge provider expiry. “Remain blocked” is not consent to expiry.
3. **Impact:** accountable confirmation of actual data classification, external and application consumers, retention duties, and expected service/readiness effects—without sharing rows or secrets.
4. **Costs:** exact plan and destination costs, fees/taxes, budget owner, and an enforceable limit. No paid activation is authorized by this record.
5. **Recovery:** approved backup/restore destination and tested recovery for preservation, or explicit acceptance of irreversible loss and lack of rollback for retirement.
6. **Execution binding:** current reviewed repository SHA, named operator, and exact UTC execution window before the expiry deadline; any provider or source mismatch means stop.

## Guard and current limits

The existing offline [`check_render_free_expiry.py`](../../scripts/check_render_free_expiry.py) reads only [`render-free-expiry-snapshot.json`](render-free-expiry-snapshot.json); it is not a provider probe. `REVIEW_REQUIRED` (exit 1) means a human decision is needed. `STALE_INVENTORY` (exit 1) means the snapshot is too old to rely on. Neither is production readiness or permission to act. This task does not add another checker or refresh the snapshot.

No database rows, credentials, connection strings, environment values, backups, or customer data were accessed. No resource was exported, migrated, upgraded, deleted, suspended, replaced, reconfigured, or deployed. P01 remains **NO-GO / BLOCKED**, AI-9 remains **BLOCKED**, and Codex runtime remains **OPEN**.

**Final status: PENDING HUMAN APPROVAL.** Keep Issue #713 open until a separate owner decision and any later independently verified outcome are recorded.

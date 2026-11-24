# Render Free PostgreSQL Retirement Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking. **This plan authorizes planning only, not resource changes.**

**Goal:** Prepare a reviewable, no-cost retirement decision for the existing disposable Render Free PostgreSQL database before its reported expiration without deleting, disabling, migrating or replacing it now.

**Architecture:** This is a non-executable, fail-closed owner decision plan. Reuse the existing read-only metadata checkpoint and offline expiration guard; require verified dependency and data-impact checks, a separate exact-resource/date owner execution authorization, then a separate execution review. Retiring a database does not make P01 staging production-ready.

**Tech Stack:** Render Free PostgreSQL 17 (Frankfurt); existing Python 3.12/3.15 offline tests; Render Blueprint `render.yaml`; GitHub pull-request and CI governance.

## Global Constraints

- **VERIFIED owner direction (2026-11-19):** Prepare a retirement plan for **`devobs-ai-staging-db`**, but **do not delete it now**. This is a planning authorization, not permission for outage, database access, data removal, automatic expiration acceptance, service suspension, backup/export, provider changes, or paid activation.
- Source baseline: GitHub `main` at `ceda79a10a68b4f6ce4a81653ea6c7606067bd01`; this plan must be reassessed if a future source SHA or provider inventory differs.
- **VERIFIED read-only Render inventory, 2026-11-19:** existing database `devobs-ai-staging-db`, database resource ID `dpg-dbm5msu1egvs73be46og-a`, **Free / available**, PostgreSQL 17, Frankfurt, expiration `2026-12-05T10:33:24.202776Z`; associated web service `devobs-ai-staging`, resource ID `srv-dbm5msu1egvs73be46lg`, Free, Frankfurt, `main` branch, auto-deploy off. Resource inventory is **not** a live connection or consumer audit.
- **VERIFIED source:** [`render.yaml`](../../render.yaml) still declares one staging database named `devobs-ai-staging-db` and one web service. A future Blueprint import may attempt resource creation; do **not** re-import it, edit deployment configuration, or remove the declaration as part of this planning PR. The source does not independently prove the live app uses the database.
- **VERIFIED historical owner statement:** [Render staging runbook](../RENDER_OPENAI_STAGING_RUNBOOK.md) dated 2026-11-18 classifies the current rows as **synthetic/disposable**, with no current-content preservation requirement. Actual row contents, legal/retention obligations, external consumers and whether any other owner depends on this database are **UNVERIFIED**; do not inspect rows to fill that gap under this authorization.
- **VERIFIED published provider policy:** [Render Free](https://render.com/docs/free) documents 30-day expiry, loss of free access after expiry, a 14-day upgrade-only grace period, eventual provider deletion, and no Free backups. [Render Postgres backups](https://render.com/docs/postgresql-backups) confirms no provider-managed Free recovery. [Delete Postgres API reference](https://api-docs.render.com/reference/delete-postgres) calls deletion irreversible. **No destructive API or dashboard action is authorized here.**
- Follow [`AGENTS.md`](../../AGENTS.md): never push directly to `main`, weaken CI/security, use/inspect secrets, contact production, incur costs, or merge/deploy without separate exact-SHA-and-scope owner approval. No Cloud or GitLab synchronization. Leave **P01 BLOCKED/NO-GO, AI-9 BLOCKED, Codex runtime OPEN**.

## Expiry decision refresh — 2026-11-24 (no action authorized)

- **VERIFIED (GitHub):** this decision review uses `main` SHA `7f23f5635fecdbdc342dfaada259e4cc0c2adc3f`, merged from PR #775 head `e12915ea1f053b4c240c11170eb201e4db45d3d5`. Exact-head CI `45306060923`, merge-SHA CI `45355683819`, and merge-SHA Push on main `45355682459` succeeded.
- **VERIFIED (fresh, read-only Render metadata):** on 2026-11-24 the exact database remained Free/available, PostgreSQL 17 in Frankfurt, with the same provider expiry; the associated web service remained present on `main`, auto-deploy off and not suspended. These records do not establish a database connection or identify active consumers.
- The exact deadline is `2026-12-05T10:33:24.202776Z` (`2026-12-05 13:33:24.202776 Asia/Amman`, UTC+03:00). Issue [#713](https://github.com/hamedonassar95/Devobs/issues/713) still records planning approval only; this review does not authorize preservation, retirement or accepting expiry.
- Use the current [expiry decision matrix](../p01/RENDER_FREE_DB_EXPIRY_DECISION_2026-11-24.md) for the preserve / retire / remain-blocked choices, unresolved consumers, backup and retention evidence, cost uncertainty, and required exact-scope owner approval. The offline expiry guard is a human-review gate, not operational readiness.

---

## Acceptance matrix — decision before execution

| Gate | Current evidence | Required independent proof before future retirement | Status |
| --- | --- | --- | --- |
| Owner selected planning path | Explicit owner consent to **prepare** retirement plan, not delete | Planning scope recorded; no execute permission implied | **VERIFIED (planning only)** |
| Expiring Free resource identity | Read-only Render resource name/ID, plan, Frankfurt and provider expiry recorded above | Fresh metadata immediately before a separately authorized action must match the exact target | **VERIFIED (point-in-time)** |
| Disposable synthetic dataset | 2026-11-18 owner classification in runbook | Affected owner reconfirms there is no real/customer or legally retained data, without sharing rows or credentials | **BLOCKED** |
| Service / external consumers | Root Blueprint defines both service and DB; latest hosted web deployment historically `update_failed` with OIDC config failure | Non-secret inventory and accountable owners confirm no active consumers/dependents; identify outage/ingress implications | **BLOCKED** |
| Recovery / rollback | Free tier has no managed backups; owner stated current rows need no preservation | Owner accepts irreversible data loss and documents response if future work depends on lost data; re-creating a DB is not restoring data | **BLOCKED** |
| Exact change approval | No resource-specific deletion/suspension authorization was granted | Separate authorization naming DB resource ID, action, UTC time/window, repository SHA, affected service, and irreversible consequences | **BLOCKED** |
| P01 activation | Existing evidence and gate remain NO-GO | Independent identity, RLS, TLS, spend, recovery and release approvals; **outside** this plan | **BLOCKED** |

### Task 1: Document dependency and data impact without touching the database

**Files:** Existing `render.yaml`, `docs/RENDER_OPENAI_STAGING_RUNBOOK.md`, `docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md`, `docs/p01/render-free-expiry-snapshot.json`; proposed **separate** future sign-off attachment to issue [#713](https://github.com/hamedonassar95/Devobs/issues/713).

**Interfaces:** Consumes only the sanitized resource inventory and repository configuration already documented. Produces an owner-reviewed *dependency and retention checklist* with evidence links (no connection strings, row data or network access).

- [ ] Confirm with the accountable service owner that `devobs-ai-staging` and any external project have **no necessary read/write dependency** on the temporary database. Source YAML alone is not proof.
- [ ] Reconfirm that current data are entirely disposable synthetic fixtures, with no customer/regulated/third-party data or retention duty; record **attestation only**, not sample rows.
- [ ] If dependencies, responsibility, or retention classification are uncertain, record **BLOCKED** and keep the database unchanged. Do not assume that the historical failed deployment establishes zero consumers.
- [ ] Run existing offline evidence checks from a trusted repository checkout: `python3 scripts/check_render_free_expiry.py --json` (expected `REVIEW_REQUIRED`, exit `1` while within 30 days and snapshot fresh, or `STALE_INVENTORY`, exit `1` after seven days). Run `python3 -m unittest discover -s tests -p 'test_render_free_expiry.py' -v` (expected all tests pass). These checks are **not** provider probes or authorization to retire.

### Task 2: Prepare the separately approved retirement action review

**Files:** Existing issue [#713](https://github.com/hamedonassar95/Devobs/issues/713) for decision history; this plan for guardrails. No executable scripts, service definitions, or deployment manifests should be changed during planning.

**Interfaces:** Consumes signed Task 1 impact outcome plus fresh non-secret provider inventory. Produces a separate **owner execution decision** tied to one action, target resource ID and a UTC window; an unsigned plan is never executable authority.

- [ ] Propose an explicit UTC action date **before `2026-12-05T10:33:24.202776Z`** and state expected web-service impact. The owner chooses the date; no default deletion or suspension is scheduled.
- [ ] Record one intended future path: **reviewed explicit retirement** versus **deliberately allowing provider expiration**; neither may be selected through silence. For expiration, require the same acknowledgement of access loss and eventual irreversible data removal.
- [ ] Obtain separate approval naming resource `dpg-dbm5msu1egvs73be46og-a`, associated web service `srv-dbm5msu1egvs73be46lg`, action, date/window, exact then-current GitHub SHA, impact, zero-paid-resource boundary, and irreversible data-loss acceptance.
- [ ] If required evidence or consent is absent by the decision deadline, report `BLOCKED / NO-GO` rather than bypassing a check, spending funds or assuming expiration is approved.

### Task 3: Execute only in a separate, later owner-authorized session

**Files:** No repository application, IAM, Blueprint, database migration or secrets may change under **this** plan-only PR. Any future code/Blueprint cleanup requires a separately reviewed feature branch, tests and PR.

**Interfaces:** Consumes Task 2 exact-scope approval and an independent current provider check. Produces sanitized proof of the authorized operation (or a documented **no-action** result), not a P01 GO claim.

- [ ] **STOP:** no database deletion, service stop, export, credential access, migration, upgrade, provider API write or deployment is included in this task's present authorization.
- [ ] In a **future** explicitly approved operation, a trusted operator reconfirms exact resource ID, dependencies, retention, irreversible nature and provider state before choosing any action. Abort on mismatch or unavailable evidence.
- [ ] After any later authorized action, independently document actual provider state and whether the related web service has lost DB functionality. A successful provider delete is not a healthy app check.
- [ ] Only then assess a **separate** Blueprint/source cleanup PR: `render.yaml` must not be re-imported as-is and accidentally reprovision the retired resource. Keep existing blueprint tests until that separate source change is proposed and verified.

### Task 4: Review rollback limits and closeout criteria

**Files:** Future review outcome to issue [#713](https://github.com/hamedonassar95/Devobs/issues/713) and `STATE.md`/ledger only if an independent approved PR later completes.

**Interfaces:** Consumes independently confirmed post-action evidence. Produces an audit trail with action/no-action, approval, observed outcome and residual work. No automated rollback exists.

- [ ] **Before irreversible deletion:** cancellation means leaving the resource untouched. For required retained data, return to a new, separately authorized preservation plan; do not invent a backup.
- [ ] **After irreversible deletion/provider expiration:** do **not** claim rollback by recreating a fresh empty Free database. Reprovisioning, connection changes and restored records all require new approvals and are **not** part of this plan.
- [ ] Keep issue #713 **open** until the approved path, outcome, downstream effects and follow-up source changes are independently verified; label unknown outcome **BLOCKED**, not complete.
- [ ] Keep P01, AI-9 and Codex runtime gates unchanged. No automatic deployment, schedule or billable inference is authorized by plan approval.

## Verification of this plan-only change

Run on the exact proposed PR head:
```sh
python3 scripts/check_render_free_expiry.py --json
python3 -m unittest discover -s tests -p 'test_render_free_expiry.py' -v
python3 -m unittest discover -s tests -p 'test_render_free_staging_blueprint.py' -v
python3 -m unittest discover -s tests -v
git diff --check
```
The first command is **expected to exit 1** with `REVIEW_REQUIRED` on the reviewed fresh snapshot, not because of a test failure; if the snapshot ages it may return `STALE_INVENTORY`. All unit tests and existing CI/security checks must pass before declaring this documentation PR ready for owner review. **No provider operation occurs.**

## Unresolved decisions (not delegated to an agent)

1. Whether every potential data consumer is free of reliance on this DB, and who confirms that.
2. The future exact retirement or expiration-acceptance action and UTC date/window.
3. The owner’s separately signed, exact-resource/exact-SHA approval to cause or intentionally accept irreversible loss, **not granted here**.

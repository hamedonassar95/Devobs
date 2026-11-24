# Repository and Database Consolidation Baseline

**Review date:** 2026-11-24

**Canonical repository:** [`hamedonassar95/Devobs`](https://github.com/hamedonassar95/Devobs)

**Branch/base:** `feature/ops-ai-database-consolidation-map` from `cb73695864fdbeb467b37f23ac9146da65768e63`
**Scope:** Read-only source review and consolidation planning. No live database records, secrets, cloud settings, or customer data were accessed.

The machine-readable inventory is [`repository_database_map.json`](repository_database_map.json). Its status values are `VERIFIED`, `UNVERIFIED`, `BLOCKED`, and `PLANNED`. “Verified” means verified from the cited repository snapshot, task-provided resource baseline, or recorded provider checkpoint; it does not imply live connectivity.

## Executive result

- **VERIFIED:** The AI Intelligence source was imported into the Devobs console at the source SHA recorded in the [consolidation record](../../apps/ai-intelligence-console/CONSOLIDATION.md), through merged PR #565. The original source remains a separate read-only repository.
- **VERIFIED:** `ops` and `DevObs-ai-Intelligence-` have extensive content overlap, but GitHub does not identify `ops` as a fork, their local histories have different roots and no merge-base, and the direction/provenance of copying is **UNVERIFIED**.
- **VERIFIED:** Legacy Firebase source configuration contains `projectId = my-apps-hamedo` and `firestoreDatabaseId = ai-studio-promptpal-f1b3ebe9-9826-4fca-9a67-b5376e8669b3`. This is a **VERIFIED SOURCE LINK**, not proof of live access, deployed rules, project ownership, or an active application connection.
- **VERIFIED:** Canonical Devobs keeps Firebase disabled unless explicitly enabled and the console Firestore rules deny all access. Those source controls remain unchanged.
- **VERIFIED:** A Render staging web service and PostgreSQL 17 Free resource are recorded in the dated provider checkpoint. The service-to-database attachment is **UNVERIFIED**. The Free database expiry is recorded as 2026-12-05.
- **VERIFIED:** `devobs-saas` is a distinct Next.js + Prisma + PostgreSQL codebase with organization/tenant checks and PostgreSQL RLS in source. Its physical database provider and any relation to Render staging are **UNVERIFIED**.
- **BLOCKED:** Phone Repair Assistant/Supabase data must remain isolated. That project was not inspected, and no Devobs attachment is authorized by this review.

## Repositories and source comparisons

| Repository | Reviewed ref | Verified facts | Unknowns |
|---|---|---|---|
| [Devobs](https://github.com/hamedonassar95/Devobs/tree/cb73695864fdbeb467b37f23ac9146da65768e63) | `cb73695864fdbeb467b37f23ac9146da65768e63` | Canonical repository and imported console. Root rules and feature flags are source evidence. | No live Firebase access or database relationship was tested. |
| [ops](https://github.com/hamedonassar95/ops/tree/57360d6a6c706d7433ac776a27c82dedd493e31a) | `57360d6a6c706d7433ac776a27c82dedd493e31a` | Repository identity and tree are verified. It has 67 identical shared blobs, 5 changed shared paths, 37 ops-only paths, and 1 AI-source-only path versus the AI source snapshot. | Its provenance relative to the AI source is unknown; no fork parent or common Git ancestor was found. |
| [DevObs-ai-Intelligence-](https://github.com/hamedonassar95/DevObs-ai-Intelligence-/tree/61e4297545c60ebcda77a4c1a1f793c7e9a20347) | `61e4297545c60ebcda77a4c1a1f793c7e9a20347` | This is the recorded source snapshot imported by PR #565. | The current source tree is not identical to the imported console. |
| [devobs-saas](https://github.com/hamedonassar95/devobs-saas/tree/a0889dce0785cbe96cd78233ecadbe4163df805a) | `a0889dce0785cbe96cd78233ecadbe4163df805a` | Separate Next.js, Prisma, PostgreSQL architecture and tenant-aware application source. | Database host, live schema state and relation to Render staging are not verified. |

Comparison counts are computed from the trees at the reviewed refs. `ops` vs AI source: shared changed paths are `README.md`, `scripts/repository_dispatch.mjs`, `server.ts`, `src/components/github/GitHubTab.tsx`, and `tests/repository_dispatch.test.mjs`. The 37 `ops`-only paths are 36 `.agents` files plus `docs/graphify-local.md`; the AI source-only path is `package-lock.json`.

The AI source vs imported console has 39 identical shared blobs, 30 changed shared paths, 4 source-only paths, and 29 console-only paths. `ops` vs imported console has 37 identical shared blobs, 31 changed shared paths, 41 ops-only paths, and 30 console-only paths. These figures describe tree similarity, not permission to overwrite or merge code.

### `ops` differences and import disposition

**VERIFIED, unsafe to import as-is:**

- The `GitHubTab` adds personal access token entry, token testing, direct push, branch selection and a force-push control. The matching `server.ts` endpoints accept a PAT and construct Git commands for add/commit/push; the push path supports `--force` and embeds the PAT in an authenticated remote URL. Do not import this UI or backend functionality.
- The `repository_dispatch.mjs` and its workflow add dispatch behavior; the reviewed `ops` version targets the canonical Devobs repository from within the related codebase. Do not import this dispatch workflow or its credentials/permissions.
- The legacy `firestore.rules` contains `allow read: if isSignedIn() || true` on `servers`, `incidents`, and `deployments`, making those reads public, plus authenticated writes checked only for an ID shape, without tenant or owner authorization. Never import or publish these rules.
- The `ops` root workflows include CI/deployment/dispatch behavior. The canonical root CI and release gates are independently governed; do not copy old workflow files.

**Later candidates — `PLANNED`, not approved imports:**

- A future isolated review may extract visual-only dashboard presentation changes from the five changed shared files after proving the extraction contains no PAT handling, direct Git mutation, force-push, dispatch, credential use, or deployment action. No current `ops` functional delta is verified safe to import unchanged.
- The local Graphify note and agent skill files may be compared for non-duplicative documentation only. Devobs already has canonical operating instructions and repository-intelligence material; deduplication is required before any documentation import.

## Database and authorization map

| Resource / relationship | Status | Evidence and limits |
|---|---|---|
| Legacy Firebase project `my-apps-hamedo`, Firestore database `ai-studio-promptpal-f1b3ebe9-9826-4fca-9a67-b5376e8669b3` | **VERIFIED SOURCE LINK**; live state **UNVERIFIED** | The identifiers occur in the legacy applet Firebase configuration in both source trees. They do not prove current deployment, access, or rule state. No live API was called. |
| Canonical console Firebase integration | **VERIFIED** | `firebaseApp.ts` requires `VITE_FIREBASE_ENABLED === 'true'` and configured values before initialization. Firebase is disabled by default. Current canonical `firestore.rules` is deny-all. Demo dashboard records stay in React state/local storage and do not call Firestore persistence. |
| Render service `devobs-ai-staging` | **VERIFIED from checkpoint** | [`P01_PROVIDER_CHECKPOINT_2026-11-23.md`](../p01/P01_PROVIDER_CHECKPOINT_2026-11-23.md) records a Free Frankfurt web service, auto-deploy off, and last deploy state `update_failed` on 2026-11-14. This task did not re-query Render. |
| Render PostgreSQL resource `devobs-ai-staging-db`, logical DB `devobs_ai_staging`, PostgreSQL 17, Free | **VERIFIED from checkpoint and supplied baseline** | The checkpoint records provider resource metadata; the supplied verified baseline provides the logical name. Free expiry: **2026-12-05**. No records were read. |
| Render service → PostgreSQL attachment | **UNVERIFIED** | Resource names existing in a checkpoint do not prove the service currently connects to that database or that a connection is healthy. |
| `devobs-saas` PostgreSQL | Application/database technology **VERIFIED**; physical host **UNVERIFIED** | `prisma/schema.prisma` declares PostgreSQL and `DATABASE_URL`/`DIRECT_URL`. Environment values were not read. The SaaS DB must not be assumed to be Render staging. A source deployment plan mentions Neon Free as a candidate, but no Neon resource is verified. |
| Phone Repair Assistant / unrelated Supabase projects | Project identity **UNVERIFIED**; attachment **BLOCKED** | Out of scope and not inspected. Keep these project/data boundaries separate; do not attach their data to Devobs. |

### Tenant and access-control notes

**VERIFIED in `devobs-saas` source:** Organization and membership models exist. `src/lib/tenant/access.ts` exposes tenant context and permission checks, tenant-scoped query/create/update helpers, and transaction-local PostgreSQL RLS context. Resource handlers use tenant filters for list/get/update/delete. RLS migrations enable and force RLS. Unit tests cover missing membership, role permissions, transaction context and cross-tenant access cases. These are source and test assertions; they are not proof that a hosted database has those migrations applied or that production access controls are configured.

**VERIFIED in legacy Firebase source:** Public reads and unscoped authenticated writes create a cross-tenant and information-disclosure risk. This finding concerns legacy source rules only. Whether those rules were ever published or remain deployed is **UNVERIFIED**.

## Canonical boundaries to preserve

1. Keep the current Firebase-disabled-by-default feature gate.
2. Keep canonical Firestore rules deny-all until a separately reviewed authorization contract exists.
3. Do not copy legacy public-read or unscoped-write rules into Devobs.
4. Keep SaaS PostgreSQL, Render staging, legacy Firestore, and unrelated Supabase projects as separate data domains unless schema, ownership, backups, and explicit approvals establish an intentional relationship.
5. Do not import old deployment workflows, PAT UI, direct GitHub push/force-push, or repository-dispatch execution.
6. Do not merge databases, run migrations, activate Firebase, publish rules, or change infrastructure as part of this baseline.

## Ordered migration strategy

Each item is **PLANNED** and requires a separate reviewable change:

1. **Reconcile safe `ops` source differences.** Compare file-by-file with canonical Devobs. Extract only narrowly scoped, side-effect-free candidates; keep the unsafe capabilities listed above excluded.
2. **Validate authentication and ownership.** Define identity, tenant membership, ownership, role permissions, and fail-closed behavior before designing any shared persistence path.
3. **Inspect schemas and backups.** Obtain approved, read-only schema metadata, retention/backup coverage and recovery evidence for each candidate database. Do not read customer rows or secrets for this baseline.
4. **Build a guarded integration adapter.** Require explicit provider selection, read-only assessment and dry-run defaults, typed boundaries, audit events, and human approval before any write-capable operation.
5. **Test with synthetic data.** Exercise tenant isolation, unauthorized reads/writes/deletes, rollback paths, and provider failure cases in local emulators or disposable test environments.
6. **Request human approval before activation.** Any live connection, data movement, rules change or migration requires owner review of the exact implementation, destination, rollback, and backup evidence.

## Validation and deployment observation

The base `cb73695864fdbeb467b37f23ac9146da65768e63` has successful recorded validation, CodeQL, and security check runs; docs-only matrix jobs were skipped. At the reviewed base, Vercel Git deployment is disabled in repository configuration and production Pages release is guarded by manual dispatch on `main`, explicit confirmation, and successful validation. The feature branch has not yet been pushed, so there is no feature-SHA deployment-history result at this stage. No deployment or cloud operation was triggered during source inspection.

Exact final-commit CI/CodeQL and read-only Vercel deployment history must be reported after the branch is pushed and a Draft PR is created. A missing status is not a pass.

## Evidence links

- [Canonical Firebase initializer](../../apps/ai-intelligence-console/src/services/firebaseApp.ts)
- [Canonical deny-all Firestore rules](../../apps/ai-intelligence-console/firestore.rules)
- [Canonical console consolidation record](../../apps/ai-intelligence-console/CONSOLIDATION.md)
- [Legacy ops rules at reviewed source ref](https://github.com/hamedonassar95/ops/blob/57360d6a6c706d7433ac776a27c82dedd493e31a/firestore.rules)
- [Legacy ops PAT/push endpoints at reviewed source ref](https://github.com/hamedonassar95/ops/blob/57360d6a6c706d7433ac776a27c82dedd493e31a/server.ts)
- [Legacy ops GitHub UI at reviewed source ref](https://github.com/hamedonassar95/ops/blob/57360d6a6c706d7433ac776a27c82dedd493e31a/src/components/github/GitHubTab.tsx)
- [SaaS Prisma schema at reviewed source ref](https://github.com/hamedonassar95/devobs-saas/blob/a0889dce0785cbe96cd78233ecadbe4163df805a/prisma/schema.prisma)
- [SaaS tenant authorization implementation](https://github.com/hamedonassar95/devobs-saas/blob/a0889dce0785cbe96cd78233ecadbe4163df805a/src/lib/tenant/access.ts)
- [SaaS tenant authorization tests](https://github.com/hamedonassar95/devobs-saas/blob/a0889dce0785cbe96cd78233ecadbe4163df805a/src/lib/tenant/access.test.ts)

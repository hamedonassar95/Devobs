# P01 Render Free resource checkpoint — 2026-11-15

**State:** READ_ONLY / NO-GO. **Scope:** existing Render `My Workspace` free-tier staging resources; not a production, billing, data-retention, security or live-API acceptance test. This is a sanitized operator-side snapshot collected through the connected Render read-only inventory, deployment and event views. No resource settings, credentials, logs, environment variables or customer data were read or changed.

## Verified provider inventory (2026-11-15 UTC)

| Surface | Read-only observation | Evidence boundary |
| --- | --- | --- |
| Staging web service | `devobs-ai-staging` exists on Render **Free**, Frankfurt region, connected to the Devobs `main` branch; automatic deployment is **off**; its configured health-check path is `/readyz`; service record is **not_suspended** | A service record and configured health path do not prove that an application process is running, authenticating users or responding successfully. The web ingress configuration permits public network access; no live authenticated access test was performed. |
| Latest deploy | Revision `1f1fd774f02579a500c07bd667865e51ed187948` (historical PR #616) was deployed on **2026-11-14**; **build succeeded** but deploy finished **update_failed** with event showing process `nonZeroExit=1` | Event metadata does not independently prove the exact configuration-error root cause. No raw logs, secret-bearing environment values or application requests were inspected. |
| Earlier deploy | Revision `5b75be633b4fd5c797d9e4fdc1e960fd0d68e07e` from **2026-11-05** also finished **update_failed**; its build succeeded and its process exited nonzero | Neither deploy establishes a healthy `/readyz` endpoint or a successful hosted API release. |
| Staging PostgreSQL | `devobs-ai-staging-db`: **Free**, PostgreSQL **17**, Frankfurt; provider reports **available**, without replicas, with a restricted temporary migration IP allowlist | Availability of a DB resource does not verify a successful application connection, database-level TLS, restricted runtime identity, actual hosted RLS, backup policy or tenant isolation. Do not publish the allowlisted IP or database credentials. |
| Free PostgreSQL expiry | Render reports `expiresAt=2026-12-05T10:33:24.202776Z` | **Action deadline, not a deletion instruction.** No upgrade, automatic renewal, backup migration, retention guarantee or safe recovery was verified. |

**VERIFIED GitHub baseline:** [PR #642](https://github.com/hamedonassar95/Devobs/pull/642) merged documentation at `2eaa2b094313dd99aeb95136cbe17c37a4e6119b`. Its exact-head [CI run 43753409287](https://github.com/hamedonassar95/Devobs/actions/runs/43753409287) finished successfully. The repository's automated AI review was **skipped** without spending approval; a separate Codex review reported that it did not complete. CI success is not human or model approval, and is not proof of P01 readiness.

## Decision required before 2026-12-05

The owner must explicitly choose an approved **Free-resource retention/retirement approach** before the reported expiry date. Options for review are to retain the current temporary DB only within the provider's actually verified Free terms, or to plan an explicitly authorized retirement after checking whether any data must be preserved. **No default action is selected.** Do not delete, renew, upgrade, migrate, trigger hosted deploys, run chargeable backups, or alter access lists without a new scope-specific approval and a retention/recovery assessment.

**Blocking constraints stay unchanged:** The owner requires a provider-enforced **all-in USD 100/month** spending cap covering compute, storage, backups, usage, fees, taxes and model inference; existing [budget evidence](P01_RENDER_BUDGET_ENVELOPE.md) does not establish it. P01 **BLOCKED / NO-GO**, AI-9 **BLOCKED**, and Codex runtime acceptance **OPEN**. Hosted identity/OIDC, verified TLS/CA/network restrictions, actual tenant-denial tests, safe backup/isolated restore and an accountable deployment approval remain separate gates.

## Safe next action

Review this checkpoint, independently verify the provider's current Free PostgreSQL expiry terms and account eligibility **without changing billing**, then obtain an explicit owner decision on retention vs retirement, the reviewed source SHA and any permitted one-time test. If the cost cap and required hosted controls cannot be proved, stop at **NO-GO**. Related checklists: [P01 activation readiness](P01_ACTIVATION_READINESS.md), [Render budget envelope](P01_RENDER_BUDGET_ENVELOPE.md), [2026 roadmap](strategy/DEVOBS_AI_ROADMAP_2026.md).

This record is evidence of *inventory at the inspection time*, not a promise of ongoing monitoring or a scheduled deletion.

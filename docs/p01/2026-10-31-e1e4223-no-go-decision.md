# Devobs P01 — current-main decision package (read-only snapshot)

**Decision: NO-GO / BLOCKED.** This is an independent review package, **not** an owner GO signature, release authorization, or provider attestation. Historical observation: **2026-10-30 UTC** (2026-10-31 local Jordan). Repository: `hamedonassar95/Devobs`. Inspected **main SHA `e1e4223ff9853109b66972e7ba997a81240f9639`**. Re-check main and CI before any later decision; this snapshot does not automatically update when main moves.

## Verified baseline and boundary

- **VERIFIED (GitHub API):** `main` resolves to the exact SHA above and is protected. The [exact-SHA CI run #41135588530](https://github.com/hamedonassar95/Devobs/actions/runs/41135588530) completed **success**, including `validate`, `security`, `postgres-rls`, `python-tests`, `node-tests`, `site-contract`, `container-build`, and `terraform-validate`. Static Pages publishing and `verify-production` passed in that same run. The baseline run predates this package; branch pushes can independently trigger CI and preview workflows. No manual workflow_dispatch was invoked.
- **VERIFIED (pinned repository sources):** [AGENTS.md](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/AGENTS.md) requires fail-closed evidence, human approval, small reviewable changes, no secrets and no unapproved deployments; [STATE.md](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/STATE.md) records P01 NO-GO and AI-9 FAIL. The [P00–P12 roadmap](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/docs/plans/2026-10-26-devobs-production-execution-roadmap.md) records **P00 owner GO only; P01–P12 BLOCKED**. The [P01 activation document](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/docs/P01_ACTIVATION_READINESS.md) explicitly records **owner-signed conditional P01 NO-GO**. The P00 GO is not permission for P01.
- **VERIFIED scope limit:** The healthy deployment is a static site, not a live tenant-isolated SaaS API. The existing P01 evidence checker can establish *structural completeness only*, not independent authenticity; the tracked `docs/p01/evidence.json` is an older SHA and all seven controls are `UNVERIFIED`. It must not be silently rebased or relabeled VERIFIED.

## Acceptance matrix — all seven P01 gates remain blocked

| Gate | Status | Evidence that exists | Required proof still unavailable |
| --- | --- | --- | --- |
| Owner authorization | **BLOCKED** | P00 owner GO and conditional P01 NO-GO are recorded in the roadmap, P00 and P01 decision documents. | New scoped provider/region/account approval and an independent P01 GO after all prerequisites; earlier conditional approval does not authorize provisioning. |
| Provider and region | **BLOCKED** | [Railway evidence](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/docs/P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md) records Railway rejection for this budget; [AWS region mapping](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html) assigns a Jordan new-experience contact address to Stockholm `eu-north-1`. | Selected eligible provider/account, owner-accepted region, verified residency terms, authorized synthetic-data environment. No AWS account or authorization is established. |
| **All-in USD 100/month hard limit** | **BLOCKED — first blocker** | [Railway official limits](https://docs.railway.com/pricing/cost-control) separate Compute and Agent. Repository-reported 2026-10-30 Railway support reply says ongoing storage/backup billing and no guaranteed max overrun. [AWS official spend limit](https://docs.aws.amazon.com/accounts/latest/reference/create-spend-limit.html) is **pre-tax project cost**, not a proven total invoice limit. | Verified automatic enforceable **combined invoice** ceiling covering compute/AI agent, DB, volumes, PITR/backups, bandwidth, logs, subscription, taxes and all other charges; no unbounded overrun or charge after shutdown. Alerts and compute-only tests are not substitutes. |
| OIDC / JWKS identity | **BLOCKED** | Auth0 proposal and local token/security tests documented in P01; verifier validates supplied metadata, not a real discovered authority. | Owner-selected IdP/issuer/audience/client, origin-validated JWKS lifecycle, revocation/rotation and live positive/negative token evidence. |
| PostgreSQL RLS / tenant isolation | **BLOCKED** | [RLS design](https://github.com/hamedonassar95/Devobs/blob/e1e4223ff9853109b66972e7ba997a81240f9639/docs/POSTGRES_RLS_STAGING.md) and disposable-Postgres CI suite; six-call synthetic smoke tests. | Hosted restricted non-owner/non-BYPASSRLS runtime role, verified grants/FORCE RLS, cross-tenant denial including same-project-name case and denied writes against authorized synthetic staging. |
| Backup / restore / operations | **BLOCKED** | Owner proposals: encrypted backups, **7-day retention**, **RPO 24h**, **RTO 24h**, health and shutdown conditions. | Evidence of actual backup, successful isolated restore, measured RPO/RTO, monitored recovery/incident and rollback practice. |
| Release approval | **BLOCKED** | P01 document records no independent approver available and owner acceptance *for synthetic scope only*. | Fresh owner decision tied to exact accepted P01 evidence, approval policy and current SHA; no automatic GO. |

**Evidence confidence distinction:** GitHub's exact-SHA source and CI outcomes are directly VERIFIED. The cited Railway support email contents and owner textual P01 signature are **REPO-REPORTED**, not independently authenticated here; no private mailbox, provider account, runtime, secret, or billing console was accessed. Absence of runtime proof is **UNVERIFIED**, not proof that a provider service does or does not exist.

## Exact decision and non-actions

**NO-GO is final for this reviewed main SHA.** No provider has demonstrated the complete USD 100 invoice ceiling. Even a suitable spend policy alone could not clear identity, live RLS, backup/restore and fresh owner signoff. Neither CI nor a GitHub Pages green release promotes P01. P02–P12 remain blocked by the sequential roadmap, and AI-9 remains FAIL.

**Single next owner decision (P01-NEXT-01):** Authorize **only a written, no-account/no-resource/no-spend clarification request to AWS** concerning all-in ceiling, excluded charges, maximum overrun, Stockholm data residency, and applicable fees/taxes **or retain AWS unselected with P01 NO-GO**. This is a request for a decision, not authorization to send it now. Even approving the inquiry does not permit any spend, account creation, deployment, or P01 GO.

## Repeatable verification (reviewer commands; read-only)

From a checkout of this review branch (the historical SHA is the evidence anchor, not this branch HEAD):

```sh
python3 -c "import json; print(json.load(open('docs/p01/2026-10-31-e1e4223-acceptance-matrix.json'))['observed_main_sha'])"
python3 -m unittest discover -s tests -p 'test_p01_decision_packet.py' -v
python3 -m unittest discover -s tests -p 'test_p01_evidence.py' -v
# EXPECTED FAIL-CLOSED (exit 1): historical evidence sample is for an older SHA.
python3 scripts/check_p01_evidence.py --file docs/p01/evidence.json --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639
```

Existing CI results are linked above; tests in this package prove **matrix consistency and conservative statuses only**. They cannot validate provider configuration, owner signature, paid service, authenticated JWT, live RLS or restoration.

## Change-control disposition

This package consists of a Markdown decision, a machine-readable seven-gate matrix and offline regression tests only. No existing files, application, CI workflows, secrets, environments or `main` are modified by the package. Treat a future main SHA as a new evidence baseline, not as proof that these historical findings automatically remain current.

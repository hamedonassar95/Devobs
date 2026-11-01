# Devobs production readiness — current evidence

## Superseding snapshot — 2026-11-01

The dated assessment below records the repository state on 2026-10-29. The current `main` revision is `122f23149c15da6d855b7606dd1eba3161b804d9` (merged PR #354); this snapshot supersedes statements below that conflict with later source evidence. PR #354's exact-head CI, CodeQL, Advanced Security, and post-merge main CI/site verification passed on 2026-11-01. Its PR-preview Vercel status and post-merge Vercel status failed with the build-rate-limit upgrade link.

- **AI-9: FAIL / BLOCKED.** The synthetic v2 evaluator is now present at [`scripts/ai_intelligence/ai9_synthetic_evaluation_v2.mjs`](../scripts/ai_intelligence/ai9_synthetic_evaluation_v2.mjs), with synthetic results and pre-registration documents in `docs/`. Its existence and synthetic runs do not prove independent real-world quality or authorize production. The independent v3 frozen seeds remain unrun pending separate approval.
- **P01: NO-GO / BLOCKED.** No enforceable all-in monthly spend cap, live identity, hosted tenant isolation, or restore evidence is established. No staging service is authorized.
- **Codex agent runtime: OPEN.** Local Docs MCP configuration/registration checks pass but explicitly report runtime unverified. Specialist-agent discovery and execution in a trusted Codex runtime have not been verified.
- PRs [#342](https://github.com/hamedonassar95/Devobs/pull/342)–[#345](https://github.com/hamedonassar95/Devobs/pull/345) added offline contracts and preflight checks; none proves hosted API, live OIDC/RLS, or external project authorization.
- PR #349 recorded the merge evidence for PR #348 and synchronized this readiness snapshot. Main CI run [41352831133](https://github.com/hamedonassar95/Devobs/actions/runs/41352831133) published Pages and passed `verify-production`; main CodeQL run [41352830537](https://github.com/hamedonassar95/Devobs/actions/runs/41352830537) passed. Vercel remained rate-limited on the PR and merged main SHA; no account settings were changed.
- PR #350 recorded the merge evidence for PR #349 and synchronized this readiness snapshot. Main CI run [41353315577](https://github.com/hamedonassar95/Devobs/actions/runs/41353315577) published Pages and passed `verify-production`; main CodeQL run [41353315286](https://github.com/hamedonassar95/Devobs/actions/runs/41353315286) passed. The PR-preview Vercel status was rate-limited, while Vercel on the merged main SHA succeeded; no account settings were changed.
- PR #351 recorded the merge evidence for PR #350 and synchronized this readiness snapshot. Main CI run [41354155904](https://github.com/hamedonassar95/Devobs/actions/runs/41354155904) published Pages and passed `verify-production`; main CodeQL run [41354155804](https://github.com/hamedonassar95/Devobs/actions/runs/41354155804) passed. Vercel was rate-limited on the PR and merged main SHA; no account settings were changed.
- PR #352 recorded the merge evidence for PR #351 and synchronized this readiness snapshot. Main CI run [41354676094](https://github.com/hamedonassar95/Devobs/actions/runs/41354676094) published Pages and passed `verify-production`; main CodeQL run [41354675758](https://github.com/hamedonassar95/Devobs/actions/runs/41354675758) passed. PR-preview Vercel was rate-limited, while Vercel on the merged main SHA succeeded; no account settings were changed.
- PR #353 recorded the merge evidence for PR #352 and synchronized this readiness snapshot. Main CI run [41354957688](https://github.com/hamedonassar95/Devobs/actions/runs/41354957688) published Pages and passed `verify-production`; main CodeQL run [41354957156](https://github.com/hamedonassar95/Devobs/actions/runs/41354957156) passed. Vercel was rate-limited on the PR and merged main SHA; no account settings were changed.
- PR #354 recorded the merge evidence for PR #353 and synchronized this readiness snapshot. Its CI [run 41355180888](https://github.com/hamedonassar95/Devobs/actions/runs/41355180888), CodeQL [run 41355178888](https://github.com/hamedonassar95/Devobs/actions/runs/41355178888), and Advanced Security [run 41355184888](https://github.com/hamedonassar95/Devobs/actions/runs/41355184888) succeeded on the exact PR head. PR CI skipped Node by path condition; push CI [run 41355170895](https://github.com/hamedonassar95/Devobs/actions/runs/41355170895) ran Node tests successfully. Main CI [run 41355453787](https://github.com/hamedonassar95/Devobs/actions/runs/41355453787) succeeded on the merge SHA, including Pages publication and `verify-production`; main security analysis [run 41355453093](https://github.com/hamedonassar95/Devobs/actions/runs/41355453093) succeeded. Vercel failed on the PR and merge SHA with the build-rate-limit upgrade link; account settings were not changed.

The current running history and exact merge evidence are maintained in [`STATE.md`](../STATE.md) and the milestone ledger.

**Assessment date:** 2026-10-29 UTC
**Repository:** `hamedonassar95/Devobs`
**PR #289 implementation merge commit:** `7fbc0c88fb3e0362c119dd9ddc2a03478753d33d`
**Merged PR:** [#289 — Prepare DevOps production-readiness safeguards](https://github.com/hamedonassar95/Devobs/pull/289)

## Decision

- **Static site:** VERIFIED. The post-merge CI run [40963935169](https://github.com/hamedonassar95/Devobs/actions/runs/40963935169) passed `validate`, published GitHub Pages, and passed `verify-production` for the merged revision.
- **AI-9:** **FAIL**, based on the owner-provided development-only synthetic report. Its source branch and files are not in this checkout or GitHub; the results have not been independently reproduced here.
- **P01 / full SaaS production readiness:** **NO-GO / BLOCKED**. There is no verified live API, hosted tenant database, authorized SaaS staging environment, operational recovery evidence, or owner decision for provider, region, budget, identity, and data handling.

## Completed readiness step

PR #289 merged at `7fbc0c8`. It added hash-locked Python dependencies, Trivy checksum signature verification, a single container image used for build/smoke/scan, bounded per-process API request/concurrency handling, and refreshed readiness documentation. The application image was scanned in CI but was not published to a registry; no SaaS API, cloud resources, secrets, or customer data were changed.

**PR verification:** CI run [40963695235](https://github.com/hamedonassar95/Devobs/actions/runs/40963695235) and the required CodeQL result passed on PR head `76fc18b`. Hosted Python validation ran **533 tests, 18 skipped, 0 failed**. Node, PostgreSQL RLS, Bandit, pip-audit, Gitleaks, Terraform, same-image Docker smoke/Trivy signature verification and scan, `validate`, and Vercel status passed. The first CI attempt exposed stale workflow-contract tests after consolidating the container job; those assertions were corrected and the rerun passed.

**Post-merge verification:** CI run [40963935169](https://github.com/hamedonassar95/Devobs/actions/runs/40963935169) passed on `main`, including **533 Python tests, 18 skipped, 0 failed**, `validate`, GitHub Pages publish, and production-site verification. CodeQL passed separately on `main` in run [40963934050](https://github.com/hamedonassar95/Devobs/actions/runs/40963934050). The verified deployment is the static site only.

## Remaining gates

1. **AI-9 quality — BLOCKED:** recover and review the exact diagnostic source/commit. Preserve the owner's report as owner-reported evidence; do not change the production detector or claim a new official evaluation.
2. **CI/container supply chain — COMPLETE for the merged revision:** current CI built, smoke-tested and scanned one image with signature-verified Trivy. No registry image was published.
3. **API, identity, and tenant boundary — PARTIAL / BLOCKED:** the API has local bounded request/concurrency controls, but needs approved provider/data scope, global gateway protections, load evidence, and authorized staging RLS validation.
4. **Operations and release approval — BLOCKED:** establish accountable SLO/on-call, alerting, tested backup restore and RPO/RTO, incident/rollback procedures, and legal/privacy/support readiness before a SaaS pilot.

Full findings and evidence limits are in [the production-readiness review](DEVOPS_PRODUCTION_READINESS_2026-10-29.md), the owner decision checklist is [P01 activation readiness](P01_ACTIVATION_READINESS.md), and the running project status is [STATE.md](../STATE.md).

**Current result: P01 NO-GO / BLOCKED.** Passing CI and a healthy static-site release do not establish readiness of the API or SaaS product.

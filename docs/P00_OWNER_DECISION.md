# Devobs P00 Owner Decision

## Purpose and scope

This unsigned record supports the repository owner’s decision to close **P00: repository governance and release safety**. It does not sign off automatically, establish production readiness, or authorize P01.

**VERIFIED baseline observation:** 2026-10-26 16:39 UTC; `main` was [`ae4edbdeb184232e62ace3308b32765f0cd8a02c`](https://github.com/hamedonassar95/Devobs/commit/ae4edbdeb184232e62ace3308b32765f0cd8a02c), merged PR #275. This is an immutable snapshot, not a claim that this SHA will remain current. **VERIFIED from workflow source:** a future document-only merge to main can trigger the existing Pages release; do not reuse the baseline below as the decision-time check.

## Evidence baseline

- **VERIFIED — main validation:** exact-SHA push run [40359244066](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066) passed [`validate`](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121700155568), [security](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892828), [Trivy](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892886), [PostgreSQL RLS](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892573), [site-contract](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892720), [container build](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892497) and [Terraform validation](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121699892743). Python and Node jobs were skipped for the documentation-only change. CodeQL Actions, Python and JavaScript/TypeScript passed in [run 40359243033](https://github.com/hamedonassar95/Devobs/actions/runs/40359243033). These checks establish CI outcomes for the baseline SHA, not later commits.
- **VERIFIED — static Pages:** [run 40359244066](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066) uploaded `validated-site-main-40359244066`; the normal [Pages publish job](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121700265575) downloaded and validated the same-run artifact, deployed it, and passed [production health verification](https://github.com/hamedonassar95/Devobs/actions/runs/40359244066/job/121700827306). The artifact metadata [for that workflow run](https://api.github.com/repos/hamedonassar95/Devobs/actions/runs/40359244066/artifacts) records expiry at 2026-11-02 16:27 UTC (seven-day retention). This is static-site evidence, not managed API/SaaS availability.
- **VERIFIED — current Vercel status at baseline:** combined commit status was success. This provider status does not show that Vercel consumed the Pages artifact, that bytes match, or that an API/SaaS is operational.
- **VERIFIED — control behavior in source:** production release is main-push-only after required `validate`; Pages checks the tested SHA and downloaded artifact manifest/layout before deploy; guarded rollback paths remain separate. Actions are SHA-pinned and job permissions are scoped. The effective [main branch rules response](https://api.github.com/repos/hamedonassar95/Devobs/rules/branches/main) requires PR and strict `validate`, blocks deletion/non-fast-forward, and reports `required_approving_review_count: 0` and `require_code_owner_review: false`. Its `pull_request` rule also reports `require_extra_approval_for_unattributed_changes: true`. Do not read the zero baseline count as proof that approval can never be required. **UNVERIFIED:** the precise conditions GitHub treats as unattributed changes and when the conditional flag requires an extra approval are not established by this response alone. See [GitHub's rules API documentation](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch).
- **VERIFIED — review record:** PR #275 merged without submitted human reviews. The advisory AI workflow skipped inference because explicit budget approval was absent. Neither merge status, automated checks, nor bot comments are a P00 phase decision.
- **VERIFIED — #273 disposition detail:** the historical [P2 partial-rerun thread](https://github.com/hamedonassar95/Devobs/pull/273#discussion_r4379203170) is still `unresolved` and `not outdated` in GitHub. Corrective code landed via [merged PR #274](https://github.com/hamedonassar95/Devobs/pull/274).

## Bounded P00 residuals for owner acceptance

- **UNVERIFIED:** no live partial “Re-run failed jobs” reproduction has been performed. Tests simulate artifact naming/overwrite behavior.
- **UNVERIFIED / risk to accept or mitigate:** concurrent full reruns can contend while replacing the same run-scoped artifact. Avoid concurrent full reruns unless a reviewed mitigation is added.
- **VERIFIED source/configuration:** the validated CI artifact is retained for seven days. It is a same-run handoff; no independent artifact signature is asserted.
- **UNVERIFIED:** GitHub Pages/CDN transformations after upload and byte-for-byte equivalence with Vercel’s independently staged output.
- **UNVERIFIED and outside P00 acceptance:** live managed staging, API/OIDC/JWKS behavior, production database tenant isolation, service uptime and commercial SaaS readiness. These belong to P01 and later acceptance.
- **VERIFIED governance constraint:** the effective rules response reports zero baseline approving reviews, Code Owner review disabled, and `require_extra_approval_for_unattributed_changes: true` on its `pull_request` rule. The flag is enabled; its exact triggering conditions are **UNVERIFIED** here. **UNVERIFIED:** traditional branch-protection details (403 to the current read identity) and external organization-level policy. The owner must decide whether this baseline and conditional review policy is sufficient; do not infer that every PR requires an approver or that no PR can require one.

## Decision-time verification required

Before choosing, the owner or authorized maintainer records the **actual latest `main` SHA** and checks the GitHub Actions run for that exact SHA. Confirm required `validate` success and the applicable security, Trivy, RLS, site-contract, build and Terraform results; if the main-push run published Pages, record its artifact validation and production health result. A missing, pending, failed, or mismatched check means **NO-GO until resolved**. Do not dispatch or rerun production workflows merely to complete this form.

At the same decision point, review the current effective ruleset and relevant PR states; explicitly consider both its zero baseline approval count / disabled Code Owner review and the enabled conditional unattributed-changes approval flag. Decide whether this review policy is acceptable; the flag's precise trigger semantics remain **UNVERIFIED** unless confirmed from authoritative GitHub documentation. Also decide whether to resolve or retain the #273 historical thread and accept or require mitigation for the partial-retry, concurrent-rerun, retention and post-upload byte-identity limitations. Record the selected option, actual main SHA and exact check-run URL in a human owner comment or reviewed decision record.

## Owner decision — leave blank until decided

Choose exactly one:

- [ ] **GO** — P00 repository release-governance evidence is sufficient, with no additional P00 residual accepted beyond the explicitly recorded boundaries.
- [ ] **GO with accepted bounded P00 residual risks** — list each accepted risk and reason below.
- [ ] **NO-GO** — list the unmet P00 gate or required remediation below.

**Decision-time main SHA:** ______________________________________________

**Exact required `validate` run URL and result:** ___________________________

**Applicable security / Trivy / RLS / site / release-health evidence:** ______

**Review policy accepted? Why? Include baseline approval count, Code Owner setting, and conditional unattributed-changes rule:** ___________

**PR #273 thread decision and retry/concurrency risk disposition:** __________

**Accepted residuals or NO-GO blockers:** __________________________________

**Owner identity:** __________________________  **UTC timestamp:** __________

**Human owner signature/approval reference:** ______________________________

## Explicit boundary of any P00 GO

A signed P00 GO approves **only repository governance and release-safety controls**. It does **not** approve P01 or create permission for a provider/account, region or residency, spend/quota, data/privacy/retention, identity provider, database, migrations, secrets, environments, cloud resources, production release/deployment, production API, commercial SaaS, or billable AI inference. P01 requires separate explicit owner authorization for provider, region, maximum spend/quota, privacy/data handling, IdP/JWKS, restricted database identity and live RLS isolation, backups and recovery before any resource is created.

**Current phase state until this form is completed and recorded:** P00 ACTIVE; P01–P12 BLOCKED.

## References

- [Canonical P00–P12 roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md)
- [P00 release-gate evidence](P00_RELEASE_GATE_EVIDENCE.md)
- [GitHub workflow runs REST API](https://docs.github.com/en/rest/actions/workflow-runs)
- [GitHub rules for a branch REST API](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)
- [GitHub rulesets and available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

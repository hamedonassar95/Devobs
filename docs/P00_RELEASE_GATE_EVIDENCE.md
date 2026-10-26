# P00 Release Gate Evidence and Owner Exit Checklist

**Evidence collected:** 2026-10-26 14:56 UTC
**Repository:** [hamedonassar95/Devobs](https://github.com/hamedonassar95/Devobs)
**Current main:** [`c0a5ca505d2f28a3f14c08fdaf4c9f3c8722c458`](https://github.com/hamedonassar95/Devobs/commit/c0a5ca505d2f28a3f14c08fdaf4c9f3c8722c458), merged from PR #270.

This is a timestamped P00 evidence snapshot, not a replacement roadmap or phase signoff. **VERIFIED (audit scope):** no secrets, environment values, deployment settings, provider accounts, billing or cloud resources were accessed.

## Current evidence

- **VERIFIED:** `GET /repos/hamedonassar95/Devobs` identifies `main` as the default branch. `GET /repos/hamedonassar95/Devobs/git/ref/heads/main` returned the SHA above. The latest matching push CI run, [40342897544](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544), completed successfully on that exact SHA. [Required `validate`](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121642341563), [security](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121642027561), [Trivy](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121642023591), [PostgreSQL RLS](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121642023709), Terraform, container build and site contract passed. Change analysis marked Python and Node suites not required and they were skipped. The separate CodeQL analysis [40342896917](https://github.com/hamedonassar95/Devobs/actions/runs/40342896917) succeeded.
- **VERIFIED:** in the same main run, Pages eligibility, [publish](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121642441277) and [production health verification](https://github.com/hamedonassar95/Devobs/actions/runs/40342897544/job/121643189760) succeeded. Automatic restoration checks were skipped after successful health verification. This is evidence for the static GitHub Pages site at this SHA, not a managed API, tenant-isolated SaaS, or continuous availability.
- **VERIFIED:** the live effective-rules response from [`GET /repos/hamedonassar95/Devobs/rules/branches/main`](https://api.github.com/repos/hamedonassar95/Devobs/rules/branches/main) and active repository ruleset [24507159](https://api.github.com/repos/hamedonassar95/Devobs/rulesets/24507159) reports: pull requests are required; strict status checks require `validate`; deletion and non-fast-forward updates are blocked; CodeQL alert rules apply. The PR rule reports **0 required approving reviews**, no required Code Owner review, no required last-push approval, and no required review-thread resolution. It also returns `require_extra_approval_for_unattributed_changes: true`; no broader interpretation is made here. The ruleset response has `bypass_actors: []` and `current_user_can_bypass: never` for the identity used for this query.
- **UNVERIFIED:** organization or enterprise rules and other authority not represented by these repository API responses. `GET /repos/hamedonassar95/Devobs/branches/main/protection` returned HTTP 403, “Resource not accessible by integration”; traditional branch-protection details could not be inspected. Do not infer hidden bypass actors from an empty repository-level list.
- **VERIFIED:** refreshed PR API results at this snapshot:

  | PR | State | Merge commit |
  | --- | --- | --- |
  | [#253](https://github.com/hamedonassar95/Devobs/pull/253) | Closed, unmerged | — |
  | [#259](https://github.com/hamedonassar95/Devobs/pull/259) | Merged | `4fc78b8f696d2fd78bf729e8792441ba3f032b46` |
  | [#262](https://github.com/hamedonassar95/Devobs/pull/262) | Closed, unmerged | — |
  | [#264](https://github.com/hamedonassar95/Devobs/pull/264) | Merged | `d948aebeb046e9d2a224dcbb89f5dc805bcfa147` |
  | [#265](https://github.com/hamedonassar95/Devobs/pull/265) | Merged | `84d187fc70e3fcab3950998831f1d806affdd1b3` |
  | [#266](https://github.com/hamedonassar95/Devobs/pull/266) | Merged | `96ea60968819a4ce50791cd805794edca9631b47` |
  | [#267](https://github.com/hamedonassar95/Devobs/pull/267) | Merged | `56961b7764ed50204f0f065edb9e8ed12b58b81d` |
  | [#268](https://github.com/hamedonassar95/Devobs/pull/268) | Merged | `d6563de320e52e70f527db26b2bd8fc3c1c033d2` |
  | [#269](https://github.com/hamedonassar95/Devobs/pull/269) | Merged | `f488a84c39c995c0166b97deac9e22fec0462b87` |
  | [#270](https://github.com/hamedonassar95/Devobs/pull/270) | Merged by `hamedonassar95` at 14:47:07 UTC | `c0a5ca505d2f28a3f14c08fdaf4c9f3c8722c458` |

  PR #270's exact-head run [40337697257](https://github.com/hamedonassar95/Devobs/actions/runs/40337697257) passed `validate`, Trivy, security, Terraform and PostgreSQL RLS. Its submitted-reviews list is empty. The merge is an owner decision on that documentation PR, not a recorded P00 exit signoff. The open PR API query (`state=open`, `per_page=100`) returned no open PRs.
- **VERIFIED:** PR run 40337697257 skipped Python and Node checks for its docs-only change and skipped production release. The separate push run [40337651505](https://github.com/hamedonassar95/Devobs/actions/runs/40337651505) on the same SHA passed Python and Node. PR previews and successful static Pages release do not establish managed staging or SaaS production.

**VERIFIED:** the older [governance audit](DEVOBS_MAIN_GOVERNANCE_AUDIT.md), [readiness report](DEVOBS_READINESS_CURRENT.md), [PR #253 review](P00_PR253_GAP_REVIEW.md), [PR #262 disposition](P00_PR262_DISPOSITION.md), [staging acceptance](STAGING_ACCEPTANCE.md), and [canonical roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md) retain their stated earlier timestamps and SHAs. Their PR queues are historical snapshots, not current API state. The roadmap still names the earlier #265 decision and #259 review in its P00 ledger; both PRs have since merged. **VERIFIED from the canonical roadmap:** P00 is **ACTIVE** and P01–P12 are **BLOCKED** pending an explicit owner exit decision.

## Release, validation and rollback controls

- **VERIFIED in current source:** `.github/workflows/ci.yml` makes `validate` depend on change analysis and the applicable language tests, security, site contract, PostgreSQL RLS, container build, Trivy scan and Terraform validation. Required applicable jobs must succeed. The rollback validation profile checks Python/site requirements and requires the other optional jobs, including container scan and Terraform, to be skipped. These workflow rules are source evidence; this audit did not trigger a rollback.
- **VERIFIED in current source:** the automatic `production-release` caller runs only for a push to `main` after `validate` succeeds. `deploy-pages.yml` rejects an outdated main SHA, stages and validates the static site, publishes Pages, then checks the deployed SHA/content. Its automatic restoration path is conditional on deployment health failure and a valid prior target. Manual one-click deployment additionally requires explicit confirmation and a valid published stable rollback release; manual rollback requires the exact `ROLLBACK` confirmation and a published stable release. No rollback execution is claimed here.
- **VERIFIED source-level gap for P00 signoff:** CI `site-contract` runs `scripts/check_site.py` on the checkout and creates a downloadable PR preview by copying files. Production Pages and the manual Vercel staging workflow call `scripts/stage_site.py` and validate the resulting `_site`; `deploy-pages.yml` stages again after CI. The shared staging helper is used by Pages/Vercel paths, but current CI does not validate the exact staged artifact later published. `tests/test_shared_staging.py` checks the helper and Pages/rollback wiring, but does not assert that CI uses it. Root `AGENTS.md` requires CI, Pages and Vercel to publish the same validated output. Resolve this gap in a separate reviewed implementation change and verify artifact identity before P00 signoff; this documentation does not change the workflow.
- **UNVERIFIED:** no run was returned by the read-only API query for workflow `devobs-staging-smoke.yml`. `docs/STAGING_ACCEPTANCE.md` describes offline synthetic tests only. No live managed staging smoke, OIDC/JWKS rotation, hosted TLS, production PostgreSQL RLS, or cross-tenant isolation evidence is established here; no environment contents were accessed.

## P00 owner exit checklist

**VERIFIED from the canonical roadmap:** P00 remains **ACTIVE**; P01–P12 remain **BLOCKED**. The owner or authorized maintainer should record each decision explicitly:

1. **PR queue:** confirm the current dispositions above. #270 is already merged; no PR review is recorded. Do not treat its merge, passing CI or earlier AI workflow conclusions as a P00 phase approval.
2. **Protected-main gate:** accept that the returned repository rules require PR plus strict `validate`, while the repository ruleset requires no independent approval or Code Owner review. Decide whether this review model is sufficient for P00. External policy is **UNVERIFIED**; do not infer it or change rules in this task.
3. **Exact current gate:** require a fresh `validate` success on the main SHA used for the owner’s P00 decision, with the applicable security, Trivy, RLS, site, build and Terraform results successful. The evidence above is current as of the timestamp, not a standing guarantee.
4. **Shared release artifact:** use a separate reviewed implementation change to make CI, Pages and Vercel validate and publish the same staged output, then prove that identity on an exact source SHA. Preserve main-only release, health verification and rollback safeguards.
5. **Phase record:** update the canonical P00 ledger in a separately reviewed documentation task with current evidence, the owner’s PR dispositions and an explicit P00 exit signoff. Until then, do not promote to P01.

**UNVERIFIED:** no separate P00 phase-exit signoff is recorded in the reviewed GitHub PR/review evidence. This report does not supply that decision.

## P01 requires separate approval

**VERIFIED from the roadmap; not approved by this report:** before any staging resource or live data is used, the owner must approve the provider/account/workspace, region and residency, exact scope, maximum spend and quota, data classification/retention/deletion, secret-manager and rotation policy, and IdP. Live acceptance must evidence TLS hostname verification, issuer/audience/signature/expiry and JWKS rotation, reviewed migrations, a restricted runtime database identity, FORCE RLS, existing-fixture cross-tenant denial, request limits, redacted logs, backups, measured restore and rollback. No provisioning, migration or P01 start is authorized here.

## GitHub documentation

- [Rules for a branch REST API](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)
- [Rules available for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub Actions secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [Get branch protection REST API](https://docs.github.com/en/rest/branches/branch-protection#get-branch-protection)
- [Workflow runs REST API](https://docs.github.com/en/rest/actions/workflow-runs)

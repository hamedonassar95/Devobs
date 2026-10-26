# Devobs main branch governance audit

**Audit time:** 2026-10-26 11:22 UTC
**Repository:** [`hamedonassar95/Devobs`](https://github.com/hamedonassar95/Devobs)
**Default branch:** `main`
**Observed main SHA:** `22237c9a8d02f1e42230f4e9fbf200e7e2d55b20`
**Scope:** Read-only review of repository metadata, effective rules for `main`, the accessible repository ruleset, and PR/check metadata for #253, #259, and #262. No secrets, tokens, Environments, deployment settings, or settings mutations were accessed.

## Findings

- **VERIFIED — pull requests required:** the effective rules endpoint reports an active `pull_request` rule for `main`.
- **VERIFIED — `validate` required:** the effective required-status-check rule requires context `validate`, with strict up-to-date policy enabled (`strict_required_status_checks_policy: true`). The reported GitHub App integration ID is `15368`.
- **VERIFIED — independent approval is not required:** the PR rule has `required_approving_review_count: 0`, `require_code_owner_review: false`, and `required_reviewers: []`. Thus the ruleset itself does not require one independent approval or Code Owner approval.
- **VERIFIED — deletion and force-push prevention rules are present:** effective rules include `deletion` and `non_fast_forward`.
- **VERIFIED — repository ruleset bypass configuration:** ruleset `24507159` (“Protect main”) is active and its returned `bypass_actors` list is empty. `current_user_can_bypass` is `never` for the authenticated identity used for this read. These fields describe the API response and current identity; they are not a claim about identities or controls outside the response's visibility.
- **VERIFIED — CodeQL rule:** the effective rules include CodeQL with security alert threshold `high_or_higher` and alert threshold `errors`.

## GitHub evidence

Read-only GitHub REST API requests were made at the audit time above:

1. `GET https://api.github.com/repos/hamedonassar95/Devobs` — returned `default_branch: main`.
2. `GET https://api.github.com/repos/hamedonassar95/Devobs/branches/main` — returned protected `true` and SHA `22237c9a8d02f1e42230f4e9fbf200e7e2d55b20`.
3. `GET https://api.github.com/repos/hamedonassar95/Devobs/rules/branches/main` — returned the effective rules shown above, sourced from repository ruleset `24507159`.
4. `GET https://api.github.com/repos/hamedonassar95/Devobs/rulesets/24507159` — returned active ruleset “Protect main”, its rules and `bypass_actors: []`.
5. `GET https://api.github.com/repos/hamedonassar95/Devobs/branches/main/protection` — returned **HTTP 403, “Resource not accessible by integration”**. Therefore traditional branch-protection endpoint fields are not available to this audit identity. No workaround or privilege change was attempted.

GitHub documents these APIs and rule semantics in [REST rules](https://docs.github.com/en/rest/repos/rules?apiVersion=2022-11-28) and [rules available for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). The protection endpoint limitation is documented at [Get branch protection](https://docs.github.com/en/rest/branches/branch-protection#get-branch-protection).

## Current pull request status

The following state and SHA values were read from `GET /repos/hamedonassar95/Devobs/pulls/{number}` and associated commit check-runs on **2026-10-26**:

| PR | State | Head SHA | Relevant check evidence |
|---|---|---|---|
| [#253](https://github.com/hamedonassar95/Devobs/pull/253) | **VERIFIED:** open, not merged; base `main` | `78483b69ca8a61eef32c787a982e08520b1264cc` | **VERIFIED:** `validate` succeeded in [run 40298656486](https://github.com/hamedonassar95/Devobs/actions/runs/40298656486). The PR remains open and has previously been identified as overlapping Trivy changes already merged in #255; this audit did not alter its state. |
| [#259](https://github.com/hamedonassar95/Devobs/pull/259) | **VERIFIED:** open, not merged; base `main` | `5b3bb1cf79c26cb2daa8daf314dfe8e6a8506866` | **VERIFIED:** the latest observed CI on the corrected head passed `validate`, Python validation, and image scan in [run 40314109382](https://github.com/hamedonassar95/Devobs/actions/runs/40314109382). `production-release` was skipped for the PR. |
| [#262](https://github.com/hamedonassar95/Devobs/pull/262) | **VERIFIED:** open draft, not merged; base `main` | `b5a1b9ea27ef2b26c9bbcfe1b7a218b705c8ffe0` | **VERIFIED:** documentation PR CI `validate` succeeded in [run 40313425421](https://github.com/hamedonassar95/Devobs/actions/runs/40313425421). It is a historical readiness snapshot based on the then-current main evidence and was not modified by this audit. |

## Limits and interpretation

- **UNVERIFIED:** any applicable organization or enterprise policies not represented by the effective rules response or accessible ruleset metadata. An empty repository ruleset bypass list does not prove that no external administrative authority exists.
- **UNVERIFIED:** traditional branch-protection configuration details because the branch-protection REST endpoint returned HTTP 403.
- **VERIFIED:** the returned active repository ruleset requires PRs and `validate`, blocks deletion and non-fast-forward updates, and does **not** require an approval. The required status check is not equivalent to human review.
- **ASSUMED:** none. This report avoids inferring hidden actors or controls from fields the API did not return.

This is a point-in-time API audit, not a guarantee that settings remain unchanged after 2026-10-26 11:22 UTC. No rules, branch protections, CI, code, billing, or deployment behavior were changed.

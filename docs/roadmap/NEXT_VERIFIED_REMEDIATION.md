# Next verified remediation — enforce an independent approval in the repository policy audit

**Decision source:** [current readiness reconciliation](../audits/DEVOBS_CURRENT_READINESS.md), audited SHA `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6`. **Status:** DEFINED ONLY — not implemented in this task, not authorized to merge, no GitHub settings changed.

## 1. Single next fix

Fail closed in `scripts/check_repo_policy.py` when the default-branch `pull_request` rule does not require at least one independent approving review. Keep every existing check (deletion block, force-push block, `validate` status, strict up-to-date branches, CodeQL thresholds, bypass actors) unchanged.

**Why this and not a P0 item:** P01, AI-9, Render expiry, backup/restore and spend cap are owner-decision gates and are correctly BLOCKED; none is an agent-owned code defect. `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md` ranks "main review policy" as remediation **#1 (highest priority)** among actionable defects. No active branch owns the candidate files (ownership scan described below), and the fix has a deterministic offline test surface.

## 2. VERIFIED defect evidence

| Claim | Evidence |
| --- | --- |
| Checker ignores review count | `scripts/check_repo_policy.py:200-207` verifies only that rule types `deletion`, `non_fast_forward`, `pull_request` exist; no parameter validation for `pull_request`. |
| Test blesses zero approvals | `tests/test_check_repo_policy.py:45` fixture sets `{"required_approving_review_count": 0}`; `:64-69` `test_accepts_current_policy_shape` expects `findings == []`. |
| Live ruleset still has zero approvals | Read-only `GET /repos/hamedonassar95/Devobs/rulesets/24507159` returned `required_approving_review_count: 0`, `required_reviewers: []`, `require_code_owner_review: false`, `require_last_push_approval: false`; `validate` and CodeQL requirements remain. (Anonymous response omitted `bypass_actors`; that field is UNVERIFIED here and must not be guessed.) |
| Security review classification | `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md` V-01: a writer can merge after checks without an approver; minimal remediation = extend checker + tests to reject a zero/absent count; official [GitHub ruleset review docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging). |
| No active owner | `git diff --name-only origin/main...<branch>` across all `feature/*` and `docs/*` branches returned no branch touching `scripts/check_repo_policy.py` or `tests/test_check_repo_policy.py`. Branches that do touch `README.md`, `STATE.md` or `docs/MILESTONE_LEDGER.json` are explicitly out of scope. |

This tool is a **read-only reporter**. It must never call a settings-writing endpoint, and a PASS from it is not proof that a ruleset was changed or that a human approved anything.

## 3. Exact candidate files

| File | Change |
| --- | --- |
| `scripts/check_repo_policy.py` | Add a bounded helper that reads `pull_request.parameters.required_approving_review_count`; append a named, fixed finding when the value is missing, non-integer, negative or `0`; keep all existing findings and error behavior intact. |
| `tests/test_check_repo_policy.py` | Update the "compliant" fixture to `required_approving_review_count: 1`; add the acceptance tests listed in §4; keep existing drift tests green. |
| `docs/security/REPOSITORY_APPROVAL_POLICY.md` (new, short) | Record the required control (≥1 independent approval), the report-only nature of the checker, the owner-only ruleset change procedure and the exact verification commands. |

**Explicitly excluded:** `README.md`, `STATE.md`, `docs/MILESTONE_LEDGER.json`, `.github/workflows/*`, hosted ruleset settings, CI gates, dependencies. Those are owned by other branches or require owner action.

## 4. Exact acceptance tests (behavioral, offline fixtures)

In `tests/test_check_repo_policy.py`, using the existing `api_fixtures()` + `audit_repository(..., api_get=fixtures.__getitem__)` pattern:

1. `test_rejects_zero_required_approving_review_count` — fixture count `0` → finding mentions the approval requirement/count; `findings` is non-empty. This codifies the currently-live shape as drift.
2. `test_rejects_missing_approval_parameter` — delete `parameters` (or the count key) from the `pull_request` rule → a finding, **no exception** and no crash.
3. `test_rejects_non_integer_or_negative_approval_count` — subTests with `"1"`, `None`, `-1`, `1.5` → a finding for each; never coerced to pass.
4. `test_accepts_one_or_more_required_approvals` — counts `1` and `2` → no approval finding; other compliant fixture checks still yield `findings == []`.
5. `test_approval_finding_does_not_hide_other_drift` — combine zero approvals with the existing missing `validate` check → both findings appear; fail-closed is additive.
6. `test_existing_policy_checks_remain_enforced` — the current 16-test suite (minus the Windows-locked temp file case fixed in its own PR) stays green; deletion/force-push/status/strict/CodeQL/bypass assertions unchanged.

**Separate follow-up, not part of this fix:** `test_actions_summary_includes_named_drift_findings` currently fails on Windows with `PermissionError` because `NamedTemporaryFile` keeps the summary path locked while `write_step_summary` reopens it (`tests/test_check_repo_policy.py:235-241`, `scripts/check_repo_policy.py:264`). Fix in its own P2 PR with a closed temp path or a mocked writer; do not mix it into the security fix.

## 5. Implementation approach (for the future branch only)

1. Parse `pull_request` rule parameters defensively: require a `dict`, then an `int` (excluding `bool`) `required_approving_review_count >= 1`.
2. Emit one stable, non-sensitive finding such as `Ruleset 'Protect main' does not require at least one approving review.`
3. Do not change `get_json`, API version, authentication, timeout, exit-code semantics or step-summary formatting.
4. Do not read tokens, modify GitHub settings, or promote P01/AI-9/Codex gates. An owner decision and a separate reviewed ruleset change are required before the live zero-count state becomes compliant.

## 6. Verification commands (to run on the future branch)

```sh
python -m unittest tests.test_check_repo_policy -v
python scripts/check_repo_policy.py --repository hamedonassar95/Devobs
python scripts/milestone_ledger.py --summary
python -m unittest tests.test_milestone_ledger -q
git diff --check
git status --short
```

Note: the repository-policy CLI uses the public GitHub API and reads `GH_TOKEN`/`GITHUB_TOKEN` from the environment if present ([source](../../scripts/check_repo_policy.py)); the agent must not inspect or print token values. In this sandbox the unauthenticated ruleset response omitted `bypass_actors`, so that check must remain inconclusive rather than inferred.

## 7. Acceptance criteria

- All six new tests pass; the existing policy suite has no new failures on Linux CI.
- A zero, missing, non-integer or negative review count yields a finding; count ≥1 yields none.
- No write request to any GitHub API; no secret, token or ruleset detail printed; no gate promotion.
- Exact-head CI (including `validate` and security jobs) is recorded before any Draft PR review; no merge, deploy or settings change.

## 8. Risk and rollback

- **Risk:** once merged, the audit reports drift until the owner actually raises the ruleset approval count; this is intentional and must not be suppressed by weakening the check. Anonymous API responses can omit fields, so "not visible" must be reported as UNVERIFIED, not PASS.
- **Rollback:** revert the three-file feature branch commit; the checker returns to its prior report-only behavior. No hosted state is changed by this fix, so there is no external rollback step.

## 9. Draft PR delivery instructions

- Branch/worktree: `feature/repo-policy-approval-count` in an isolated worktree; one concern, small commits (source+tests, then doc).
- Target `main` as a **Draft PR only**; title `fix(policy): fail closed on zero required approvals`.
- Body must include: exact source SHA, the six acceptance tests with final output lines, the read-only ruleset field values, explicit statement that no settings/token/gate was changed, and the owner decision still required for the live ruleset.
- Do not merge, deploy, force-push or activate any gate. Keep the existing CI, CodeQL, Trivy, RLS and Phase 8 human approval gates intact.

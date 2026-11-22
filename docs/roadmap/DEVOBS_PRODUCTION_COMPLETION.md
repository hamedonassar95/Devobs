# Devobs production-readiness completion record (2026-11-22)

This is a phase-completion record for the isolated branch
`feature/devobs-production-recovery` at base
`88556034e24e52e529c276ab6cc753e8fc026c91` (`origin/main`, PR #747 merge).
It records what was done and what was deliberately **not** done. It is not a
release GO, a gate promotion, or owner approval.

## Phase 1 — Reconciliation (COMPLETE, with stated limits)

- VERIFIED: `git fetch origin` exit `0`; `git rev-parse origin/main` =
  `88556034e24e52e529c276ab6cc753e8fc026c91`.
- VERIFIED: all thirteen requested PRs confirmed merged via public read-only
  GitHub REST; full head/merge SHA and check-run table in
  `docs/audits/DEVOBS_PRODUCTION_GAP_ANALYSIS.md` §2.
- VERIFIED: no `APPROVED` review on any listed PR; #722/#740 are feature-branch
  merges. Current branch protection and current-base CI are UNVERIFIED.
- VERIFIED: prior progress-report and integration branches and all overlapping
  audit worktrees were preserved without modification.
- BLOCKED: further REST queries after anonymous quota exhaustion; no token used.

## Phase 2 — Gap inventory (COMPLETE)

- VERIFIED: 22 capability rows across CI/governance, API/RLS/auth, supply
  chain, cloud/K8s, reliability, AI/agents, Graphify/integrations and P01.
- VERIFIED classifications: 6 IMPLEMENTED_NOT_VERIFIED groups,
  1 IMPLEMENTED_AND_VERIFIED, several PARTIAL, 3 MISSING, and the owner-gated
  BLOCKED set (hosted OIDC/RLS, live restore/alert/SLO, Codex runtime, P01).
- VERIFIED correction to prior roadmap: F04 (Graphify wheel hash verification)
  is **resolved** in current source — `tools/graphify/supply_chain.py:26-52`
  and `tests/graphify/test_supply_chain.py` — and is not carried forward.
- UNVERIFIED items (hosted tenant denial, live OIDC, backup restore, alert
  delivery, live SLO, real wheel/CLI provenance) are explicitly excluded from
  the defect set.
- ASSUMED item: ledger `codex-agent-runtime-acceptance=OPEN` normalized to
  BLOCKED in the required status vocabulary.

## Phase 3 — Prioritization and single selection (COMPLETE)

Six confirmed defects were recorded (D1–D6 in the gap analysis). Selection rule:
confirmed impact × fail-closed value ÷ change risk.

**Selected: D1 only** — `scripts/check_two_agent_tasks.py` accepted branch
names with traversal segments (`feature/../main`) or empty segments
(`feature//x`) as PASS, defeating the concurrent branch-ownership conflict
check. It is offline-reproducible, security-relevant, and bounded.

Deferred, with reasons: D2 self-asserted evidence trust and D3 skipped
agent validation need contract/policy decisions; D4 `PR_RE` repository binding
needs manifest compatibility review; D5 governance lag (#717/#641 vs #747)
needs owner-reviewed exact CI evidence and is REST-quota blocked; D6 stale
console Bun lock needs dependency regeneration tooling. None was changed here.

## Phase 4 — Single repair (COMPLETE)

- Test-first: added `test_branch_traversal_and_empty_segments_fail_closed`
  with seven subtests. Baseline against the unmodified `HEAD` source (loaded
  from `git show HEAD:scripts/check_two_agent_tasks.py` into the approved temp
  directory, without changing the branch) produced:
  `Ran 1 test ... FAILED (failures=7)`;
  `BASELINE_TESTS_RUN=1 FAILURES=7 ERRORS=0`; `BASELINE_REPRO_EXIT=1`.
- Production change: added `_valid_branch(value)` requiring `BRANCH_RE` plus
  rejection of `""`, `"."` and `".."` segments after the prefix; `evaluate()`
  now calls it instead of the bare regex.
- Diff: `2 files changed, 17 insertions(+), 1 deletion(-)` in
  `scripts/check_two_agent_tasks.py` and `tests/test_two_agent_tasks.py`.
  No other source/test file changed; no evidence doc was overwritten.

## Phase 5 — Verification (COMPLETE within local scope)

Exact commands and final lines (Python `3.12.10`, git `2.56.1.windows.1`):

| Command | Result | Exit |
|---|---|---|
| `python -B -m unittest tests.test_two_agent_tasks -v` | `Ran 27 tests in 5.074s` / `OK` | `0` |
| `python -B -m unittest tests.test_milestone_ledger` | `Ran 86 tests in 4.016s` / `OK` | `0` |
| `python -B scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` | `0` |
| `python scripts/milestone_ledger.py --summary` | `latest_pr:717`, `merged_milestones:304`, `open_gates:3`, gates unchanged | `0` |
| `git diff --check` | no output | `0` |

Baseline failures and regressions: the seven pre-fix subtest failures are the
documented repro and are resolved; no new failure was introduced in the two
focused modules.

Full suite was subsequently run **on this repaired SHA**:
`python -B -m unittest discover -s tests -v` → `Ran 1480 tests in 495.511s`
→ `FAILED (failures=84, errors=126, skipped=38)` → exit `1` (VERIFIED).
A scan of that log found **zero** `FAIL:`/`ERROR:` entries naming
`two_agent`, so the repaired module is not implicated (VERIFIED). Failure
categories are local-environment dominated: 123 lines mentioning symlink or
non-regular-file guards, 108 Windows-path lines, 58 `SECURE_OPEN_UNAVAILABLE`
lines and 6 `GITHUB_WORKSPACE` staging-guard lines (VERIFIED by log scan).
A baseline full-suite run in a detached worktree at `88556034e24e52e529c276ab6cc753e8fc026c91`
was started but interrupted by two harness restarts before its summary line;
it is **UNVERIFIED** and is not used to claim regression parity. The temporary
worktree was removed (exit `0`).

Older audited evidence at a different SHA reported `Ran 1197 tests`,
`FAILED (failures=47, errors=123, skipped=44)`; it is historical, not current.
Known Windows-only blockers from that evidence include
`platform_no_follow_unsupported` (not reproduced in the current run),
`SECURE_OPEN_UNAVAILABLE`, and the actionlint wrapper timeout with its default
shellcheck argv (actionlint `1.7.12` itself passed 38 authored workflows with
`-shellcheck=`).

## Phase 6 — Required documentation (COMPLETE)

- `docs/audits/DEVOBS_PRODUCTION_GAP_ANALYSIS.md` (new)
- `docs/roadmap/DEVOBS_PRODUCTION_COMPLETION.md` (new)
- `docs/runbooks/DEVOBS_RECOVERY_STATUS.md` (new)
- `README.md` (short pointer added; existing evidence preserved)

## Phase 7 — Delivery (COMPLETE except owner-gated Draft PR)

- One repair commit `4567125d79e88077cb2fbe940a66aae201dd45b8` was created and
  pushed to `origin/feature/devobs-production-recovery` (exit `0`; remote SHA
  matches local). A second, evidence-only commit records the full-suite and
  PR-auth findings; no production code changes in it.
- Draft PR to `main`: BLOCKED. `gh` is absent; after quota reset, anonymous
  `POST /pulls` returned `401 Requires authentication` while `GET /rate_limit`
  showed `remaining: 60`. No token was read. A read-only
  `GET /pulls?head=…&state=all` returned an empty array, confirming no PR was
  created. Manual URL is in the runbook.
- Post-baseline movement (VERIFIED 2026-11-23): `origin/main` advanced to
  `b90407040e3d2a34627679f2cbca14db46eb70ca` (#748/#749/#750); compare reports
  `ahead_by:2`, `behind_by:3`, with no overlapping files. #750 resolved D5
  upstream (ledger `latest_pr:747`, `305` milestones, gates unchanged). No
  rebase or history rewrite was done; reviewed SHAs remain bound to the fixed
  base.
- No merge, deploy, gate promotion or hosted change was requested or performed.

## What remains owner-gated (unchanged)

P01 managed SaaS (BLOCKED), AI-9 detection quality (BLOCKED), Codex runtime
acceptance (OPEN → BLOCKED by normalization), hosted OIDC/RLS denial proof,
encrypted backup restore, live alert delivery, live SLO, WIF/IAM/GKE
provisioning, NetworkPolicy, billing/metering/tenant onboarding, exact-SHA
release approval, branch-protection verification, and all cost/cloud/deploy
actions. The disposable local Keycloak exception is **not active** — it is
gated on this reconciliation PR being merged to `main`, so no Keycloak runtime
test was run.

**PENDING HUMAN APPROVAL**

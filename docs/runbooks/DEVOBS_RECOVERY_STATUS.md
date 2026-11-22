# Devobs recovery status runbook (2026-11-22)

Purpose: a reproducible, fail-closed status snapshot for the isolated
recovery branch. Read this before treating any local `PASS` as a production
signal. Nothing here authorizes a merge, deploy, spend, gate promotion or
hosted action.

## 1. Current state

| Field | Value | Label |
|---|---|---|
| Worktree | `C:\Users\NASSAR FAMILY\AppData\Local\Temp\opencode\devobs-production-recovery` | VERIFIED |
| Branch | `feature/devobs-production-recovery` | VERIFIED |
| Base / `origin/main` | `88556034e24e52e529c276ab6cc753e8fc026c91` (PR #747 merge) | VERIFIED |
| Local HEAD before commit | `88556034e24e52e529c276ab6cc753e8fc026c91` | VERIFIED |
| Commit SHA | a commit cannot contain its own SHA; the exact HEAD SHA and push result are in the final delivery report | VERIFIED at delivery |
| Toolchain | Python `3.12.10`, git `2.56.1.windows.1`, Windows | VERIFIED |
| Ledger summary | `latest_pr:717`, `304` milestones, `3` open gates, gates unchanged | VERIFIED |
| P01 / AI-9 / Codex gates | `BLOCKED` / `BLOCKED` / `OPEN` (normalized BLOCKED) | VERIFIED + ASSUMED normalization |

## 2. Exactly one repair on this branch

- Defect D1: weak branch-name validation in the offline two-agent manifest
  checker. Traversal (`feature/../main`, `docs/../main`, `feature/x/..`) and
  empty/`.` segments (`feature//x`, `feature/x/`, `fix/./y`, `chore//x`) were
  accepted as PASS, so the checker could miss concurrent branch ownership.
- Files: `scripts/check_two_agent_tasks.py` (+9/-1),
  `tests/test_two_agent_tasks.py` (+8). Total `2 files, 17 insertions(+), 1 deletion(-)`.
- Mechanism: `_valid_branch()` requires `BRANCH_RE` and rejects `""`, `"."`,
  `".."` segments; `evaluate()` uses it for the `invalid task branch` error.
- Behavior on error: `FAIL` (exit `2` from CLI per the existing contract) with
  `invalid task branch` — fail closed, never silently pass.

## 3. Reproduce and verify

```sh
# from the recovery worktree
python --version
git --version
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD

# baseline (unmodified HEAD source, read via git show into approved temp dir)
# observed: BASELINE_TESTS_RUN=1 FAILURES=7 ERRORS=0 ; BASELINE_REPRO_EXIT=1

python -B -m unittest tests.test_two_agent_tasks -v
python -B -m unittest tests.test_milestone_ledger
python -B scripts/check_action_pins.py
python scripts/milestone_ledger.py --summary
git diff --check
```

Expected final lines on the repaired branch (VERIFIED here):

- `Ran 27 tests in 5.074s` → `OK` → exit `0`
- `Ran 86 tests in 4.016s` → `OK` → exit `0`
- `Action pin check passed for 48 workflow and template files.` → exit `0`
- ledger summary JSON as in §1 → exit `0`
- `git diff --check` → no output → exit `0`
- `python -B -m unittest discover -s tests -v` → `Ran 1480 tests in 495.511s`
  → `FAILED (failures=84, errors=126, skipped=38)` → exit `1`; zero reported
  failures name `two_agent` (VERIFIED). This full-suite exit is recorded, not
  hidden.

Do not substitute local output for GitHub CI. There is no current-base hosted
CI run in this evidence set (UNVERIFIED).

## 4. Checks that could not run / did not pass

- BLOCKED: Draft PR creation is definitively unavailable here. `gh` is
  absent (`GH_UNAVAILABLE`). After the anonymous quota reset, `POST
  /repos/hamedonassar95/Devobs/pulls` with `draft: true` returned HTTP `401
  Requires authentication` while `GET /rate_limit` showed `remaining: 60`.
  No token was read or used; the manual URL in §6 is the only path.
- BLOCKED: branch-protection current state, exact Actions run IDs per PR,
  reviews beyond the read-only snapshot, hosted CI rerun.
- BLOCKED: Keycloak runtime. The disposable exception is not active until this
  reconciliation PR is merged to `main`; no signing material was generated or
  inspected.
- BLOCKED by owner/cloud policy: gcloud, deploy, WIF/IAM/GKE, hosted OIDC/JWKS,
  tenant RLS denial, backup restore, alert delivery, live SLO, billing, paid AI
  inference, release approval.
- UNVERIFIED: Linux/WSL run, real Graphify wheel/CLI provenance, console Bun
  lock regeneration.
- Current full-suite failures are local-environment dominated (VERIFIED log
  scan): 123 symlink/non-regular-file guard lines, 108 Windows-path lines,
  58 `SECURE_OPEN_UNAVAILABLE` lines, 6 `GITHUB_WORKSPACE` staging lines. A
  same-SHA baseline comparison run was interrupted by harness restarts before
  its summary; it is UNVERIFIED and no regression-parity claim is made.
- Older audited full-suite evidence (different SHA): 47 failures, 123 errors,
  44 skipped out of 1197 tests, including `platform_no_follow_unsupported`
  (not reproduced in the current run) and the actionlint wrapper timeout with
  default shellcheck argv. Historical only.

## 5. Safety invariants observed

- No secret, token, credential, environment or deployment setting was read,
  printed, created or changed.
- No production account, cloud resource, database, hosted IdP or customer data
  was accessed.
- No merge, push to `main`, deploy, agent dispatch, subscription, paid service
  or gate promotion occurred.
- All overlapping worktrees and prior branches were preserved; only the two
  repair files plus the four required docs were changed on this branch.
- no Keycloak service was started; TLS material was not opened.

## 6. Delivery record

| Step | Status | Evidence |
|---|---|---|
| Commit on isolated branch | COMPLETE — one bounded commit; exact SHA in final delivery report (a commit cannot record its own SHA) | `git rev-parse HEAD` in the delivery report |
| Push to `origin/feature/devobs-production-recovery` | see final delivery report for exit code | `git push -u origin ...` |
| Draft PR to `main` | BLOCKED — anonymous REST `401 Requires authentication`, `gh` absent | manual URL below |
| Merge / deploy | NOT PERFORMED | owner approval required |

Manual Draft PR URL if authenticated creation remains blocked:

`https://github.com/hamedonassar95/Devobs/pull/new/feature/devobs-production-recovery?base=main`

Open that URL, select **Draft pull request**, keep `main` as base, and attach the
verification table above. Do not merge or promote gates from that PR.

## 7. Escalation / next owner decision

Owner must decide, on a separate reviewed SHA: (a) whether to accept this D1
repair, (b) whether to schedule the deferred D2–D6 work, and (c) whether to
update governance docs/ledger with exact per-PR CI evidence once REST quota is
available. No item proceeds from this runbook alone.

**PENDING HUMAN APPROVAL**

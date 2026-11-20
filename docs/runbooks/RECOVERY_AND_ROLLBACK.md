# Recovery and rollback runbook — 2026-11-20

**Applies to:** `feature/devobs-recovery-readiness` recovery assessment.
**Selected repair:** F01a canonical Graphify designation (P1, bounded).
**Scope:** one legacy CLI source file, one test file, documentation and README.
**Production impact:** none. This change edits source-control files only. It
does not touch Pages, Render, Google Cloud, PostgreSQL, identity, workflow
permissions, secrets, deployed artifacts or hosted state. No migration,
deployment, merge, service start or paid AI call exists to roll back.

## 1. Preconditions

```powershell
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status --short --branch
git ls-remote origin refs/heads/feature/devobs-recovery-readiness
git ls-remote origin refs/heads/main
```

Expected branch: `feature/devobs-recovery-readiness`. Expected base:
`cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1`. Do not run `reset --hard` on
`main`, on another user's worktree, or on a branch with unrelated changes.

## 2. Change inventory

| File | Change class | Runtime effect |
| --- | --- | --- |
| `scripts/integrations/graphify_portfolio.py` | Source | Adds warning/metadata only; CLI exit codes, flags and 0.9.112 behavior unchanged. |
| `tests/test_graphify_portfolio.py` | Test | Adds one regression test. |
| `README.md` | Docs | Documents canonical/legacy surfaces. |
| `docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md` | Docs | New decision record. |
| `docs/architecture/graphify-integration.md` | Docs | Canonical-status note. |
| `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md` | Docs | Legacy/historical note. |
| `docs/audits/DEVOBS_RECOVERY_AUDIT.md` | Docs | New audit. |
| `docs/roadmap/DEVOBS_RECOVERY_ROADMAP.md` | Docs | New roadmap. |
| `docs/runbooks/RECOVERY_AND_ROLLBACK.md` | Docs | This runbook. |

No GitHub Actions file, dependency lock, secret, permission or infrastructure
file was changed.

## 3. Rollback option A — revert the source fix commit (preferred)

If the source/test fix is its own commit:

```powershell
git log --oneline -5
git revert --no-edit <SOURCE_FIX_COMMIT_SHA>
python -B -m unittest tests.test_graphify_portfolio -v
git diff --check
git push origin feature/devobs-recovery-readiness
```

Effect: removes the deprecation warning and canonical metadata, returns the
legacy CLI to its prior behavior, and leaves documentation changes in place.
If documentation must also be reverted, use option B.

## 4. Rollback option B — restore exact base file content

For a surgical rollback of only the two source/test files:

```powershell
git checkout cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1 -- scripts/integrations/graphify_portfolio.py tests/test_graphify_portfolio.py
python -B -m unittest tests.test_graphify_portfolio -v
git diff --check
```

This is safe because both files were unchanged at the reviewed base. It must not
be used if unrelated owner edits have since been added to either file.

## 5. Rollback option C — discard the entire feature branch

Only if all changes on this branch are to be abandoned and no other work is
present:

```powershell
git switch main
git branch -D feature/devobs-recovery-readiness
git push origin --delete feature/devobs-recovery-readiness
```

`git push origin --delete` changes a remote branch name; it does not revert any
merge or deployment. Use only with explicit owner approval if the branch is
shared. Never force-push.

## 6. If a Draft PR already exists

- Keep the PR open and explain the rollback in a comment; do not silently
  rewrite reviewed history.
- If the PR has been merged, **stop**. A merge requires a separate owner-approved
  revert branch. Do not revert `main` directly or force-push.
- No production release or Pages publish is triggered by this change; a revert
  therefore has no hosted artifact to restore.

## 7. Verification after rollback

| Check | Command | Expected |
| --- | --- | --- |
| Legacy suite | `python -B -m unittest tests.test_graphify_portfolio -v` | `Ran 26 tests`, `OK` |
| F02 regression | `python -B -m unittest tests.test_python_source_coverage -v` | `Ran 3 tests`, `OK` |
| Graphify package | `python -B -m unittest discover -s tests/graphify -v` | `Ran 41 tests`, `OK` |
| Pin policy | `python scripts/check_action_pins.py` | exit `0`, 48 files |
| Whitespace | `git diff --check` | exit `0` |
| Clean state | `git status --short --branch` | only expected branch state |

If rollback verification fails, stop and report the exact command/output. Do not
suppress tests or change unrelated files to force green.

## 8. Gates and forbidden actions

Rolling this change back does **not** change P01 (BLOCKED/NO-GO), AI-9
(BLOCKED), Codex runtime acceptance (OPEN), OIDC/WIF, RLS, observability or
reliability gates. It does not authorize merge, deployment, production access,
secret handling, scanning-pipeline changes, paid AI, cloud writes, Terraform
apply/destroy or database migrations.

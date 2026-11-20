# Graphify F01b rollback runbook — 2026-11-20

**Applies to:** `feature/graphify-unification-readiness`.
**Base revision:** `41353d1451524492d6ca6e3ae8bb1b7d12c87b45` (`origin/main`, PR
#725 merge commit).
**Reviewed implementation commits (oldest to newest):** `b95ac86`, `01b980d`,
`1bbccc9`, `2df481b`, `c19e4a0`, `ed55a06`.

This change is source-control only. It does not modify Pages, Render, Google
Cloud, PostgreSQL, Keycloak, workflow permissions, secrets, hosted state, Graphify
indexes or any source tree being analyzed. No deployment, migration, merge,
service start, paid inference or external upload exists to roll back.

## 1. Confirm the affected revision

```powershell
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status --short --branch
git log --oneline origin/main..HEAD
```

Expected branch: `feature/graphify-unification-readiness`. Do not run
`reset --hard` on `main`, on another user's worktree, or on a branch with
unrelated changes. Stop if `git status` shows unrelated files.

## 2. Change inventory

| File | Change class | Runtime effect |
| --- | --- | --- |
| `tools/graphify/portfolio.py` | New source | Canonical policy, discovery and plan contracts. |
| `tools/graphify/portfolio_execution.py` | New source | Canonical execution/CLI layer used by the legacy adapter. |
| `tools/graphify/supply_chain.py` | New source | Local, fail-closed SHA-256 verifier. |
| `tools/graphify/repository_intelligence.py` | Source | Adds `verify-wheel` subcommand and error mapping. |
| `scripts/integrations/graphify_portfolio.py` | Source | Converted from implementation to thin adapter. |
| `tests/graphify/test_portfolio.py` | New test | Canonical parity coverage. |
| `tests/graphify/test_supply_chain.py` | New test | Digest/CLI failure coverage. |
| `tests/test_graphify_portfolio.py` | Test | Adapter-delegation assertion. |
| `docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md` | Docs | Supersedes F01a designation with F01b completion. |
| `docs/architecture/graphify-integration.md` | Docs | Architecture, verifier and evidence updates. |
| `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md` | Docs | Legacy/adapter pointer. |
| `docs/audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md` | Docs | New A–K audit. |
| `docs/runbooks/GRAPHIFY_ROLLBACK.md` | Docs | This runbook. |
| `README.md` | Docs | Canonical/legacy/adapter/verifier pointers. |

No workflow, dependency lock, secret, permission, infrastructure or indexed data
file was changed.

## 3. Option A — revert the reviewed commits (preferred)

Revert in reverse chronological order, then the documentation commit:

```powershell
git log --oneline origin/main..HEAD
git revert --no-edit ed55a06 c19e4a0 2df481b 1bbccc9 01b980d b95ac86
git revert --no-edit <DOCUMENTATION_COMMIT_SHA>
python -B -m unittest discover -s tests/graphify -v
python -B -m unittest tests.test_graphify_portfolio -v
python -B -m compileall -q tools/graphify scripts/graphify scripts/integrations/graphify_portfolio.py
git diff --check
```

Effect: restores the F01a state at the base revision, including the legacy
0.9.112 implementation and its deprecation notice. No hosted state or external
index needs restoration. Do not push or open a PR unless separately authorized.

## 4. Option B — restore only the legacy entrypoint

If only the legacy CLI behavior must be restored while retaining canonical tests:

```powershell
git checkout 41353d1451524492d6ca6e3ae8bb1b7d12c87b45 -- scripts/integrations/graphify_portfolio.py tests/test_graphify_portfolio.py
python -B -m unittest tests.test_graphify_portfolio -v
python -B -m compileall -q scripts/integrations/graphify_portfolio.py
git diff --check
```

This is safe because those files were unchanged at the reviewed base. Do not use
it if unrelated owner edits have since been added to either file.

## 5. Option C — discard the entire branch

Only if all branch work is to be abandoned and no other work is present:

```powershell
git switch main
git branch -D feature/graphify-unification-readiness
git push origin --delete feature/graphify-unification-readiness
```

The final command is destructive on the remote branch and requires explicit
owner approval. Do not use it to work around a review finding.

## 6. Post-rollback verification

```powershell
python -B -m unittest discover -s tests/graphify -v
python -B -m unittest tests.test_graphify_portfolio -v
python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
python scripts/check_action_pins.py
git diff --check
```

Record the exact final output lines. If any check fails, stop and report the
failure; do not suppress tests or delete indexed data to force a green result.

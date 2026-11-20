# Rollback runbook — F02 Python source coverage fix

**Applies to:** `feature/devobs-root-cause-repair` (root-cause audit 2026-11-20).
**Scope:** CI change selection, compile paths, Bandit target, three Graphify
source annotations, one dead import removal, two test updates, one new test file
and three audit/roadmap documents.

## Production impact

**None.** This change modifies source-control configuration and local tests
only. It does not touch `main`, GitHub Pages content, cloud resources,
databases, secrets, permissions, workflow runtimes or deployed artifacts. No
migration, deployment or hosted state exists to roll back.

## Preconditions

- Work from a clean checkout of the feature branch.
- Confirm the current head and that the remote branch exists:

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/feature/devobs-root-cause-repair
```

- Do not run `reset --hard` on `main` or on another user's worktree.

## Rollback option A — revert the fix commit (preferred)

If the fix was committed as its own commit:

```powershell
git checkout feature/devobs-root-cause-repair
git revert --no-edit <fix-commit-sha>
git push origin feature/devobs-root-cause-repair
```

Then let CI run on the revert. This preserves history and audit evidence.

## Rollback option B — restore the audited baseline in the feature branch

Use only when a clean historical boundary is required and all local changes on
this branch are known to be from this remediation:

```powershell
git checkout feature/devobs-root-cause-repair
git diff --stat
git restore --source=4299a9d47f94b479f0935dd25ee5c5309eb8e1d1 -- `
  .github/workflows/ci.yml `
  scripts/assess_change.py `
  tests/graphify/test_runner.py `
  tests/test_python_dependency_automation.py `
  tools/graphify/common.py `
  tools/graphify/repository_intelligence.py `
  tools/graphify/runner.py
git rm tests/test_python_source_coverage.py `
  docs/audits/DEVOBS_ROOT_CAUSE_AUDIT.md `
  docs/roadmap/REMEDIATION_ROADMAP.md `
  docs/runbooks/REMEDIATION_ROLLBACK.md
git status --short
git commit -m "revert(graphify-ci): restore pre-audit CI coverage"
git push origin feature/devobs-root-cause-repair
```

Verify that the diff against the audited baseline is empty:

```powershell
git diff --stat 4299a9d47f94b479f0935dd25ee5c5309eb8e1d1..HEAD
```

## Partial rollback — CI coverage only

If the Graphify source annotations are acceptable but CI coverage must be
restored, revert only these lines:

- `.github/workflows/ci.yml`: `compile_paths_json` back to
  `'["scripts", "tests"]'`; Bandit back to `-r scripts`.
- `scripts/assess_change.py`: remove `("tools",)` from `is_python()`.
- `tests/test_python_dependency_automation.py`: restore the original Bandit
  assertion.
- `tests/test_python_source_coverage.py`: delete the file.

Do **not** remove only the `# nosec` annotations while keeping `tools/` in the
Bandit target: the scan will fail on the six reviewed low-severity findings and
CI will correctly block the branch.

## Post-rollback verification

```powershell
python -B -m unittest tests.test_python_dependency_automation -v
python -B -m unittest discover -s tests/graphify -v
python scripts/check_action_pins.py
git diff --check
git status --short --branch
```

Expected after a full rollback: Graphify and dependency-automation tests pass,
action pins pass, diff check passes, and the feature branch is clean. Do not
interpret the pre-existing Windows-only full-suite failures as rollback
regressions; compare counts with the audit baseline (`47 failures`,
`123 errors`, `44 skipped`).

## If the PR already exists

1. Do not merge.
2. Add a PR comment linking the audit and the revert SHA.
3. Ask the human reviewer to close or update the Draft PR after CI passes on
   the revert. No automatic merge or force push is authorized.

## Escalation

If rollback commands fail because of permissions, stale remote state or an
unexpected dirty worktree, stop and report the exact error. Do not use broad
cleanup, force push, branch-protection bypass or deletion of unrelated files.

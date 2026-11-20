# Remediation roadmap — root-cause audit 2026-11-20

Scope: `feature/devobs-root-cause-repair` from `origin/main`
`4299a9d47f94b479f0935dd25ee5c5309eb8e1d1`. This roadmap records one completed
remediation and the remaining, owner-gated work. It does not change any release
gate.

## 1. Completed remediation — F02 (P1, CONFIRMED)

**Root cause:** Python source under `tools/` was invisible to CI change
selection, compile paths and Bandit. See
[`docs/audits/DEVOBS_ROOT_CAUSE_AUDIT.md`](../audits/DEVOBS_ROOT_CAUSE_AUDIT.md)
for reproduction and Graphify impact analysis.

**Changes applied:**

| File | Change |
| --- | --- |
| `scripts/assess_change.py` | `is_python()` now includes `tools/`. |
| `.github/workflows/ci.yml` | `compile_paths_json` now `["scripts", "tests", "tools"]`; Bandit target now `scripts tools`. |
| `tests/test_python_source_coverage.py` | New behavioral and workflow-contract regression tests. |
| `tests/test_python_dependency_automation.py` | Bandit contract assertion updated to the new command. |
| `tests/graphify/test_runner.py` | Subprocess-error test now patches the actual implementation module (`tools.graphify.runner`) instead of a re-export namespace. |
| `tools/graphify/common.py`, `runner.py` | Four justified `# nosec` annotations for low-severity subprocess findings; dead `subprocess` import removed from `repository_intelligence.py`. |

**Security note:** no check was disabled. Bandit now scans more code than
before; the four suppressed findings are all Low severity, High confidence and
relate to fixed-argv, `shell=False`, read-only subprocess calls. Each has an
adjacent explanatory comment. Bandit exit code is `0` after the change.

## 2. Before/after verification matrix

| Check | Before (baseline at `4299a9d`) | After (this branch) | Status |
| --- | --- | --- | --- |
| `is_python(tools/graphify/common.py)` | `False` | `True` | VERIFIED |
| tools-only change selects Python CI | test absent; inferred skip | test passes, `python_required=true` | VERIFIED |
| `compile_paths_json` | `["scripts", "tests"]` | `["scripts", "tests", "tools"]` | VERIFIED |
| Bandit command | `-r scripts -x scripts/check_site.py` | `-r scripts tools -x scripts/check_site.py` | VERIFIED |
| Bandit scan of `scripts tools` | 6 Low findings, exit `1` | 0 findings, exit `0` | VERIFIED |
| Graphify tests | `Ran 41 tests`, `OK` | `Ran 41 tests`, `OK` | VERIFIED |
| New regression tests | did not exist | `Ran 3 tests`, `OK` | VERIFIED |
| Full unittest suite | `Ran 1197 tests`, `FAILED (failures=47, errors=123, skipped=44)` | `Ran 1200 tests`, `FAILED (failures=47, errors=123, skipped=44)` | VERIFIED — no new failures; +3 passing tests |
| Action pin check | exit `0`, 48 files | exit `0`, 48 files | VERIFIED |
| `git diff --check` | exit `0` | exit `0` | VERIFIED |
| YAML parse | 43 workflows parsed | 43 workflows parsed | VERIFIED |
| Hosted CI on new branch | n/a | not yet run | UNVERIFIED / BLOCKED until PR exists |

The persistent 47 failures and 123 errors are Windows-harness artifacts
classified in the audit; they are unchanged in count and were not suppressed.

## 3. Exact verification commands and final output

```text
python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
Ran 11 tests in 0.107s
OK
TARGETED_EXIT=0

python -B -m unittest discover -s tests/graphify -v
Ran 41 tests in 8.007s
OK
GRAPHIFY_EXIT=0

<temp-venv>/python.exe -m bandit -r scripts tools -x scripts/check_site.py -q
BANDIT_EXIT=0

python scripts/check_action_pins.py
Action pin check passed for 48 workflow and template files.
ACTION_PINS_EXIT=0

python -B -m unittest discover -s tests -v
Ran 1200 tests in 203.494s
FAILED (failures=47, errors=123, skipped=44)
UNITTEST_AFTER_EXIT=1

node --test tests/incident_guard.test.cjs
ℹ tests 22
ℹ pass 22
ℹ fail 0
NODE_SMOKE_EXIT=0

<temp-venv>/python.exe -c "import glob,yaml; ..."
YAML_PARSE_OK 43
YAML_PARSE_EXIT=0

git diff --check
warning: in the working copy of 'tests/graphify/test_runner.py', LF will be replaced by CRLF the next time Git touches it
DIFF_CHECK_EXIT=0
```

Bandit was installed into a temporary external virtualenv at version `1.9.4`,
matching `requirements-dev.lock`. The repository's CI installs it with
`--require-hashes`; the local install did not modify the repository or any
dependency manifest.

## 4. Checks not run / blocked

| Check | Reason | Impact |
| --- | --- | --- |
| Ruff | Not installed and not declared in `requirements-dev.lock`; no project Ruff gate exists. | UNVERIFIED |
| actionlint binary | `actionlint` is not installed locally; CI installs a pinned copy on pull requests. | UNVERIFIED locally; latest main CI security job succeeded |
| pip-audit | Not installed locally; declared in `requirements-dev.lock` and run in CI. | UNVERIFIED locally |
| Docker build / Trivy | `docker` and `trivy` are not available in this environment. | NOT RUN; no container change in this fix |
| Terraform fmt/init/validate | `terraform` is not installed; no Terraform files changed. | NOT RUN |
| Kubernetes dry-run / schema | `kubectl` is not installed; no Kubernetes files changed. | NOT RUN |
| Full Node lint/type check / console tests | `node_modules` not installed and `npm ci` would add dependency state; no Node files changed. A 22-test offline Node smoke test passed. | PARTIAL |
| Secret scanning (Gitleaks) | Local wrapper tests fail because `PATH` is cleared before invoking `git` on Windows; hosted CI at the audited SHA succeeded. | UNVERIFIED locally |
| Hosted CI on feature branch | No PR exists yet; push is available but PR creation needs authenticated tooling or owner action. | BLOCKED |
| Cloud/OIDC/RLS runtime, backup/restore, Keycloak runtime | Explicitly out of scope; no credentials, hosted access or activation approval. | BLOCKED |

No failed or unavailable check was reported as passing.

## 5. Remaining roadmap (not implemented here)

| Order | Finding | Severity / status | Recommended single next task | Owner decision needed? |
| ---: | --- | --- | --- | --- |
| 1 | F01 — two Graphify stacks with different pins/policies | P1 / CONFIRMED | Choose the canonical implementation (recommend `tools/graphify` 0.9.113), deprecate or align `scripts/integrations/graphify_portfolio.py`, and update README/docs. | **Yes** — determines public CLI and migration path. |
| 2 | F03 — ledger/STATE lag merged #720/#723 | P2 / CONFIRMED | On a new reviewed branch, reconcile exact PR/head/merge SHAs and CI run IDs; keep gates unchanged. | No, but requires CI run evidence. |
| 3 | F04 — wheel hash not enforced | P2 / CONFIRMED | Add optional `--require-wheel-sha256` that verifies the installed artifact before extraction; keep current version check as fallback. | No. |
| 4 | F05 — stale `bun.lock` | P2 / CONFIRMED | Remove the unused lockfile or regenerate it from the current `package.json`; add a test that CI and lockfile manager agree. | Yes, if Bun is intentionally supported. |
| 5 | F08 — unbounded directory walks | P3 / INFERRED | Add a file-count cutoff to `rglob("*")` snapshots with a fail-closed error and synthetic test. | No. |
| 6 | F09 — missing version comments in `.md` workflow sources | P3 / CONFIRMED | Add comments and extend `check_action_pins.py` to require them; update fixtures. | No. |

## 6. Gate status

P01 managed SaaS: **BLOCKED / NO-GO**.
AI-9 detection quality: **BLOCKED**.
Codex agent runtime acceptance: **OPEN**.
This remediation changes none of them. No merge, deployment, cloud change,
database migration, Terraform apply/destroy, permission change or paid service
was performed.

## 7. Recommended next single remediation task

Task 1 above: obtain the owner's decision on which Graphify implementation is
canonical, then deprecate or align the other stack. It is the only remaining
confirmed P1 and it directly reduces the risk of two different privacy,
pinning and reporting contracts being used under the same product name.

## 8. Rollback

See [`docs/runbooks/REMEDIATION_ROLLBACK.md`](../runbooks/REMEDIATION_ROLLBACK.md).
No production state is changed by this fix; rollback is a feature-branch revert
and does not affect deployed Pages or any hosted resource.

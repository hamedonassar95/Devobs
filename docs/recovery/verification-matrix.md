# Recovery verification matrix

**Branch / base (VERIFIED):** `feature/repository-recovery-hardening` at `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f` before this change; `git rev-parse HEAD` and `git ls-remote origin refs/heads/main` agree.
**Evidence window (VERIFIED):** 2026-11-21, 14:20–14:45 UTC.
**Rule applied:** a check is `PASS` only with fresh output at the stated revision. `SKIPPED`, `BLOCKED` and `UNVERIFIED` are never reported as pass. A `FAIL` is retained as evidence, not suppressed.

## 1. Local checks at the base revision

| Check | Exact command | Final output (VERIFIED) | Result |
|---|---|---|---|
| Full Python suite (fresh) | `python -m unittest discover -s tests -q` | `Ran 1396 tests in 382.177s`; `FAILED (failures=47, errors=123, skipped=44)`; `BASELINE_UNITTEST_EXIT=1` | **FAIL** |
| Baseline exception classification | classification of the captured full-suite text | 78 `FileNotFoundError`, 47 `AssertionError`, 22 `ModuleNotFoundError`, 22 `ImportError`, 13 `OSError`, 6 `secure_open_unavailable`, plus one each of `DatasetValidationError`, `EvaluationError`, `AttributeError`, `PermissionError` | **FAIL** (diagnostic) |
| An older local capture | temp log `recovery-baseline-unittest.txt` | `Ran 1200 tests in 279.679s`; same failure totals; its exact source SHA was not reasserted in this session | UNVERIFIED as to SHA |
| Ledger summary | `python scripts/milestone_ledger.py --summary` | `{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}`; `LEDGER_EXIT=0` | **PASS** command, STALE data |
| Workflow YAML parse | inline `yaml.safe_load` over `.github/workflows/*.yml` | `YAML_PARSE_OK files=43`; `WORKFLOW_YAML_EXIT=0` | **PASS** (local substitute only) |
| Action SHA pin check | `python -B scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.`; `ACTION_PINS_EXIT=0` | **PASS** |
| Python compile | `python -m compileall -q scripts tests tools` | no output; `COMPILEALL_EXIT=0` | **PASS** |
| Diff hygiene | `git diff --check` | no output; `DIFF_CHECK_EXIT=0` | **PASS** |

## 2. Fresh targeted reproductions at the base revision

All six commands were rerun with `python -B -m unittest <module>` and output captured outside the working tree.

| Module | Final output (VERIFIED) | Exit | Interpreting evidence |
|---|---|---:|---|
| `tests.test_vercel_site_health` | `Ran 10 tests in 5.183s`; `FAILED (errors=9)` | 1 | `FileNotFoundError: [WinError 2]` — Bash/tool resolution; owned by REC-B01 |
| `tests.test_agentdust_readonly_adapter` | `Ran 39 tests in 0.780s`; `FAILED (failures=25, errors=13)` | 1 | `secure_open_unavailable`; production correctly fails closed |
| `tests.test_gitleaks_coverage` | `Ran 21 tests in 48.497s`; `FAILED (failures=17)` | 1 | `AssertionError: 1 != 0 : ... Git unavailable or timed out` |
| `tests.test_p01_keycloak_external_plan` | `Ran 6 tests in 7.732s`; `FAILED (failures=1)` | 1 | Expected `EXTERNAL_ROUTE_PLAN_BLOCKED` gate; do not "fix" |
| `tests.test_intelligence_api_security` | `Ran 1 test in 0.001s`; `FAILED (errors=1)` | 1 | `ModuleNotFoundError: No module named 'jwt'` — missing declared dependency |
| `tests.test_incident_evals` | `Ran 17 tests in 0.094s`; `FAILED (errors=1)` | 1 | `OSError: [WinError 1314] A required privilege is not held by the client` |

## 3. Checks on this branch's change

| Check | Exact command | Final output (VERIFIED) | Result |
|---|---|---|---|
| Validator behavioural tests | `python -B -m unittest tests.test_two_agent_tasks -v` | `Ran 32 tests in 0.975s`; `OK`; `TWO_AGENT_EXIT=0` | **PASS** |
| Regression proof (revert/restore) | temporarily restore `HEAD` validator, run tests, then restore patched file | with original script: `Ran 32 tests ... FAILED (failures=13)`, `REVERTED_FIX_EXIT=1`; after restore: `Ran 32 tests ... OK`, `RESTORED_FIX_EXIT=0`, `DIFF_CHECK_EXIT=0` | **PASS** — new tests catch the fixed defects |
| Python compile | `python -m compileall -q scripts tests tools` | `COMPILEALL_EXIT=0` | **PASS** |
| Action pins | `python -B scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.`; `ACTION_PINS_EXIT=0` | **PASS** |
| Diff hygiene | `git diff --check` | `DIFF_CHECK_EXIT=0` | **PASS** |
| Change size | `git diff --stat` | `2 files changed, 126 insertions(+), 12 deletions(-)` | VERIFIED |
| Ownership scan | dirty-file scan over all active worktrees for the two changed files and the four recovery docs | `SCAN_DONE` with no `DIRTY` lines | **PASS** at this snapshot; recheck before edits |

The full Python suite was **not** rerun after this change. Its base result remains `FAIL`, so no claim is made that the whole suite passes here.

## 4. Hosted evidence (public HTML / embedded run data only)

| Check | Source | Final observation (VERIFIED unless labelled) | Result |
|---|---|---|---|
| Open PR count | public PR list query `is:pr is:open` | `Open 1 (1)`, `Closed 691 (691)`; sole PR is Draft #741, head `04c6b4e2e38ddd858d320baeff5da9c4c2f2a7ad`, `isDraft: true` | VERIFIED |
| PR #739 CI | run `44911030553` | `WORKFLOW_RUN_STATUS_COMPLETED`, `WORKFLOW_RUN_CONCLUSION_SUCCESS`, created `2026-11-21T13:52:30Z` | **PASS** (that SHA only) |
| PR #740 CI | run `44910604496` | `WORKFLOW_RUN_STATUS_COMPLETED`, `WORKFLOW_RUN_CONCLUSION_SUCCESS`, created `2026-11-21T13:47:24Z` | **PASS** (that SHA only) |
| PR #741 CI | run `44913420874` | `WORKFLOW_RUN_STATUS_COMPLETED`, `WORKFLOW_RUN_CONCLUSION_FAILURE`, created `2026-11-21T14:20:29Z`; failing job attribution UNVERIFIED | **FAIL** (owner's branch) |
| PR #739 CodeQL | run `44911028864` | previously observed completed successfully | VERIFIED (prior capture) |
| Earlier exact-head runs | #733 `44892050714`, #734 `44892337191`, #736 `44897966027`, #737 `44901488605`, #738 `44906235546`, #739 `44911030553` | recorded in prior capture | VERIFIED (prior capture) |
| Exact CI/CodeQL for `bf8bf31` and this branch head | GitHub REST / checks UI | combined status previously `pending`, `total_count=0`; full log view requires sign-in. Not established. | **UNVERIFIED** |
| Branch protection rulesets | `GET /repos/{owner}/{repo}/branches/main` and ruleset API | unauthenticated snapshot showed `protected=true`, `protection.enabled=false`, `required_status_checks.enforcement_level="off"`, `contexts=[]`, `checks=[]`; ruleset state requires auth | **UNVERIFIED** |
| REST rate limit | `GET https://api.github.com/rate_limit` | HTTP `200`, `now=2026-11-21T14:23:22.752Z`, `core.remaining=0`, `core.limit=60`, reset `2026-11-21T15:05:02Z` | **BLOCKED** until reset/auth |

## 5. Not run — explicit SKIPPED/BLOCKED inventory

| Item | Reason | Status |
|---|---|---|
| Hosted Ubuntu CI and CodeQL on this branch | no authenticated PR creation and no push of this branch | BLOCKED |
| `actionlint` / ShellCheck job | tool not found locally; hosted job not observed for this SHA | SKIPPED |
| Docker, Trivy, Terraform, OpenTofu, `kubectl`, Bandit, Gitleaks CLI, Semgrep CLI | tool not found locally (`CommandNotFound`) | SKIPPED |
| Node `node --check` / `node --test` batches | PowerShell execution policy blocked `npm.ps1`; `node_modules` absent | BLOCKED |
| Keycloak HTTPS discovery/JWKS runtime | AGENTS.md exception is not active until the reconciliation PR merges; no per-run approval | BLOCKED |
| Live OIDC/JWKS, tenant isolation, backup restore, alert delivery, provider billing, cloud state | no production authorization | BLOCKED |
| `gh auth status` / Draft PR creation | current shell: `gh` not found (`CommandNotFoundException`); earlier attempt: unauthenticated (`gh auth login` required, `PR_CREATE_EXIT=4`) | BLOCKED |
| Google Cloud commands | owner's machine only; explicitly out of sandbox scope | BLOCKED |

## 6. Interpretation

- **PASS** applies only to rows with fresh, successful output at the stated revision.
- The base full suite is **FAIL**; REC-B01 owns those failures, and this branch neither masks nor duplicates them.
- The validator patch is **PASS** for its own behavioural suite; it does not make AUD-01/AUD-12 trusted, and those remain OPEN in the defect register.
- P01/AI-9/Codex gates are **unchanged**: NO-GO / BLOCKED / OPEN respectively.

## 7. Final branch publication state

- Local commits (VERIFIED): `d46d201efff4ed403228cd699ed73a5f6aa40914` (validator fix), `fd246554f1cf00fc0ba4d2885dd1f80643333f93` (recovery docs). Base `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f`; `git rev-list --left-right --count origin/main...HEAD` → `0	2`.
- Push (VERIFIED): `git push -u origin feature/repository-recovery-hardening` → `* [new branch] feature/repository-recovery-hardening -> feature/repository-recovery-hardening`, `PUSH_EXIT=0`; `git ls-remote origin refs/heads/feature/repository-recovery-hardening` → `fd246554f1cf00fc0ba4d2885dd1f80643333f93`.
- Draft PR creation: **BLOCKED**. `gh` is not installed or on `PATH` in this session (`GH_NOT_ON_PATH`; no executable in standard install locations). The earlier session also recorded unauthenticated `gh` and an exhausted REST core rate limit. No authenticated PR API call was made. Owner can open the Draft PR at the push-provided URL: `https://github.com/hamedonassar95/Devobs/pull/new/feature/repository-recovery-hardening`.
- Hosted CI/CodeQL on `fd24655` is UNVERIFIED; no check claim is made for the published head.

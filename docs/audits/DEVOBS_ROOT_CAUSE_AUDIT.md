# Devobs root-cause audit — 2026-11-20

**Audited revision:** `4299a9d47f94b479f0935dd25ee5c5309eb8e1d1`
(`origin/main`, fetched with `git fetch origin --prune`, exit `0`).
**Working branch:** `feature/devobs-root-cause-repair`, created from that
revision; `main` was never modified.

**Evidence labels:** VERIFIED = local command output, repository file, or public
API response recorded below; UNVERIFIED = not independently reproduced;
ASSUMED = reasoned from available evidence; BLOCKED = tool/permission/runtime
unavailable. Unverified suspicions are not defects.

## 1. Executive summary

- **No CONFIRMED P0 finding.** No credential exposure, secret read, source
  upload, tenant-isolation failure or authentication bypass was found. Existing
  security checks remain intact.
- **Selected root cause (CONFIRMED, P1):** the change-impact classifier and CI
  static-analysis paths cover `scripts/` and `tests/` but omit `tools/`. The
  merged Graphify package lives in `tools/graphify/`, so a tools-only change can
  skip Python CI and is never compiled or scanned by Bandit. Reproduced locally
  with `is_python(PurePosixPath("tools/graphify/common.py")) == False`.
- **Fixed in this branch:** include `tools/` in change selection, compile paths
  and Bandit target; remove one dead `subprocess` import; add targeted,
  justified `# nosec` annotations for six low-severity subprocess findings
  (two import findings and four call-site findings) in the Graphify package;
  add regression tests.
- **Not fixed here:** two independently implemented Graphify stacks, stale
  governance records, an unverified wheel-hash runtime check, and a stale Bun
  lockfile. These are recorded in the roadmap with owner decisions where needed.
- **Documented gates are unchanged:** P01 = BLOCKED/NO-GO, AI-9 = BLOCKED,
  Codex runtime acceptance = OPEN. No hosted, production or paid action was run.

## 2. Scope and method

Inspected: root and nested `AGENTS.md` (only the root file exists), dependency
manifests and locks, 45 workflow files plus 11 authored workflow artifacts,
`scripts/`, `tests/`, `tools/graphify/`, `assets/graphify/`, infrastructure
(`infra/terraform/`, `k8s/`, `monitoring/`, `dev/keycloak/`), readiness and gate
documentation, the milestone ledger, public GitHub issues/PRs/workflow runs, and
the existing Graphify docs and adapters. Two read-only specialist audits were
run in parallel; their claims were rechecked against local files and commands
before inclusion.

Official platform references used:
- GitHub Actions workflow syntax: <https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#about-yaml-syntax-for-workflows>
- GitHub rulesets API (`bypass_actors` visibility): <https://docs.github.com/en/rest/repos/rules?apiVersion=2022-11-28#get-a-repository-ruleset>
- Bandit `# nosec` suppression syntax: <https://bandit.readthedocs.io/en/latest/config.html>

## 3. Baseline (before changes)

### 3.1 Repository and CI state

| Check | Command / source | Result | Label |
| --- | --- | --- | --- |
| Revision | `git rev-parse HEAD` | `4299a9d47f94b479f0935dd25ee5c5309eb8e1d1` | VERIFIED |
| Ledger | `python scripts/milestone_ledger.py --summary` | `latest_pr: 717`, `merged_milestones: 304`, open gates 3 | VERIFIED |
| Action pins | `python scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` exit `0` | VERIFIED |
| Compile baseline | `python -m compileall -q scripts tests tools` | exit `0` | VERIFIED |
| Graphify unit tests | `python -m unittest discover -s tests/graphify -v` | `Ran 41 tests`, `OK`, exit `0` | VERIFIED |
| Site contract | `python scripts/check_site.py` | `Page contract and HTTP smoke checks passed.` exit `0` | VERIFIED |
| Full unittest suite | `python -m unittest discover -s tests -v` | `Ran 1197 tests`, `FAILED (failures=47, errors=123, skipped=44)` | VERIFIED |
| Latest `main` CI | public REST `GET /actions/runs?branch=main&per_page=10` → `200`; run `44645443400` | `CI` conclusion `success` at `4299a9d`; 19 jobs, `FAILING=0` | VERIFIED |
| Open PRs | public REST `GET /pulls?state=open&per_page=20` → `200` | `COUNT=0` | VERIFIED |
| Branch protection | public REST `GET /branches/main` → `200` | `protected=True`; active ruleset `Protect main` id `24507159` | VERIFIED |

### 3.2 Baseline failure triage

The large full-suite failure count is dominated by Windows-only harness
limitations, not by product defects. Representative evidence:

- `OSError: [WinError 1314] A required privilege is not held by the client`
  from tests that call `Path.symlink_to()` (for example
  `tests/test_actionlint_gate.py:47`, `tests/test_stage_site.py:38,84,93,167`).
  CI runs `ubuntu-24.04` (`.github/workflows/ci.yml:37`), where these fixtures
  are valid.
- `secure_open_unavailable` from `scripts/agentdust_readonly_adapter.py:186`
  because `os.O_NOFOLLOW`/`O_DIRECTORY` are unavailable on Windows. The code
  fails closed as designed.
- `FileNotFoundError: [WinError 2]` in tests that clear `PATH` before invoking
  Unix tools (`tests/test_gitleaks_coverage.py:147-149`) or import `jwt`, which
  is installed from the hash-locked API requirements in CI.
- `test_stage_site` path errors arise from Windows 8.3 short-name canonicalization
  (`NASSAR~1` versus `NASSAR FAMILY`) in temporary paths.

These are **ASSUMED environment-specific**, not confirmed defects. They were
not modified and are not counted as fixed. The latest hosted CI run at the
audited SHA succeeded with all 19 jobs passing, which is consistent with that
classification but is not a re-run of every local test on Windows.

## 4. Findings

| ID | Severity | Status | Affected files | Summary |
| --- | --- | --- | --- | --- |
| F01 | P1 | CONFIRMED | `scripts/integrations/graphify_portfolio.py`, `tools/graphify/*`, `README.md`, `docs/architecture/graphify-integration.md`, `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md` | Two Graphify stacks coexist: `0.9.112` / policy `devobs-graphify-portfolio-v1` versus `0.9.113` / policy `devobs-repository-intelligence-v1`. Different privacy controls and report schemas. Needs owner decision on canonical implementation. |
| F02 | P1 | CONFIRMED | `scripts/assess_change.py:104-105`, `.github/workflows/ci.yml:75,344-345` | `tools/` Python is not selected by `is_python()`, not compiled by reusable CI, and not scanned by Bandit. **Selected for remediation.** |
| F03 | P2 | CONFIRMED | `STATE.md`, `docs/MILESTONE_LEDGER.json` | Ledger records `latest_pr: 717` although HEAD contains merged #720 and #723. Governance evidence lags source; no exact-head CI evidence recorded in ledger. |
| F04 | P2 | CONFIRMED | `tools/graphify/common.py:18`, `runner.py:133-141` | `PINNED_WHEEL_SHA256` is reported in metadata but not enforced at runtime; identity relies on `graphify --version`. |
| F05 | P2 | CONFIRMED | `apps/ai-intelligence-console/bun.lock`, `package.json`, `ci.yml:252-257` | Unused/stale Bun lockfile names `react-example` and omits current packages; CI authoritatively uses `package-lock.json`. |
| F06 | P2 | CONFIRMED | `scripts/graphify/*.py`, `requirements*.txt` | No Python packaging manifest; CLI wrappers inject `sys.path`; Graphify binary is supplied externally by design. |
| F07 | P1 | CONFIRMED | `README.md:14-23`, both Graphify docs | P01/AI-9/Codex gates remain BLOCKED/OPEN. No Graphify evidence satisfies their acceptance criteria. |
| F08 | P3 | INFERRED | `tools/graphify/common.py:383-388`, `multi_repo.py:187-194` | Unbounded `rglob("*")` walks may be slow on very large portfolios; no resource cutoff observed. |
| F09 | P3 | CONFIRMED | `scripts/check_action_pins.py` (via subagent scan) | Ten remote `uses:` references in `.github/workflows/*.md` authoring templates lack version comments; generated workflows are compliant. |

No P0 finding was confirmed. Live hosted cloud state, hosted RLS denial and
ruleset bypass actors are **UNKNOWN**; public API omits some fields to
non-writers, and no authenticated call or token was used.

## 5. Selected root cause — F02

### Reproduction evidence

```text
python -B -c "import importlib.util, pathlib; from pathlib import PurePosixPath; \
spec=importlib.util.spec_from_file_location('assess_change','scripts/assess_change.py'); \
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); \
print('TOOLS_PY_IS_PYTHON', m.is_python(PurePosixPath('tools/graphify/common.py')))"
# TOOLS_PY_IS_PYTHON False

python -B -m unittest tests.test_python_source_coverage -v   # before fix
# FAIL: test_tools_python_file_is_classified_as_python  -> False is not true
# FAIL: test_ci_compiles_and_scans_tools_directory      -> expected tools missing
```

CI wiring confirmed by reading `.github/workflows/ci.yml:75`
(`compile_paths_json: '["scripts", "tests"]'`) and `:345`
(`python3 -m bandit -r scripts -x scripts/check_site.py`). The reusable workflow
only compiles the paths supplied in that input
(`.github/workflows/reusable-python-ci.yml:127-143`).

### Root cause

The Python classification heuristic was written before `tools/` became a
first-class Python source directory. Adding the Graphify package under `tools/`
therefore created source that is invisible to change selection and static
checks. This is a single root cause with three coupled manifestations:
selection, compilation and Bandit coverage.

### Impact analysis (Graphify)

A fresh local index was built from the audited revision using the verified
pinned offline CLI (`graphify 0.9.113`):

```text
python audit_graphify_extract.py
EXTRACT_EXIT 0
NODES 9118
EDGES 17440
GRAPH_BYTES 7444135

graphify query 'is_python()' --graph <external-index>/graphify-out/graph.json --depth 1 --budget 800
# NODE is_python() [src=scripts/assess_change.py loc=L104]
# EDGE risk_signals() --calls--> is_python() at=scripts/assess_change.py:L169
# EDGE main() --calls--> is_python() at=scripts/assess_change.py:L221
# EDGE test_python_dependency_automation.py --imports_from--> assess_change.py
```

Affected components identified before editing: `is_python()`, `risk_signals()`,
`main()`, `tests/test_python_dependency_automation.py`, `ci.yml`, and
`tools/graphify/*`. No source was uploaded; extraction used blank provider keys,
`GRAPHIFY_BACKEND=none`, disabled query logging and an external output root.

### Proposed remediation and risk

- Add `("tools",)` to `is_python()`.
- Add `"tools"` to `compile_paths_json` and to the Bandit target.
- Remove dead `subprocess` import in `tools/graphify/repository_intelligence.py`.
- Add explicit, justified `# nosec` annotations for the four low-severity
  subprocess findings in the Graphify package. No security test is disabled.
- Add behavioral tests for classification and change selection, plus a workflow
  contract test for compile/Bandit coverage.

Risk: minimal and reversible. Adding `tools/` to Bandit initially surfaced six
low-severity findings, all in the new Graphify package; they were reviewed and
explicitly justified. CI remains fail-closed. Rollback is described in
`docs/runbooks/REMEDIATION_ROLLBACK.md`.

## 6. Verification after remediation

See `docs/roadmap/REMEDIATION_ROADMAP.md` for the before/after matrix and the
exact commands with final output lines. The selected fix is verified locally by
regression tests, compileall, Bandit, action-pin check, Graphify tests and
`git diff --check`; hosted CI on the new branch remains **UNVERIFIED** until a
Draft PR is opened and GitHub runs it.

## 7. Production readiness

| Gate | Documented status | Effect of this audit |
| --- | --- | --- |
| P01 managed SaaS | BLOCKED / NO-GO (`docs/p01/P01_NO_GO_DECISION_2026-11-19.md:3,33`) | Unchanged. No hosted account, database or deployment touched. |
| AI-9 detection quality | BLOCKED (`docs/AI9_V3_INDEPENDENT_EVAL_GATE.md:57-59`) | Unchanged. |
| Codex agent runtime | OPEN (`docs/CODEX_AGENT_OPERATING_MODEL.md:61-70`) | Unchanged. Configuration is not runtime proof. |
| CI/CD integrity | Latest audited SHA succeeded; new branch not yet run | Improved by F02 fix; new-branch CI unverified. |
| GitHub OIDC / WIF | Source uses `id-token: write` and role assumption in `aws.yml`; live exchange UNKNOWN | Unchanged. |
| Multi-tenant isolation | Real disposable PostgreSQL RLS job exists in CI; hosted denial UNKNOWN | Unchanged. |
| Observability / alerting | Monitoring manifests and incident workflows present; live proof UNKNOWN | Unchanged. |
| Backup / rollback | Runbook added for this change; hosted restore proof UNKNOWN | Unchanged. |

## 8. Security risks and open assumptions

- No secret was read, printed, created or changed. No production system, cloud
  provider, database migration, Terraform apply/destroy, Keycloak runtime or
  paid inference was used.
- The Graphify wheel hash constant remains metadata only (F04); the CLI version
  string is enforced. This is a supply-chain hardening opportunity, not a
  confirmed exploit.
- Public API 404s and omitted fields are treated as UNKNOWN, not as proof of
  absence or permission.
- Windows local-test failures are classified as ASSUMED environment artifacts;
  they were not silently skipped, deleted or weakened.

## 9. Conclusion

One P1 root cause was confirmed and fixed with regression coverage. The audit
does **not** claim that all problems are resolved: F01, F03-F06, F08 and F09
remain on the roadmap, and all three release gates remain closed pending owner
evidence and approval.

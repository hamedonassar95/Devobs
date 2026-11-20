# Devobs recovery roadmap — 2026-11-20

**Scope:** `feature/devobs-recovery-readiness` from `origin/main`
`cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1`. This roadmap records one bounded
repair, its verification, all remaining known work, and the exact owner gates
that were **not** changed.

**Evidence source:** [`docs/audits/DEVOBS_RECOVERY_AUDIT.md`](../audits/DEVOBS_RECOVERY_AUDIT.md).
**Rollback:** [`docs/runbooks/RECOVERY_AND_ROLLBACK.md`](../runbooks/RECOVERY_AND_ROLLBACK.md).
**Canonicalization detail:** [`docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md`](../architecture/GRAPHIFY_CONSOLIDATION_PLAN.md).

## 1. Selected repair — F01a, canonical Graphify designation

**Status:** CONFIRMED root cause; bounded repair VERIFIED; full consolidation
remains owner-gated.
**Severity:** P1 (governance/supply-chain ambiguity), no P0.

### What changed

| File | Change |
| --- | --- |
| `scripts/integrations/graphify_portfolio.py` | Added canonical constants, a `DEPRECATED` stderr/CLI-help notice, and `legacy`/`canonical` fields in JSON reports. Legacy behavior and 0.9.112 pin unchanged. |
| `tests/test_graphify_portfolio.py` | Added `CliTests.test_legacy_cli_identifies_canonical_implementation`; proved red → green → red-on-revert → green. |
| `README.md` | Canonical stack documented first; legacy command and 0.9.112 explicitly marked. Recovery docs linked. |
| `docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md` | New canonical/legacy decision record and migration path. |
| `docs/architecture/graphify-integration.md` | Explicit canonical-status subsection. |
| `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md` | Historical rollout document marked legacy; canonical pointer added. |
| Recovery audit/roadmap/runbook | New evidence and rollback records. |

### What did not change

- No Graphify implementation was deleted, merged or re-pinned.
- No CLI flag, default, output contract, safety check or test was removed.
- No GitHub workflow, permission, gate, secret, cloud resource, database,
  Terraform state or production setting was changed.
- The `tools/graphify` 0.9.113 package and legacy 0.9.112 script remain intact.

## 2. Before/after verification matrix

| Check | Before | After | Label |
| --- | --- | --- | --- |
| Canonical implementation declared | Two current surfaces in README/docs | `tools/graphify` declared canonical in README, architecture doc, CLI help and JSON report | VERIFIED |
| Legacy warning | None | `DEPRECATED` on stderr, `--help` epilog and JSON `deprecation_notice` | VERIFIED |
| Machine-readable canonical metadata | None | `legacy=true`, `canonical.implementation=tools/graphify`, `canonical.cli=scripts/graphify/multi_repo.py`, `canonical.pinned_version=0.9.113` | VERIFIED |
| Legacy portfolio tests | `Ran 26 tests`, OK | `Ran 27 tests`, OK | VERIFIED |
| New regression test | Did not exist; red when added before source fix | green; red after temporary source revert; green after restore | VERIFIED |
| F02 source coverage | Present at base | unchanged; 3 targeted tests OK | VERIFIED |
| Graphify package tests | `Ran 41 tests`, OK | unchanged; `Ran 41 tests`, OK | VERIFIED |
| Full Windows unittest suite (baseline) | `Ran 1200 tests`, `FAILED (failures=47, errors=123, skipped=44)` | after-change rerun recorded below; no failures suppressed | VERIFIED |
| Action pin check | exit `0`, 48 files | unchanged | VERIFIED |
| Hosted CI at base `cecae6c` | run `44650319512`, success | no CI-related source changed | VERIFIED |
| P01 / AI-9 / Codex gates | BLOCKED / BLOCKED / OPEN | unchanged | VERIFIED |

## 3. Exact commands and final output lines

All commands were run from `C:\DevProjects\Devobs` in this session.

```text
git fetch origin --prune
  4299a9d..cecae6c  main -> origin/main

git checkout -b feature/devobs-recovery-readiness origin/main
  Switched to a new branch 'feature/devobs-recovery-readiness'

python scripts/milestone_ledger.py --summary
  {"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}

python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
  Ran 11 tests in 0.198s
  OK

python -B -m unittest discover -s tests/graphify -v
  Ran 41 tests in 21.460s
  OK

python -B -m unittest tests.test_graphify_portfolio.CliTests.test_legacy_cli_identifies_canonical_implementation -v
  BEFORE: FAILED (failures=1); REGRESSION_BEFORE_EXIT=1
  AFTER:  Ran 1 test; OK; REGRESSION_AFTER_EXIT=0
  REVERT: FAILED (failures=1); REGRESSION_REVERT_EXIT=1
  RESTORE: Ran 1 test; OK; REGRESSION_RESTORE_EXIT=0

python -B -m unittest tests.test_graphify_portfolio -v
  Ran 27 tests in 44.989s
  OK
  PORTFOLIO_EXIT=0

python -B -m unittest discover -s tests -v
  Ran 1200 tests in 279.679s
  FAILED (failures=47, errors=123, skipped=44)
  BASELINE_UNITTEST_EXIT=1

python scripts/check_action_pins.py
  Action pin check passed for 48 workflow and template files.
  ACTION_PINS_EXIT=0

git diff --check
  DIFF_CHECK_EXIT=0
```

Post-change full-suite, compile and Bandit results are appended in section 6
after those checks are executed.

## 4. Checks unavailable or blocked

| Check | Reason | Impact |
| --- | --- | --- |
| `npm` install/lint/type check | PowerShell execution policy blocks `npm.ps1`; `node_modules` not installed. Full Node suite NOT RUN; no Node source changed. | PARTIAL |
| `ruff`, `actionlint` binary, `pip-audit` | Not installed locally. Hosted security job succeeded at base. | UNVERIFIED locally |
| Docker build / Trivy | No container runtime/scanner in environment. | NOT RUN |
| `terraform fmt/init/validate/plan`, `kubectl --dry-run` | CLIs unavailable; no Terraform/Kubernetes source changed. | NOT RUN |
| Fresh GitHub REST metadata after rate limit | Unauthenticated API returned HTTP 403; earlier successful responses and local git/CI evidence used and labeled. | BLOCKED |
| Hosted OIDC/WIF, RLS denial, backup restore, alert delivery, Keycloak runtime | No credentials or approval; explicit policy block. | BLOCKED |
| Graphify runtime extraction/wheel hash | `graphify` not installed locally; prior offline graph queried only. | BLOCKED |

No unavailable or unexecuted check is reported as passing.

## 5. Remaining prioritized work

| Order | Finding | Severity / status | Single next task | Owner decision |
| ---: | --- | --- | --- | --- |
| 1 | F03 governance lag | P2 / CONFIRMED | Reconcile #718–#724 in `MILESTONE_LEDGER.json`, `STATE.md`, `DEVOBS_READINESS_CURRENT.md` and `tests/test_milestone_ledger.py` with exact SHAs and CI run `44650319512`. | No, but fresh API evidence needed. |
| 2 | F04 Graphify wheel hash | P2 / CONFIRMED | Add explicitly opted-in local-wheel hash verification before extraction; keep `--version` fallback; add mismatch test. | No. |
| 3 | F10 P01 readiness | P1 / BLOCKED | Rebind NO-GO matrix to a new exact SHA after owner-approved spend/provider/OIDC/RLS/TLS/backup/owner/release evidence. | **Yes**; no hosted access authorized. |
| 4 | F11 AI operations | P1 AI-9 BLOCKED; Codex OPEN | Obtain independent natural-incident corpus; in a trusted Codex client run `codex mcp list` and one harmless public Docs lookup. | **Yes** for corpus/provenance; no paid inference. |
| 5 | F05/F13 lockfiles | P2 / CONFIRMED | Decide npm-only vs pinned Bun; remove or regenerate `bun.lock`; add `bun.lock` to Node change selector if retained. | **Yes** if Bun is supported. |
| 6 | F08 template pin comments | P2 / PARTIAL | Extend `check_action_pins.py` to require version comments in `.md` templates; add fixtures. | No. |
| 7 | F07 filesystem bounds | P3 / INFERRED | Add in-loop file/entry counters and symlink-directory policy; synthetic oversized-tree test. | No. |
| 8 | F01 full consolidation | P1 / owner-gated | Migrate callers to canonical CLI, then deprecate/remove legacy script in a separate reviewed PR. | **Yes**. |
| 9 | F12 operational reliability | P2 / Partial | Hosted restore, SLO/error budget and live alert-delivery test. | **Yes**. |
| 10 | F14 duplicated skills | P3 / CONFIRMED | Declare `.agents/skills/` source of truth and add sync check. | No. |

## 6. Post-change validation log

All commands below were run from `C:\DevProjects\Devobs` on the final source
state (`6635c52` at capture time). Logs are in the approved temporary directory.

```text
git diff --check
  DIFF_CHECK_EXIT=0

python -B -m compileall -q tools/graphify scripts/graphify scripts/integrations/graphify_portfolio.py
  COMPILEALL_EXIT=0

python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
  Ran 11 tests in 0.097s
  OK
  TARGETED_AFTER_EXIT=0

python -B -m unittest discover -s tests/graphify -v
  Ran 41 tests in 6.796s
  OK
  GRAPHIFY_AFTER_EXIT=0

python -B -m unittest tests.test_graphify_portfolio -v
  Ran 27 tests in 30.140s
  OK
  PORTFOLIO_AFTER_EXIT=0

Bandit 1.9.4 (local audit virtual environment):
  python -m bandit -r scripts tools -x scripts/check_site.py -q
  90 manager warning lines about "Test in comment" (pre-existing comment text)
  0 issue-summary lines
  BANDIT_AFTER_EXIT=0

python -B -m unittest discover -s tests -v
  BASELINE: Ran 1200 tests in 279.679s; FAILED (failures=47, errors=123, skipped=44)
  AFTER:    Ran 1201 tests in 196.234s; FAILED (failures=47, errors=123, skipped=44)
  AFTER_UNITTEST_EXIT=1
  Header comparison: BASE_HEADERS=170, AFTER_HEADERS=170, NEW_IN_AFTER=0, MISSING_FROM_AFTER=0

python scripts/check_action_pins.py
  Action pin check passed for 48 workflow and template files.
  ACTION_PINS_AFTER_EXIT=0

node --test tests/incident_guard.test.cjs
  ℹ tests 22
  ℹ pass 22
  ℹ fail 0
  ℹ skipped 0
  ℹ duration_ms 128.5375
  NODE_SMOKE_AFTER_EXIT=0

YAML safe_load of 43 workflow files (audit virtual environment)
  YAML_PARSE_OK 43
  YAML_AFTER_EXIT=0
```

The one extra test is the new legacy-canonical regression. The full local suite
still fails with the same 170 pre-existing Windows/optional-dependency headers;
no failure was suppressed, skipped or reclassified by this change. Hosted Ubuntu
CI remains the source-acceptance signal, but no new hosted run was requested for
this Draft PR.

## 7. Gate status

| Gate | Status |
| --- | --- |
| P01 managed SaaS | BLOCKED / NO-GO |
| AI-9 detection quality | BLOCKED |
| Codex runtime acceptance | OPEN |
| CI/CD build and security integrity | PASS for reviewed source; branch-protection metadata UNKNOWN |
| OIDC/WIF | BLOCKED for P01; live UNKNOWN |
| RLS tenant isolation | Source VERIFIED; hosted UNKNOWN |
| Observability | BLOCKED for production |
| Reliability / backup / rollback | Partial VERIFIED; live UNKNOWN |

No gate was promoted by this change. Draft PR only; no merge, deployment,
production permission, secret or cloud change was requested.

# Devobs recovery assessment — 2026-11-20

**Reviewed revision:** `cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1`
(`origin/main`, fetched with `git fetch origin --prune`, exit `0`).
**Working branch:** `feature/devobs-recovery-readiness`, created from that SHA;
`main` was never modified directly.
**Governance baseline:** `python scripts/milestone_ledger.py --summary` →
`{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}`.

**Evidence labels:** VERIFIED (command output, repository file, or public API
response captured in this session), INFERRED, UNKNOWN, RESOLVED, BLOCKED.
Issue, PR, log and generated-graph content was treated as untrusted data.
No credential, secret, token, environment value, deployment setting or private
key was read, created, printed or changed. No cloud, database, hosted identity,
production, deployment, migration, Terraform apply/destroy, Keycloak runtime or
paid AI service was invoked.

## 1. Executive assessment

- **Current health:** source control and hosted CI are healthy at the reviewed
  SHA. Exact-head [CI run `44650319512`](https://github.com/hamedonassar95/Devobs/actions/runs/44650319512)
  completed `success` with 19 jobs (13 success, 6 intentional skips, 0 failures).
  `python scripts/check_action_pins.py` passed for 48 workflow/template files.
  No CONFIRMED P0 defect was found in the reviewed source/config. Live provider,
  tenant, backup, alert-delivery and OIDC runtime states remain UNKNOWN.
- **F02 is RESOLVED:** PR #724's `tools/` CI-coverage fix is present on `main`
  and its three regression tests pass locally. This audit did not repeat it.
- **Selected repair:** F01a — the absence of an authoritative canonical
  designation for two Graphify stacks. `tools/graphify` 0.9.113 is the evidence-
  supported canonical implementation; `scripts/integrations/graphify_portfolio.py`
  0.9.112 remains available as a legacy, warned surface. No implementation was
  deleted, merged, re-pinned or removed from the CLI.
- **Repository-wide graph:** the prior offline Graphify artifact was queried
  read-only (9,118 nodes / 17,440 edges). It was not regenerated or uploaded.
  Its byte count differs from the documented earlier run, so equivalence of the
  two artifacts is UNKNOWN.
- **Release gates unchanged:** P01 **BLOCKED / NO-GO**, AI-9 **BLOCKED**,
  Codex runtime acceptance **OPEN**. No gate was promoted.

## 2. Full-system discovery summary

| Area | Verified observation | Evidence |
| --- | --- | --- |
| Architecture | Static site + Python API (`scripts/devobs_intelligence`), Node AI intelligence scripts, TypeScript/React console in `apps/ai-intelligence-console`, Python automation/CLIs, Graphify package in `tools/graphify`. | Repository tree; `render.yaml:9-19`; `apps/ai-intelligence-console/package.json:1-45`. |
| CI/CD | 48 workflow/template files; reusable Python, Node, security, RLS, Terraform, site, container and release jobs. Top-level `permissions: contents: read` in `ci.yml:26-27`; scoped `pages: write`/`id-token: write` only for eligible release. | `ci.yml`; `check_action_pins.py` output. |
| Graphify | Canonical package `tools/graphify` with thin CLI shims in `scripts/graphify/`; separate legacy portfolio orchestrator with its own pin/policy. | `tools/graphify/common.py:17-19`; `scripts/graphify/multi_repo.py:9-13`; `scripts/integrations/graphify_portfolio.py:43-44`. |
| Agents/automation | `.codex/`, `.agents/skills/`, `.claude/skills/`, generated `.github/aw/*.lock.yml`, PR-Agent/Claude/Copilot/Phase8B workflows. Configuration is not runtime acceptance evidence. | `docs/CODEX_AGENT_OPERATING_MODEL.md:3,15-21`; `.codex/config.toml:1-11`. |
| Auth/tenancy/RLS | Source RLS policies and disposable PostgreSQL job exist; hosted denial evidence does not. | `deploy/postgres/001_tenant_rls.sql:31-54`; `docs/STAGING_ACCEPTANCE.md:38-44,52`. |
| Containers/K8s/Terraform | Root `Dockerfile` uses a digest-pinned nginx base and non-root user; `k8s/` manifests exist; Terraform validates Artifact Registry configuration only and uses a placeholder backend with `-backend=false`. | `Dockerfile`; `infra/terraform/main.tf:4-7`; `ci.yml:660-665`. |
| Render | `render.yaml` declares Free PostgreSQL 17 with expiry `2026-12-05`; retirement is owner-gated. | `render.yaml:24-32`; `docs/p01/P01_NO_GO_DECISION_2026-11-19.md`. |
| Observability/reliability | Local Prometheus/Grafana starter, bounded deployment health retry, Pages rollback rehearsal; no live alert delivery, restore proof or SLO evidence. | `monitoring/README.md:7-9`; `deployment-health-check.yml:52-120`; `docs/ROLLBACK_RUNBOOK.md:9-34`. |
| Dependencies | npm manifest/lock agree; `bun.lock` is stale; Graphify binary is external and absent from hash-locked Python requirements. | `package.json:2-45`; `package-lock.json:2-36`; `bun.lock:2-32`; requirements scans. |
| Governance | Ledger/STATE/readiness docs stop at #717/#641 while main contains #718, #720, #721, #723, #724. | `docs/MILESTONE_LEDGER.json`; `STATE.md:1-7`; `docs/DEVOBS_READINESS_CURRENT.md:1-7`; `git log`. |
| Open work | 25 open issues, 0 open PRs (captured before unauthenticated REST rate limit). Recent failing CI runs were on feature branches, not current `main`. | `GET /issues?state=open`; `GET /actions/runs?per_page=100`. |

## 3. Reconciled findings

| ID | Severity | Status | Affected files | Reproduction / actual evidence | Root cause | Dependency impact | Proposed fix; regression; rollback | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | P1 | **PARTIALLY REMEDIATED** (full consolidation BLOCKED) | `tools/graphify/*`, `scripts/graphify/*.py`, `scripts/integrations/graphify_portfolio.py`, `README.md`, two Graphify docs | `tools/graphify/common.py:17-19` pins `0.9.113`; portfolio script `:43-44` pins `0.9.112`; wrappers at `scripts/graphify/multi_repo.py:9-13` import `tools.graphify.*`; README advertises both. | No authoritative canonical designation; both stacks were documented as current surfaces. | Different pins, policies, report schemas and privacy contracts under one product name; callers and tests are split (`tests/graphify/*` vs `tests/test_graphify_portfolio.py`). | Selected fix: declare canonical implementation, emit legacy warning and machine-readable report metadata; do not delete. Regression: `CliTests.test_legacy_cli_identifies_canonical_implementation`. Rollback: revert the single fix commit. | VERIFIED code/test pass; VERIFIED wrappers are shims. Deletion/merge remains BLOCKED pending owner migration decision. |
| F02 | P1 | **RESOLVED** | `scripts/assess_change.py:105`, `ci.yml:75,345` | `is_python()` includes `tools/`; compile paths `["scripts","tests","tools"]`; Bandit `-r scripts tools`; 3 regression tests pass. | Python heuristic predated first-class `tools/` source. | Tools-only changes could skip Python CI and Bandit. | Already fixed in PR #724; no action. | VERIFIED local + hosted. |
| F03 | P2 | CONFIRMED / OPEN | `docs/MILESTONE_LEDGER.json`, `STATE.md`, `docs/DEVOBS_READINESS_CURRENT.md`, `tests/test_milestone_ledger.py` | Ledger summary `latest_pr:717`; git log contains #718/#720/#721/#723/#724; test hardcodes `304`/`717`. | Ledger reconciled only in dedicated PRs; feature PRs did not update it. | Audit traceability lags source; next reconciliation must update four files together. | Add reviewed reconciliation PR with exact head/merge/CI evidence; update tests; keep gates. Rollback: revert docs commit. | VERIFIED local/git; fresh REST detail BLOCKED by HTTP 403. |
| F04 | P2 | CONFIRMED / OPEN | `tools/graphify/common.py:19`, `runner.py:135-143` | `PINNED_WHEEL_SHA256` is emitted as metadata; runtime identity checks only `graphify --version`; Graphify absent from hash-locked requirements. | Artifact hash is declared but not verified against an artifact. | Wrong/tampered artifact reporting the expected version would pass. | Add explicit local-wheel or hash-pin verification while retaining version fallback; fake-runner mismatch test. Rollback: revert verification commit. | VERIFIED source; runtime hash check NOT RUN (CLI not installed locally). |
| F05 | P2 | CONFIRMED / OPEN | `bun.lock`, `package.json`, `package-lock.json`, `ci.yml:247-257` | `bun.lock` names `react-example` and older ranges; npm lock equals manifest; CI uses `npm ci`. Stale `bun.lock` is not a Node CI selector in `assess_change.py`. | Two lockfiles for one app; Bun support never declared. | Bun users may resolve a different graph than CI; lockfile-only changes can skip Node CI. | Owner declares npm-only → remove stale lock; or pin Bun, regenerate, add consistency/CI-selector test. Rollback: restore lockfile. | VERIFIED parser/API output. |
| F06 | P2 | CONFIRMED / OPEN | `scripts/graphify/*.py`, requirements files | No `pyproject.toml`/setup manifest; wrappers inject repository root; binary supplied externally by design. | Graphify is a repo-relative tool distribution, not an installed package. | Moving wrappers or changing import layout can break imports; reproduction depends on external CLI. | Document exact install/provenance contract; add packaging only if productized. Rollback: docs revert. | VERIFIED manifest scan and wrapper smoke. |
| F07 | P3 | INFERRED / OPEN | `tools/graphify/common.py:370-395`, `adapters.py:27-46`, `multi_repo.py:187-194` | `rglob("*")` walks have no in-loop count cutoff; no explicit symlink-directory policy. Exclusions, overlap checks and source snapshots exist. | Resource bounds are applied after path materialization on very large trees. | Potential time/memory exhaustion; no confirmed incident. | Add fail-closed entry counter and symlink policy; synthetic oversized-tree test. Rollback: revert guard commit. | INFERRED; not reproduced at scale. |
| F08 | P2 | VERIFIED controls; PARTIAL | `.github/workflows/**`, `scripts/check_action_pins.py` | Pin check exit `0`; no `pull_request_target`; least-privilege defaults; 10 template `uses:` lines lack version comments. | Template authoring policy is not fully checked by the pin script. | Immutability intact; version-readability gap only. No exploit shown. | Extend checker to templates and add comments; regression fixture. Rollback: revert checker change. | VERIFIED source/scan. |
| F09 | P2 | VERIFIED reproduced; CLASSIFIED | Local Windows harness + optional API deps | Baseline `Ran 1200 tests`, `FAILED (failures=47, errors=123, skipped=44)`; 170 headers classified below. | Windows privileges/path semantics and missing API-only dependencies in local interpreter. | Local suite is not a clean signal; hosted Ubuntu CI is authoritative for source acceptance. | Do not suppress. Add POSIX guards, install API lock for local runs, verify fixture digest. Rollback: n/a (diagnosis). | VERIFIED classification; 2 digest cases UNVERIFIED. |
| F10 | P1 release blocker | BLOCKED / NO-GO | P01 decision/matrix, `render.yaml`, RLS/identity source | All eight P01 controls `SPEND`, `PROVIDER`, `OIDC`, `RLS`, `TLS_NETWORK`, `BACKUP`, `OWNER`, `RELEASE` are BLOCKED in the fixed-SHA decision; Free PostgreSQL expires `2026-12-05`. | No fresh hosted evidence for spend cap, provider, OIDC, tenant denial, TLS, backup/restore, owner and release approval. | Blocks SaaS activation, paid resources and production AI diagnostics. | Owner-approved staging evidence and decision; no action here. | VERIFIED source; live state UNKNOWN. |
| F11 | P1/P2 | AI-9 BLOCKED; Codex OPEN | AI-9 gate doc, `.codex/*`, agent specs | AI-9 evidence is synthetic-only and `check_ai9_evidence.py` never returns GO; Codex config/docs explicitly say configuration is not runtime proof. | No independent natural-incident corpus or trusted-client MCP handshake/lookup. | Blocks detector authorization and agent-runtime acceptance. | Preregistered independent corpus; trusted-client `codex mcp list` + harmless public lookup. | VERIFIED source. |
| F12 | P2 | Partial VERIFIED; live UNKNOWN | `deployment-health-check.yml`, `monitoring/*`, rollback docs | Bounded health retry and Pages verification succeed; restore jobs skipped; local monitoring has no external receiver. | Live restore, SLO and alert-delivery evidence absent. | Operational incidents cannot be shown to page humans or meet RPO/RTO. | Exercise isolated hosted restore and live alert test; define SLOs. | VERIFIED source/CI; live UNKNOWN. |
| F13 | P2 | CONFIRMED / OPEN | `scripts/assess_change.py:112-123`, `bun.lock` | Node selectors list `package.json`/`package-lock.json` only; `bun.lock` change does not select Node CI. | Selector drift after the lockfile was added. | A lockfile-only change can pass `validate` without Node tests. | Add `bun.lock` selector and regression test if lockfile retained; otherwise remove it. Rollback: revert selector. | VERIFIED source. |
| F14 | P3 | CONFIRMED / OPEN | `.agents/skills/`, `.claude/skills/` | 41 vs 39 files; all but two are copies. | Duplicated skill trees with no sync gate. | Skill drift and duplicated maintenance. | Declare `.agents/skills/` source of truth; add sync check. Rollback: revert policy. | VERIFIED counts. |

## 4. F09 Windows failure classification

The 170 failure/error headers were classified from stack-trace signatures in
`C:\Users\NASSAR FAMILY\AppData\Local\Temp\opencode\recovery-baseline-unittest.txt`
and the prior `audit-after-unittest.txt`. Counts are from the scripted signature
classification; the log is untrusted data and no test was changed.

| Category | Count | Classification |
| --- | ---: | --- |
| `FileNotFoundError [WinError 2]` after `PATH` clearing / temp-path fixtures | 78 | Windows harness/environment |
| `secure_open_unavailable` (`O_NOFOLLOW`/`O_DIRECTORY` unavailable) | 29 | By-design fail-closed on Windows; environment limitation |
| `OSError [WinError 1314]` symlink creation | 13 | Windows privilege/harness |
| `No module named 'cryptography'` | 13 | Missing optional API dependency in local interpreter |
| Gitleaks `git unavailable or timed out` | ~18 | Windows harness/PATH |
| `No module named 'jwt'` | 7 | Missing optional API dependency |
| Other CLI assertion mismatches | ~4 | Downstream of missing deps/PATH |
| `GITHUB_WORKSPACE` 8.3 short-name rejection | 3 | Windows path canonicalization |
| `dataset_digest_mismatch` | 2 | **UNVERIFIED** — fixture/digest drift or CRLF |
| `os.mkfifo` absent | 1 | Windows harness |
| Temp permission via `NASSAR~1` | 1 | Windows harness |
| Missing `psycopg` / `opentelemetry` imports | 2 | Missing optional API dependencies |

No signature demonstrated a product-code defect. This is an ASSUMPTION for the
two digest cases, not a blanket resolution. Hosted runners are `ubuntu-24.04`
(`ci.yml:37`), so green hosted CI is consistent with but does not prove a clean
Windows suite.

## 5. Graphify consolidation finding

**Canonical:** `tools/graphify` (policy `devobs-repository-intelligence-v1`,
pinned `graphifyy` 0.9.113, wheel SHA-256 declared). Public CLI:
`scripts/graphify/multi_repo.py`. Supporting files: `tests/graphify/*`,
`assets/graphify/multi_repo_manifest.json`,
`docs/architecture/graphify-integration.md`,
`docs/architecture/repository-intelligence.md`.

**Legacy:** `scripts/integrations/graphify_portfolio.py` (policy
`devobs-graphify-portfolio-v1`, pinned 0.9.112) with `tests/test_graphify_portfolio.py`
and `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md`. `scripts/graphify/*.py`
are thin wrappers and are **not** a third implementation.

The decision is based on actual callers/tests (five test modules import
`tools.graphify.*`), wrapper import direction, later merge order (#723 after
#720), richer validation/exclusion controls, and explicit wheel-SHA metadata.
Full deletion or API merge remains a separate owner-approved migration. This
change only makes the existing reality explicit and fail-visible.

## 6. Selected root cause and bounded repair

**Selected:** F01a — ambiguous canonical ownership, not a code-execution fault.
**Root cause:** two Graphify orchestrators were merged at different times and
both remained documented as current; no runtime or report field identified one
as canonical.

**Changes applied:**
1. `scripts/integrations/graphify_portfolio.py` now declares canonical
   implementation/CLI/version constants, emits a `DEPRECATED` notice on every
   CLI invocation and in `--help`, and includes a `legacy`/`canonical` block in
   JSON reports.
2. `tests/test_graphify_portfolio.py` adds a behavioral regression test that
   asserts the warning, report metadata and help epilog.
3. Documentation declares the canonical stack, records the migration path and
   preserves the historical rollout document as legacy evidence.

**Preserved:** all legacy CLI flags, dry-run defaults, `--execute --only`
safety rule, output-root checks, 0.9.112 behavior, 27 existing portfolio tests,
and all release gates. No implementation was deleted or re-pinned.

### Regression evidence

| Stage | Command | Final output |
| --- | --- | --- |
| Red (before fix) | `python -B -m unittest tests.test_graphify_portfolio.CliTests.test_legacy_cli_identifies_canonical_implementation -v` | `FAILED (failures=1)`, `REGRESSION_BEFORE_EXIT=1` |
| Green (after fix) | same command | `Ran 1 test`, `OK`, `REGRESSION_AFTER_EXIT=0` |
| Control (fix reverted) | same command after temporary source revert | `FAILED (failures=1)`, `REGRESSION_REVERT_EXIT=1` |
| Restored | same command after restoring fixed source | `Ran 1 test`, `OK`, `REGRESSION_RESTORE_EXIT=0` |
| Full legacy suite | `python -B -m unittest tests.test_graphify_portfolio -v` | `Ran 27 tests`, `OK`, `PORTFOLIO_EXIT=0` |

## 7. Before/after matrix

| Check | Before | After | Status |
| --- | --- | --- | --- |
| Canonical Graphify implementation in docs | Two competing current surfaces | `tools/graphify` declared canonical; legacy explicitly marked | VERIFIED |
| Legacy CLI deprecation signal | None | stderr notice + `--help` epilog + JSON `legacy`/`canonical` fields | VERIFIED |
| Legacy CLI behavior/pin | 0.9.112, dry-run default | unchanged | VERIFIED by 27 tests |
| F02 tools coverage | Present on main | Present, 3 tests pass | VERIFIED |
| Hosted CI at reviewed base | 19 jobs, 0 failures | unchanged; no source CI file changed | VERIFIED |
| Full Windows unittest suite | 1200 tests, 47 failures/123 errors/44 skips | same counts at baseline; after-change rerun recorded in roadmap | VERIFIED |
| P01 / AI-9 / Codex gates | BLOCKED / BLOCKED / OPEN | unchanged | VERIFIED |

## 8. Readiness gates

| Gate | Status | Basis |
| --- | --- | --- |
| P01 managed SaaS | **BLOCKED / NO-GO** | Fixed-SHA decision: all eight controls BLOCKED; Free DB expiry owner-gated. |
| AI-9 detection quality | **BLOCKED** | Synthetic holdout only; independent natural corpus absent. |
| Codex runtime acceptance | **OPEN** | Config present; trusted-client `codex mcp list` and public lookup not recorded. |
| CI/CD integrity | **PASS for reviewed source** | Exact-head run success; pin check pass. Fresh branch-protection metadata UNKNOWN/BLOCKED. |
| OIDC/WIF | **BLOCKED for P01; live UNKNOWN** | Source hardening present; no fresh hosted trust exchange. |
| RLS tenant isolation | **Source VERIFIED; hosted UNKNOWN** | Disposable PG job passed; hosted cross-tenant denial absent. |
| Observability | **BLOCKED for production** | Local starter only; no external alert path or live delivery. |
| Reliability / backup / rollback | **Partial VERIFIED; live UNKNOWN** | Health retry/Pages verification pass; restore jobs skipped, no RPO/RTO proof. |

## 9. Outstanding blockers and next priority

1. **F03 governance reconciliation** — next bounded task: add verified #718–#724
   entries and CI evidence; update four coupled files; keep gates unchanged.
2. **F04 wheel-hash enforcement** — highest remaining security supply-chain task.
3. **F10/F11/F12 live acceptance evidence** — requires owner-approved staging
   access, independent AI corpus and hosted restore/alert tests.
4. **F05/F13 Bun lockfile decision** — owner chooses npm-only or pinned Bun.
5. **F01 full consolidation** — owner approves removal/API merge of the legacy
   orchestrator after migration.

## 10. Official references used

- GitHub REST pull request fields (`draft`, `merged`, `mergeable_state`):
  <https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request>
- GitHub Actions workflow permissions:
  <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- GitHub OIDC hardening:
  <https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect>
- pip hash-checking mode:
  <https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode>
- Python `Path.rglob`:
  <https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.rglob>

Full commands, blocked checks and rollback steps are in
[`docs/roadmap/DEVOBS_RECOVERY_ROADMAP.md`](../roadmap/DEVOBS_RECOVERY_ROADMAP.md)
and [`docs/runbooks/RECOVERY_AND_ROLLBACK.md`](../runbooks/RECOVERY_AND_ROLLBACK.md).

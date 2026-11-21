# Recovery defect register — repository hardening

**Base revision (VERIFIED):** `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f` — `git rev-parse HEAD` on branch `feature/repository-recovery-hardening`.
**Upstream `main` at capture (VERIFIED):** the same SHA — `git ls-remote origin refs/heads/main`.
**Capture window (VERIFIED):** 2026-11-21, approximately 14:20–14:40 UTC (hosted HTML) and local shell evidence.
**Scope of this change:** recovery documentation and offline validator hardening. No hosted mutation, secret access, deployment, merge, paid service, provider change or release-gate change.

Priority: **P1** blocks production readiness; **P2** blocks a clean review/lifecycle record; **P3** is hardening or cleanup.
Status: **FIXED** (this branch), **OWNED-DEPENDENCY** (active branch, not duplicated here), **OPEN** (owner decision required), **BLOCKED** (missing approval/tooling), **GATE** (deliberately unchanged).

Every non-trivial claim below carries `VERIFIED`, `UNVERIFIED`, or `ASSUMED`.

## A. Fixed on this branch

| ID | Pri | Component | Defect and evidence | Minimal correction | Regression evidence | State |
|---|---|---|---|---|---|---|
| REC-A01 | P2 | `scripts/check_two_agent_tasks.py` | `AUD-13`: deeply nested JSON raised `RecursionError`, which was not caught, so the CLI exited without a JSON verdict. `AUD-14`: plain `json.loads` collapsed duplicate keys (`{"a":1,"a":2}` → `{"a":2}`). Both VERIFIED by read-only probes reported by the code/config specialist and reproduced by CLI fixtures. | Catch `RecursionError`/`MemoryError` in the parse path; reject duplicate keys with `object_pairs_hook`; return `FAIL` JSON and exit `2`. | `python -B -m unittest tests.test_two_agent_tasks -v` → `Ran 32 tests ... OK`, exit `0` (new `test_main_fails_closed_on_duplicate_keys_and_deep_nesting`). | FIXED |
| REC-A02 | P2 | same | `AUD-03`: a disabled non-worker agent could own a `complete` task and still yield `PASS` because terminal tasks skipped the enabled check. VERIFIED by specialist probe. | A `complete` task assigned to a disabled agent is now a manifest `FAIL`. Non-terminal disabled assignments still report `BLOCKED`, preserving the existing contract. | New `test_disabled_agent_cannot_own_a_complete_task`; full validator suite OK. | FIXED |
| REC-A03 | P2 | same | `AUD-04`: `BRANCH_RE` accepted `feature/../main` and `feature//x`; branch conflicts use string equality. VERIFIED by specialist probe (`PASS`). | Reject empty, `.`, `..`, and dangling-dot branch segments before comparison. | New `test_invalid_branch_segments_fail_closed`; full validator suite OK. | FIXED |
| REC-A04 | P2 | same | `AUD-05`: any owner/repo URL and unbounded PR numbers (`#0`, 100-digit) were accepted. VERIFIED by specialist probes (`PASS`). | Bound PR numbers to positive ≤7 digits and require URL references to name the task's own repository. | New `test_pr_reference_is_repository_bound_and_bounded`; full validator suite OK. | FIXED |
| REC-A05 | P3 | same | `AUD-06`: `Shared/Module.py` and `shared/module.py` were distinct paths in the conflict intersection. VERIFIED by specialist probe (`PASS`). | Compare case-folded path keys (Windows-relevant contract) while displaying original spelling; reject case-only duplicates inside one task. | New `test_case_only_path_collision_is_a_conflict`; full validator suite OK. | FIXED |
| REC-A06 | P2 | same | `AUD-07`: caller-supplied `repositories=["../.."]` passed `REPO_RE` and yielded `PASS`. VERIFIED by specialist probe. | Require a concrete `owner/name` pair; reject dot/dot-dot and dot-leading components. | New `test_repository_allowlist_rejects_dot_navigation`; full validator suite OK. | FIXED |
| REC-A07 | P3 | validator documentation | `AUD-01`/`AUD-12` cannot be proven offline: the checker validates shape, not execution or prior trusted history. VERIFIED by source reading (`scripts/check_two_agent_tasks.py:218-245`, `:212-217`) and specialist probes. | Module docstring now states explicitly that command execution and observed `previous_status` are not verified. No false "fully enforced" claim is made. | Source review; the two residual items remain OPEN below. | DOCUMENTED |

**Changed files (VERIFIED):** `scripts/check_two_agent_tasks.py` (+68/−12), `tests/test_two_agent_tasks.py` (+58/−0); `git diff --stat` reports 126 insertions, 12 deletions.

## B. Owned dependencies — deliberately not duplicated

| ID | Pri | Defect and evidence | Owner / dependency | Required action | State |
|---|---|---|---|---|---|
| REC-B01 | P1 | Baseline Windows run at this base: `Ran 1200 tests in 279.679s`, `FAILED (failures=47, errors=123, skipped=44)`, exit `1`. Fresh targeted reruns at the same SHA reproduced `FileNotFoundError`, `secure_open_unavailable`, Git-unavailable, `WinError 1314` and missing-module classes. VERIFIED. | `feature/windows-test-reliability` at `ace94c2f52fcc9150ce0c6ea1f76059b00eba143` changes 58 files (Git discovery, capability guards, byte-pinned fixtures, dependency pins, `stage_site` path handling). Its analysis records a local `Ran 1487 tests`, `OK (skipped=91)`, exit `0`; hosted Ubuntu CI is UNVERIFIED. | Review/merge that branch first, then rerun the full suite on the combined SHA. This branch touches none of its files. | OWNED-DEPENDENCY |
| REC-B02 | P2 | Governance lag: `python scripts/milestone_ledger.py --summary` → `latest_pr: 717`, `merged_milestones: 304`, while VERIFIED `git log` at base contains PRs #733–#739 and hosted `main` is `bf8bf31` (#739). `STATE.md` stops at #716/#717; `docs/DEVOBS_READINESS_CURRENT.md` at #639–#641. VERIFIED. | `feature/blocked-task-ownership-guard` changes `docs/MILESTONE_LEDGER.json`, `STATE.md`, `README.md`, `tests/test_milestone_ledger.py`; many active branches also change `README.md`. | Reconcile #718–#739 with exact head/merge SHAs and CI run IDs on the owning branch; keep all gate states unchanged. | OWNED-DEPENDENCY |
| REC-B03 | P2 | Hosted PR list shows exactly one open PR: Draft PR #741 `Feature/ai quality coordination gate` (`isDraft: true`, head `04c6b4e2e38ddd858d320baeff5da9c4c2f2a7ad`). Its CI run `44913420874` completed `WORKFLOW_RUN_CONCLUSION_FAILURE` at `2026-11-21T14:20:29Z`; job attribution is UNVERIFIED without authenticated API access. VERIFIED from public GitHub HTML/embedded run data. | Owner's separate coordination-gate work. | No action here. Do not treat its failure as evidence about this branch. | OWNED-DEPENDENCY |
| REC-B04 | P2 | AUD-02 (`blocked` ownership silently released) is already fixed at this base: `check_two_agent_tasks.py` reports `blocked` as `task_blocked` and returns `BLOCKED`; regression tests exist. VERIFIED by source reading, specialist probe and `tests.test_two_agent_tasks`. | Already merged in prior work. | Preserve the #732 regression tests. | FIXED-UPSTREAM |

## C. Open decisions — no unverified fix claimed

| ID | Pri | Finding and evidence | Why not fixed here | Owner decision required |
|---|---|---|---|---|
| REC-C01 | P1 | `AUD-01`: `complete` with a fabricated SHA and `commands=["echo FABRICATED_PASS"]` returns `PASS`; the checker never executes commands. VERIFIED. | Fixing it properly needs a trusted evidence source (CI run/SHA binding) and human sign-off; inventing an offline "pass" rule would be a false control. | Approve an evidence contract that requires operator-supplied trusted CI/SHA proof plus separate human approval, then assign an owning branch. |
| REC-C02 | P2 | `AUD-12`: `previous_status` and `status` are two fields of the same record; a claimed `evidence_ready → complete` transition passes. VERIFIED. | Cannot observe history from one manifest without a prior trusted manifest or append-only log. | Decide between a trusted prior-manifest comparison or relabelling the field as a claim (already documented). |
| REC-C03 | P3 | `AUD-08`: validator is stateless; no lock or prior-manifest hash. UNVERIFIED that concurrent writers caused a problem. | Adding locks needs a new threat model and runtime state, outside this offline contract. | Approve either per-worker manifests with reviewed merge, or a new threat model. |
| REC-C04 | P2 | `F04`: `tools/graphify/runner.py` verifies only `--version`; `supply_chain.py` adds an explicit `verify-wheel` command, but no wheel hash pin exists in requirements. VERIFIED by source reading; runtime hash check UNVERIFIED. | Requires a wheel distribution/pinning decision and possibly a new artifact. | Choose a hash-pinned wheel source and fail-closed extraction policy. |
| REC-C05 | P2 | `F05`: `apps/ai-intelligence-console/bun.lock` still names `react-example` and differs from `package.json`/`package-lock.json` in 8 versions plus package membership; `scripts/assess_change.py:114-125` does not select `bun.lock`. VERIFIED. | Choice between npm-only and supported Bun changes CI and lock policy. | Remove the stale lock, or regenerate/pin it and add it to the Node selector. |
| REC-C06 | P3 | `F08`: `check_action_pins.py` verifies SHA pinning but not version comments; 10 `uses:` lines in four workflow templates lack them. VERIFIED. | Small but independent checker change with fixture work. | Approve extending the checker; no security control is currently lost. |
| REC-C07 | P3 | `F14`: `.agents/skills` (41 files) and `.claude/skills` (39 files) have no sync gate. VERIFIED. | Requires declaring an authoritative tree and a diff check. | Nominate `.agents/skills` authoritative and approve the gate. |
| REC-C08 | P3 | `F10`: `docs/audits/DEVOBS_RECOVERY_AUDIT.md:50` cites `render.yaml:24-32` for the `2026-12-05` expiry, but the exact value is in `docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md:10`. VERIFIED. | Citation-only fix touches a P01-adjacent audit document; no live resource change is authorized. | Approve a documentation-only correction. |
| REC-C09 | P3 | `F07`: unbounded directory walks in `tools/graphify` (`common.py`, `adapters.py`, `multi_repo.py`) with no in-loop cutoff/symlink policy. Resource-exploitation impact UNVERIFIED. | Needs scale reproduction and a boundary policy. | Approve a bounded-walk threat model before changing code. |
| REC-C10 | P1 | P01 managed SaaS is `BLOCKED`/NO-GO with eight controls blocked; AI-9 detection quality is `BLOCKED`; Codex agent runtime acceptance is `OPEN`. VERIFIED from ledger summary and `docs/p01/P01_NO_GO_DECISION_2026-11-19.md`, `docs/CODEX_AGENT_OPERATING_MODEL.md`. | Gates require owner evidence and approval, not code edits. | Separate owner decisions tied to exact SHA and scope for each gate. |

## D. Verification gaps (tracked as SKIPPED/BLOCKED, never PASS)

- Full hosted CI/CodeQL on the exact base and this branch head: UNVERIFIED. Public REST calls were rate-limited (`limit 60`, `remaining 0`, reset `2026-11-21T15:05:02Z`); branch-protection rulesets require authentication.
- `actionlint`, Docker/Trivy, Terraform/OpenTofu, Bandit, Gitleaks CLI, Semgrep CLI, `gh`, `kubectl`: tool not found locally. YAML parse of 43 workflows passed as a **local substitute only** (`YAML_PARSE_OK files=43`).
- Node checks: BLOCKED locally by PowerShell execution policy (`npm.ps1 cannot be loaded`) and absent `node_modules`.
- Keycloak runtime: BLOCKED. The AGENTS.md exception is not active until the reconciliation PR is merged, and no per-run approval exists.
- Live OIDC/JWKS, tenant isolation, backup restore, alert delivery, provider billing and cloud state: UNVERIFIED by design; no production access is authorized.

See [`verification-matrix.md`](verification-matrix.md) for exact commands and final output lines.

## Rollback

Revert the two source/test commits (or reset this unpublished branch to `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f`). No migration, hosted state, gate, secret or deployment is changed by this work, so rollback is local-only.

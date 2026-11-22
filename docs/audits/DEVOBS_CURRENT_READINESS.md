# Devobs — current readiness reconciliation (evidence-backed)

**Audited `origin/main` SHA:** `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` (VERIFIED: `git fetch origin` exit 0, `git rev-parse origin/main` after fetch; isolated branch `feature/devobs-readiness-reconciliation`, clean tree). Date: 2026-11-22.

**Labels:** VERIFIED = command output, local file:line or read-only GitHub API response in this session; UNVERIFIED = not established; ASSUMED = judgment. A checked-in document, ledger claim or historical CI run is never proof of a running service or an accepted gate. No hosted resource, provider, cloud account, secret, token or deployment setting was accessed or modified. No gate was promoted.

## 1. Baseline and scope decisions

- Previous production-gap audit baseline was `10f8dd9b1e884e16cea3ffd847cf20405794cb8b`; its branch `feature/devobs-production-gap-audit` head `3b14d6f5feec45426640cf6c783a1fc651b67e40` is **not merged** (`git merge-base --is-ancestor 3b14d6f origin/main` → exit 1), so `docs/audits/DEVOBS_FULL_GAP_AUDIT.md` and its companions are **absent from main**. I did not create, modify or copy those files; the audit is complete-and-unmerged, not still running. Open-PR query returned `OPEN_PR_COUNT=0`.
- `README.md` was **not modified**. Six active branches have uncommitted-push diffs that include `README.md` (`feature/agent-approval-gates`, `feature/agent-policy-engine`, `feature/multi-agent-work-orchestrator`, `feature/worktree-coordination-inspector`, `feature/agent-task-status-report`, `feature/orchestrator-integration-audit`). Per the task condition ("only if no active agent owns it"), it is treated as owned and left untouched. `STATE.md` and `docs/MILESTONE_LEDGER.json` are likewise owned by `docs/record-pr736-milestone` and are not edited here.
- Only the two requested new documents are added; the next-fix implementation is explicitly **not** implemented.

## 2. PR reconciliation — #720, #744, #745 (VERIFIED via read-only GitHub API)

| PR | State / merge commit | Exact merged head | Merged at | What changed and evidence |
| --- | --- | --- | --- | --- |
| #720 `feat(graphify): add opt-in offline portfolio graph orchestration` | closed / merged=True / merge `1b8a28711ece5f168a74d736e429abd88f5760c9` | `25b2afa38137796dfee6f071fe8af21a8a675569` | 2026-11-20T00:03:47Z | Opt-in, dry-run-first local Graphify orchestration. PR body names an earlier head `23b18502434b0d22f40a14037ac94c0901936e92`; this report uses the **API-reported merged head**. Historical PR text says diagnostics/network attestation issues were open before later fixes; current live behavior UNVERIFIED here. |
| #744 `docs(agents): adopt guarded Codex and OpenCode multi-agent workflow` | closed / merged=True / merge `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` | `20224238e9a2aacae4463dfaa15637b7a2bd55e2` | 2026-11-21T21:08:00Z | Adopted `docs/AI_MULTI_AGENT_WORKFLOW.md` v1.0 as human-supervised policy; no scheduler or dispatch activation. This merge is the previous audit's exact baseline. |
| #745 `feat(security): guard local AI-agent output artifacts before review` | closed / merged=True / merge `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` | `af99155d757f332443f0a07d064ea4d215c9c02a` | 2026-11-22T13:03:25Z | Adds exactly 3 files (607 insertions): `tools/agent_output_guard.py`, `tests/test_agent_output_guard.py`, `docs/security/AGENT_OUTPUT_GUARD.md`. Read-only deterministic CLI for explicit local artifact paths; no existing file, CI, dependency or hosted setting changed. |

**Independent CI verification (VERIFIED, read-only Actions API `head_sha` filter):**
- PR #745 head `af99155d`: `CI` run `45025101917` **success**; `AI Code Review` run `45025101872` **success**; `PR #745` run `45025098775` **success**; Claude/PR-Agent runs **skipped**.
- Current main `a9e6e1b`: `CI` run `45025462954` **success**, `Push on main` run `45025462455` **success**; `Claude Code Assistant` and `Incident Response` **skipped** by scope. Skipped jobs are not represented as executed evidence.
- Official API semantics used: [Get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request) and [List workflow runs for a repository (`head_sha`)](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository).

## 3. Capabilities reconciled at current main

| Capability | Evidence at `a9e6e1b` | Status |
| --- | --- | --- |
| Local AI-agent output guard (#745) | `tools/agent_output_guard.py` (181 lines), `tests/test_agent_output_guard.py` (267 lines), `docs/security/AGENT_OUTPUT_GUARD.md` (159 lines); `git diff --name-only 10f8dd9..a9e6e1b` lists exactly those 3; Linux exact-head CI success above | VERIFIED (source + CI); Windows runtime FAILED CLOSED by design (see §7) |
| Multi-agent workflow policy (#744) | `docs/AI_MULTI_AGENT_WORKFLOW.md` present; `scripts/check_agent_spec.py` fresh PASS for 7 specs and 5 gh-aw budget gates | VERIFIED (policy/config); live agent runtime UNVERIFIED |
| Offline Graphify orchestration (#720) | Merged; canonical `tools/graphify` + legacy adapter documented in README; PR body's pre-merge caveats are historical | CONFIGURED; current rollout UNVERIFIED |
| Full SHA action pinning | `python scripts/check_action_pins.py` → `Action pin check passed for 48 workflow and template files.` exit 0 | VERIFIED (offline) |
| Milestone ledger / tests | `python scripts/milestone_ledger.py --summary` → `latest_pr: 717`, `merged_milestones: 304`, 3 open gates; `python -m unittest tests.test_milestone_ledger -q` → `Ran 86 tests in 3.036s` / `OK` | VERIFIED (offline) — ledger text is stale vs merged #720–#745; `docs/record-pr736-milestone` owns updates |

## 4. Remaining acceptance blockers (no promotion)

| Gate | Current state and fresh evidence | Decision |
| --- | --- | --- |
| P01 managed SaaS | `docs/p01/P01_NO_GO_DECISION_2026-11-19.md` is a fixed-SHA (`0f062c03`) owner **NO-GO**; 8 controls SPEND, PROVIDER, OIDC, RLS, TLS_NETWORK, BACKUP, OWNER, RELEASE all **BLOCKED**; `python -m unittest discover -s tests -p "test_p01_no_go_matrix.py"` → `Ran 5 tests` / `OK`. The merge of #745 does not rebind that review. | **BLOCKED / NO-GO** — unchanged |
| AI-9 detection quality | `python scripts/check_ai9_evidence.py --expected-sha a9e6e1b…` → `AI9 BLOCKED: source SHA does not match the checked revision; synthetic_holdout: UNVERIFIED; … independent_release_approval: UNVERIFIED` (exit 1); unit suite `test_ai9_evidence.py` → `Ran 16 tests` / `OK`. Ledger gate `ai9-detection-quality: BLOCKED`. | **BLOCKED** — unchanged |
| Codex runtime acceptance | Ledger `codex-agent-runtime-acceptance: OPEN`; no trusted-client MCP probe or agent runtime evidence in this session; dispatch tools are DRY_RUN by design. | **OPEN / UNVERIFIED** — unchanged |
| Spend cap | `docs/P01_RENDER_BUDGET_ENVELOPE.md` targets are not provider limits; `render.yaml` budget flag remains false in the reviewed baseline; no enforced combined USD 100 cap evidenced. | **BLOCKED** |
| Backup / restore | No isolated hosted restore or observed RPO/RTO; Free Render has no provider-managed backup (Render docs). | **BLOCKED** |

Official references relied on: [Render Free](https://render.com/docs/free), [Render Postgres backups](https://render.com/docs/postgresql-backups), [GitHub ruleset review requirement](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging).

## 5. Render Free PostgreSQL expiry planning (reviewed, no action)

- Fresh guard: `python scripts/check_render_free_expiry.py --json` → `{"exit_code":1,"expires_at":"2026-12-05T10:33:24.202776Z","observed_on":"2026-11-19","paid_activation_authorized":false,"production_approved":false,"provider_access_performed":false,"status":"REVIEW_REQUIRED"}` (exit 1, fail-closed as designed).
- `docs/plans/2026-11-19-render-free-postgres-retirement-plan.md:3-13` explicitly authorizes **planning only**: prepare a no-cost decision for database `devobs-ai-staging-db` (resource `dpg-dbm5msu1egvs73be46og-a`), no delete/offline/migrate/export/backup/provider change now; requires a separate exact-resource/date owner authorization and review. "Synthetic/disposable" row classification is stated as historical and is **not** delete approval; row contents and external consumers remain UNVERIFIED.
- The 2026-11-19 snapshot is point-in-time and is 3 days old relative to this audit; the guard correctly refuses to treat it as fresh proof. No provider API was called.

## 6. Highest-priority unowned defect (definition only, not implemented)

Full implementation specification is in [NEXT_VERIFIED_REMEDIATION.md](../roadmap/NEXT_VERIFIED_REMEDIATION.md).

- **Defect:** the repository policy auditor cannot detect a zero-approval ruleset. `scripts/check_repo_policy.py:200-207` checks only that a `pull_request` rule exists; `tests/test_check_repo_policy.py:45` sets `required_approving_review_count: 0` and `test_accepts_current_policy_shape` (`:64-69`) expects no findings. Read-only live ruleset `24507159` currently returns `required_approving_review_count: 0`, `required_reviewers: []`, `require_code_owner_review: false`, `require_last_push_approval: false`, while still requiring `validate`, CodeQL and up-to-date branches.
- **Why this one:** `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md` ranks "main review policy" as remediation **#1 (highest priority)**; it is a concrete, security-relevant source defect with a fail-closed fix and exact tests. P01/AI-9/Render/Codex items above are higher-severity *blocked gates* requiring owner decisions, not agent-owned code defects.
- **Ownership check:** `git diff --name-only origin/main...<branch>` over all `feature/*` and `docs/*` branches produced **no** branch touching `scripts/check_repo_policy.py` or `tests/test_check_repo_policy.py`. Unowned. README and ledger are owned by others and are out of scope for that fix.

## 7. Verification evidence (exact commands and final lines)

| Command | Final output | Exit |
| --- | --- | ---: |
| `git fetch origin --quiet` | silent; `ORIGIN_MAIN=a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` | 0 |
| `git merge-base --is-ancestor 3b14d6f origin/main` | `audit_branch_ancestor=1` (not merged) | 1 |
| GitHub API: open PRs | `OPEN_PR_COUNT=0` | 0 |
| GitHub API: PRs #720/#744/#745 | all `state=closed merged=True`, merge heads `1b8a287…`/`10f8dd9…`/`a9e6e1b…` | 0 |
| GitHub API: Actions by `head_sha` | #745 CI `45025101917` success, main CI `45025462954` success | 0 |
| `python scripts/milestone_ledger.py --summary` | `{"gate_statuses":{"ai9-detection-quality":"BLOCKED","codex-agent-runtime-acceptance":"OPEN","p01-managed-saas":"BLOCKED"},"latest_pr":717,"merged_milestones":304,"open_gates":3}` | 0 |
| `python -m unittest tests.test_milestone_ledger -q` | `Ran 86 tests in 3.036s` / `OK` | 0 |
| `python -m unittest tests.test_check_repo_policy -q` | `Ran 16 tests in 0.038s` / `FAILED (errors=1)` | 1 |
| `python -m unittest discover -s tests -p "test_p01_no_go_matrix.py"` | `Ran 5 tests in 0.084s` / `OK` | 0 |
| `python scripts/check_ai9_evidence.py --expected-sha a9e6e1b…` | `AI9 BLOCKED: source SHA does not match …` + 7 UNVERIFIED controls | 1 (fail-closed) |
| `python -m unittest discover -s tests -p "test_ai9_evidence.py"` | `Ran 16 tests in 0.426s` / `OK` | 0 |
| `python scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` | 0 |
| `python scripts/check_agent_spec.py` | `Validated 7 agent specs, … all 5 gh-aw source/lock budget gates.` | 0 |
| `python scripts/check_render_free_expiry.py --json` | `REVIEW_REQUIRED`, expiry `2026-12-05T10:33:24.202776Z` | 1 (fail-closed) |
| `python -m unittest discover -s tests -p "test_agent_output_guard.py"` | `Ran 30 tests in 38.724s` / `FAILED (failures=36, errors=2)` on Windows | 1 |
| `python -m compileall -q tools` | silent | 0 |
| Read-only ruleset API `rulesets/24507159` | `required_approving_review_count: 0`; `validate`/CodeQL requirements still present | 0 |

**Local failures classified, not hidden:**
1. `test_check_repo_policy.test_actions_summary_includes_named_drift_findings`: `PermissionError: [Errno 13] … 'C:\\Users\\NASSAR~1\\AppData\\Local\\Temp\\tmpv5z4cxdh'` — the test opens `tempfile.NamedTemporaryFile` and production `write_step_summary` reopens the same path for append (`:235-241`); Windows file locking causes it. Genuine cross-platform test-harness defect (P2, separate PR); Linux CI is the authoritative green evidence.
2. `test_agent_output_guard.py`: on Windows, secure-reader APIs are unsupported, so the tool returns `FAIL` where tests expect `PASS`/`BLOCKED`, and symlink setup raises `OSError: [WinError 1314] A required privilege is not held by the client`. This matches PR #745's documented design ("Windows/unsupported platforms fail closed, without a weaker fallback"); exact-head Linux CI passed. NOT a regression claim.

**Could not run:** hosted OIDC/RLS/backup/restore, provider inference, `gcloud`/Terraform apply, Keycloak runtime (AGENTS.md activation conditions unmet), full `tests/` discovery, authenticated Dependabot/ruleset write inspection. GitHub REST reads are unauthenticated; private fields may be omitted (ruleset `bypass_actors` was absent from the anonymous response), so that field is UNVERIFIED here.

## 8. Conclusion

Merged capabilities from #720/#744/#745 are reconciled above; the new artifact guard has exact-head CI evidence. No gate moved: P01 **NO-GO/BLOCKED**, AI-9 **BLOCKED**, Codex runtime **OPEN**. The next single, unowned, evidence-backed fix is V-01 approval-count enforcement; its files, tests and Draft-PR boundary are specified in the companion roadmap. Devobs is **not** production-ready.

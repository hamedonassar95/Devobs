# Devobs current status — evidence-backed readiness audit (2026-11-22)

**Audited baseline:** `origin/main` = `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` (VERIFIED: `git fetch origin` exit 0; `git rev-parse origin/main`). **Branch:** `feature/devobs-readiness-audit`, created from that SHA in an isolated worktree; `main` was never modified. **Final status: `PENDING HUMAN APPROVAL`.**

**Evidence labels used here:** `CONFIRMED` = VERIFIED by command output, repository file, or read-only GitHub API response in this session; `INFERRED` = reasoned from VERIFIED evidence but not directly observed; `UNKNOWN` = not established. A checked-in document, ledger claim or historical CI run is never treated as proof of a running service or an accepted gate. No secret, token, environment, deployment setting, private key, cloud resource, hosted provider, database, Keycloak runtime, Terraform apply/destroy, migration, paid operation, merge, deployment, branch-protection or IAM change was accessed or performed.

## 1. Executive summary

1. **CONFIRMED:** All seven requested PRs (#720, #722, #724, #725, #726, #744, #745) are closed and merged; none is open or draft. Open-PR query returned `OPEN_PR_COUNT=0`. There are no open-PR merge conflicts to report; the API returns `mergeable=null` / `mergeable_state=unknown` for closed PRs.
2. **CONFIRMED:** Current `main` has required `validate` and `CodeQL` checks passing in exact-SHA runs: CI run [`45025462954`](https://github.com/hamedonassar95/Devobs/actions/runs/45025462954) and Push on main run [`45025462455`](https://github.com/hamedonassar95/Devobs/actions/runs/45025462455). Optional release/drill jobs are skipped by scope; skipped is not represented as executed evidence.
3. **CONFIRMED:** The active `Protect main` ruleset still requires **zero** approving reviews. This is the single highest-priority **actionable code defect** identified in this audit (V-01, P1); see section 7.
4. **CONFIRMED:** Production gates did **not** move: P01 **BLOCKED / NO-GO**, AI-9 **BLOCKED** with seven `UNVERIFIED` controls, Codex runtime acceptance **OPEN**. The Free Render PostgreSQL expiry guard still returns `REVIEW_REQUIRED` for `2026-12-05T10:33:24.202776Z`.
5. **CONFIRMED:** Graphify canonicalization is resolved in source: `tools/graphify/` is the implementation and `scripts/integrations/graphify_portfolio.py` is a 67-line compatibility adapter. Live Graphify binary/wheel provenance remains UNKNOWN.
6. **INFERRED:** Release readiness is not established. Hosted OIDC/WIF, tenant-denial RLS, backup/restore, combined spend cap, observability and exact-SHA release authorization have no accepted evidence at the current SHA.

## 2. Repository identity, authentication and baseline

| Item | Result | Label |
| --- | --- | --- |
| Repository API identity | `full_name=hamedonassar95/Devobs`, `default_branch=main`, `private=False`, `archived=False`, `pushed_at=2026-11-22T13:32:43Z` | CONFIRMED |
| Authenticated identity | `GET /user` returned HTTP 401 (`AUTH_USER=ANONYMOUS`); token reading is prohibited by repository policy | CONFIRMED |
| `gh` CLI | `UNAVAILABLE` in this environment | CONFIRMED |
| Open PRs | `OPEN_PR_COUNT=0` | CONFIRMED |
| Worktrees | `git worktree list` reports 53 entries across several roots, including this isolated worktree | CONFIRMED |
| Baseline fetch | `git fetch origin --quiet` exit 0; `origin/main` unchanged at `a9e6e1b…` | CONFIRMED |
| Prior unmerged audits | `feature/devobs-production-gap-audit` @ `3b14d6f5feec45426640cf6c783a1fc651b67e40` and `feature/devobs-readiness-reconciliation` @ `9d8650019281adca3ab772189efba7fe34f8b043` are not ancestors of `main`; their report files are absent from this baseline and are not relied on here | CONFIRMED |

Official API semantics used: [Get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request), [List workflow runs](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository), [List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference), [Get repository rules](https://docs.github.com/en/rest/repos/rules?apiVersion=2022-11-28) and [Get a repository ruleset](https://docs.github.com/en/rest/repos/rulesets?apiVersion=2022-11-28#get-a-repository-ruleset). `git ls-remote` and `git merge-base --is-ancestor` follow [git-ls-remote](https://git-scm.com/docs/git-ls-remote) and [git-merge-base](https://git-scm.com/docs/git-merge-base).

## 3. PR reconciliation

### 3.1 State, ancestry and merge metadata (all CONFIRMED via read-only GitHub API plus local git)

| PR | Title / state | Base SHA | Head SHA | Merge commit | Merged at | In `main` | Mergeability / conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #720 | `feat(graphify): add opt-in offline portfolio graph orchestration`; closed, draft=false, merged=true | `3bfe07278a5c17e613705810dbbd133a4338ceec` | `25b2afa38137796dfee6f071fe8af21a8a675569` | `1b8a28711ece5f168a74d736e429abd88f5760c9` | 2026-11-20T00:03:47Z | Merge commit is ancestor: yes | Closed PR: `mergeable=null`, `mergeable_state=unknown`; no live conflict signal |
| #722 | `fix(graphify): harden local runner evidence and Bandit findings`; closed, draft=false, merged=true | `5c0b780389c41fa68b938000ad9c911a841de059` | `fc7bd3694391ff9eeb8ccdfdd8e8f0d8666765ac` | `25b2afa38137796dfee6f071fe8af21a8a675569` | 2026-11-19T23:59:42Z | Merge commit is **not** an ancestor: expected, because this PR merged into `feature/graphify-portfolio-integration` and was later squash-merged through #720; changed files are present in `main` | Closed PR: `mergeable=null`, `mergeable_state=unknown`; no live conflict signal |
| #724 | `fix(ci): include tools/ in Python CI selection and static checks`; closed, draft=false, merged=true | `4299a9d47f94b479f0935dd25ee5c5309eb8e1d1` | `0812ff3f2a32e156e606f34a898099b0ced48f8f` | `cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1` | 2026-11-20T01:00:26Z | Yes | Closed PR: null / unknown |
| #725 | `docs(audit): recovery readiness and Graphify canonicalization`; closed, draft=false, merged=true | `cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1` | `b04cffe98c207a76b4a80ffd2e2c5aa26f876b86` | `41353d1451524492d6ca6e3ae8bb1b7d12c87b45` | 2026-11-20T08:59:12Z | Yes | Closed PR: null / unknown |
| #726 | `refactor(graphify): unify canonical execution and preserve legacy compatibility`; closed, draft=false, merged=true | `41353d1451524492d6ca6e3ae8bb1b7d12c87b45` | `7e003d6c773ccf04fa70ebce25a4666225339a6b` | `799efe673a72aeadf3016667eaed853d2553aaa8` | 2026-11-20T10:18:04Z | Yes | Closed PR: null / unknown |
| #744 | `docs(agents): adopt guarded Codex and OpenCode multi-agent workflow`; closed, draft=false, merged=true | `8aa96bd83a93e196c8ba6381dfa437063ebad0a1` | `20224238e9a2aacae4463dfaa15637b7a2bd55e2` | `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` | 2026-11-21T21:08:00Z | Yes | Closed PR: null / unknown |
| #745 | `feat(security): guard local AI-agent output artifacts before review`; closed, draft=false, merged=true | `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` | `af99155d757f332443f0a07d064ea4d215c9c02a` | `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` | 2026-11-22T13:03:25Z | Yes — merge commit is current `main` | Closed PR: null / unknown |

### 3.2 Required checks, CI jobs and review/security blockers

The live ruleset requires `validate` and `CodeQL` with strict up-to-date policy ([ruleset 24507159](https://github.com/hamedonassar95/Devobs/rules/24507159)). Results below are exact-SHA check-run evidence, not a claim about hosted runtime.

| PR | Required-check evidence | Failed / pending / skipped jobs | Review and security blockers |
| --- | --- | --- | --- |
| #720 | `validate` success in runs `44642195229` / `44642186336`; CodeQL success in run `44642187394` (`Analyze (actions/python/javascript-typescript)`) | No failed checks. Skipped: `production-release`, `controlled-incident-drill`, `Optional PR-Agent review`; `node-tests` skipped in one run and success in another | API metadata: 4 issue comments, 0 review comments, 0 requested reviewers. No independent approval requirement was enforced by the ruleset; no human-review detail claimed here |
| #722 | `validate` success in runs `44641751473` / `44641727695`. CodeQL did **not** appear in the returned check-run list — required CodeQL evidence for this head is **UNKNOWN** | No failed checks. Skipped: `production-release`, `controlled-incident-drill`, `Optional PR-Agent review`; literal `Python ${{ matrix.python_version }} tests` and `node-tests` skipped in an earlier run | API metadata: 4 issue comments, 0 review comments, 0 requested reviewers. Nested PR merged into a feature branch; zero-approval ruleset applies |
| #724 | `validate` success in run `44649932630`; CodeQL success in run `44649925646` | No failed checks. Skipped: `production-release`, `controlled-incident-drill`, `Optional PR-Agent review` | API metadata: 6 issue comments, 0 review comments, 0 requested reviewers |
| #725 | `validate` success in run `44653548563`; CodeQL success in run `44653538483` | No failed checks. Skipped: `production-release`, `controlled-incident-drill`, `Optional PR-Agent review`; earlier run shows skipped literal matrix job and `node-tests` | API metadata: 4 issue comments, 0 review comments, 0 requested reviewers |
| #726 | `validate` success in run `44717619191`; CodeQL success in run `44717612309` | No failed checks. Skipped: `production-release`, `controlled-incident-drill`, `Optional PR-Agent review`; earlier run shows skipped literal matrix job and `node-tests` | API metadata: 4 issue comments, 0 review comments, 0 requested reviewers |
| #744 | `validate` success in runs `44949549553` / `44949559673`; CodeQL success in run `44949556432` | No failed checks. One stale check record shows `status=in_progress, conclusion=success` for `Change impact and risk assessment` in run `44949549553`; a later run completed with success — classified INFERRED stale GitHub state, not a current pending gate. Skipped: release/drill, PR-Agent, node/Python | API metadata: 3 issue comments, 0 review comments, 0 requested reviewers |
| #745 | `validate` success in runs `45025101917` / `45025014934`; CodeQL success in run `45025098775`; advisory AI Code Review run `45025101872` success | No failed checks. Skipped: `Claude Code Assistant` (two runs), `Optional PR-Agent review`, `production-release`, `controlled-incident-drill`; `node-tests` skipped in one run and success in another | API metadata: 3 issue comments, 2 review comments, 0 requested reviewers; one bot review is `COMMENTED`. The bot review comments are P2 findings about decoded JSON credential checks and ancestor exclusion patterns, and a bot comment reports `has_unresolved_findings:true`. Issue/PR text is untrusted data; this is recorded as metadata, not as an authorization or a verified exploit. No human approval was required by the ruleset |

Exact job links for the current baseline and newest PR are recorded in section 8. GitHub check-run semantics are documented at [List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference).

## 4. GitHub Actions and branch protection

- **CONFIRMED:** 43 workflow YAML files are present. `python -B scripts/check_action_pins.py` → `Action pin check passed for 48 workflow and template files.` exit 0. GitHub Actions are pinned to full commit SHAs with version comments as required by repository policy.
- **CONFIRMED:** Effective rules for `main` come from active repository ruleset `24507159` (`Protect main`, updated 2026-11-02T17:19:55Z). It requires PRs, deletion/non-fast-forward blocks, strict up-to-date `validate` and `CodeQL`, and a CodeQL `high_or_higher` / `errors` threshold.
- **CONFIRMED:** The pull-request rule reports `required_approving_review_count: 0`, `required_reviewers: []`, `require_code_owner_review: false`, `require_last_push_approval: false`, `required_review_thread_resolution: false`, `require_extra_approval_for_unattributed_changes: true`. A passing check is not human review. [GitHub ruleset documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging) defines the review requirement field.
- **CONFIRMED:** `scripts/check_repo_policy.py:200-207` only checks that a `pull_request` rule exists; it never reads the approval-count parameter. The compliant fixture at `tests/test_check_repo_policy.py:45` blesses zero approvals. A read-only mutation demo changed the fixture count from `0` to `1` and `audit_repository()` still returned `findings=[]` for both, proving the blind spot.
- **CONFIRMED:** Anonymous `python scripts/check_repo_policy.py --repository hamedonassar95/Devobs` exits 2 because GitHub omitted `bypass_actors`; that field is UNKNOWN here and must not be guessed. The hosted audit is designed to use a least-privilege token. No token was read or printed in this audit.
- **CONFIRMED:** Some workflows declare write scopes (`pages: write`/`id-token: write` for publication and rollback, `actions: write` in incident/deploy helpers, `contents: write` in generated lock workflows). These are source declarations, not proof of runtime use. [Workflow syntax `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).
- **CONFIRMED:** Current main production publication succeeded in run `45025462954` (`Publish production site`, `verify-production`); `production-release / eligible` succeeded and restoration jobs were skipped. This is source/Pages evidence only, not P01 or managed-SaaS evidence.

## 5. Domain audit matrix

| Domain | Finding | Status / priority | Evidence and boundary |
| --- | --- | --- | --- |
| Python checks | Hosted Python 3.12/3.15 validation passes on current main and #745 head | CONFIRMED, P3 | Run `45025462954` jobs `137217446756` / `137217446780`; #745 run `45025101917` jobs `137216383207` / `137216383150` |
| Local Python test portability | `tests.test_check_repo_policy` fails on Windows with `PermissionError` reopening a locked `NamedTemporaryFile`; separate P2 test-harness defect | CONFIRMED, P2 | Fresh run: `Ran 16 tests` / `FAILED (errors=1)`; `feature/windows-test-reliability` owns the test file, so it is out of scope for this audit |
| Node tests | Hosted `node-tests` passed on #745 head and merged ancestry; skipped on the docs-only main push | CONFIRMED, P3 | Run `45025014934` job `137216114112` success; run `45025462954` node job skipped. Skipped ≠ failed |
| Local agent-output guard tests | 30 tests fail on Windows because the secure reader deliberately fails closed and symlink setup raises `WinError 1314`; exact-head Ubuntu CI passed | CONFIRMED, P2 | Fresh local output: `Ran 30 tests` / `FAILED (failures=36, errors=2)`; `docs/security/AGENT_OUTPUT_GUARD.md:90-91,151` documents no weaker Windows fallback. NOT a regression claim |
| Graphify canonical vs legacy | Canonical implementation is `tools/graphify/`; `scripts/integrations/graphify_portfolio.py` is a 67-line re-export adapter; no duplicate orchestration remains in source | CONFIRMED, P1 resolved | Files present at `a9e6e1b`; PR #726 merged; adapter header declares canonical path. Real CLI/wheel provenance UNKNOWN |
| Docker / image scanning | One container image is built, smoke-tested and scanned with signature/checksum-verified Trivy 0.76.1; CycloneDX SBOM policy runs in CI | CONFIRMED, P3 | `ci.yml:578-640`; main check `Build, smoke-test and scan one container image` success in run `45025462954` |
| Dependency scanning | `pip-audit` on both dev/API locks and `npm audit --audit-level=high` are in CI; no fresh local scan run here | CONFIRMED (configuration), P3 | `ci.yml:261,381-382`; hosted main run success. Local Bandit unavailable in this environment |
| Terraform | `fmt`, `init -backend=false -lockfile=readonly`, `validate`, synthetic `test`, conftest HCL policy and unit tests run in CI and pass on main | CONFIRMED (source/CI), P3 | `ci.yml:652-698`; main `terraform-validate` success. No apply, plan with real backend, cloud auth or resource change |
| Kubernetes | `k8s/` manifests exist, but no validation job (`kubectl`, `kubeconform`, kustomize or helm lint) was found; no local validation run | UNKNOWN, P2 | Workflow grep returned only example/research mentions; `k8s/README.md` describes examples. No cluster access attempted |
| OIDC / WIF | No trusted issuer/client, HTTPS callback, JWKS rotation/revocation or signed-token acceptance at the current SHA; historical staging classification was `invalid_staging_config stage=oidc` | BLOCKED / CONFIRMED gap, P0 | `docs/p01/P01_NO_GO_DECISION_2026-11-19.md:11,21`; ledger gate `p01-managed-saas=BLOCKED`. No hosted IdP contacted |
| Tenant isolation / RLS | Disposable CI PostgreSQL RLS checks pass; hosted API cross-tenant denial with a restricted non-owner identity is absent | BLOCKED / CONFIRMED gap, P0 | CI `postgres-rls` success on main; NO-GO matrix row `RLS`; no database/provider access |
| AI-9 | Evidence file is bound to SHA `838083fd…`, not current `a9e6e1b…`; all seven controls are `UNVERIFIED` | CONFIRMED, P0 gate | `docs/ai9/evidence.json:4-55`; `python scripts/check_ai9_evidence.py --expected-sha a9e6e1b…` exit 1; ledger `ai9-detection-quality=BLOCKED` |
| Codex runtime | No configured-repository CLI/MCP handshake or trusted-client public lookup was performed; dispatch tools are `DRY_RUN` by design | UNKNOWN, P1 | Ledger `codex-agent-runtime-acceptance=OPEN`; `docs/CODEX_AGENT_OPERATING_MODEL.md`; no agent service started |
| P01 managed SaaS | Fixed-SHA owner NO-GO covers eight controls: SPEND, PROVIDER, OIDC, RLS, TLS_NETWORK, BACKUP, OWNER, RELEASE | CONFIRMED, P0 gate | `docs/p01/P01_NO_GO_DECISION_2026-11-19.md` is bound to `0f062c03…`; it does not rebind to newer commits |
| Observability | Local OTLP endpoint is documented as fixed to `127.0.0.1:4318` and disabled in hosted/CI/Kubernetes runtimes; no production telemetry evidence | INFERRED source claim / UNKNOWN runtime, P2 | `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md:67,77` describes source-level monitoring controls; the underlying runtime doc was not reopened here and no monitoring stack was inspected |
| Backups / restore | No encrypted seven-day hosted backup or independent restore with observed RPO/RTO; Render Free has no managed backup | CONFIRMED gap, P0 gate | P01 NO-GO row `BACKUP`; [Render Free](https://render.com/docs/free) and [Render Postgres backups](https://render.com/docs/postgresql-backups) |
| Rollback | Pages rollback workflow exists and main publication succeeded; no hosted managed-service restore was exercised | CONFIRMED source / BLOCKED runtime, P0 for release | `.github/workflows/rollback-pages.yml`; `docs/runbooks/GRAPHIFY_ROLLBACK.md` is source-control rollback only |
| Cost controls / Render expiry | Fail-closed guard reports `REVIEW_REQUIRED`; expiry is `2026-12-05T10:33:24.202776Z`; no combined tax-inclusive USD 100 provider cap proven | CONFIRMED, P0 gate | `python scripts/check_render_free_expiry.py --json` exit 1; `paid_activation_authorized=false`, `production_approved=false`, `provider_access_performed=false` |
| Milestone ledger | Summary reports `latest_pr: 717` while merged PRs through #745 exist; three gates remain open | CONFIRMED, P2 | `python scripts/milestone_ledger.py --summary` exit 0; `docs/MILESTONE_LEDGER.json` and `STATE.md` are owned by other branches |
| Agent worktree ownership | 53 worktrees; 49 feature/docs branches touch `README.md`; four touch `STATE.md` and `docs/MILESTONE_LEDGER.json`; one owns `tests/test_check_repo_policy.py` | CONFIRMED, P1 conflict risk | `git worktree list` and `git diff --name-only origin/main...<branch>` scan; this audit avoids those owned files except the explicitly authorized README links |
| Keycloak runtime | Not started; the AGENTS.md exception is inactive until the reconciliation PR is merged and separate per-run approval is given | BLOCKED / UNKNOWN, P1 | No Docker context inspection, container start, TLS material access or token operation performed |

## 6. Overlapping branches and file ownership

- `README.md` has 49 competing branch diffs, including `feature/agent-approval-gates`, `feature/agent-policy-engine`, `feature/ai-provider-evaluation-finalization`, `feature/devobs-production-gap-audit`, `feature/graphify-unification-readiness`, `feature/multi-agent-work-orchestrator` and `feature/windows-test-reliability`. This audit changes only the two authorized report links in README; any parallel README work will need a reviewed reconciliation.
- `STATE.md` and `docs/MILESTONE_LEDGER.json` are owned by `docs/record-pr736-milestone`, `feature/blocked-task-ownership-guard`, `feature/ledger-reconcile-pr704` and `feature/reconcile-pr716-pr717`; they were not edited.
- `scripts/check_repo_policy.py` has no competing branch owner. `tests/test_check_repo_policy.py` is owned by `feature/windows-test-reliability`; the future V-01 branch must coordinate that test file with that owner rather than overwrite unrelated work.
- The two new report paths and `docs/roadmap/NEXT_VERIFIED_REMEDIATION.md`-style prior names are not duplicated on `main`. This audit creates only `docs/audits/DEVOBS_CURRENT_STATUS.md` and `docs/roadmap/DEVOBS_NEXT_ACTIONS.md`.
- No agent was started, no Draft PR was auto-created by an agent service, and no branch was merged or deployed.

## 7. Exactly one highest-priority confirmed unresolved actionable blocker

**V-01 — repository policy auditor cannot detect a zero-approval ruleset (CONFIRMED, P1).**

P01, AI-9, Render spend/backup and exact-SHA release authorization are higher-severity **owner-decision gates** and remain P0/BLOCKED in section 5; they are not agent-owned source defects and cannot be delivered as a code fix on a branch without owner authorization. Among actionable, evidence-backed source defects, V-01 is the single highest priority because it directly weakens independent review of all future security-sensitive changes and is ranked as remediation #1 in `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md:32-40`.

| Item | Definition |
| --- | --- |
| Root cause | The read-only checker validates rule *presence* but never inspects `pull_request.parameters.required_approving_review_count`; the “compliant” test fixture and the live ruleset both use zero approvals |
| Files | `scripts/check_repo_policy.py:200-207` (validator); `tests/test_check_repo_policy.py:45,64-69` (fixture and passing assertion). A short new `docs/security/REPOSITORY_APPROVAL_POLICY.md` is optional documentation in the future branch |
| Live evidence | Ruleset `24507159`: `required_approving_review_count: 0`, `required_reviewers: []`, `require_code_owner_review: false`, `require_last_push_approval: false`; `validate` and CodeQL remain required |
| Proof of defect | Fixture mutation demo: count `0` → `findings=[]`; count `1` → `findings=[]`. Neither state produces a finding |
| Test requirement | Behavioral offline tests using `api_fixtures()` + `audit_repository(api_get=...)`: reject `0`, missing, `None`, string, float and negative counts; accept `1` and `2`; ensure other drift findings are additive; preserve all existing checks |
| Rollback | Revert the future three-file feature branch; no hosted settings, secrets or deployments are changed by the fix. The checker returns to report-only behavior |
| Proposed branch/worktree | New isolated branch `feature/repo-policy-approval-count` from `a9e6e1b…`; Draft PR title `fix(policy): fail closed on zero required approvals`; target `main`; no merge, deployment, auto-merge or settings change |
| Owner decision still required | The live ruleset must be changed separately by the owner to require at least one independent approval. The checker becoming stricter will intentionally report drift until that happens |
| Out of scope | `README.md`, `STATE.md`, ledger, workflows, dependencies, hosted ruleset settings, gate promotion and the Windows temp-file test owned by `feature/windows-test-reliability` |

The full prioritized sequence, acceptance tests and rollback criteria are in [DEVOBS_NEXT_ACTIONS.md](../roadmap/DEVOBS_NEXT_ACTIONS.md).

## 8. Verification evidence (exact commands and final lines)

| Command / read | Final output | Exit |
| --- | --- | ---: |
| `git fetch origin --quiet` | silent; `git rev-parse origin/main` = `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` | 0 |
| GitHub API `GET /repos/hamedonassar95/Devobs` | `full_name=hamedonassar95/Devobs default_branch=main private=False archived=False pushed_at=2026-11-22T13:32:43Z` | 0 |
| GitHub API `GET /user` | `AUTH_USER=ANONYMOUS status=401` | 401 |
| GitHub API open pulls | `OPEN_PR_COUNT=0` | 0 |
| GitHub API pulls #720/#722/#724/#725/#726/#744/#745 | all `state=closed draft=False merged=True`; exact SHAs in section 3.1 | 0 |
| `git ls-remote origin refs/pull/<n>/head` | full head SHAs in section 3.1 | 0 |
| `git merge-base --is-ancestor <merge> origin/main` | true for #720/#724/#725/#726/#744/#745; false for #722 nested merge, with changed files present | 0/1 as expected |
| GitHub API `commits/<sha>/check-runs` | required-check and skipped-job evidence in section 3.2 | 0 |
| GitHub API `actions/runs?head_sha=<sha>` | #745 `45025101917` success, `45025101872` success, `45025098775` success; main `45025462954` success, `45025462455` success | 0 |
| GitHub API `rules/branches/main` and `rulesets/24507159` | `validate`, `CodeQL`, strict up-to-date, PR required, `required_approving_review_count: 0` | 0 |
| `python scripts/milestone_ledger.py --summary` | `{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}` | 0 |
| `python scripts/check_ai9_evidence.py --expected-sha a9e6e1b…` | `AI9 BLOCKED: source SHA does not match the checked revision; … 7 UNVERIFIED` | 1 (fail-closed) |
| `python scripts/check_render_free_expiry.py --json` | `{"exit_code": 1, "expires_at": "2026-12-05T10:33:24.202776Z", … "status": "REVIEW_REQUIRED"}` | 1 (fail-closed) |
| `python scripts/check_repo_policy.py --repository hamedonassar95/Devobs` | `Ruleset 'Protect main' response did not include bypass actors…` | 2 (inconclusive, anonymous API) |
| `python -B scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` | 0 |
| `python -c` fixture mutation demo | `RESULT_ZERO []`; `RESULT_ONE []` | 0 |
| `python -B -m unittest tests.test_check_repo_policy -v` | `Ran 16 tests` / `FAILED (errors=1)` — Windows `PermissionError` on locked temp file | 1 |
| `python -B -m unittest tests.test_agent_output_guard -v` | `Ran 30 tests` / `FAILED (failures=36, errors=2)` — documented Windows fail-closed / `WinError 1314` | 1 |
| `git diff --check` | silent | 0 (run after edits) |

## 9. Checks that could not run or were deliberately skipped

- Authenticated GitHub review histories and private ruleset fields: unauthenticated API; `/user` returned 401. `bypass_actors` was omitted, so it is UNKNOWN.
- PR creation via `gh`: CLI unavailable. Unauthenticated GitHub REST Draft PR creation previously returned 401; no token was read.
- Further live GitHub API queries: anonymous rate limit was reached after the evidence above was collected. Earlier responses are retained as VERIFIED; no missing value was inferred.
- Hosted OIDC/WIF, JWKS, signed-token tests, managed PostgreSQL RLS denial, backup/restore, RPO/RTO, provider billing caps, cloud/GCP commands, production deployment settings and customer data: out of scope and not accessed.
- Terraform apply/destroy, Kubernetes apply or dry-run, Docker daemon operations, Keycloak container runtime, paid inference, OpenArt generation and agent dispatch: not run; required approvals/conditions are absent.
- Full `tests/` discovery and local Bandit/Trivy/kubectl: not available or not needed for this documentation-only audit; hosted exact-head evidence is reported instead and local failures are not suppressed.

## 10. Conclusion

Merged PRs and current CI are reconciled; no open PR or merge conflict is blocking this branch. Source-level controls are substantially in place, but Devobs is **not** production-ready: P01 remains **NO-GO/BLOCKED**, AI-9 remains **BLOCKED**, Codex runtime acceptance remains **OPEN**, the Render Free database expiry remains `REVIEW_REQUIRED`, and the active ruleset still permits merges without an independent approval. The single actionable next fix is V-01 as specified above and in [DEVOBS_NEXT_ACTIONS.md](../roadmap/DEVOBS_NEXT_ACTIONS.md).

**Final status: `PENDING HUMAN APPROVAL`.** No gate was promoted, no branch was merged, and no production or hosted action was taken.

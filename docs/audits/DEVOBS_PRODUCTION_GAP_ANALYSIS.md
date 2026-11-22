# Devobs production-readiness gap analysis (2026-11-22)

Scope: read-only reconciliation of requested merged work against
`hamedonassar95/Devobs`, followed by exactly one bounded repair on an isolated
branch. This document is evidence classification, **not** a production GO, a
gate promotion, or owner approval.

## 1. Fixed baseline and method

| Item | Value | Label |
|---|---|---|
| Owner remote | `https://github.com/hamedonassar95/Devobs.git` | VERIFIED (`git remote get-url origin`) |
| `git fetch origin` | exit `0` | VERIFIED |
| `origin/main` at fetch | `88556034e24e52e529c276ab6cc753e8fc026c91` | VERIFIED (`git rev-parse origin/main`) |
| Worktree | `C:\Users\NASSAR FAMILY\AppData\Local\Temp\opencode\devobs-production-recovery` | VERIFIED |
| Branch | `feature/devobs-production-recovery`, created from the SHA above; `main` untouched | VERIFIED |
| Tool versions | Python `3.12.10`; git `2.56.1.windows.1` | VERIFIED (`python --version`, `git --version`) |

Method: no hosted action, no secret read, no agent dispatch, no paid service,
no cloud command, no merge and no deploy. Historical claims were checked only
against local files and public read-only GitHub REST responses.

Official references relied on:

- GitHub REST API, [Get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request) — fields `merged` and `merge_commit_sha`.
- GitHub REST API, [Get rate limit status](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) — anonymous core quota.
- GitHub REST API, [List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference).
- Git, [`git rev-parse`](https://git-scm.com/docs/git-rev-parse) and [`git diff --check`](https://git-scm.com/docs/git-diff#Documentation/git-diff.txt---check).
- Python, [`unittest` command-line interface](https://docs.python.org/3/library/unittest.html#command-line-interface).

## 2. Reconciliation of the requested PRs

All thirteen requested PR references (#720, #722, #724, #725, #726, #739,
#740, #741, #743, #744, #745, #746, #747) were confirmed **merged** through the
public pull endpoint. Label: VERIFIED (API `merged: true`; `merged_by` =
`hamedonassar95` for every PR). `merge_commit_sha` is the resulting commit,
which is not necessarily the PR head SHA on squash/rebased stacks — ledger
reconciliation must use merge SHAs (ASSUMED normalization of squash-merge
semantics).

| PR | Head SHA | `merge_commit_sha` | Check runs reported by read-only REST (success/skipped) |
|---|---|---|---|
| #720 | `25b2afa38137796dfee6f071fe8af21a8a675569` | `1b8a28711ece5f168a74d736e429abd88f5760c9` | 26 / 6 |
| #722 | `fc7bd3694391ff9eeb8ccdfdd8e8f0d8666765ac` | `25b2afa38137796dfee6f071fe8af21a8a675569` | 19 / 8 |
| #724 | `0812ff3f2a32e156e606f34a898099b0ced48f8f` | `cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1` | 27 / 5 |
| #725 | `b04cffe98c207a76b4a80ffd2e2c5aa26f876b86` | `41353d1451524492d6ca6e3ae8bb1b7d12c87b45` | 24 / 7 |
| #726 | `7e003d6c773ccf04fa70ebce25a4666225339a6b` | `799efe673a72aeadf3016667eaed853d2553aaa8` | 24 / 7 |
| #739 | `6fe382fcad57f7d1276874c833af1918886ee79b` | `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f` | 26 / 6 |
| #740 | `4a9ece94630eb1325ef5852b90c7b8b800252bbb` | `6fe382fcad57f7d1276874c833af1918886ee79b` | 21 / 7 |
| #741 | `35e368ebf72656938a8fdebd453fef794607a108` | `f02319237b604d5447598cfb6f2d39e66e14d3f0` | 26 / 6 |
| #743 | `066f060c401c8d99a445640ef49707bc68990dd0` | `8aa96bd83a93e196c8ba6381dfa437063ebad0a1` | 27 / 5 |
| #744 | `20224238e9a2aacae4463dfaa15637b7a2bd55e2` | `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` | 21 / 9 |
| #745 | `af99155d757f332443f0a07d064ea4d215c9c02a` | `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6` | 26 / 8 |
| #746 | `aa61b9877eb52b08cd2d83d83dab6a508b341398` | `66cc062cfea96eda025c643e1929d450c0f0f528` | 26 / 6 |
| #747 | `762353cceb808054c1e6b748e880003d7f7fc34e` | `88556034e24e52e529c276ab6cc753e8fc026c91` | 25 / 6 |

Reconciliation notes:

- Exact-head check-run groups contained only `success` and `skipped`; no
  failure, cancellation or timeout was reported in any listed PR (VERIFIED by
  the same read-only queries). An earlier read of #720/#724 produced a
  different success/skip grouping (16/10 and 16/12 respectively), so these
  counts are endpoint/selection dependent and are **not** used as proof of
  current CI (UNVERIFIED).
- `/reviews` returned **no `APPROVED` review** for any of the thirteen PRs;
  #720 has an owner `COMMENTED` review and #745 a bot `COMMENTED` review
  (VERIFIED). This is not owner approval of an exact SHA for this task.
- #722 and #740 are feature-branch merges feeding the stack; their head SHAs
  are not ancestors of `main` (VERIFIED). Do not present their heads as
  `main` content.
- Current branch-protection ruleset details: UNVERIFIED. A prior audit
  recorded `protected=True`, ruleset "Protect main" id `24507159` on
  2026-11-20; historical evidence only.
- Exact Actions run ID per listed PR was not captured (UNVERIFIED). A prior
  recovery audit records CI `44650319512` at `cecae6c`; historical only.

Preserved prior work (not modified, not merged): progress-report branch
`feature/opencode-local-progress-readiness` at
`7e3231a5c9acd0ffc7b4a8bac7a2190672259ca9`; integration branch
`feature/alertmanager-v035-contract` at
`7ac3f690356f4999980fc37ca53b5de6bef9964e`. Overlapping worktrees were
inspected and left untouched, including `feature/devobs-production-gap-audit`,
`feature/devobs-readiness-reconciliation`, `feature/devobs-readiness-audit`,
`feature/repository-recovery-finalization`,
`feature/repository-recovery-hardening`, `feature/agent-coordination-security-audit`,
`feature/blocked-task-ownership-guard`, `feature/integration-evidence-readiness`,
`feature/intelligent-integration-control-plane`, and
`feature/pr-readiness-evidence-engine` (VERIFIED clean where scanned).
Duplicate/overlap exists across unmerged branches for Graphify 0.9.112/0.9.113,
PR-readiness engines, integration-control runbooks, `.agents/skills/` vs
`.claude/skills/` (F14), and several audit documents; this pass resolves none
of those overlaps.

### Reconciliation limits

- Further live GitHub REST verification: BLOCKED — the anonymous core quota
  was exhausted (`limit 60`, `remaining 0` in one read; `remaining 2` in the
  earlier Phase-1 read before its final queries). No token was read or used.
- `gh` CLI is unavailable; Draft PR creation by authenticated CLI is BLOCKED.
- Current-base hosted CI run: UNVERIFIED. No hosted rerun was authorized.

### Post-baseline movement (VERIFIED 2026-11-23)

A later `git fetch origin` (exit `0`) showed `origin/main` advanced to
`b90407040e3d2a34627679f2cbca14db46eb70ca` with three new merges:
#748 `4ddf18a`, #749 `b904070`, #750 `2db6788`. GitHub `compare/main...feature/devobs-production-recovery`
returned `diverged`, initially `ahead_by: 2` and later `ahead_by: 3` after the
second evidence commit, `behind_by: 3`, `status: 200`. The changed
files on newer `main` are `STATE.md`, `docs/MILESTONE_LEDGER.json`,
`tests/test_milestone_ledger.py`, and console UI files — **no overlap** with
this branch's six changed files (VERIFIED by `git diff --name-only`).

Consequence for D5: the governance drift was CONFIRMED at the fixed base
(`latest_pr:717`), but PR #750 subsequently reconciled it on `main`. The
ledger at newer `main` validates to
`{"latest_pr":747,"merged_milestones":305,"open_gates":3}` with gate statuses
unchanged (VERIFIED via `python scripts/milestone_ledger.py --file <exported
main ledger> --summary`, exit `0`). D5 is therefore **resolved upstream**, not
by this branch, and remains unmodified here.

No history rewrite or rebase was performed: the reviewed SHAs and evidence in
this audit stay bound to the fixed base. The manual Draft PR should use
`main` (`b904070…`) as base; no conflicting file is expected.

## 3. Capability inventory

Statuses are normalized as: IMPLEMENTED_AND_VERIFIED (local evidence + tests
run here), IMPLEMENTED_NOT_VERIFIED (source/history exists; current live proof
absent), PARTIAL, MISSING, BLOCKED (owner/hosted dependency).

| Area | Capability | Status | Evidence / limit |
|---|---|---|---|
| CI/governance | CI workflow suite | IMPLEMENTED_NOT_VERIFIED | `.github/workflows/ci.yml:26-27,34-783` with least-privilege defaults and python/RLS/security/container/Terraform/site jobs; current-base CI UNVERIFIED. |
| CI/governance | Ledger schema validator | IMPLEMENTED_AND_VERIFIED | `scripts/milestone_ledger.py:97-118`; 86 ledger tests pass here. |
| CI/governance | Ledger/state freshness | PARTIAL | `docs/MILESTONE_LEDGER.json` summary `latest_pr: 717`; `STATE.md:1-7` ends at #717; `docs/DEVOBS_READINESS_CURRENT.md:1-7` ends at #641; HEAD includes #747. |
| API/auth | Read-only WSGI API + OIDC/tenant gate | IMPLEMENTED_NOT_VERIFIED | `scripts/devobs_intelligence/api_app.py:21-30`, `oidc_tokens.py:29-47`, `tenant_scope.py:1-19`; no live issuer/JWKS exchange. |
| API/auth | PostgreSQL RLS schema + disposable tests | IMPLEMENTED_NOT_VERIFIED | `deploy/postgres/001_tenant_rls.sql:4-57`, `002_service_registry.sql:7-22`, `tests/test_postgres_rls_integration.py:1-35`; hosted denial UNVERIFIED. |
| API/auth | Hosted OIDC and cross-tenant acceptance | BLOCKED | `docs/p01/p01-no-go-matrix-2026-11-19.json:23-36` marks OIDC and RLS BLOCKED. |
| Supply chain | Action pinning / Trivy / CodeQL-style jobs | IMPLEMENTED_NOT_VERIFIED | `scripts/check_action_pins.py`, `ci.yml:270-650`; 48 files pass locally here. Zizmor manual/informational per `docs/audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md:88-89`. |
| Supply chain | Graphify wheel local verifier | IMPLEMENTED_NOT_VERIFIED | `tools/graphify/supply_chain.py:26-52`, `repository_intelligence.py:144-155`; real wheel/provenance NOT RUN. **The older F04 "missing hash verification" finding is RESOLVED in current source and is not an open defect.** |
| Supply chain | Console lockfile consistency | PARTIAL | `apps/ai-intelligence-console/bun.lock:6-32` still names `react-example` with older ranges while `package.json:2-40` names `devobs-ai-intelligence-console`; node selector covers console paths (`scripts/assess_change.py:110-125`). |
| Cloud/K8s | Terraform Artifact Registry validation | IMPLEMENTED_NOT_VERIFIED | `infra/terraform/main.tf:1-32`, `infra/terraform/README.md:3-17` — validation only, placeholder backend, no apply. |
| Cloud/K8s | Hardened container/K8s baseline | IMPLEMENTED_NOT_VERIFIED | `k8s/deployment.yaml:17-37` (non-root, dropped caps, read-only root), `k8s/service.yaml:8` (`ClusterIP`); no live deploy. |
| Cloud/K8s | WIF/IAM/GKE provisioning and NetworkPolicy | MISSING | Terraform README says no GKE/IAM/deploy; no `NetworkPolicy` found under `k8s/`. |
| Reliability | Local monitoring stack | IMPLEMENTED_NOT_VERIFIED | `monitoring/compose.yml:1-100` binds Prometheus/Alertmanager/OTLP to loopback only. |
| Reliability | Health retry / Pages rollback rehearsal | PARTIAL | `.github/workflows/deployment-health-check.yml:22-91`, `docs/ROLLBACK_RUNBOOK.md`; restore jobs historically skipped. |
| Reliability | Live alert delivery, restore, SLO | BLOCKED | No external receiver, isolated hosted restore, RPO/RTO or live SLO evidence; see `docs/audits/DEVOBS_RECOVERY_AUDIT.md:167-176`. |
| AI/agents | AI-9 evidence intake checker | PARTIAL | `scripts/check_ai9_evidence.py:2-6,70-77,118-120` never returns GO; ledger `ai9-detection-quality=BLOCKED`; no natural incident corpus. |
| AI/agents | Two-agent/offline artifact guards | PARTIAL | `scripts/check_two_agent_tasks.py`, `tools/agent_output_guard.py`, `docs/security/AGENT_OUTPUT_GUARD.md:3-6`; confirmed bypasses listed below. |
| AI/agents | Codex runtime acceptance | BLOCKED (ASSUMED normalization) | Ledger says `codex-agent-runtime-acceptance` **OPEN**; normalized to BLOCKED. Config/docs are not runtime proof (`docs/CODEX_CAPABILITY_READINESS.md:5-19`). |
| Graphify | Canonical consolidation | IMPLEMENTED_NOT_VERIFIED | `tools/graphify/common.py:18-19`, `portfolio.py:6-92`, `docs/audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md:79-95,122-160`; real CLI extraction UNVERIFIED. |
| Integrations | Offline CloudEvents/Alertmanager/OTLP bridges | PARTIAL | `docs/AI_EVENT_INGESTION.md`, `docs/integrations/ALERTMANAGER_BRIDGE.md:15`, `docs/integrations/opentelemetry.md:7`; no live routing. |
| P01 | Managed SaaS | BLOCKED | All eight controls BLOCKED in `docs/p01/p01-no-go-matrix-2026-11-19.json:8-64`; ledger `p01-managed-saas=BLOCKED`. |
| P01 | Billing/metering/tenant onboarding | MISSING | `docs/PRODUCT_SAAS_READINESS.md:3-9` says not sellable; no billing implementation found in bounded searches. |
| P01 | Production release GO | BLOCKED | `docs/P01_ACTIVATION_READINESS.md:67-69,109-112`; P00 GO is separate and there is no independent exact-SHA release approval. |

UNVERIFIED, therefore **not** classified as defects: hosted tenant denial,
live OIDC exchange, encrypted backup restore, alert delivery, live SLO, and
real Graphify wheel/CLI provenance.

## 4. Confirmed defects and prioritization

All items below are CONFIRMED against the fixed base. Only one was repaired.

| ID | Defect | Evidence | Disposition |
|---|---|---|---|
| D1 | Two-agent manifest accepts traversal/empty branch segments (`feature/../main`, `feature//x`, `feature/x/..`, `feature/x/`, `fix/./y`, `docs/../main`, `chore//x`) as PASS, breaking ownership-conflict detection. | `scripts/check_two_agent_tasks.py:52` old `BRANCH_RE`; behavioral repro 1 test / 7 subtest failures / exit 1. | **SELECTED — repaired here.** |
| D2 | Two-agent completion evidence trusts self-asserted `PASS` and `previous_status`; no command output or source SHA binding. | `scripts/check_two_agent_tasks.py:218-245` (pre-repair numbering). | Deferred: requires contract redesign and owner review; larger than one bounded repair. |
| D3 | `complete`/`blocked` tasks skip enabled-agent validation. | `scripts/check_two_agent_tasks.py:278-288`. | Deferred: behavioral policy change, not a one-line fail-closed fix. |
| D4 | `PR_RE` is not bound to the task repository; weak ref validation remains after D1. | `scripts/check_two_agent_tasks.py:53-55,243-245`. | Deferred: needs a separate compatibility decision for existing manifests. |
| D5 | Governance drift: ledger #717 / readiness doc #641 vs merge #747 at the fixed base. | `docs/MILESTONE_LEDGER.json`, `STATE.md`, `docs/DEVOBS_READINESS_CURRENT.md`. | Deferred here (needs owner-reviewed exact CI evidence; was REST-quota blocked). **Resolved upstream by #750** on newer `main` (ledger `latest_pr:747`, `305` milestones, gates unchanged) — VERIFIED 2026-11-23; not changed on this branch. |
| D6 | Stale console Bun lock (`react-example`, older ranges). | `apps/ai-intelligence-console/bun.lock:6-32`, `package.json:2-40`. | Deferred: dependency regeneration is a separate supply-chain change; no network/dependency install authorized here. |

Resolved historical finding, not an open defect: AUD-02 blocked-task ownership
is fixed in current source (`scripts/check_two_agent_tasks.py:32-36,276-317`).

**Selection rule applied:** maximize confirmed impact × fail-closed value ÷
change risk. D1 wins because it is a confirmed security-relevant bypass in a
gate that is explicitly documented as advisory but fail-closed, it is fully
reproducible offline, and the repair is bounded to one helper plus one call
site with a behavioral regression test. D2/D3/D4 need contract/policy
decisions, D5 needs owner-reviewed CI evidence, D6 needs dependency tooling —
none is a safe single repair in this pass.

## 5. The single selected repair

- Files: `scripts/check_two_agent_tasks.py`, `tests/test_two_agent_tasks.py`.
- Diff: **2 files changed, 17 insertions(+), 1 deletion(-)**.
- Production change: add `_valid_branch()` requiring a `BRANCH_RE` match plus
  segment-by-segment rejection of `""`, `"."` and `".."` after the prefix, and
  call it from `evaluate()` in place of the bare regex check.
- Test change: one behavioral test with seven subtests asserting `FAIL` and
  `invalid task branch`.
- No other source/test file was changed. No report evidence was overwritten.
  No gate status, ledger milestone, CI config, or hosted setting was changed.

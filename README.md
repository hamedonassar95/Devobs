# Devobs

## P01 readiness: verified NO-GO evidence (2026-11-19)

[Read the fixed-SHA P01 NO-GO owner decision and acceptance matrix](docs/p01/P01_NO_GO_DECISION_2026-11-19.md) for the reviewed `main` SHA `0f062c03dbefceebf8eaca79bdaf30c2483f99be`. This is source/read-only metadata evidence, **not** a provider hard-cap, hosted test or P01 approval. The existing P01 evidence sample and P01/AI-9/Codex gates are unchanged. A separate owner decision is needed before the existing Free PostgreSQL expiry on 2026-12-05.


[![CI](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml)

## PR Readiness and Security Evidence Engine

[PR Readiness Engine](docs/architecture/PR_READINESS_ENGINE.md) provides a deterministic, fail-closed, read-only governance model for PR evidence. It evaluates pre-collected CI/check/security/approval evidence into READY_FOR_HUMAN_REVIEW, PENDING, BLOCKED, or UNVERIFIED, redacts sensitive values, and never auto-approves or merges.

`sh
python -m py_compile devobs/governance/__init__.py devobs/governance/evidence_validator.py devobs/governance/pr_readiness.py
python -m unittest tests.governance.test_evidence_validator tests.governance.test_pr_readiness -v
`

## Read-only PR readiness gate

[The PR Readiness Gate](docs/agents/PR_READINESS_GATE.md) is a read-only CLI that combines GitHub
PR metadata, Actions checks, branch protection, review state, unresolved review requests, and
mergeability into `VERIFIED_READY`, `BLOCKED`, or `UNVERIFIED`. Missing evidence never counts as
success, local test output is never treated as GitHub CI, and `VERIFIED_READY` is not human
approval and does not authorize a merge.

```sh
python scripts/pr_readiness_gate.py --pr 123 --repo OWNER/REPO
python -m unittest discover -s tests -p "test_pr_readiness_gate.py" -v
```

**Read-only Render Free checkpoint refreshed (2026-11-19):** [Free PostgreSQL inventory, fixed 2026-12-05 expiry, and offline fail-closed preflight](docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md). This is not a hosted API test, backup, paid activation or P01 GO; separate owner retention/retirement authorization remains required.

**Retirement planning approved (no deletion, 2026-11-19):** [Owner-gated Render Free PostgreSQL retirement plan](docs/plans/2026-11-19-render-free-postgres-retirement-plan.md). The plan documents dependencies, rollback limits and separate execution approval; it makes no hosted changes and P01 remains NO-GO.

## Offline Graphify repository intelligence (local, opt-in)

A pinned, offline Graphify CLI can build one local graph index per authorized
repository from a single installation, with no source upload, hosted service or
repository permission change. The allowlist, privacy controls, measured
per-repository results and current blockers are in
[the Graphify integration design](docs/architecture/graphify-integration.md);
the reusable module layout and native-versus-Devobs feature split are in
[repository intelligence](docs/architecture/repository-intelligence.md).
This is local evidence only and does not change P01, AI-9 or Codex runtime gates.

## Two-agent offline task coordination (manual; no agents started)

[The offline task contract](docs/agents/TWO_AGENT_COORDINATION.md) defines `CODEX`
and `OPENCODE` as separate worker roles driven by a local JSON manifest. The
checker validates unique task IDs, status transitions, concurrent file/branch
ownership, unresolved dependencies and completion evidence. It starts no agent,
makes no network call and does not grant merge, deploy, billing or production
approval. Arabic guidance is included in the same document.

```sh
python scripts/check_two_agent_tasks.py --help
python scripts/check_two_agent_tasks.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
```

`PASS` (0), `BLOCKED` (1) and `FAIL` (2) are advisory; P01 stays NO-GO, AI-9 stays
BLOCKED and Codex runtime acceptance stays OPEN.

A local [agent dispatch preflight guide](docs/agents/AGENT_DISPATCH_OPERATING_GUIDE.md)
now builds on that validator. It reuses the same contract, detects whether the
`codex` and `opencode` CLIs are present without invoking them, writes separate
per-worker instruction files, and lists the exact human-approval actions. Its
default and only mode is `DRY_RUN`; it starts no agent and grants no approval.

```sh
python scripts/agent_dispatch_preflight.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
```

A local [agent task-status report](docs/agents/AGENT_TASK_STATUS_REPORT.md) now
reuses the same manifest contract to print required task fields, blocked tasks,
PR references and evidence states. It is advisory local data only: it never
executes stored commands, fetches GitHub data, starts agents or treats a
manifest `PASS` as verification or approval. Arabic usage is included.

```sh
python tools/agent_task_status_report.py --manifest /path/to/tasks.json
python tools/agent_task_status_report.py --manifest /path/to/tasks.json --json-only
python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
```

## Root-cause audit and remediation roadmap (2026-11-20)

An evidence-driven audit of `origin/main` `4299a9d` confirmed one P1 root cause:
Python code under `tools/` was excluded from CI change selection, compilation
and Bandit scanning. The fix and its regression evidence are in
[the root-cause audit](docs/audits/DEVOBS_ROOT_CAUSE_AUDIT.md),
[the remediation roadmap](docs/roadmap/REMEDIATION_ROADMAP.md), and
[the rollback runbook](docs/runbooks/REMEDIATION_ROLLBACK.md). P01 remains
NO-GO/BLOCKED, AI-9 remains BLOCKED, and Codex runtime acceptance remains OPEN.

A subsequent recovery assessment of `origin/main` `cecae6c` verified that fix on
`main`, selected the remaining P1 Graphify canonicalization ambiguity for a
bounded repair, and documented all other blockers. See
[the recovery audit](docs/audits/DEVOBS_RECOVERY_AUDIT.md),
[the recovery roadmap](docs/roadmap/DEVOBS_RECOVERY_ROADMAP.md),
[the recovery rollback runbook](docs/runbooks/RECOVERY_AND_ROLLBACK.md), and
[the Graphify consolidation plan](docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md).
No release gate was promoted by this work.

## CI Failure Intelligence (read-only)

[CI Failure Intelligence](docs/agents/CI_FAILURE_INTELLIGENCE.md) provides deterministic, evidence-based diagnostics for failed GitHub Actions runs. It classifies failures (code/infrastructure/ambiguous), detects repeated signatures, correlates commit evidence, redacts secrets, labels findings `VERIFIED/INFERRED/UNVERIFIED`, and supports optional injectable AI summaries with rule-based fallback. Read-only: no code changes, reruns, merges, or deploys.

## AI Incident Intelligence (offline library)

[AI Incident Intelligence](docs/agents/AI_INCIDENT_INTELLIGENCE.md) builds on CI Failure Intelligence with evidence-linked hypotheses, explicit `HIGH`/`MEDIUM`/`LOW` confidence, advisory remediation steps, and human-readable summaries. It classifies dependency, configuration, timeout, test, CI failure, infrastructure, and unknown failures from sanitized logs, and maps bounded existing adviser signals to CI/infrastructure categories with schema-validated JSON reports. The raw project reference and source SHA stay inside the strict envelope boundary. AI providers are disabled by default; no automatic fixes, external API calls, merges, or deployments are performed.

## ظ…ط±ط§ط¬ط¹ط© ط®ط·ط· Codex ظˆط§ظ„ظƒظˆط¯ ط¨طµط±ظٹظ‹ط§ â€” Plannotator (ط§ط®طھظٹط§ط±ظٹ)

ط£ط¶ظپظ†ط§ [ط¯ظ„ظٹظ„ طھظƒط§ظ…ظ„ Plannotator ظ…ط¹ Codex](docs/integrations/PLANNOTATOR_CODEX_REVIEW.md) ظ„ط¥ط¬ط±ط§ط، ظ…ط±ط§ط¬ط¹ط§طھ ط¨طµط±ظٹط© ظٹط¯ظˆظٹط© ظ„ظ„ط®ط·ط· ظˆط§ظ„ظ€ diff ط¹ظ„ظ‰ ط¬ظ‡ط§ط² ظ…ظˆط«ظˆظ‚طŒ ط¯ظˆظ† طھظپط¹ظٹظ„ Hooks ط£ظˆ طھط´ط؛ظٹظ„ ط®ط¯ظ…ط§طھ ط£ظˆ ط¥ط¶ط§ظپط© طھط¨ط¹ظٹط§طھ ط¯ط§ط®ظ„ ط§ظ„ظ…ط³طھظˆط¯ط¹. **ط§ظ„ط­ط§ظ„ط©: ظ…ظˆط«ظ‘ظ‚ ظپظ‚ط· / ط§ظ„طھط´ط؛ظٹظ„ ط؛ظٹط± ظ…طھط­ظ‚ظ‚.** ظٹط­طھط§ط¬ ط§ط³طھط®ط¯ط§ظ… ط§ظ„ط£ط¯ط§ط© ط¥ظ„ظ‰ طھط«ط¨ظٹطھ ط§ط®طھظٹط§ط±ظٹ ظٹط±ط§ط¬ط¹ظ‡ ط§ظ„ظ…ط§ظ„ظƒ ط¹ظ„ظ‰ ط¬ظ‡ط§ط²ظ‡ط› ط¯ط¹ظ… ChatGPT ط¹ظ„ظ‰ iPhone ط£ظˆ Codex ط§ظ„ط³ط­ط§ط¨ظٹ ط؛ظٹط± ظ…ط«ط¨طھ. طھط³طھظ…ط± ظ…ظˆط§ظپظ‚ط§طھ ط§ظ„ط¥ظ†ط³ط§ظ† ظˆط­ظ…ط§ظٹط© `main` ظˆظپط­ظˆطµ CI ظˆط¨ظˆط§ط¨ط§طھ P01/AI-9 ط¯ظˆظ† طھط؛ظٹظٹط±.


### ظپط­طµ Plannotator ط¹ظ„ظ‰ Windows â€” ظ‚ط±ط§ط،ط© ظپظ‚ط·

ط¨ط¹ط¯ طھظ†ط²ظٹظ„ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط¹ظ„ظ‰ ط¬ظ‡ط§ط² Windows ظ…ظˆط«ظˆظ‚طŒ ظٹظ…ظƒظ† طھط´ط؛ظٹظ„ ظپط­طµ ط§ظ„ظ…طھط·ظ„ط¨ط§طھ ط¯ظˆظ† ط§ط³طھظ‡ظ„ط§ظƒ ط±طµظٹط¯ Codex ط£ظˆ طھط«ط¨ظٹطھ ط£ط¯ط§ط© ط£ظˆ طھظپط¹ظٹظ„ Hooks:

```powershell
$env:PLANNOTATOR_SHARE = "disabled"
$env:PLANNOTATOR_REMOTE = "0"
py -3 scripts/check_plannotator_windows_preflight.py --json
```

ط±ط§ط¬ط¹ [ط¯ظ„ظٹظ„ Windows ط§ظ„ط¢ظ…ظ†](docs/integrations/PLANNOTATOR_CODEX_REVIEW.md#windows-powershell-read-only-prerequisite-check-no-codex-credits). ط§ظ„ظ†طھظٹط¬ط© `PREREQUISITES_PRESENT_RUNTIME_UNVERIFIED` ظ„ط§ طھط«ط¨طھ ط£ظ† Plannotator ظٹط¹ظ…ظ„طŒ ط£ظ…ط§ `BLOCKED` ظپطھطھط·ظ„ط¨ ظ…ط±ط§ط¬ط¹ط© ط§ظ„ط³ط¨ط¨ ظ‚ط¨ظ„ ط£ظٹ طھط«ط¨ظٹطھ ظٹط¯ظˆظٹ. ط§ظ„ط£ط¯ط§ط© ظ„ط§ طھطھطµظ„ ط¨ط®ط¯ظ…ط© ط®ط§ط±ط¬ظٹط© ظˆظ„ط§ طھط¹ط¯ظ„ ط¥ط¹ط¯ط§ط¯ط§طھ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط£ظˆ Codex.

## طھظ†ط¨ظٹظ‡ ط£ظ…ظ†ظٹ ظ…ط؛ظ„ظ‚ â€” ط³ط­ط¨ طھظ‚ط±ظٹط± picomatch (`GHSA-fc5q-39xc-vjpf`)

ط³ظڈط­ط¨ ط§ظ„طھظ‚ط±ظٹط± ط§ظ„ط£ظ…ظ†ظٹ `GHSA-fc5q-39xc-vjpf` / `CVE-2026-112366` ط§ظ„ط®ط§طµ ط¨ط­ط²ظ…ط© `picomatch` ظ…ظ† ظ‚ط§ط¹ط¯ط© ط¨ظٹط§ظ†ط§طھ GitHub Advisory ظپظٹ **2026-11-18T15:38:56Z**طŒ ط¨ط¹ط¯ ط£ظ† ظƒط§ظ† ظٹط؛ط·ظٹ ط§ظ„ط¥طµط¯ط§ط±ط§طھ `<= 4.0.7` ط¯ظˆظ† ط¥طµط¯ط§ط± ظ…ظڈطµظ„ط­. ظٹط¹طھظ…ط¯ ظ‡ط°ط§ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط¹ظ„ظ‰ `picomatch@4.0.7` ط¹ط¨ط± `vite@8.3.8` ظˆ`vite â†’ tinyglobby â†’ fdir`طŒ ظˆط£ط¹ط§ط¯ طھط´ط؛ظٹظ„ `npm audit --audit-level=high` ط¯ط§ط®ظ„ `apps/ai-intelligence-console` ط¹ظ†ط¯ **2026-11-18T20:39:02Z** ط§ظ„ظ†طھظٹط¬ط© `found 0 vulnerabilities` ظ…ط¹ ط±ظ…ط² ط®ط±ظˆط¬ `0`.

**ظ„ظ… ظٹظڈط؛ظٹظژظ‘ط± ط£ظٹ ط§ط¹طھظ…ط§ط¯ ط£ظˆ ظ…ظ„ظپ ظ‚ظپظ„ ط£ظˆ ظپط­طµ CI ط£ظˆ ظƒظˆط¯ ظ…طµط¯ط±.** ط³ط­ط¨ ط§ظ„طھظ‚ط±ظٹط± ظ„ظٹط³ ط¥طµظ„ط§ط­ظ‹ط§ ط¨ط±ظ…ط¬ظٹظ‹ط§طŒ ظˆظ„ط§ ظٹط¬ظˆط² ط§ظ„ط§ط³طھط´ظ‡ط§ط¯ ط¨ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ظ„ط§ط­ظ‚ظ‹ط§ ظƒط¯ظ„ظٹظ„ ط¹ظ„ظ‰ ظ…ط¹ط§ظ„ط¬ط© ط«ط؛ط±ط©. ظٹط¸ظ„ ط§ظ„طھظ†ط¨ظٹظ‡ط§ظ† ط§ظ„ط´ظ‚ظٹظ‚ط§ظ† `CVE-2026-33671` ظˆ`CVE-2026-33672` ظ†ط´ط·ظٹظ† ظˆظ…ظڈطµظ„ط­ظٹظ† ظپظٹ `4.0.4`ط› ظˆظ„ط£ظ† ط§ظ„ط¥طµط¯ط§ط± ط§ظ„ظ…ط³طھط®ط¯ظ… `4.0.7` ظپط¥ظ†ظ‡ ط®ط§ط±ط¬ ظ†ط·ط§ظ‚ظ‡ظ…ط§ â€” ظ„ط§ طھظڈط®ظپظگظ‘ط¶ ط§ظ„ط¥طµط¯ط§ط± ظˆظ„ط§ طھظڈط«ط¨ظگظ‘طھظ‡ طھط­طھ `4.0.4` ظˆظ„ط§ طھظڈط¶ظگظپ `overrides` ظˆظ„ط§ طھظڈط¹ط·ظگظ‘ظ„ ط§ظ„طھط¯ظ‚ظٹظ‚ ظˆظ„ط§ طھط´ط؛ظ‘ظ„ `npm audit fix --force`.

ط§ظ„ط£ط¯ظ„ط© ط§ظ„ظƒط§ظ…ظ„ط© ظˆطھط­ظ„ظٹظ„ ظ‚ط§ط¨ظ„ظٹط© ط§ظ„ظˆطµظˆظ„ ظˆط´ط±ظˆط· ط¥ط¹ط§ط¯ط© ط§ظ„ظپطھط­ ظپظٹ [ط³ط¬ظ„ ط§ظ„ط³ط­ط¨](docs/security/PICOMATCH_GHSA_FC5Q_39XC_VJPF.md). ظ„ط§ ظٹط؛ظٹظ‘ط± ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ط¨ظˆط§ط¨ط§طھ P01 (**NO-GO**) ط£ظˆ AI-9 (**BLOCKED**) ط£ظˆ ظ‚ط¨ظˆظ„ طھط´ط؛ظٹظ„ Codex (**OPEN**)طŒ ظˆظ„ط§ ظٹظ†ظپظ‘ط° ط£ظٹ ظ…ط²ط§ظ…ظ†ط© ظ…ط¹ GitLab.

## GitLab Free CI â€” طھط­ط¶ظٹط± ظٹط¯ظˆظٹ ظپظ‚ط· (ظ„ظ… ظٹظڈط´ط؛ظ‘ظژظ„)

ط£ظڈط¶ظٹظپ ظ†ظ…ظˆط°ط¬ `.gitlab-ci.yml` ظ„طھط¬ظ‡ظٹط² ظپط­طµ ظ…ط¬ط§ظ†ظٹ **ظ…ط³طھظ‚ط¨ظ„ظٹ** ظ„ط³ط¬ظ„ ط§ظ„ط¥ظ†ط¬ط§ط²ط§طھطŒ ظˆظٹط´طھط±ط· ط¥ط¬ط±ط§ط،ظٹظ† ظ…ظ†ظپطµظ„ظٹظ† ظ…ظ† ط§ظ„ظ…ط³طھط®ط¯ظ…: ط¥ظ†ط´ط§ط، Pipeline ظٹط¯ظˆظٹظ‹ط§ ط¹ط¨ط± ظˆط§ط¬ظ‡ط© GitLab ط¹ظ„ظ‰ ط§ظ„ظپط±ط¹ ط§ظ„ط§ظپطھط±ط§ط¶ظٹطŒ ط«ظ… ط¨ط¯ط، ظˆط¸ظٹظپط© `free_offline_smoke` ظٹط¯ظˆظٹظ‹ط§. ظ„ط§ طھظ†ط´ط£ Pipelines ط¹ظ†ط¯ push ط£ظˆ merge request ط£ظˆ schedule ط£ظˆ APIطŒ ظˆظ„ط§ ظٹظڈط³طھظ‡ظ„ظƒ ط±طµظٹط¯ GitLab ط¨ط³ط¨ط¨ ط¥ظ†ط´ط§ط، ط§ظ„ظ…ظ„ظپ ط¹ظ„ظ‰ GitHub.

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_free_ci_pilot.py' -v
python3 scripts/milestone_ledger.py --summary
```

ظ‡ط°ط§ **طھط­ط¶ظٹط± ظپظٹ GitHub ظپظ‚ط·**ط› ظ†ط³ط®ط© GitLab ط§ظ„ط­ط§ظ„ظٹط© ظ‚ط¯ظٹظ…ط© ظˆظ„ظ… طھط­ط¯ط« ظ…ط²ط§ظ…ظ†ط© ط£ظˆ طھط´ط؛ظٹظ„. ظ„ط§ طھط´ط؛ظ‘ظ„ ظˆط¸ظٹظپط© GitLab ظ‚ط¨ظ„ ط§ظ„طھط£ظƒط¯ ظ…ظ† طھط¬ط¯ط¯ ط­طµطھظ‡ط§ ط§ظ„ظ…ط¬ط§ظ†ظٹط© ظˆط§ظ„ط­طµظˆظ„ ط¹ظ„ظ‰ ظ…ظˆط§ظپظ‚ط© ظ…ط­ط¯ط¯ط© ظ„ظ†ظ‚ظ„ ظ†ظپط³ ظ…طµط¯ط± GitHub ظˆظ…ط±ط§ط¬ط¹طھظ‡طŒ ظ…ط¹ ط§ظ„ط­ظپط§ط¸ ط¹ظ„ظ‰ ط­ظ…ط§ظٹط© `main` ظˆظ‚ط±ط§ط±ط§طھ P01/AI-9. ط§ظ„طھظپط§طµظٹظ„: [ط¯ظ„ظٹظ„ GitLab Free CI ط§ظ„طھط¬ط±ظٹط¨ظٹ](docs/GITLAB_FREE_CI_PILOT.md).

ظ…ط´ط±ظˆط¹ ط¹ظ…ظ„ظٹ ظ„طھط¹ظ„ظ‘ظ… DevOps ظˆCI/CD ط¨ط§ط³طھط®ط¯ط§ظ… GitHub Actions ظˆGitHub Pages. طھطھط¶ظ…ظ† ط§ظ„ظ…ط³طھظˆط¯ط¹ ط£طھظ…طھط© ط¥ط¶ط§ظپظٹط© ظ…ظˆط«ظ‚ط©ط› ط§ظ„طµظپط­ط© ط§ظ„ظ…ظ†ط´ظˆط±ط© ط­ط§ظ„ظٹظ‹ط§ طµظپط­ط© HTML ط«ط§ط¨طھط© ظˆظ„ط§ طھط­طھط§ط¬ ط®ط§ط¯ظ… طھط·ط¨ظٹظ‚ ط£ظˆ ظ‚ط§ط¹ط¯ط© ط¨ظٹط§ظ†ط§طھ.


## ظپط­طµ طھط·ط§ط¨ظ‚ ظ†ط³ط®ط© Devobs ط¹ظ„ظ‰ GitLab â€” ظٹط¯ظˆظٹ ظˆط¨ط¯ظˆظ† ط±ظ…ظˆط²

ظٹظ…ظƒظ†ظƒ ظ…ظ‚ط§ط±ظ†ط© ط§ظ„طھط²ط§ظ… `main` ط§ظ„ط¹ط§ظ… ط¨ظٹظ† GitHub ظˆGitLab ط¯ظˆظ† ظ…طµط§ط¯ظ‚ط© ط£ظˆ طھط¹ط¯ظٹظ„ ط£ظٹ ظ…ط³طھظˆط¯ط¹:

```sh
python3 scripts/check_gitlab_replica_parity.py --json
python3 -m unittest discover -s tests -p 'test_gitlab_replica_parity.py' -v
```

طھط¹ظ†ظٹ `MATCH` طھط·ط§ط¨ظ‚ SHA ظˆظ‚طھ ط§ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط· (`exit 0`)طŒ ظˆ`DRIFT` ط§ط®طھظ„ط§ظپظ‡ظ…ط§ (`exit 1`)طŒ ظˆ`UNKNOWN` طھط¹ط°ط± ط§ظ„طھط­ظ‚ظ‚ (`exit 2`). ظ„ط§ ظٹظ†ط´ط¦ ظ‡ط°ط§ ط§ظ„ظپط­طµ ظ…ط²ط§ظ…ظ†ط© ط£ظˆ ظ†ط³ط®ط© ط§ط­طھظٹط§ط·ظٹط© ط£ظˆ Pipeline ط£ظˆ ط®ط¯ظ…ط© ظ…ط¯ظپظˆط¹ط©ط› ط±ط§ط¬ط¹ [ط­ط¯ظˆط¯ ظپط­طµ GitLab](docs/GITLAB_REPLICA_PARITY.md) ظ‚ط¨ظ„ ط§ط¹طھظ…ط§ط¯ ط§ظ„ظ†طھظٹط¬ط©.

## طھط­ط¶ظٹط± طھط­ط¯ظٹط« GitLab ط¨طھظ‚ط¯ظ… ط¢ظ…ظ† ظپظ‚ط· (Fast-forward)

ط£ط¶ظپظ†ط§ ظپط­طµظ‹ط§ ظٹط¯ظˆظٹظ‹ط§ ط¨ط§ط³طھط®ط¯ط§ظ… `git ls-remote` ظˆ`git merge-base` ظ„ظ„طھط­ظ‚ظ‚ ظ…ظ† ط¥ظ…ظƒط§ظ†ظٹط© ظ†ظ‚ظ„ ط§ظ„ط§ظ„طھط²ط§ظ…ط§طھ ظ…ظ† GitHub ط¥ظ„ظ‰ GitLab ط¨ط¯ظˆظ† طھط؛ظٹظٹط± ط§ظ„طھط§ط±ظٹط®. ط§ظ„ط£ط¯ط§ط© **ظ„ط§ طھط±ظپط¹ ط£ظٹ ط§ظ„طھط²ط§ظ… ظˆظ„ط§ طھط³طھط®ط¯ظ… ظ…ظپط§طھظٹط­**:

```sh
python3 scripts/gitlab_fast_forward_preflight.py --repo . --json
python3 -m unittest discover -s tests -p 'test_gitlab_fast_forward_preflight.py' -v
```

طھط¹ظ†ظٹ `ALREADY_MATCHED` ط£ظ† ط§ظ„ط§ظ„طھط²ط§ظ…ظٹظ† ظ…طھط·ط§ط¨ظ‚ط§ظ† ط¹ظ†ط¯ ط§ظ„ظ‚ط±ط§ط،ط©طŒ ظˆ`FAST_FORWARD_CANDIDATE` ط£ظ† ط§ظ„ظ†ظ‚ظ„ ظ…ظ…ظƒظ† ظ†ط¸ط±ظٹظ‹ط§ ظˆظٹطھط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط© ط§ظ„ظ…ط§ظ„ظƒ ظˆظپط­طµ طµظ„ط§ط­ظٹط§طھ GitLabطŒ ظˆ`BLOCKED` ط¶ط±ظˆط±ط© ط§ظ„طھظˆظ‚ظپ. ط±ط§ط¬ط¹ [ط¯ظ„ظٹظ„ ط§ظ„ظپط­طµ ط§ظ„ط¢ظ…ظ†](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md)ط› ظ‡ط°ظ‡ ظ„ظٹط³طھ ظ…ط²ط§ظ…ظ†ط© طھظ„ظ‚ط§ط¦ظٹط© ط£ظˆ ظ†ط³ط®ط© ط§ط­طھظٹط§ط·ظٹط© ظ…ط«ط¨طھط©.

## ظپط­طµ GitLab ظ…ظ† GitHub Actions ط§ظ„ط¹ط§ظ… â€” ظٹط¯ظˆظٹ ط¨ط§ظ„ظƒط§ظ…ظ„

ط£ظڈط¹ط¯ظ‘ **ظپط­طµط§ظ† ظ…ط³طھظ‚ظ„ط§ظ†** ظٹط³طھط®ط¯ظ…ط§ظ† **GitHub Actions ط§ظ„ط¹ط§ظ… ط§ظ„ظ…ط¬ط§ظ†ظٹ** ط¨ط¯ظ„ ط§ط­طھظٹط§ط¬ ط¬ظ‡ط§ط² Windows ط§ظ„ظ…طھطµظ„ ط£ظˆ ط±طµظٹط¯ GitLab CI. ظƒظ„ط§ظ‡ظ…ط§ ظ„ط§ ظٹط¨ط¯ط£ ط¥ظ„ط§ ظٹط¯ظˆظٹظ‹ط§ (`workflow_dispatch`) ظˆظ…ظ‚ظٹظ‘ط¯ ط¨ظ€`refs/heads/main`طŒ ظˆظ„ط§ ظٹط¹ظ…ظ„ طھظ„ظ‚ط§ط¦ظٹظ‹ط§ ط¹ظ†ط¯ ط§ظ„ط¯ظپط¹ ط£ظˆ ط·ظ„ط¨ط§طھ ط§ظ„ط¯ظ…ط¬ ط£ظˆ ط§ظ„ط¬ط¯ظˆظ„ط©:

- [GitLab Replica Read-only Preflight](https://github.com/hamedonassar95/Devobs/actions/workflows/gitlab-replica-preflight-manual.yml): ظٹظ‚ط§ط±ظ† ط¢ط®ط± ط§ظ„طھط²ط§ظ…ط§طھ GitHub/GitLab ط¨ط§ط³طھط®ط¯ط§ظ… `git ls-remote` ظˆ`git merge-base`طŒ ط¯ظˆظ† ظ†ط³ط® ط§ظ„ظƒظˆط¯ ط¥ظ„ظ‰ GitLab ط£ظˆ ط§ط³طھط®ط¯ط§ظ… ط£ط³ط±ط§ط± ط£ظˆ طھط´ط؛ظٹظ„ ط£ظٹ Pipeline ظ‡ظ†ط§ظƒ.
- [GitLab MR Policy Audit](https://github.com/hamedonassar95/Devobs/actions/workflows/gitlab-mr-policy-audit-manual.yml): ظٹظ‚ط±ط£ `merge_method` ط§ظ„ط®ط§طµ ط¨ط³ظٹط§ط³ط© ط·ظ„ط¨ط§طھ ط§ظ„ط¯ظ…ط¬ ظپظ‚ط·طŒ ظ…ط³طھظ‚ظ„ظ‹ط§ طھظ…ط§ظ…ظ‹ط§ ط¹ظ† ظپط­طµ ط§ظ„ط£ظ†ط³ط§ط¨.

ظ†ط¬ط§ط­ ط£ط­ط¯ظ‡ظ…ط§ ظ„ط§ ظٹط¹ظ†ظٹ ظ†ط¬ط§ط­ ط§ظ„ط¢ط®ط± ظˆظ„ط§ ظٹط¬ظٹط² ط£ظٹ ظ…ط²ط§ظ…ظ†ط©. **ظ†ط¬ط§ط­ ظپط­طµ ط§ظ„ط£ظ†ط³ط§ط¨ ظٹظڈطµظ†ظژظ‘ظپ `ALREADY_MATCHED` ط£ظˆ `REVIEW_REQUIRED`طŒ ظˆظ„ط§ طھظڈطµط¯ط± ط£ظٹ ط£ط¯ط§ط© ظ†طھظٹط¬ط© ط¨ط§ط³ظ… `SYNC_APPROVED`.** ظƒظ„ط§ ط§ظ„ظپط­طµظٹظ† ظٹط³طھط®ط¯ظ… `contents: read` ظپظ‚ط·طŒ ظˆط£ظƒط´ظ†ط§طھ ظ…ط«ط¨طھط© ط¨ظ€SHA ظƒط§ظ…ظ„طŒ ظˆ`persist-credentials: false`طŒ ظˆظ„ط§ ظٹط¯ظپط¹ ط£ظˆ ظٹظƒطھط¨ ط¥ظ„ظ‰ ط£ظٹ ظ…ط³طھظˆط¯ط¹.

ظٹظ…ظƒظ† ط§ظ„طھط­ظ‚ظ‚ ظ…ط­ظ„ظٹظ‹ط§ ظ…ظ† ظ…ظ†ط·ظ‚ ط§ظ„ظ†طھط§ط¦ط¬ ط¯ظˆظ† ط­ط³ط§ط¨ط§طھ ط£ظˆ ط´ط¨ظƒط©:

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_hosted_preflight.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_fast_forward_preflight.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_preflight_workflow_contract.py' -v
```

ط§ظ„ظ†طھط§ط¦ط¬: `ALREADY_MATCHED` طھط¹ظ†ظٹ ط£ظ† SHA ظ…طھط·ط§ط¨ظ‚ ظˆظ‚طھ ط§ظ„ظ‚ط±ط§ط،ط©طŒ ظˆ`REVIEW_REQUIRED` طھط¹ظ†ظٹ ظپظ‚ط· ط£ظ† طھط­ط¯ظٹط« Fast-forward ظ…ظ…ظƒظ† ظ†ط¸ط±ظٹظ‹ط§ ظˆظٹطھط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط© ظ…ط³طھظ‚ظ„ط© ظ‚ط¨ظ„ ط£ظٹ ظƒطھط§ط¨ط©طŒ ظˆ`BLOCKED` طھط¹ظ†ظٹ ط§ظ„طھظˆظ‚ظپ. **ظ†ط¬ط§ط­ ظپط­طµ GitHub ظ„ظٹط³ ظ…ظˆط§ظپظ‚ط© ط¹ظ„ظ‰ ظ…ط²ط§ظ…ظ†ط© GitLab ط£ظˆ ط¬ط§ظ‡ط²ظٹط© SaaS.** ظ‡ط°ظ‡ ط§ظ„ط®ط·ظˆط© ظ„ط§ طھظپطھط­ ط¨ظˆط§ط¨طھظٹ P01 ظˆAI-9 ظˆظ„ط§ طھط´ط؛ظ‘ظ„ ط®ط¯ظ…ط© ظ…ط¯ظپظˆط¹ط©. ط§ظ„طھظپط§طµظٹظ„: [ط§ظ„ظپط­طµ ظˆط§ظ„ط§ط³طھط«ظ†ط§ط،ط§طھ](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md).

## ظپط­طµ ط·ط±ظٹظ‚ط© ط¯ظ…ط¬ GitLab â€” ظ„ظ„ظ…ط±ط§ط¬ط¹ط© ظپظ‚ط·

ظٹظ‚ط±ط£ ظپط­طµ `GitLab MR Policy Audit` ط§ظ„ظ…ط³طھظ‚ظ„ ط¥ط¹ط¯ط§ط¯ ط¯ظ…ط¬ Merge Requests ظپظٹ ظ…ط´ط±ظˆط¹ GitLab ط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ ظƒطھط§ط¨ط©طŒ ظˆظ„ط§ ظٹط¹ظ…ظ„ ط¯ط§ط®ظ„ ظ…ظ‡ظ…ط© ط§ظ„ط£ظ†ط³ط§ط¨. ط¹ظ†ط¯ `merge` ط£ظˆ `rebase_merge` ظٹظڈط¸ظ‡ط± `mr_path=MR_ADDS_COMMIT`ط› ط£ظٹ ط¥ظ† **ط¯ظ…ط¬ Merge Request ط§ظ„ط¹ط§ط¯ظٹ** ط³ظٹظڈظ†ط´ط¦ ط§ظ„طھط²ط§ظ…ظ‹ط§ ط¥ط¶ط§ظپظٹظ‹ط§ ظˆظ„ظ† ظٹط­ط§ظپط¸ ط¹ظ„ظ‰ SHA ط§ظ„ط®ط§طµ ط¨ظ€GitHub. ط¹ظ†ط¯ `ff` ظٹظڈط¸ظ‡ط± `mr_path=FF_MR_POLICY_ONLY`.

**ظ…ظ‡ظ…:** ظ‡ط°ط§ ط§ظ„ط¥ط¹ط¯ط§ط¯ ظ„ط§ ظٹظ…ظ†ط¹ ط¨ط­ط¯ ط°ط§طھظ‡ `git push` ط§ظ„ط¹ط§ط¯ظٹ ط¨ط·ط±ظٹظ‚ط© Fast-forwardطŒ ظ„ط£ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ظپط¹ ط¥ظ„ظ‰ ط§ظ„ظپط±ط¹ ط§ظ„ظ…ط­ظ…ظٹ طھظڈط¯ط§ط± ط¨ط´ظƒظ„ ظ…ط³طھظ‚ظ„. ظ„ط°ظ„ظƒ ظٹط­طھظپط¸ ط§ظ„ظپط­طµ ط¨ط§ظ„ظ†طھظٹط¬ط© `direct_git_push=NOT_EVALUATED`. ط§ظ†طھظ‡ط§ط، ط§ظ„ظپط­طµ ط¨ظ†ط¬ط§ط­ ظٹط¹ظ†ظٹ ط§ظƒطھظ…ط§ظ„ ط§ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·طŒ **ظˆظ„ط§ ظٹط¬ظٹط² ط£ظٹ ظ…ط²ط§ظ…ظ†ط© ط£ظˆ ط¯ظ…ط¬**. طھط؛ظٹظٹط± GitLab ط£ظˆ ط§ظ„ط¯ظپط¹ ط¥ظ„ظ‰ `main` ظٹطھط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط© ظ…ظ†ظپطµظ„ط© ظˆظ…ط±ط§ط¬ط¹ط© ط£ط­ط¯ط« SHA.

**طھط´ط®ظٹطµ ط¬ط°ط± ط§ظ„ظ…ط´ظƒظ„ط© (19 ظ†ظˆظپظ…ط¨ط± 2026):** ظپط´ظ„طھ ط®ط·ظˆط© ط³ظٹط§ط³ط© ط§ظ„ط¯ظ…ط¬ ظپظٹ ط§ظ„طھط´ط؛ظٹظ„ ط§ظ„ظٹط¯ظˆظٹ [44399119755](https://github.com/hamedonassar95/Devobs/actions/runs/44399119755) ط¨ط³ط¨ط¨ ط³ط¨ط¨ ط¹ط§ظ… `unverified_project_metadata`. ط£ط¸ظ‡ط± ط§ظ„ظپط­طµ ط§ظ„ظ…ط­ظ„ظٹ ط£ظ† ط§ظ„ط­ظ‚ظ„ `merge_method` **ط؛ظٹط± ظ…ظˆط¬ظˆط¯** ظپظٹ ط§ظ„ط§ط³طھط¬ط§ط¨ط© ط§ظ„ط¹ط§ظ…ط© ظ„ظ„ظ…ط´ط±ظˆط¹ ط¹ظ†ط¯ ط§ظ„ط·ظ„ط¨ ط¨ظ„ط§ ظ…طµط§ط¯ظ‚ط©طŒ ط¨ظٹظ†ظ…ط§ طھط·ط§ط¨ظ‚ `id` ظˆ`path_with_namespace` ظˆ`default_branch` ظˆ`visibility`ط› ظˆطھظˆط«ظ‘ظ‚ GitLab ط£ظ† ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ظڈط¹ط§ط¯ط© طھط®طھظ„ظپ ط­ط³ط¨ طµظ„ط§ط­ظٹط§طھ ط§ظ„ظ…ط³طھط®ط¯ظ… ([Projects API](https://docs.gitlab.com/api/projects/)). ظٹط¹ط±ط¶ ط§ظ„ظپط­طµ ط§ظ„ط¢ظ† ط³ط¨ط¨ظ‹ط§ ط¯ظ‚ظٹظ‚ظ‹ط§ ظ…ط«ظ„ `missing_field:merge_method` ط£ظˆ `mismatched_field:<name>` ط£ظˆ `wrong_type:<name>` ط¯ظˆظ† ط¥ط¸ظ‡ط§ط± ط£ظٹ ظ‚ظٹظ…ط© ظ…ظ† ط§ظ„ظ…ط²ظˆظ‘ط¯.

ظٹط¨ظ‚ظ‰ ط±ظ…ط² ط§ظ„ط®ط±ظˆط¬ `2` ظˆط§ظ„ظ†طھظٹط¬ط© `BLOCKED` ظƒظ…ط§ ظ‡ظ…ط§طŒ ظˆظ„ط§ ظٹظڈظپط³ظژظ‘ط± ط؛ظٹط§ط¨ ط§ظ„ط­ظ‚ظ„ ظƒظ‚ظٹظ…ط© ط§ظپطھط±ط§ط¶ظٹط© `merge` ط£ظˆ `ff`ط› ظپط³ظٹط§ط³ط© ط§ظ„ط¯ظ…ط¬ طھط¸ظ„ **`UNVERIFIED`** ط¥ظ„ظ‰ ط£ظ† ظٹظ‚ظˆظ… ط§ظ„ظ…ط§ظ„ظƒ ط¨ظ‚ط±ط§ط،ط© ظ…ظˆط«ظ‘ظ‚ط© ط¨ط¥ط°ظ† ط£ظˆ ط¨طھط³ط¬ظٹظ„ ط§ظ„ط¥ط¹ط¯ط§ط¯ ظ…ظ† ظˆط§ط¬ظ‡ط© GitLab. ظ„ط§ ظٹظڈط؛ظٹظگظ‘ط± ظ‡ط°ط§ ط¥ط¹ط¯ط§ط¯ط§طھ GitLab ط£ظˆ ط­ظ…ط§ظٹط© ط§ظ„ظپط±ظˆط¹ ط£ظˆ ط§ظ„ظ…ط²ط§ظ…ظ†ط© ط£ظˆ ط¨ظˆط§ط¨ط§طھ ط§ظ„ط¥طµط¯ط§ط±طŒ ظˆظ„ط§ ظٹط®ظپظپ ط£ظٹ ظپط­طµ ط£ظ…ظ†ظٹ.

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_merge_policy.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_preflight_workflow_contract.py' -v
python3 -m py_compile scripts/gitlab_merge_policy.py
```

ط§ظ„طھظˆط«ظٹظ‚: [ط§ظ„ظپط±ظ‚ ط¨ظٹظ† Merge Request ظˆGit Fast-forward](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md). ظ„ط§ ط®ط¯ظ…ط§طھ ظ…ط¯ظپظˆط¹ط©طŒ ظˆظ„ط§ GitLab CIطŒ ظˆظ„ط§ ظ†ظ‚ظ„ طھظ„ظ‚ط§ط¦ظٹ ظ„ظ„ظƒظˆط¯.

## ط®ط·ط© طھط¹ط§ظپظٹ Render OIDC ط¨ط¹ط¯ ظ‚ط±ط§ط± ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„طھط¬ط±ظٹط¨ظٹط©

**ظ‚ط±ط§ط± ط§ظ„ظ…ط§ظ„ظƒ (18 ظ†ظˆظپظ…ط¨ط± 2026):** ط¨ظٹط§ظ†ط§طھ ظ‚ط§ط¹ط¯ط© Render ط§ظ„طھط¬ط±ظٹط¨ظٹط© ط§ظ„ط­ط§ظ„ظٹط© ظ„ط§ طھط­طھط§ط¬ ط¥ظ„ظ‰ ط­ظپط¸ط› ظ‡ط°ط§ ظ„ط§ ظٹط¬ظٹط² ط­ط°ظپ ط§ظ„ظ‚ط§ط¹ط¯ط© ط£ظˆ طھط¹ط·ظٹظ„ ط§ظ„ط®ط¯ظ…ط©طŒ ظˆظ„ط§ ظٹظڈط³ظ‚ط· ظ…طھط·ظ„ط¨ط§طھ ط§ظ„ظ†ط³ط® ط§ظ„ط§ط­طھظٹط§ط·ظٹ ط¹ظ†ط¯ظ…ط§ طھظˆط¬ط¯ ط¨ظٹط§ظ†ط§طھ ط­ظ‚ظٹظ‚ظٹط©. ظ…ظˆط¹ط¯ ط§ظ†طھظ‡ط§ط، ظ‚ط§ط¹ط¯ط© Render Free ط§ظ„ط­ط§ظ„ظٹط©: **5 ط¯ظٹط³ظ…ط¨ط± 2026**.

**ط§ظ„ط¹ط§ط¦ظ‚ ط§ظ„ظ…ط«ط¨طھ:** ظ†ط´ط± Render ط§ظ„ط£ط®ظٹط± ظپط´ظ„ ظپظٹ ظ…ط±ط­ظ„ط© `oidc` ط¨ط®ط·ط£ `invalid_staging_config`طŒ ظ„ظƒظ† ط§ط³ظ… ط§ظ„ط¥ط¹ط¯ط§ط¯ ط؛ظٹط± ط§ظ„طµط§ظ„ط­ ظ„ظ… ظٹظڈط­ط¯ظ‘ظژط¯. ظ†ط³طھط®ط¯ظ… ط£ط¯ط§ط© [P01 Startup Triage](docs/P01_STARTUP_TRIAGE.md) ط§ظ„ظ…ظˆط¬ظˆط¯ط© ط£طµظ„ظ‹ط§ ظ„ظپط­طµ **ظˆط¬ظˆط¯ ط£ط³ظ…ط§ط، ط§ظ„ظ…طھط؛ظٹط±ط§طھ ظپظ‚ط·**ط› ظˆط­طھظ‰ ط¥ط°ط§ ظƒط§ظ†طھ ط¬ظ…ظٹط¹ ط§ظ„ط£ط³ظ…ط§ط، ظ…ظˆط¬ظˆط¯ط©طŒ طھط¹ظٹط¯ ط§ظ„ط£ط¯ط§ط© ط±ظ…ط² ط§ظ„ط®ط±ظˆط¬ `5` ط¨ط¯ظ„ `0` ظ„ط£ظ† ط§ظ„ظ‚ظٹظ… ظ…ط§ ط²ط§ظ„طھ ط؛ظٹط± ظ…طھط­ظ‚ظ‚ط©. ط¨ط¹ط¯ظ‡ط§ ظ†ط±ط§ط¬ط¹ طµط­ط© ظ‚ظٹظ… OIDC ط³ط±ظ‘ظ‹ط§ ظ„ط¯ظ‰ ط§ظ„ظ…ط´ط؛ظ‘ظ„ ظ‚ط¨ظ„ ط£ظٹ ظ†ط´ط± ط¬ط¯ظٹط¯. ظ„ط§ طھظڈط±ط³ظ„ ظ…ظپط§طھظٹط­ ط£ظˆ ط¨ظٹط§ظ†ط§طھ ط§طھطµط§ظ„ ط£ظˆ طµظˆط±ظ‹ط§ ظ„ظ‚ظٹظ… ط§ظ„ظ…طھط؛ظٹط±ط§طھطŒ ظˆظ„ط§ طھط¹ط·ظ‘ظ„ ط§ظ„ظ…طµط§ط¯ظ‚ط© ظ„طھط¬ط§ظˆط² ط§ظ„ظ…ط´ظƒظ„ط©. ط§ظ„طھظپط§طµظٹظ„ ظˆط§ظ„ط®ط·ظˆط§طھ: [ط®ط·ط© طھط¹ط§ظپظٹ Render ط§ظ„ط¢ظ…ظ†ط©](docs/RENDER_OPENAI_STAGING_RUNBOOK.md#2026-11-18-owner-checkpoint--disposable-data-and-oidc-recovery). ط¨ظˆط§ط¨ط© P01 ظ„ط§ طھط²ط§ظ„ `BLOCKED / NO-GO` ظˆAI-9 ظ„ط§ طھط²ط§ظ„ `BLOCKED`.

## ط¨ظˆط§ط¨ط© طھط·ط§ط¨ظ‚ ط¥طµط¯ط§ط± Render ظ…ط¹ GitHub â€” ظ‚ط±ط§ط،ط© ظ…ط­ظ„ظٹط© ظپظ‚ط·

طھط³طھط®ط¯ظ… ط£ط¯ط§ط© ط§ظ„ط¬ط§ظ‡ط²ظٹط© ط§ظ„ظ…ظˆط¬ظˆط¯ط© `scripts/check_free_staging_health.py` ظ„ظ‚ط·ط© ط¨ظٹط§ظ†ط§طھ **schema_version=3** طھط­طھظˆظٹ `render.canonical_main_commit` (ط¢ط®ط± SHA ظ…طھط­ظ‚ظ‚ ظ…ظ†ظ‡ ظ…ظ† GitHub) ظˆ`render.web_last_deploy_commit` (SHA ط¢ط®ط± ظ†ط´ط± ظ…طھط­ظ‚ظ‚ ظ…ظ†ظ‡ ظ…ظ† Render). ط¥ط°ط§ ط§ط®طھظ„ظپط§طŒ طھط¹ط±ط¶ `RENDER_DEPLOY_SOURCE_OUTDATED` ط¶ظ…ظ† ط£ط³ط¨ط§ط¨ ط§ط³طھظ…ط±ط§ط± `REVIEW_REQUIRED`طŒ **ط­طھظ‰ ط¹ظ†ط¯ظ…ط§ ظٹظڈطµظ†ظ‘ظپ ط§ظ„ظ†ط´ط± `live`**. ظˆط¬ظˆط¯ SHA ظ…طھط·ط§ط¨ظ‚ ظ„ط§ ظٹط«ط¨طھ ظ†ط¬ط§ط­ ط§ظ„ط¯ط®ظˆظ„ ط£ظˆ ط¹ط²ظ„ ط§ظ„ظ…ط³طھط£ط¬ط±ظٹظ† ط£ظˆ ط¬ط§ظ‡ط²ظٹط© ط§ظ„ط¥ظ†طھط§ط¬ط› ظˆطھط§ط±ظٹط® ط§ظ„ظ„ظ‚ط·ط© ظٹط®ط¶ط¹ ظ„ظپط­طµ ط§ظ„طھظ‚ط§ط¯ظ…. ظ‡ط°ط§ ظپط­طµ ظ…ط­ظ„ظٹ ظ…ط¬ط§ظ†ظٹ ظ„ط§ ظٹط¬ظ„ط¨ ط¥ط¹ط¯ط§ط¯ط§طھ ط³ط±ظٹط© ظˆظ„ط§ ظٹط´ط؛ظ‘ظ„ ظ†ط´ط±ظ‹ط§ ط£ظˆ pipeline.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

ط±ط§ط¬ط¹ [ط®ط·ط© طھط¹ط§ظپظٹ Render](docs/RENDER_OPENAI_STAGING_RUNBOOK.md#render-source-commit-drift-preflight--2026-11-18). ظ„ط§ طھط؛ظٹظ‘ط± ط¥ط¹ط¯ط§ط¯ط§طھ OIDC ظˆظ„ط§ طھظ†ط´ط± ط¹ظ„ظ‰ Render ط§ط³طھظ†ط§ط¯ظ‹ط§ ط¥ظ„ظ‰ ط§ط®طھظ„ط§ظپ SHA ظˆط­ط¯ظ‡.

## ظپط­طµ ط¬ط§ظ‡ط²ظٹط© ظ…ظˆط§ط±ط¯ Devobs ط§ظ„ظ…ط¬ط§ظ†ظٹط© â€” Render + Supabase

طھظ‚ط±ظٹط± ظ…ط­ظ„ظٹ ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط· ظٹط¬ظ…ط¹ ط­ط§ظ„ط© ظ…ظˆط§ط±ط¯ **Devobs** ط§ظ„ظ…ط¬ط§ظ†ظٹط© ظ…ظ† ظ„ظ‚ط·ط© ظ…ط²ظˆط¯ظٹظ† ظ…ط­ط¯ظˆط¯ط© ط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ ط§طھطµط§ظ„ط§طھ ظ…ط¨ط§ط´ط±ط©طŒ ظˆظٹط±ظپط¶ ط¥ط¹ظ„ط§ظ† ط¬ط§ظ‡ط²ظٹط© ط§ظ„ط¥ظ†طھط§ط¬ ط¹ظ†ط¯ ظˆط¬ظˆط¯ ط£ط¯ظ„ط© ظ†ط§ظ‚طµط© ط£ظˆ ظ‚ط¯ظٹظ…ط©. ظ„ط§ ظٹط³طھط®ط¯ظ… ظ…ظˆط§ط±ط¯ ظ…ط´ط±ظˆط¹ طµظٹط§ظ†ط© ط§ظ„ظ‡ظˆط§طھظپ.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

ظٹطھط­ظ‚ظ‚ ط§ظ„ط¥طµط¯ط§ط± ط§ظ„ط«ط§ظ†ظٹ ظ…ظ† ط§ظ„ط¬ط±ط¯ ط£ظٹط¶ظ‹ط§ ظ…ظ† **ط¢ط®ط± ط­ط§ظ„ط© ظ†ط´ط± ظپط¹ظ„ظٹط©** ط¹ظ„ظ‰ Render ظˆط§ظ„ط§ظ„طھط²ط§ظ… ط§ظ„ط£طµظ„ظٹ ظ„ظ‡ط§ط› ط¥ط° ط§ظ†طھظ‡طھ ط£ط­ط¯ط« ظ…ط­ط§ظˆظ„ط© ط¨ظ€`update_failed`طŒ ظپظٹط¸ظ‡ط± ظ…ط§ظ†ط¹ `RENDER_LATEST_DEPLOY_NOT_LIVE`. `live` ظˆط­ط¯ظ‡ط§ ظ„ط§ طھظƒظپظٹ ظ„ظ„ظ…ظˆط§ظپظ‚ط© ط¹ظ„ظ‰ ط§ظ„ط¥ظ†طھط§ط¬طŒ ظˆظ„ط§ ظٹط¬ط±ظٹ ظ‡ط°ط§ ط§ظ„ظپط­طµ ط£ظٹ ط§طھطµط§ظ„ ط®ط§ط±ط¬ظٹ ط£ظˆ ظ†ط´ط±.

ط§ظ„ظ†طھظٹط¬ط© ط§ظ„ظ…ظ‚طµظˆط¯ط© ظ‡ظٹ `REVIEW_REQUIRED` (ط±ظ…ط² 1) ط£ظˆ `INVALID_SNAPSHOT` (ط±ظ…ط² 2) ظˆظ„ظٹط³ ط§ظ„ظ…ظˆط§ظپظ‚ط© ط¹ظ„ظ‰ ط§ظ„ظ†ط´ط±. ظ‚ط§ط¹ط¯ط© Render ط§ظ„ظ…ط¬ط§ظ†ظٹط© طھظ†طھظ‡ظٹ ظپظٹ **2026-12-05** ط­ط³ط¨ ط¢ط®ط± ط¬ط±ط¯طŒ ظˆSupabase ط§ظ„ط®ط§طµ ط¨ظ€Devobs ط؛ظٹط± ظ†ط´ط·ط› ط±ط§ط¬ط¹ [ط§ظ„طھظ‚ط±ظٹط± ظˆط§ظ„ط£ط¯ظ„ط© ظˆط­ط¯ظˆط¯ ط§ظ„طھظƒط§ظ„ظٹظپ](docs/P01_FREE_STAGING_PROVIDER_GATE_2026-11-17.md). ظ„ط§ طھظ†ظپط° ط§ظ„ط£ط¯ط§ط© ظ†ط´ط±ظ‹ط§ ط£ظˆ ظ…ط²ط§ظ…ظ†ط© ط£ظˆ طھط±ظ‚ظٹط© ظ…ط¯ظپظˆط¹ط©.

## ظپط­طµ ط§ظ†طھظ‡ط§ط، PostgreSQL ط§ظ„ظ…ط¬ط§ظ†ظٹط© (ط¯ظˆظ† ط§طھطµط§ظ„ ط£ظˆ طھظƒظ„ظپط©)

طھطھط­ظ‚ظ‚ [ط£ط¯ط§ط© ظپط­طµ ظ…ظˆط¹ط¯ ط§ظ†طھظ‡ط§ط، Render Free](scripts/check_render_free_expiry.py) ظ…ظ† طھط§ط±ظٹط® ط§ظ†طھظ‡ط§ط، ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ ظˆظپظ‚ [ظ„ظ‚ط·ط© ط¬ط±ط¯ ظ…ط­ط¯ظˆط¯ط©](docs/p01/render-free-expiry-snapshot.json) ط¨طھط§ط±ظٹط® 2026-11-15. ظ„ط§ طھظ‚ط±ط£ ط§ظ„ط£ط¯ط§ط© ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ‚ط§ط¹ط¯ط© ط£ظˆ ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ظ…ط²ظˆط¯ ط£ظˆ ط£ط³ط±ط§ط±ظ‹ط§طŒ ظˆظ„ط§ طھظ†ط´ط± ط£ظˆ طھط±ظ‚ظ‘ظٹ ط£ظˆ طھط­ط°ظپ ط´ظٹط¦ظ‹ط§.

```sh
python3 scripts/check_render_free_expiry.py --json
python3 -m unittest discover -s tests -p 'test_render_free_expiry.py' -v
```

**ط±ظ…ظˆط² ط§ظ„ط®ط±ظˆط¬:** `0` ظٹط¹ظ†ظٹ ط£ظ† ط§ظ„ظ…ظˆط¹ط¯ ظ„ظٹط³ ظ‚ط±ظٹط¨ظ‹ط§ ط­ط³ط¨ ظ„ظ‚ط·ط© ط­ط¯ظٹط«ط© ظپظ‚ط· (ظ„ظٹط³ ظ…ظˆط§ظپظ‚ط© طھط´ط؛ظٹظ„)طŒ ظˆ`1` ظٹط¹ظ†ظٹ ظ…ط±ط§ط¬ط¹ط© ط¨ط´ط±ظٹط© ظ„ط§ط²ظ…ط© ط£ظˆ ط§ظ†طھظ‡ط§ط،/طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„ ط£ظˆ طھظ‚ط§ط¯ظ… ط§ظ„ظ„ظ‚ط·ط© ظ„ط£ظƒط«ط± ظ…ظ† 7 ط£ظٹط§ظ…طŒ ظˆ`2` ظٹط¹ظ†ظٹ ط£ظ† ظ…ظ„ظپ ط§ظ„ط¬ط±ط¯ ط؛ظٹط± طµط§ظ„ط­. **ط§ظ„ظ…طھظˆظ‚ط¹ ط­ط§ظ„ظٹظ‹ط§ ظ‡ظˆ `REVIEW_REQUIRED` ظˆط±ظ…ط² `1`** ط­طھظ‰ ظٹظڈطھط®ط° ظ‚ط±ط§ط± ط§ظ„ط§ط­طھظپط§ط¸ ط£ظˆ ط§ظ„ط¥ظ†ظ‡ط§ط،ط› ظˆط¨ط¹ط¯ طھظ‚ط§ط¯ظ… ط§ظ„ظ„ظ‚ط·ط©طŒ ظ„ط§ ظٹظ…ظƒظ† ط§ط¹طھط¨ط§ط±ظ‡ط§ ط­ط§ظ„ط© ط­ظٹط©. ظ…ظˆط¹ط¯ ط§ظ†طھظ‡ط§ط، ط§ظ„ظ‚ط§ط¹ط¯ط© ط§ظ„ظ…ط³ط¬ظ„: **2026-12-05 10:33 UTC**طŒ ظˆظ„ظٹط³ طھط§ط±ظٹط®ظ‹ط§ ظٹط¬ظٹط² ط§ظ„ط­ط°ظپ ط£ظˆ ط§ظ„طھط±ظ‚ظٹط©. ط±ط§ط¬ط¹ [ط­ط¯ظˆط¯ ط§ظ„ط¯ظ„ظٹظ„ ظˆط®ظٹط§ط±ط§طھ ط§ظ„ظ‚ط±ط§ط±](docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md). ط¨ظˆط§ط¨ط© P01 طھط¨ظ‚ظ‰ `NO-GO`.

## ظ‚ط§ط±ط¦ CI ظ„ظ…ط­ظپط¸ط© ط§ظ„ظ…ط´ط§ط±ظٹط¹ ط§ظ„ط¹ط§ظ…ط© (ظٹط¯ظˆظٹ ظˆظ…ظ† ط¯ظˆظ† ظ…ظپط§طھظٹط­)

ط£طµط¨ط­ ط¨ط§ظ„ط¥ظ…ظƒط§ظ† ظپط­طµ ظ†طھط§ط¦ط¬ GitHub CI ط§ظ„ط¹ط§ظ…ط© ظ„ط£ط±ط¨ط¹ط© ظ…ط´ط§ط±ظٹط¹ ظ…ط³طھظ‚ظ„ط© ظ…ظ† طھط´ط؛ظٹظ„ ظ…ط­ظ„ظٹ ظˆط§ط­ط¯طŒ ظ…ط¹ ظ…ط·ط§ط¨ظ‚ط© ظ†طھط§ط¦ط¬ ظƒظ„ طھط´ط؛ظٹظ„ ظ„ط§ظ„طھط²ط§ظ… `main` ط§ظ„ط®ط§طµ ط¨ط§ظ„ظ…ط´ط±ظˆط¹طŒ ظˆط¯ظˆظ† ظ…ط±ط§ظ‚ط¨ط© ظ…ط³طھظˆط¯ط¹ط§طھ ط®ط§طµط© ط£ظˆ ظ†ظ‚ظ„ ط£ظƒظˆط§ط¯ظ‡ط§ ط£ظˆ ط£ط³ط±ط§ط±ظ‡ط§:

```sh
node scripts/portfolio_public_ci.mjs
node --test tests/portfolio_public_ci.test.mjs
```

ظٹظ…ظƒظ†ظƒ ظƒط°ظ„ظƒ ظپطھط­ [ظ‚ط§ط±ط¦ CI ط¹ط¨ط± ط§ظ„ظ…طھطµظپط­](https://hamedonassar95.github.io/Devobs/assets/public-ci/) ظˆط§ط®طھظٹط§ط± ط²ط± **ظپط­طµ ط§ظ„ظ…ط´ط§ط±ظٹط¹ ط§ظ„ط£ط±ط¨ط¹ط©** ظ„ط¹ط±ط¶ ط§ظ„ط­ط§ظ„ط§طھ ط§ظ„ط¹ط§ظ…ط©طŒ ظٹط¯ظˆظٹظ‹ط§ ظˆط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ ظ…ط±ط§ظ‚ط¨ط© طھظ„ظ‚ط§ط¦ظٹط©.

ط¨ط¹ط¯ ظپط­طµ ط§ظ„ظ…ط³طھظˆط¯ط¹ط§طھ ط§ظ„ط£ط±ط¨ط¹ط© ظپظٹ [ط§ظ„ظ‚ط§ط±ط¦ ط§ظ„ط¹ط§ظ…](https://hamedonassar95.github.io/Devobs/assets/public-ci/)طŒ ظٹظ…ظƒظ†ظƒ طھظ†ط²ظٹظ„ ط£ط­ط¯ط§ط« CI ط§ظ„ظ…ط¤ظ‡ظ„ط© ط¨طµظٹط؛ط© CloudEvents ظˆطھط­ظ„ظٹظ„ظ‡ط§ ظ…ظ† ط¬ظ‡ط§ط²ظƒ ط¨ط§ط³طھط®ط¯ط§ظ… **ظ…ط­ط±ظƒ AI-7 ط§ظ„ظ…ظˆط¬ظˆط¯ ط¨ط§ظ„ظپط¹ظ„** (ظ‚ط±ط§ط،ط© ظپظ‚ط·طŒ ط¯ظˆظ† طھط´ط؛ظٹظ„ ط®ط§ط¯ظ… ط£ظˆ ط§ط³طھظ†طھط§ط¬ ط³ط¨ط¨ ط¬ط°ط±ظٹ ظ…ظ† ط­ط§ظ„ط© CI ظˆط­ط¯ظ‡ط§):

```sh
node scripts/portfolio_ci_ai7.mjs --input /path/to/devobs-portfolio-ci.cloudevents.jsonl
```

**ط¬ط¯ظٹط¯ â€” ظپط­طµ ظˆطھط­ظ„ظٹظ„ CI ط§ظ„ط¹ط§ظ…ط© ظ…ط¨ط§ط´ط±ط© ط¨ط£ظ…ط± ظˆط§ط­ط¯ ط¹ظ†ط¯ ط§ظ„ط·ظ„ط¨** (ظ…ظ† ط¯ظˆظ† طھظ†ط²ظٹظ„ ط§ظ„ظ…ظ„ظپ ط£ظˆ ط­ظپط¸ظ‡طŒ ظˆط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ طھظ†ظپظٹط° ط¥طµظ„ط§ط­ط§طھ):

```sh
node scripts/portfolio_ci_ai7_live.mjs
```

ط§ظ„ط£ظ…ط± ظٹط¹ط±ط¶ ظ†طھظٹط¬ط© ظƒظ„ ظ…ط´ط±ظˆط¹ ظˆظٹط´ط؛ظ‘ظ„ AI-7 ظپظ‚ط· ظ„ظ„ط£ط­ط¯ط§ط« ط§ظ„ظ…ظƒطھظ…ظ„ط© ط§ظ„طھظٹ طھط­ظ‚ظ‚طھ ط´ط±ظˆط·ظ‡ط§. ط¥ط°ط§ ظƒط§ظ†طھ ط§ظ„ظ†طھط§ط¦ط¬ ظ†ط§ظ‚طµط© ظٹظڈط¸ظ‡ط± ط­ط§ظ„ط© ط¬ط²ط¦ظٹط© ظˆظٹط®ط±ط¬ ط¨ط±ظ…ط² ظپط´ظ„طŒ ط­طھظ‰ ظ„ط§ ظٹط¹طھط¨ط± ط§ظ„طھط´ط؛ظٹظ„ ظ†ط§ط¬ط­ظ‹ط§ ط¨ط§ظ„ط®ط·ط£.

**ظ„ظ„طھط´ط؛ظٹظ„ ظ…ظ† GitHub ط¯ظˆظ† ظƒظ…ط¨ظٹظˆطھط±:** ط¨ط¹ط¯ ط¯ظ…ط¬ ط§ظ„طھط؛ظٹظٹط± ظٹظ…ظƒظ†ظƒ ظپطھط­ [Portfolio AI-7 Public CI Observation](https://github.com/hamedonassar95/Devobs/actions/workflows/portfolio-ai7-manual.yml) ظˆط§ط®طھظٹط§ط± **Run workflow** ط¹ظ„ظ‰ `main`. ظٹظ‚ط±ط£ ط£ط±ط¨ط¹ط© ظ…ط³طھظˆط¯ط¹ط§طھ ط¹ط§ظ…ط©طŒ ظˆظٹط¶ط¹ ظ…ظ„ط®طµظ‹ط§ ط¹ط±ط¨ظٹظ‹ط§/ط¥ظ†ط¬ظ„ظٹط²ظٹظ‹ط§ ظ…ط­ط¯ظˆط¯ظ‹ط§ ظˆظ…ظ„ظپ JSON ظ…ظ†ظ‚ظ‘ظ‰ ظ„ظ„ظ…ط±ط§ط¬ط¹ط© ط¯ط§ط®ظ„ ActionsطŒ ط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ ظ†ط´ط± ط£ظˆ ط¬ط¯ظˆظ„ط©. ط¥ط°ط§ ظƒط§ظ†طھ ط§ظ„ط£ط¯ظ„ط© ظ†ط§ظ‚طµط© ظٹطھظˆظ‚ظپ ط¨ظ†طھظٹط¬ط© ظپط´ظ„ ظˆط§ط¶ط­ط©طŒ ظˆظ„ط§ ظٹط¹طھط¨ط± ظ‡ط°ط§ ط¨ط­ط¯ ط°ط§طھظ‡ ط¹ط·ظ„ظ‹ط§ ظپظٹ ظƒظˆط¯ Devobs.

ط§ظ„طھظپط§طµظٹظ„ ظˆظ…طµط§ط¯ط± GitHub ظˆط§ظ„طھط­ط°ظٹط±ط§طھ: [Portfolio Public CI](docs/integrations/PORTFOLIO_PUBLIC_CI.md). ظ‡ط°ظ‡ ظ‚ط±ط§ط،ط© ط¹ط§ظ…ط© ط¹ظ†ط¯ ط§ظ„ط·ظ„ط¨ ظپظ‚ط·طŒ ظ„ط§ طھط«ط¨طھ ط§ظ„طھط´ط؛ظٹظ„ ط§ظ„طھط¬ط§ط±ظٹ ظˆظ„ط§ طھظپط¹ظ‘ظ„ ط®ط¯ظ…ط§طھ ظ…ط¯ظپظˆط¹ط© ط£ظˆ طھط±ط³ظ„ ط£ط­ط¯ط§ط«ظ‹ط§ طھظ„ظ‚ط§ط¦ظٹظ‹ط§.

## طھظ‚ط±ظٹط± ظ…ظˆط­ظ‘ط¯ ظ„ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط© â€” ظ…ط­ظ„ظٹ ظپظ‚ط·

ظٹظ…ظƒظ† ط§ظ„ط¢ظ† ط¬ظ…ط¹ ظ†طھط§ط¦ط¬ ط£ط¯ظˆط§طھ ط§ظ„ظپط­طµ **ط§ظ„ظ…ظˆط¬ظˆط¯ط© ط£طµظ„ظ‹ط§** ظپظٹ ط£ظ…ط± ظˆط§ط­ط¯ ط¯ظˆظ† ط­ط³ط§ط¨ط§طھ ط®ط§ط±ط¬ظٹط© ط£ظˆ ظ…ظپط§طھظٹط­ ط£ظˆ ط¥ظ†ط´ط§ط، ط®ط¯ظ…ط§طھ:

```sh
python3 scripts/free_readiness_one_command.py --json
python3 -m unittest discover -s tests -p 'test_free_readiness_one_command.py' -v
```

ظٹط¹ظٹط¯ ط§ظ„ط£ظ…ط± ط§ط³طھط®ط¯ط§ظ… ظپط­طµ ط¯ظپطھط± ط§ظ„ط¥ظ†ط¬ط§ط²ط§طھطŒ ظˆط¬ط±ط¯ ط§ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط©طŒ ظˆظ…ط±ط´ط­ظٹ ط§ظ„طھظƒط§ظ…ظ„طŒ ظˆظ„ظ‚ط·ط© Render/SupabaseطŒ ظˆطھط§ط±ظٹط® ط§ظ†طھظ‡ط§ط، Render Free. ط§ظ„ظ†طھظٹط¬ط© ط§ظ„ظ…ط¹طھط§ط¯ط© `REVIEW_REQUIRED` (exit 1) ظˆظ„ظٹط³طھ ظ†ط¬ط§ط­ ط¥ظ†طھط§ط¬ظٹطŒ ظˆ`INVALID_CHECKS` (exit 2) ط¹ظ†ط¯ ط£ظٹ ظپط­طµ ظ†ط§ظ‚طµ ط£ظˆ ظ†طھظٹط¬ط© ط؛ظٹط± ظ…طھظˆظ‚ط¹ط©. ظ„ط§ ظٹطھطµظ„ ط§ظ„ط£ظ…ط± ط¨ظ…ط²ظˆط¯ ط£ظˆ ظ…ط³طھظˆط¯ط¹ ط¢ط®ط± ظˆظ„ط§ ظٹظ†ظ‚ظ„ ط£ط³ط±ط§ط±ظ‹ط§ ط£ظˆ ظٹط­ط¯ظ‘ط« ط¥ط¹ط¯ط§ط¯ط§طھ. ظ‚ط¯ طھظƒظˆظ† ظ…ط¤ط´ط±ط§طھ ط§ظ„ظ…ظˆط§ط±ط¯ ظ‚ط¯ظٹظ…ط©ط› **ظ†ط¬ط§ط­ ط§ظ„ظپط­طµ ظ„ط§ ظٹط«ط¨طھ ط¬ط§ظ‡ط²ظٹط© ط§ظ„ط®ط¯ظ…ط§طھ ط§ظ„ط­ظٹط© ط£ظˆ ظٹط¬ظٹط² ط§ظ„ط¯ظ…ط¬ ظˆط§ظ„ظ†ط´ط±**.

## ظپط­طµ ط§ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط© (ط¯ظˆظ† طھظپط¹ظٹظ„ ط®ط¯ظ…ط§طھ ط¬ط¯ظٹط¯ط©)

ط£ظڈط¶ظٹظپ [ظپط­طµ ط¬ط§ظ‡ط²ظٹط© ط§ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط©](docs/strategy/DEVOBS_FREE_RESOURCE_PLAN_2026.md) ظ„ظپط­طµ 12 ظ…ظ„ظپظ‹ط§ ظ…ظˆط¬ظˆط¯ظ‹ط§ ظپظٹ ط§ظ„ظ…ط³طھظˆط¯ط¹ ظˆطھط£ظƒظٹط¯ ط¨ظ‚ط§ط، ط§ظ„ط³ظٹط§ط³ط© ط¯ظˆظ† طھط´ط؛ظٹظ„ ط®ط§ط±ط¬ظٹ ط£ظˆ ط¯ظپط¹. ط´ط؛ظ‘ظ„ `python3 scripts/check_free_resource_plan.py --json` ظ„ط¥ط¸ظ‡ط§ط± طھظ‚ط±ظٹط± ظ…ط­ط¯ظˆط¯ ظ„ظ„ظ…ظ„ظپط§طھ ظپظ‚ط·ط› ظ„ط§ ظٹط«ط¨طھ ط°ظ„ظƒ ط¬ط§ظ‡ط²ظٹط© ط§ظ„ط®ط¯ظ…ط§طھ ط§ظ„ظ…ط³طھط¶ط§ظپط© ط£ظˆ ظ…ط¬ط§ظ†ظٹط© ط§ظ„ظپط§طھظˆط±ط© ط§ظ„ظپط¹ظ„ظٹط©.

ظ„ظ„طھط­ط¶ظٹط± ط§ظ„ظ…ظ†ظپطµظ„ ظ„ظ…ط´ط§ط±ظٹط¹ظ†ط§طŒ ط±ط§ط¬ط¹ [ط®ط±ظٹط·ط© طھظƒط§ظ…ظ„ ط§ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط© ط§ظ„ظ…ط±ط´ط­ط©](docs/portfolio/PORTFOLIO_FREE_READINESS.md) ظˆط´ط؛ظ‘ظ„ `python3 scripts/portfolio_free_readiness.py --json`. ظ‡ط°ط§ طھظ‚ط±ظٹط± طھط®ط·ظٹط· ظ…ط­ظ„ظٹط› ظ„ط§ ظٹط«ط¨طھ ط§طھطµط§ظ„ ط£ظٹ ظ…ط³طھظˆط¯ط¹ ط¢ط®ط± ظˆظ„ط§ ظٹط³ظ…ط­ ط¨ظ†ظ‚ظ„ ط¨ظٹط§ظ†ط§طھظ‡.

## طھظƒط§ظ…ظ„ ظ…ط­ظ„ظٹ ط¬ط¯ظٹط¯: ظˆط§ط¬ظ‡ط© AI Intelligence Console ظ…ط¹ ظ…ط­ط±ظƒ AI-7

طھطھظٹط­ [ط§ظ„ظˆط§ط¬ظ‡ط© ط§ظ„ط­ط§ظ„ظٹط©](apps/ai-intelligence-console/README.md) ظپظٹ ظ‚ط³ظ… Overview ظ‚ط±ط§ط،ط© ظ…ظ„ط®طµط§طھ **ظ…ط­ط±ظƒ AI-7 ط§ظ„ط­ظ‚ظٹظ‚ظٹ ظ…ط­ظ„ظٹظ‹ط§** ط¹ظ†ط¯ ط§ظ„ط¶ط؛ط· ظٹط¯ظˆظٹظ‹ط§ ط¹ظ„ظ‰ آ«ظ‚ط±ط§ط،ط© ط§ظ„ظ…ط­ط±ظƒ ط§ظ„ظ…ط­ظ„ظٹآ»ط› ط¹ط±ط¶ ط§ظ„ط£ط¹ط¯ط§ط¯ ظˆط­ط§ظ„ط§طھ ط§ظ„ظ…ط±ط§ط­ظ„ ط§ظ„ط³ط¨ط¹ ظپظ‚ط·طŒ ط¯ظˆظ† ط³ط¬ظ„ط§طھ ط®ط§ظ… ط£ظˆ طµظ„ط§ط­ظٹط§طھ طھظ†ظپظٹط°. ط§ظ„ظ…ط³ط§ط± ظ…ط¹ط·ظ‘ظ„ ط§ظپطھط±ط§ط¶ظٹظ‹ط§ ظˆظ„ط§ ظٹطھطµظ„ ط¥ظ„ط§ ط¨ط¹ظ†ظˆط§ظ† loopback ط«ط§ط¨طھ ط¹ظ„ظ‰ ظ†ظپط³ ط§ظ„ط¬ظ‡ط§ط² ط¹ظ†ط¯ ط§ظ„طھظپط¹ظٹظ„ ط§ظ„طµط±ظٹط­. ظ‡ظˆ طھط·ظˆظٹط± ظ…ظ†طھط¬ ط¨ط±ظ…ط¬ظٹ طھط¬ط±ظٹط¨ظٹ ظˆظ„ظٹط³ ط±ط¨ط·ظ‹ط§ ط¨ط®ظˆط§ط¯ظ… ط§ظ„ط¥ظ†طھط§ط¬ ط£ظˆ ط¥ط·ظ„ط§ظ‚ SaaSط› ط±ط§ط¬ط¹ [ط§ظ„طھط´ط؛ظٹظ„ ظˆط§ظ„ط§ط®طھط¨ط§ط±ط§طھ ظˆط­ط¯ظˆط¯ ط§ظ„ط£ظ…ط§ظ†](apps/ai-intelligence-console/README.md#ai-7-local-snapshot-integration-optional-read-only).

## DevOps AI Intelligence â€” ظ…طµط¯ط± ظ…ظˆط­ظ‘ط¯

ظ‡ط°ط§ ط§ظ„ظ…ط³طھظˆط¯ط¹ `Devobs` ظ‡ظˆ ط§ظ„ظ…طµط¯ط± ط§ظ„ط£ط³ط§ط³ظٹ ظ„ظ„ظ…ط´ط±ظˆط¹ظٹظ†. ظ…ط±ط§ط­ظ„ ط§ظ„ط°ظƒط§ط، ط§ظ„طھط´ط؛ظٹظ„ظٹ ط§ظ„ظ…ط­ظ„ظٹط© AI-1 ط¥ظ„ظ‰ AI-7 ظˆظ„ظˆط­ط© AI-7 ظ…ط¯ظ…ط¬ط© ظ‡ظ†ط§ ط¨ط§ظ„ظپط¹ظ„ط› ظ†ط¶ظٹظپ ظپظ‚ط· ظ…ط§ ظٹط³ط¯ ظپط¬ظˆط© ظˆط§ط¶ط­ط© ط¨ط¯ظ„ ظ†ط³ط® ظ…ظƒظˆظ†ط§طھ ظ…ظƒط±ط±ط©. ط§ظ„ظ…ط­ط±ظƒط§طھ ط§ظ„ط­ط§ظ„ظٹط© ظ…ط­ظ„ظٹط© ظˆط­طھظ…ظٹط©/ط¥ط­طµط§ط¦ظٹط© ظˆظ„ط§ طھط³طھط¯ط¹ظٹ ظ†ظ…ظˆط°ط¬ظ‹ط§ ظ„ط؛ظˆظٹظ‹ط§.

### طھط·ط¨ظٹظ‚ DevOps AI Intelligence ط§ظ„ظ…ط­ظپظˆط¸

ظ†ظڈظ‚ظ„طھ ظˆط§ط¬ظ‡ط© React/TypeScript ظ…ظ† ظ…ط³طھظˆط¯ط¹ `DevObs-ai-Intelligence-` ط¥ظ„ظ‰ [`apps/ai-intelligence-console/`](apps/ai-intelligence-console/)طŒ ظ…ط¹ ط§ظ„ط§ط­طھظپط§ط¸ ط¨طھط§ط±ظٹط® ط§ظ„ظ…طµط¯ط± ظˆط±ط®طµط© MIT. طھط¶ظ… ظ„ظˆط­ط© ط§ظ„ط®ظˆط§ط¯ظ… ظˆط§ظ„ط­ظˆط§ط¯ط« ظˆط§ظ„ظ†ط´ط±طŒ ظˆط§ط¬ظ‡ط© GitHubطŒ ظ…ط³ط§ط­ط© Google WorkspaceطŒ GeminiطŒ ظˆط¹ط±ط¶ ط؛ط±ظپط© ط§ظ„ط®ظˆط§ط¯ظ… ط«ظ„ط§ط«ظٹ ط§ظ„ط£ط¨ط¹ط§ط¯. ظ‡ظٹ ظ†ظ…ظˆط°ط¬ ط£ظˆظ„ظٹ ظ…ظ†ظپطµظ„ ط¹ظ† ظ…ط­ط±ظƒط§طھ AI-1 ط¥ظ„ظ‰ AI-7 ط§ظ„ظ…ظˆط¬ظˆط¯ط© ظپظٹ ط§ظ„ط¬ط°ط±ط› ط³ط¬ظ„ط§طھظ‡ط§ طھط¬ط±ظٹط¨ظٹط© ظˆظ„ط§ طھطھط­ظƒظ… ط¨ط®ظˆط§ط¯ظ… ط£ظˆ ط¹ظ…ظ„ظٹط§طھ ظ†ط´ط± ط­ظ‚ظٹظ‚ظٹط©. Firebase ظˆGoogle ظˆGemini ظ…طھظˆظ‚ظپط© ط§ظپطھط±ط§ط¶ظٹظ‹ط§طŒ ظˆظ‚ظˆط§ط¹ط¯ Firestore طھظ…ظ†ط¹ ط§ظ„ظˆطµظˆظ„طŒ ظˆط§ظ„طھط·ط¨ظٹظ‚ ط؛ظٹط± ظ…ط´ظ…ظˆظ„ ط¨ظ†ط´ط± GitHub Pages. ط±ط§ط¬ط¹ [ط­ط§ظ„ط© ط§ظ„طھط·ط¨ظٹظ‚ ظˆطھط´ط؛ظٹظ„ظ‡ ظ…ط­ظ„ظٹظ‹ط§](apps/ai-intelligence-console/README.md).

ظ„طھظ…ظٹظٹط² ط§ظ„ظ…ظˆط¬ظˆط¯ ظˆط§ظ„ظ…طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„طھط¬ط±ظٹط¨ظٹ ظˆط§ظ„ظ…ط­ط¬ظˆط¨ ظ‚ط¨ظ„ ط£ظٹ ط¥ط¶ط§ظپط©طŒ ط±ط§ط¬ط¹ [ظ…ظˆط§ط،ظ…ط© ط£ط¨ط­ط§ط« Devobs AI ظ„ط¹ط§ظ… 2026](docs/strategy/DEVOBS_AI_RESEARCH_ALIGNMENT_2026.md)طŒ ظˆ[ظ…ط±ط§ط¬ط¹ط© ظ…ظ†ط¸ظˆظ…ط© DevOps ظˆط§ظ„ط°ظƒط§ط، ط§ظ„ط§طµط·ظ†ط§ط¹ظٹ](docs/AI_DEVOPS_ECOSYSTEM_REVIEW_2026-11-11.md)طŒ ظˆ[ط®ط§ط±ط·ط© ط§ظ„طھظ†ظپظٹط° ط§ظ„ظ…ط±ط­ظ„ظٹط©](docs/strategy/DEVOBS_AI_ROADMAP_2026.md). ظ‡ط°ظ‡ ط§ظ„ظ…ط³طھظ†ط¯ط§طھ طھط®ط·ط· ظ„ظ„ط¹ظ…ظ„ ظˆظ„ط§ طھظپطھط­ AI-9 ط£ظˆ P01 ط£ظˆ طھط¬ظٹط² ظ†ط´ط±ظ‹ط§.

ظ„طھط³ط¬ظٹظ„ ظ…طھط·ظ„ط¨ط§طھ ط£ظٹ طھظ‚ظٹظٹظ… ظ…ط³طھظ‚ظ„ ظ…ط³طھظ‚ط¨ظ„ظٹ ظ„ط­ظˆط§ط¯ط« AI-9 ط§ظ„ط·ط¨ظٹط¹ظٹط©طŒ ط±ط§ط¬ط¹ [ط¨ط±ظˆطھظˆظƒظˆظ„ ط§ظ„طھط³ط¬ظٹظ„ ط§ظ„ظ…ط³ط¨ظ‚](docs/AI9_REAL_INCIDENT_PREREGISTRATION.md). ظ‡ط°ط§ طھطµظ…ظٹظ… ظپظ‚ط·ط› ظ„ط§ طھظˆط¬ط¯ ظ…ط¬ظ…ظˆط¹ط© ظ…ط¤ظ‡ظ„ط© ظ…ط¹طھظ…ط¯ط©طŒ ظˆظ„ط§ ظٹظپطھط­ ط§ظ„ط¨ظˆط§ط¨ط© ط£ظˆ ظٹط¬ظٹط² ط§ظ„طھظ‚ظٹظٹظ….

```text
ط¨ظٹط§ظ†ط§طھ طھط´ط؛ظٹظ„ ط§طµط·ظ†ط§ط¹ظٹط© ظ…ط­ظ„ظٹط©
  â†’ AI-1 ط§ط³طھظ‚ط¨ط§ظ„ ظˆطھط­ظ‚ظ‚
  â†’ AI-2 ظƒط´ظپ ط´ط°ظˆط° â†’ AI-3 طھط­ظ„ظٹظ„ â†’ AI-4 طھظˆطµظٹط§طھ runbook
  â†’ AI-5 ط§طھط¬ط§ظ‡ط§طھ â†’ AI-6 طھط؛ط°ظٹط© ط±ط§ط¬ط¹ط© ط§ط®طھظٹط§ط±ظٹط© â†’ AI-7 ظ„ظˆط­ط©/API ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·
  â†’ GitHub Actions: ط§ط®طھط¨ط§ط±ط§طھ ظˆظپط­ظˆطµ ط£ظ…ظ†ظٹط© ظˆظ…ط±ط§ط¬ط¹ط© PR ط§ط®طھظٹط§ط±ظٹط©
```

ظ„ط±ط¤ظٹط© ظ…ط³ط§ط± AI-1 ط¥ظ„ظ‰ AI-7 ظٹط¹ظ…ظ„ ظ…ط­ظ„ظٹظ‹ط§ ط¹ظ„ظ‰ ط¨ظٹط§ظ†ط§طھ ط§طµط·ظ†ط§ط¹ظٹط©طŒ ط´ط؛ظ‘ظ„ `node scripts/local_advisory_acceptance.mjs` ظ…ظ† ط¬ط°ط± ط§ظ„ظ…ط³طھظˆط¯ط¹. [ط¯ظ„ظٹظ„ ط§ظ„ظ‚ط¨ظˆظ„ ط§ظ„ظ…ط­ظ„ظٹ ظˆط­ط¯ظˆط¯ظ‡](docs/LOCAL_ADVISORY_V01_ACCEPTANCE.md) ظٹط´ط±ط­ ط§ظ„ظ†طھظٹط¬ط© ظˆط§ظ„ط§ط®طھط¨ط§ط±ط§طھط› ظ‡ط°ط§ ط§ظ„ط¹ط±ط¶ ظ„ط§ ظٹط«ط¨طھ ط¬ط§ظ‡ط²ظٹط© AI-9 ط£ظˆ ط§ظ„ط§ط³طھط¶ط§ظپط© ط£ظˆ ط§ظ„ط¥ظ†طھط§ط¬.

ط¥ط¶ط§ظپط© PR-Agent ط§ط®طھظٹط§ط±ظٹط© ظˆظ…ط·ظپط£ط© ط§ظپطھط±ط§ط¶ظٹظ‹ط§طŒ ظˆطھط¹ظ…ظ„ ظƒظ…ط±ط§ط¬ط¹ ط¨ط¯ظٹظ„ ط¹ظ† ظ…ط±ط§ط¬ط¹ط© Codex ط­طھظ‰ ظ„ط§ ظٹطھظƒط±ط± ط§ظ„ط§ط³طھط¯ظ„ط§ظ„. ط¥ط¹ط¯ط§ط¯ط§ Ollama ظˆLocalAI ط§ظ„ظ…ط­ظ„ظٹط§ظ† ظ…ظˆط«ظ‚ط§ظ† ظپظٹ [`models/docker-compose.yml`](models/docker-compose.yml)طŒ ظˆظ„ط§ ظٹط¹ظ…ظ„ط§ظ† طھظ„ظ‚ط§ط¦ظٹظ‹ط§ ظˆظ„ط§ ظٹطھط¶ظ…ظ†ط§ظ† ط£ظˆط²ط§ظ† ظ†ظ…ط§ط°ط¬. ظٹظ…ظƒظ† ط§ط®طھظٹط§ط± ط£ط­ط¯ظ‡ظ…ط§ ظٹط¯ظˆظٹظ‹ط§ ظ„طھط´ط®ظٹطµ ط§ظ„ط³ط¬ظ„ط§طھ ط¹ط¨ط± API staging ط¨ط¹ط¯ ط§ظ„ظ…ظˆط§ظپظ‚ط§طھ ط§ظ„طµط±ظٹط­ط©طŒ ظ„ظƒظ†ظ‡ظ…ط§ ظ„ط§ ظٹطھطµظ„ط§ظ† طھظ„ظ‚ط§ط¦ظٹظ‹ط§ ط¨ط³ظ„ط³ظ„ط© AI-1 ط¥ظ„ظ‰ AI-7. ظٹظˆط¬ط¯ ط£ظٹط¶ظ‹ط§ [ظ…ط³ط§ط¹ط¯ ط¨ط±ظ…ط¬ط© ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹ ط¨ط§ط³طھط®ط¯ط§ظ… Aider ظˆOllama](docs/LOCAL_AI_CODE_ASSISTANT.md)طŒ ظ„ط§ ظٹط­طھط§ط¬ ظ…ظپطھط§ط­ API ظˆظٹط¹ط·ظ‘ظ„ ط§ظ„ط§ظ„طھط²ط§ظ… ط§ظ„طھظ„ظ‚ط§ط¦ظٹ. ط£ظ…ط«ظ„ط© K8sGPT ظˆHolmesGPT ط§ط®طھظٹط§ط±ظٹط© ظˆظ…ط­ط¯ظˆط¯ط© ظ„ظ„ظ‚ط±ط§ط،ط© ظپظٹ [`k8s/`](k8s/README.md)طŒ ظˆظ„ط§ طھط«ط¨ظ‘طھ ط§ظ„ط£ط¯ظˆط§طھ ظˆظ„ط§ طھط·ط¨ظ‚ ط¥ط¹ط¯ط§ط¯ط§طھ ط¹ظ„ظ‰ ط¹ظ†ظ‚ظˆط¯. ظٹط¸ظ„ MLflow ظ…ط±ط´ط­ظ‹ط§ ظ„ظ…ط±ط§ط¬ط¹ط© ظ…ظ†ظپطµظ„ط©.

| ط§ظ„ظ…ظƒظˆظ‘ظ† ط§ظ„ط®ط§ط±ط¬ظٹ ط§ظ„ظ…ط¶ط§ظپ ط£ظˆ ط§ظ„ظ…ظˆط«ظ‚ | ط§ظ„ط¥طµط¯ط§ط±/ط§ظ„ط¨طµظ…ط© | ط§ظ„ط±ط®طµط© | ط§ظ„ظ†ط·ط§ظ‚ |
| --- | --- | --- | --- |
| [PR-Agent](https://github.com/The-PR-Agent/pr-agent) | v0.49.0ط› طµظˆط±ط© ظ…ط«ط¨طھط© ط¹ظ„ظ‰ digest ظ…ظˆط«ظ‚ ظپظٹ [ط¯ظ„ظٹظ„ ط§ظ„طھظƒط§ظ…ظ„](docs/PR_AGENT_INTEGRATION.md) | [MIT](https://github.com/The-PR-Agent/pr-agent/blob/v0.49.0/LICENSE) | ظ…ط±ط§ط¬ط¹ط© PR ط§ط®طھظٹط§ط±ظٹط©ط› ط؛ظٹط± ظ…ظپط¹ظ‘ظ„ط© ظ…ط§ ظ„ظ… طھظڈط³طھظˆظپظژ ط¨ظˆط§ط¨ط§طھ ط§ظ„ط§ط®طھظٹط§ط± ظˆط§ظ„ظ…ظٹط²ط§ظ†ظٹط© ظˆط§ظ„طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ظ…طµط¯ط± ظˆط§ظ„ط§ط¹طھظ…ط§ط¯ ط§ظ„ظ…ظˆط¬ظˆط¯ |
| [Ollama](https://github.com/ollama/ollama) | v0.40.15ط› digest ظ…ظˆط«ظ‚ ظپظٹ [ط¯ظ„ظٹظ„ ط§ظ„ظ†ظ…ط§ط°ط¬](models/README.md) | [MIT](https://github.com/ollama/ollama/blob/v0.40.15/LICENSE) | ط®ط§ط¯ظ… CPU ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹط› ظ„ط§ ظٹظ†ط²ظ„ ظ†ظ…ظˆط°ط¬ظ‹ط§ طھظ„ظ‚ط§ط¦ظٹظ‹ط§ط› ظٹط´ط؛ظ‘ظ„ طھط´ط®ظٹطµ staging ظˆظ…ط³ط§ط¹ط¯ ط§ظ„ط¨ط±ظ…ط¬ط© ط§ظ„ظ…ط­ظ„ظٹ ط¨ط¹ط¯ ط§ظ„ط¥ط¹ط¯ط§ط¯ |
| [Aider](https://github.com/Aider-AI/aider) | v0.86.2ط› ط§ط³طھط®ط¯ط§ظ… ط§ط®طھظٹط§ط±ظٹ ظ…ظˆط«ظ‚ | [Apache-2.0](https://github.com/Aider-AI/aider/blob/v0.86.2/LICENSE.txt) | ظ…ط³ط§ط¹ط¯ ط¨ط±ظ…ط¬ط© طھظپط§ط¹ظ„ظٹ ظ…ط­ظ„ظٹ ط¹ط¨ط± Ollamaط› ظ„ظٹط³ ط¶ظ…ظ† CI ظˆظ„ط§ ظٹط¹ظ…ظ„ طھظ„ظ‚ط§ط¦ظٹظ‹ط§ |
| [LocalAI](https://github.com/mudler/LocalAI) | v4.12.1ط› digest ظ…ظˆط«ظ‚ ظپظٹ [ط¯ظ„ظٹظ„ ط§ظ„ظ†ظ…ط§ط°ط¬](models/README.md) | [MIT](https://github.com/mudler/LocalAI/blob/v4.12.1/LICENSE) | CPU ط§ط®طھظٹط§ط±ظٹ ط®ظ„ظپ profileط› ظ„ط§ ظٹظ†ط²ظ„ ظ†ظ…ظˆط°ط¬ظ‹ط§ طھظ„ظ‚ط§ط¦ظٹظ‹ط§ط› ط§ط®طھظٹط§ط± ظٹط¯ظˆظٹ ظ…ظ…ظƒظ† ظ„ظ€API ط§ظ„طھط´ط®ظٹطµ ظپظ‚ط· |
| [GitHub MCP Server](https://github.com/github/github-mcp-server/tree/v2.1.0) | v2.1.0ط› ط§ظ„ظ…طµط¯ط± `4bcdcdf8d7beee98c9448e73e257308280924cc4` ظˆطµظˆط±ط© OCI ظ…ط«ط¨طھط© ط¹ظ„ظ‰ `sha256:f6056fc10bfffcc8c81a6417a2e9ca12808647e8dd6049642a4feaadee0e0f8a` | [MIT](https://github.com/github/github-mcp-server/blob/v2.1.0/LICENSE) | ط®ط§ط¯ظ… ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹ ظ„ظ€CodexطŒ ط£ط¯ظˆط§طھ GitHub ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط· ظˆظ„ظ…ط³طھظˆط¯ط¹ط§طھ ط¹ط§ظ…ط©ط› ظ„ط§ ظٹط¯ط®ظ„ ظپظٹ CI ط£ظˆ طھط´ط؛ظٹظ„ ط§ظ„طھط·ط¨ظٹظ‚طŒ ظˆظ„ط§ ظٹظڈظپط¹ظ‘ظ„ طھظ„ظ‚ط§ط¦ظٹظ‹ط§ |
| [Grafana MCP](https://github.com/grafana/mcp-grafana/tree/v2.3.0) | v2.3.0ط› ط§ظ„ظ…طµط¯ط± `c8cafb67854c45e79f8f9b5fca7d9b3a403f1771`ط› ط¨طµظ…ط© ط­ط²ظ…ط© Windows x64 ظپظٹ [ط§ظ„ط¯ظ„ظٹظ„](docs/GRAFANA_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/grafana/mcp-grafana/blob/v2.3.0/LICENSE) | ط®ط§ط¯ظ… Codex ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹط› ظ„ظˆط­ط§طھ Grafana ظˆPrometheus ظپظ‚ط·طŒ ظ…ط¹ ط­ط¬ط¨ ط§ظ„ظƒطھط§ط¨ط© ظˆAPIط› ط؛ظٹط± ظ…ظپط¹ظ‘ظ„ ط§ظپطھط±ط§ط¶ظٹظ‹ط§ |
| [Kubernetes MCP Server](https://github.com/containers/kubernetes-mcp-server/tree/v0.1.2) | v0.1.2ط› ط§ظ„ظ…طµط¯ط± `66553fed5c16454e5814b41e331b4357f15806d8`ط› ط¨طµظ…ط© Windows x64 ظپظٹ [ط§ظ„ط¯ظ„ظٹظ„](docs/KUBERNETES_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/containers/kubernetes-mcp-server/blob/v0.1.2/LICENSE) | Codex ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹط› ط£ط­ط¯ط§ط« namespace ظ…ط­ط¯ط¯ ظپظ‚ط· ظ…ط¹ `read_only` ظˆRBAC ظپط¹ظ„ظٹط› ظ„ط§ ط³ط¬ظ„ط§طھ ط£ظˆ ط£ط³ط±ط§ط± ط£ظˆ طھط¹ط¯ظٹظ„ |
| [Argo CD MCP](https://github.com/argoproj-labs/mcp-for-argocd/tree/v0.9.0) | v0.9.0ط› ط§ظ„ظ…طµط¯ط± `28d15ca69b0c31387cc6ec73d201fd13c5d22b6a`ط› طµظˆط±ط© ظ…ط«ط¨طھط© ط¹ظ„ظ‰ digest ظ…ط¹ ط¨ظٹط§ظ† ط¨ظ†ط§ط، ظپظٹ [ط§ظ„ط¯ظ„ظٹظ„](docs/ARGOCD_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/LICENSE) | Codex ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹط› ط£ط¯ط§ط© `list_applications` ظپظ‚ط· ظ…ط¹ ظ…ظˆط§ظپظ‚ط© ظˆRBAC ظ…ظ‚ظٹط¯ط› ط¨ظ„ط§ ظƒطھط§ط¨ط© ط£ظˆ ظ…ظˆط§ط±ط¯ ط£ظˆ ط³ط¬ظ„ط§طھ |
| [K8sGPT](https://github.com/k8sgpt-ai/k8sgpt) | v0.4.41ط› ط£ظ…ط«ظ„ط© CLI ظپظ‚ط· | [Apache-2.0](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/LICENSE) | ظپط­طµ ظٹط¯ظˆظٹ ظ…ط­ط¯ظˆط¯ ط¨ط§ظ„ظ€namespaceط› ط£ظ…ط± ط§ظ„ظ…ط«ط§ظ„ ظ„ط§ ظٹط·ظ„ط¨ ط´ط±ط­ظ‹ط§ ظ…ظ† ظ†ظ…ظˆط°ط¬ |
| [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) | 0.46.0ط› ط£ظ…ط«ظ„ط© ط¥ط¹ط¯ط§ط¯ ظپظ‚ط· | [Apache-2.0](https://github.com/HolmesGPT/holmesgpt/blob/0.46.0/LICENSE) | ط¥ط¹ط¯ط§ط¯ toolset ظˆطµظ„ط§ط­ظٹط§طھ ظ‚ط±ط§ط،ط© ظپظ‚ط·ط› ظ„ط§ طھط«ط¨ظٹطھ ط£ظˆ ط§ط³طھط¯ظ„ط§ظ„ طھظ„ظ‚ط§ط¦ظٹ |

ظ…ط¬ظ„ط¯ط§طھ `agents/` ظˆ`workflows/` ظˆ`models/` ظˆ`mlops/` ظ‡ظٹ ظپظ‡ط§ط±ط³ طھظˆط«ظٹظ‚ظٹط© ظ„ظ‡ط°ظ‡ ط§ظ„ظ…ط±ط­ظ„ط©ط› ظ…ظ„ظپط§طھ ط§ظ„طھط´ط؛ظٹظ„ ط§ظ„ظپط¹ظ„ظٹط© طھط¨ظ‚ظ‰ ظپظٹ ظ…ظˆط§ظ‚ط¹ظ‡ط§ ط§ظ„ط­ط§ظ„ظٹط©. ط±ط§ط¬ط¹ [ط®ط±ظٹط·ط© ط§ظ„ظˆظƒظ„ط§ط،](agents/README.md)طŒ [ط®ط±ظٹط·ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„](workflows/README.md)طŒ [ط®ط±ظٹط·ط© ط§ظ„ظ†ظ…ط§ط°ط¬](models/README.md)طŒ [ط£ظ…ط«ظ„ط© Kubernetes ط§ظ„ط§ط®طھظٹط§ط±ظٹط©](k8s/README.md)طŒ [طھظƒط§ظ…ظ„ PR-Agent](docs/PR_AGENT_INTEGRATION.md)طŒ [ط®ط±ظٹط·ط© ط§ظ„ظ…ط±ط§ظ‚ط¨ط©](monitoring/README.md)طŒ ظˆ[ط®ط±ظٹط·ط© MLOps](mlops/README.md).

ظ„طھط³ط¬ظٹظ„ ظ†طھظٹط¬ط© CI ظ…ظ† ظ…ط³طھظˆط¯ط¹ LiveOps ط¯ظˆظ† ط¥ط±ط³ط§ظ„ ظ…ط­طھظˆظ‰ ط§ظ„طھط·ط¨ظٹظ‚ ط£ظˆ ط¨ظٹط§ظ†ط§طھ GeminiطŒ ط±ط§ط¬ط¹ [ط¬ط³ط± LiveOps ط§ظ„ط§ط®طھظٹط§ط±ظٹ](docs/LIVEOPS_CI_INTEGRATION.md). ظٹط³ط¬ظ„ ط§ظ„ط¬ط³ط± ط¨ظٹط§ظ†ط§طھ طھط´ط؛ظٹظ„ ظپظ‚ط· ظˆظ„ط§ ظٹظپط¹ظ‘ظ„ ط§ط³طھط¯ظ„ط§ظ„ظ‹ط§ ط£ظˆ ط¥طµظ„ط§ط­ظ‹ط§ طھظ„ظ‚ط§ط¦ظٹظ‹ط§.

## ظ…ط±ظƒط² ط§ظ„ط£طھظ…طھط©

- **طھط´ط®ظٹطµ ط£ظ…ظ† CI / Gitleaks:** [ط¯ظ„ظٹظ„ ظ…ط±ط§ط¬ط¹ط© طھط§ط±ظٹط® Git ظپظٹ GitBook](docs/gitbook-sync-prep/GITLEAKS_HISTORY_DIAGNOSTICS.md) â€” ظپطµظ„ظŒ ط¨ظٹظ† ط¹ط·ظ„ طھط­ظ‚ظ‚ Git ظˆط¨ظٹظ† طھط³ط±ظٹط¨ ظ…ط¤ظƒظ‘ط¯طŒ ط¯ظˆظ† طھط¹ط·ظٹظ„ ط§ظ„ظ…ط³ط­ ط£ظˆ ظ†ط´ط± ط£ط³ط±ط§ط±.

- **ط§ط¨ط¯ط£ ظ…ظ† ظ‡ظ†ط§:** [ظ…ط±ظƒط² ط§ظ„ط£طھظ…طھط© ظˆط³ظٹط± ط§ظ„طھط´ط؛ظٹظ„ ط§ظ„ظ…ظˆط­ط¯](docs/AUTOMATION_HUB.md)
- **CineForge-AI CI review-only handoff:** [ظپط­طµ ظ…ط­ط¯ظˆط¯ ظ„ظ†طھط§ط¦ط¬ CI ط¯ظˆظ† ظ†ظ‚ظ„ ط§ظ„ظƒظˆط¯ ط£ظˆ طھط´ط؛ظٹظ„ ط®ط¯ظ…ط§طھ](docs/CINEFORGE_CI_REVIEW_HANDOFF.md) â€” ط¨ظˆط§ط¨ط© ظ…ط±ط§ط¬ط¹ط© ظ…ط­ظ„ظٹط© ظپظ‚ط·طŒ ظ„ظٹط³طھ طھظƒط§ظ…ظ„ظ‹ط§ ط­ظٹظ‹ط§ ظˆظ„ط§ ط¥طµظ„ط§ط­ظ‹ط§ ظ„ط®ظ„ظ„ GitHub Runner.
- **Cross-project Runner evidence triage (offline):** [طھط´ط®ظٹطµ ظ…ط­ط¯ظˆط¯ ظ„ط£ط¯ظ„ط© GitHub Actions ظ„ظ…ط´ط±ظˆط¹ظٹ CineForge ظˆPhone Repair Assistant](docs/integrations/CINEFORGE_RUNNER_TRIAGE.md) â€” ظٹظپطµظ„ ط¨ظٹظ† ط§ظ„ظ…ط¹ظ„ظˆظ…ط§طھ ط§ظ„ظ…ظپظ‚ظˆط¯ط© (`null`) ظˆظ‚ظٹظ… Runner ط§ظ„ظپط¹ظ„ظٹط©طŒ ظˆظٹط³ظ…ط­ ظپظ‚ط· ط¨ط£ط³ظ…ط§ط، ط§ظ„ظ…ط´ط§ط±ظٹط¹ ظˆط§ظ„ظˆط¸ط§ط¦ظپ ط§ظ„ظ…ط­ط¯ط¯ط©ط› ظ„ط§ ظٹط¬ظ„ط¨ ط³ط¬ظ„ط§طھ ط®ط§طµط© ظˆظ„ط§ ظٹظ†ظپظ‘ط° ط¹ظ…ظ„ظٹط§طھ ط£ظˆ ظٹط¯ظ‘ط¹ظٹ ط³ط¨ط¨ظ‹ط§ ط¬ط°ط±ظٹظ‹ط§.
- **ط¬ط§ظ‡ط²ظٹط© ط¥طµط¯ط§ط±ط§طھ ط§ظ„ظ…ط´ط§ط±ظٹط¹:** [Portfolio v1 release-readiness tracker](docs/portfolio/PORTFOLIO_V1_READINESS.md) â€” ظ„ظ‚ط·ط© ظ…ظˆط«ظ‚ط© ط¨ط§ظ„ط£ط¯ظ„ط© ظ„ظ…ط³طھظˆط¯ط¹ط§طھ ط§ظ„ظ…ط§ظ„ظƒ ط§ظ„ط®ظ…ط³ط©ط› طھظ…ظٹظ‘ط² ظ†ط¬ط§ط­ CI ط¹ظ† ط§ظ„ظ†ط´ط± ظˆط§ظ„طھط´ط؛ظٹظ„ ط§ظ„ظپط¹ظ„ظٹطŒ ظˆظ„ط§ طھط؛ظٹظ‘ط± ط­ط§ظ„ط© ط£ظٹ ط¨ظˆط§ط¨ط©.
- **ط³ط¬ظ„ ط§ظ„ط¥ظ†ط¬ط§ط²ط§طھ ظˆط§ظ„ط¨ظˆط§ط¨ط§طھ:** [Milestone Ledger](docs/MILESTONE_LEDGER.md) â€” ظپط­طµ ط¯ظˆظ† ط´ط¨ظƒط© ظٹط±ط¨ط· ظƒظ„ ط¥ظ†ط¬ط§ط² ظ…ظˆط«ظ‚ ط¨ط±ظ‚ظ… PR ظˆSHA ظˆط¯ظ„ظٹظ„ CIطŒ ظˆظٹط¹ط±ط¶ ط§ظ„ظ†ظˆط§ظ‚طµ ط¯ظˆظ† طھط؛ظٹظٹط± ط­ط§ظ„ط© ط¬ط§ظ‡ط²ظٹطھظ‡ط§.
- **طھظƒط§ظ…ظ„ OpenArt ط§ظ„ط§ط®طھظٹط§ط±ظٹ:** [ط­ظˆظƒظ…ط© ط·ظ„ط¨ط§طھ ط§ظ„طµظˆط± ظˆط§ظ„ظپظٹط¯ظٹظˆ ط¹ط¨ط± MCP](docs/OPENART_MCP_INTEGRATION.md) â€” طµظٹط؛ط© ط·ظ„ط¨ ط®ط§طµط© ط¢ظ…ظ†ط© ط¯ظˆظ† ط´ط¨ظƒط© ط£ظˆ ظƒظ„ظپط©طŒ ظ…ط¹ ظ…ظˆط§ظپظ‚ط© ظ…ظ†ظپطµظ„ط© ظ‚ط¨ظ„ ط£ظٹ طھظˆظ„ظٹط¯.
- **GitHub MCP ظ„ظ„ظ…ط·ظˆط±ظٹظ†:** [ط¥ط¹ط¯ط§ط¯ ط§ط®طھظٹط§ط±ظٹ ظ…ط­ظ„ظٹ ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·](docs/GITHUB_MCP_INTEGRATION.md) â€” ظٹط³طھط¹ظ…ظ„ ط§ظ„ط®ط§ط¯ظ… ط§ظ„ط±ط³ظ…ظٹ ظ…ظ† طµظˆط±ط© ظ…ط«ط¨طھط©ط› ظ„ط§ طھظڈط­ظپط¸ ط£ط³ط±ط§ط± ظپظٹ ط§ظ„ظ…ط³طھظˆط¯ط¹ ظˆظ„ط§ ظٹط¹ظ…ظ„ طھظ„ظ‚ط§ط¦ظٹظ‹ط§.
- **Grafana MCP ظ„ظ„ظ…ط·ظˆط±ظٹظ†:** [ط¥ط¹ط¯ط§ط¯ ط§ط®طھظٹط§ط±ظٹ ظ…ط­ظ„ظٹ ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·](docs/GRAFANA_MCP_INTEGRATION.md) â€” ظٹظ‚طھطµط± ط¹ظ„ظ‰ ظ„ظˆط­ط§طھ Grafana ظˆظ…ظ‚ط§ظٹظٹط³ Prometheusط› ظ„ط§ ظٹظڈظپط¹ظ‘ظ„ ظپظٹ ط¥ط¹ط¯ط§ط¯ ط§ظ„ظ…ط³طھظˆط¯ط¹.
- **Kubernetes MCP ظ„ظ„ظ…ط·ظˆط±ظٹظ†:** [ط¥ط¹ط¯ط§ط¯ ط§ط®طھظٹط§ط±ظٹ ظ„ط£ط­ط¯ط§ط« namespace ظˆط§ط­ط¯](docs/KUBERNETES_MCP_INTEGRATION.md) â€” ط£ط¯ط§ط© ط£ط­ط¯ط§ط« ظپظ‚ط·طŒ ظ…ط¹ طµظ„ط§ط­ظٹط© Kubernetes `list` ط§ظ„ظپط¹ظ„ظٹط©ط› ظ„ط§ ظٹظڈظپط¹ظ‘ظ„ ظپظٹ ط¥ط¹ط¯ط§ط¯ ط§ظ„ظ…ط³طھظˆط¯ط¹.
- **Argo CD MCP ظ„ظ„ظ…ط·ظˆط±ظٹظ†:** [ظ‚ط±ط§ط،ط© ط­ط§ظ„ط© ط§ظ„طھط·ط¨ظٹظ‚ط§طھ](docs/ARGOCD_MCP_INTEGRATION.md) â€” ط£ط¯ط§ط© `list_applications` ظپظ‚ط·طŒ ظ…ط¹ ظ…ظˆط§ظپظ‚ط© Codex ظˆط±ظ…ط² Argo CD ظ…ط®طµطµ ظ„ظ„ظ‚ط±ط§ط،ط©ط› ط؛ظٹط± ظ…ظپط¹ظ‘ظ„ ط§ظپطھط±ط§ط¶ظٹظ‹ط§.
- [Devobs AI DevOps Control Room](docs/AI_DEVOPS_CONTROL_ROOM.md): طھظˆط«ظٹظ‚ ظ…ط³ط§ط±ط§طھ AI ظˆCI ظˆط­ط§ظ„ط© ط§ظ„طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ظ…طµط¯ط± ظ…ظ‚ط§ط¨ظ„ ط§ظ„طھط´ط؛ظٹظ„.
- [Devobs ط¨ط§ظ„ظ…ظˆط§ط±ط¯ ط§ظ„ظ…ط¬ط§ظ†ظٹط© ط§ظ„ط­ط§ظ„ظٹط©](docs/FREE_DEVOBS_MODE.md): ظ…ط¹ط§ظٹظ†ط© ظ…ظ†ط´ظˆط±ط© ظ„ظ…ط³ط§ط± AI-1 ط¥ظ„ظ‰ AI-7 ط¨ط¹ظٹظ†ط© ط§طµط·ظ†ط§ط¹ظٹط©طŒ ظˆظ…ط°ظƒط±ط§طھ ظپظٹ ط§ظ„ظ…طھطµظپط­طŒ ظˆطھط´ط؛ظٹظ„ ظ…ط­ظ„ظٹ ط¯ظˆظ† ظ…ظپط§طھظٹط­ ط£ظˆ ط±ط³ظˆظ… ط§ط³طھط¶ط§ظپط© ط¬ط¯ظٹط¯ط©.
- [ط§ط³طھظ‚ط¨ط§ظ„ ط£ط­ط¯ط§ط« AI-1 ظ…ط­ظ„ظٹظ‹ط§](docs/AI_EVENT_INGESTION.md): طµظٹط؛ط© ظ…ظˆط­ظ‘ط¯ط© ظˆظ…ظ„ظپ JSONL ظ…ط­ظ„ظٹط› ط¨ظ„ط§ ط§طھطµط§ظ„ط§طھ ط£ظˆ ط®ط¯ظ…ط§طھ ط®ط§ط±ط¬ظٹط©.
- [ط¬ط³ط± CloudEvents ظ„ظ†طھط§ط¦ط¬ CI](docs/integrations/CLOUDEVENTS_CI_BRIDGE.md): ظ…ط­ظˆظ‘ظ„ ظ…ط­ظ„ظٹ ط؛ظٹط± ظ…ظˆط«ظ‘ظ‚ ط§ظ„ظ…طµط¯ط± ط¥ظ„ظ‰ ظ…ط®ط·ط· AI-1 ط§ظ„ظ‚ط§ط¦ظ…طŒ ظˆظٹط´ظ…ظ„ CineForge-AI ط¨ط­ط¯ط« ط§طµط·ظ†ط§ط¹ظٹ ظپظ‚ط· ط¯ظˆظ† ظ…ط±ط³ظ„ ط­ظٹ ط£ظˆ ظ†ظ‚ظ„ ط¨ظٹط§ظ†ط§طھط› ط¨ظˆط§ط¨ط© `REVIEW_ONLY` ظ…ط³طھظ‚ظ„ط©.
- [ط¬ط³ط± OpenTelemetry OTLP ظ„ظ…ظ‚ظٹط§ط³ ط§ظ„ط®ط·ط£](docs/integrations/OTLP_ERROR_RATE_BRIDGE.md): ظ…ط­ظˆظ‘ظ„ ط§طµط·ظ†ط§ط¹ظٹ ظ…ط­ظ„ظٹ ظ„ظ…ظ‚ظٹط§ط³ `error_rate_pct` ط¥ظ„ظ‰ AI-1ط› ط¨ظ„ط§ ط§طھطµط§ظ„ط§طھ ط£ظˆ ط¨ظٹط§ظ†ط§طھ ط¹ظ…ظ„ط§ط، ط£ظˆ ط®ط¯ظ…ط§طھ ظ…ط¯ظپظˆط¹ط©.
- [ظƒط´ظپ ط§ظ„ط´ط°ظˆط° AI-2 ظ…ط­ظ„ظٹظ‹ط§](docs/AI_ANOMALY_DETECTION.md): ظ…ط¤ط´ط±ط§طھ ط¥ط­طµط§ط¦ظٹط© ظ‚ط§ط¨ظ„ط© ظ„ظ„طھظپط³ظٹط± ط¹ظ„ظ‰ ط£ط­ط¯ط§ط« ظ…ظ‚ط§ظٹظٹط³ ظ…ط­ظ„ظٹط© ط§طµط·ظ†ط§ط¹ظٹط©.
- [طھط­ظ„ظٹظ„ ط§ظ„ط­ظˆط§ط¯ط« AI-3 ظ…ط­ظ„ظٹظ‹ط§](docs/AI_INCIDENT_ANALYSIS.md): طھط¬ظ…ظٹط¹ ط³ط¬ظ„ط§طھ ط§طµط·ظ†ط§ط¹ظٹط© ظˆظپط±ط¶ظٹط§طھ ط£ط³ط¨ط§ط¨ ظ…ط­طھظ…ظ„ط© ظˆط³ظٹط§ظ‚ CI ظپظ‚ط·.
- [طھظˆطµظٹط§طھ AI-4 ط§ظ„ظ…ط­ظ„ظٹط©](docs/AI_RECOMMENDATIONS.md): ظ…ط·ط§ط¨ظ‚ط© ظپط±ط¶ظٹط§طھ AI-3 ظ…ط¹ runbooks ط«ط§ط¨طھط©طŒ ط¨ظˆط¶ط¹ ط§ظ„ط§ظ‚طھط±ط§ط­ ظپظ‚ط·.
- [طھظ‚ط§ط±ظٹط± ط§ظ„ط§طھط¬ط§ظ‡ AI-5 ظ…ط­ظ„ظٹظ‹ط§](docs/AI_TREND_REPORTS.md): ظ…ظ„ط®طµ ظٹظˆظ…ظٹ/ط£ط³ط¨ظˆط¹ظٹ ظˆط§ط³طھظ‚ط±ط§ط، ط£ظˆظ„ظٹ ظ„ظ…ظ‚ط§ظٹظٹط³ ط³ط¬ظ„ ظ…ط­ظ„ظٹ ط¯ظˆظ† ط§طھطµط§ظ„ ط®ط§ط±ط¬ظٹ.
- [طھط؛ط°ظٹط© ط±ط§ط¬ط¹ط© ظ„ظ„طھظˆطµظٹط§طھ AI-6](docs/AI_FEEDBACK_LEARNING.md): طھط³ط¬ظٹظ„ ظ‚ط¨ظˆظ„/ط±ظپط¶ ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹ ظٹط¤ط«ط± ظپظٹ طھط±طھظٹط¨ ط§ظ„ظ…ط±ط§ط¬ط¹ط© ط¨ط¹ط¯ ط­ط¯ ط£ط¯ظ†ظ‰ ظ…ظ† ط§ظ„ظ‚ط±ط§ط±ط§طھ.
- [ظ„ظˆط­ط© ظˆAPI ط§ظ„ط°ظƒط§ط، ط§ظ„طھط´ط؛ظٹظ„ظٹ AI-7](docs/AI_LOCAL_DASHBOARD.md): ظ„ظ‚ط·ط© ظ…ط­ظ„ظٹط© ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·ط› ظ„ط§ طھظڈظ†ط´ط± ظ…ط¹ ط§ظ„ظ…ظˆظ‚ط¹ ظˆظ„ط§ طھط¹ط±ط¶ ط§ظ„ط³ط¬ظ„ط§طھ ط§ظ„ط®ط§ظ…. طھطھط¶ظ…ظ† طھطµط¯ظٹط±ظ‹ط§ ط§ط®طھظٹط§ط±ظٹظ‹ط§ ظ„ظ…ظ„ط®طµط§طھ ظ…ط¬ظ…ط¹ط© ط¥ظ„ظ‰ Google DocsطŒ ظˆط¬ط¯ظˆظ„ط© ظ…ظˆط¹ط¯ ظ…طھط§ط¨ط¹ط© ظپظٹ طھظ‚ظˆظٹظ… Google ط«ط§ظ†ظˆظٹ ط¨ط¹ط¯ ظ…ظˆط§ظپظ‚ط© ط§ظ„ظ…ط³طھط®ط¯ظ…ط› ظƒظ„ط§ظ‡ظ…ط§ ظ…ط¹ط·ظ‘ظ„ ط§ظپطھط±ط§ط¶ظٹظ‹ط§.
- [طھط¯ظ‚ظٹظ‚ ط­ظˆظƒظ…ط© main ط§ظ„ط­ط§ظ„ظٹ](docs/DEVOBS_MAIN_GOVERNANCE_AUDIT.md): ط§ظ„ظ‚ظˆط§ط¹ط¯ ط§ظ„ظپط¹ط§ظ„ط© ظˆظپط­ظˆطµ PR ظˆط­ط§ظ„ط© ط§ظ„ظ…ظˆط§ظپظ‚ط§طھ ظˆظپظ‚ GitHub API.
- [P00 release gate evidence](docs/P00_RELEASE_GATE_EVIDENCE.md): current branch rules, exact-main CI evidence, release safeguards and owner exit checklist.
- [P00 unsigned owner decision packet](docs/P00_OWNER_DECISION.md): immutable evidence baseline and blank GO/NO-GO fields for the human owner.
- [P00 PR #253 image-scan gap review](docs/P00_PR253_GAP_REVIEW.md): overlap with merged Trivy CI, unique scan-report gaps, and recommended rework.
- CI stages and validates `_site`; the main Pages release downloads the same run-scoped artifact across partial retries and revalidates it before publication. Rollback and Vercel remain separate paths; see [CI details](docs/CI.md).
- **Container security in CI:** the existing scan job builds `devobs-web:<checked-out SHA>` and Trivy 0.76.1 scans only that local Docker image. The fail-closed JSON policy requires the report's `container_image` type and exact `ArtifactName`; scanner/image/report errors or HIGH/CRITICAL findings (including unfixed) fail the required `validate` gate. The JSON report is retained for seven days and no image is published. Validate changes with `python3 -m unittest discover -s tests -p 'test_trivy_report_policy.py' -v` and `python3 scripts/check_action_pins.py`; see [CI details](docs/CI.md).
- [ظ‚ط±ط§ط± P00 ط¨ط´ط£ظ† PR #262](docs/P00_PR262_DISPOSITION.md): ط³ط¬ظ„ ط¯ظ„ظٹظ„ ط§ظ„ط¥ط­ظ„ط§ظ„ ظˆط­ط§ظ„ط© طھط¹ظ„ظٹظ‚ ط§ظ„ط¥ط؛ظ„ط§ظ‚ ط¨ط§ظ†طھط¸ط§ط± ط­ط³ظ… ظ…ط±ط§ط¬ط¹ط© PR.
- [طھظ‚ط±ظٹط± ط¬ط§ظ‡ط²ظٹط© Devobs ط§ظ„ط­ط§ظ„ظٹ](docs/DEVOBS_READINESS_CURRENT.md): ط­ط§ظ„ط© ظ…ظˆط«ظ‚ط© ط¨ط§ظ„ط£ط¯ظ„ط© ط¹ظ„ظ‰ SHA ط§ظ„ط­ط§ظ„ظٹطŒ ظ…ط¹ ظپطµظ„ ط§ظ„ظ†ط´ط± ط§ظ„ط«ط§ط¨طھ ط¹ظ† ط¬ط§ظ‡ط²ظٹط© API ظˆSaaS ط؛ظٹط± ط§ظ„ظ…ط«ط¨طھط©.
- [Staging acceptance evidence](docs/STAGING_ACCEPTANCE.md): separates the mocked HTTP smoke contract from the full `build_app()` and tenant-read integration against disposable PostgreSQL 17 in CI; neither proves Render readiness or changes P01 **NO-GO / BLOCKED**.
- [P01 startup configuration triage](docs/P01_STARTUP_TRIAGE.md): an offline, presence-only inventory checker for required staging names; it never reads values and cannot prove hosted readiness or approve P01. New source-side startup diagnostics distinguish missing required configuration from an invalid setting through fixed reason codes without exposing values; [staging runbook](docs/RENDER_OPENAI_STAGING_RUNBOOK.md). Actual Render startup remains unverified.
- [P01 managed-staging activation decision](docs/P01_ACTIVATION_READINESS.md): default NO-GO owner checklist. `/readyz` coalesces PostgreSQL probes with a 250 ms per-process result cache, and concurrent followers now fail closed after a bounded 4-second wait if a DB probe stalls. This is **not** a hosted rate limiter, successful Render DB connection, or approval for live staging; see [staging RLS and readiness details](docs/POSTGRES_RLS_STAGING.md). See the [region/budget decision](docs/P01_REGION_BUDGET_SECURITY.md) and [Render + Supabase proposal](docs/RENDER_SUPABASE_STAGING.md).
- [Devobs Production Execution Roadmap](docs/plans/2026-10-26-devobs-production-execution-roadmap.md): sequential P00â€“P12 gates, current evidence, blockers, and owner signoffs.

## ط§ظ„طھط«ط¨ظٹطھ ظˆط§ظ„طھط´ط؛ظٹظ„ ظ…ط­ظ„ظٹظ‹ط§

ط§ظ„ظ…طھط·ظ„ط¨ط§طھ: GitطŒ ظˆPython 3.10 ط£ظˆ ط£ط­ط¯ط« ظ„ظپط­ظˆطµ ط§ظ„ظ…ظˆظ‚ط¹ ظˆط§ظ„ط§ط®طھط¨ط§ط±ط§طھطŒ ظˆNode.js ظ„ط§ط®طھط¨ط§ط±ط§طھ ط§ظ„ط­ظˆط§ط¯ط« ظˆظ…ط±ط§ط­ظ„ AI-1 ط¥ظ„ظ‰ AI-7 ط§ظ„ظ…ط­ظ„ظٹط©. طµظپط­ط© ط§ظ„ظ…ظˆظ‚ط¹ ظˆظ„ظˆط­ط© AI-7 ط§ظ„ظ…ط­ظ„ظٹط© ظ„ط§ طھطھط·ظ„ط¨ط§ظ† ط­ط²ظ… ظˆط§ط¬ظ‡ط© ط£ظ…ط§ظ…ظٹط©. طھط·ط¨ظٹظ‚ React ط§ظ„ط§ط®طھظٹط§ط±ظٹ ط¯ط§ط®ظ„ `apps/ai-intelligence-console/` ظٹطھط·ظ„ط¨ Node.js 22.12 ط£ظˆ ط£ط­ط¯ط« (ظٹظˆطµظ‰ ط¨ظ€24) ظˆظٹظڈط´ط؛ظ‘ظ„ ظ…ظ† ط¯ظ„ظٹظ„ظ‡ ظˆظپظ‚ طھط¹ظ„ظٹظ…ط§طھظ‡ط› ظ„ط§ ظٹط¯ط®ظ„ ظپظٹ ظ†ط´ط± Pages.

```sh
git clone https://github.com/hamedonassar95/Devobs.git
cd Devobs
python3 -m http.server 8000 --bind 127.0.0.1
```

ط§ظپطھط­ <http://127.0.0.1:8000> ظپظٹ ط§ظ„ظ…طھطµظپط­. ظ„ط¥ظٹظ‚ط§ظپ ط§ظ„ط®ط§ط¯ظ… ط§ط¶ط؛ط· `Ctrl+C`. ط¹ظ„ظ‰ Windows ط§ط³طھط®ط¯ظ… `py -3 -m http.server 8000 --bind 127.0.0.1` ط¨ط¯ظ„ظ‹ط§ ظ…ظ† `python3`.

## ط§ظ„ط§ط®طھط¨ط§ط±ط§طھ ظˆط§ظ„ظپط­ظˆطµ

ظ…ظ† ط¬ط°ط± ط§ظ„ظ…ط³طھظˆط¯ط¹:

ظ„طھط´ط؛ظٹظ„ ظ…ط¬ظ…ظˆط¹ط© ط§ط®طھط¨ط§ط±ط§طھ Python ظƒط§ظ…ظ„ط© ظپظٹ ط¨ظٹط¦ط© ظ…ط­ظ„ظٹط© ط¬ط¯ظٹط¯ط©طŒ ط«ط¨ظ‘طھ ط§ظ„ط§ط¹طھظ…ط§ط¯ظٹط§طھ ط§ظ„ظ…ظ‚ظپظ„ط© ظپظٹ ط¨ظٹط¦ط© ط§ظپطھط±ط§ط¶ظٹط©. ط¨ط¹ط¶ ط§ط®طھط¨ط§ط±ط§طھ ط¹ظ‚ظˆط¯ YAML طھط³طھط®ط¯ظ… PyYAMLطŒ ط£ظˆ Ruby/Psych ط¥ط°ط§ ظƒط§ظ† ظ…طھط§ط­ظ‹ط§:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check --require-hashes -r requirements-api.lock -r requirements-dev.lock
```

ط¨ط¹ط¯ظ‡ط§ ط´ط؛ظ‘ظ„ ط§ظ„ط£ظˆط§ظ…ط± ط§ظ„طھط§ظ„ظٹط©. ط§ط®طھط¨ط§ط±ط§طھ PostgreSQL طھطھط®ط·ظ‰ ظ†ظپط³ظ‡ط§ ظ…ط§ ظ„ظ… طھظڈط¶ط¨ط· ظ‚ظˆط§ط¹ط¯ ط¨ظٹط§ظ†ط§طھ ط§ط®طھط¨ط§ط± ظ…ط¹ط²ظˆظ„ط© ط¹ط¨ط± ظ…طھط؛ظٹط±ط§طھ DSN ط§ظ„ظ…ظˆط«ظ‚ط© ظپظٹ CI.

```sh
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests -v
node --test tests/incident_guard.test.cjs tests/ai_event_ingest.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_incident_analysis.test.mjs tests/ai_recommendations.test.mjs tests/ai_trend_forecast.test.mjs tests/ai_feedback_learning.test.mjs tests/ai_dashboard_api.test.mjs
python3 scripts/check_site.py
```

ظ„طھط¬ط±ط¨ط© ط§ط³طھظ‚ط¨ط§ظ„ ظ…ط­ظ„ظٹ ط¨ط¨ظٹط§ظ†ط§طھ ط§طµط·ظ†ط§ط¹ظٹط©طŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ AI-1](docs/AI_EVENT_INGESTION.md). ظ„ط§ ظٹظ‚ط±ط£ ط§ظ„ط£ظ…ط± ط³ط¬ظ„ط§طھ GitHub ط£ظˆ ط§ظ„ط®ظˆط§ط¯ظ… طھظ„ظ‚ط§ط¦ظٹظ‹ط§.

ظ„طھط´ط؛ظٹظ„ ظƒط´ظپ AI-2 ط¹ظ„ظ‰ ط§ظ„ط³ط¬ظ„ ط§ظ„ط§طµط·ظ†ط§ط¹ظٹ ظ†ظپط³ظ‡ ط¯ظˆظ† طھط؛ظٹظٹط± ط§ظ„ظ…ظ„ظپطŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ ظƒط´ظپ ط§ظ„ط´ط°ظˆط°](docs/AI_ANOMALY_DETECTION.md). ط§ظ„ظ…ط®ط±ط¬ط§طھ ظ…ط±ط´ط­ط§طھ ط¥ط­طµط§ط¦ظٹط© ظˆظ„ظٹط³طھ طھط´ط®ظٹطµظ‹ط§ ط£ظˆ طھظ†ط¨ظٹظ‡ظ‹ط§ ظ…ط¤ظƒط¯ظ‹ط§.

ظ„طھط¬ظ…ظٹط¹ ط§ظ„ط³ط¬ظ„ط§طھ ظˆط±ط¨ط· ط³ظٹط§ظ‚ CI ظ…ط­ظ„ظٹظ‹ط§طŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ AI-3](docs/AI_INCIDENT_ANALYSIS.md). ظ„ط§ ظٹط«ط¨طھ ط°ظ„ظƒ ط³ط¨ط¨ظ‹ط§ ط¬ط°ط±ظٹظ‹ط§ ظˆظ„ط§ ظٹط¯ط¹ظ… ط±ط¨ط· ط£ط­ط¯ط§ط« ط§ظ„ظ†ط´ط± ظپظٹ ظ…ط®ط·ط· AI-1 ط§ظ„ط­ط§ظ„ظٹ.

ظ„طھظˆظ„ظٹط¯ ط§ظ‚طھط±ط§ط­ط§طھ ظ…ط­ظ„ظٹط© ظ…ظ† runbooks ط«ط§ط¨طھط© ط¯ظˆظ† طھظ†ظپظٹط°طŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ AI-4](docs/AI_RECOMMENDATIONS.md). ظٹظ„ط²ظ… ط§ط¹طھظ…ط§ط¯ ط¨ط´ط±ظٹ ظ…ظ†ظپطµظ„ ظ„ط£ظٹ طھط؛ظٹظٹط±ط› ط§ظ„ظ…ط®ط±ط¬ط§طھ ط§ط­طھظ…ط§ظ„ظٹط© ظˆظ„ط§ طھطھطµظ„ ط¨ط®ط¯ظ…ط§طھ ط®ط§ط±ط¬ظٹط©.

ظ„ط¥ظ†طھط§ط¬ ظ…ظ„ط®طµ ظٹظˆظ…ظٹ/ط£ط³ط¨ظˆط¹ظٹ ظˆط§ط³طھظ‚ط±ط§ط، ط£ظˆظ„ظٹ ظ„ظ„ظ…ظ‚ط§ظٹظٹط³ ظ…ظ† ظ…ظ„ظپ JSONL ظ…ط­ظ„ظٹطŒ ط´ط؛ظ‘ظ„ `node scripts/ai_intelligence/trend_report.mjs --store <local-jsonl-file>` ظˆط§طھط¨ط¹ [ط¯ظ„ظٹظ„ AI-5](docs/AI_TREND_REPORTS.md). ظ„ط§ ظٹظƒطھط¨ ط§ظ„ط£ظ…ط± ظپظٹ ط§ظ„ظ…ظ„ظپ ط£ظˆ ظٹطھطµظ„ ط¨ط§ظ„ط´ط¨ظƒط©طŒ ظˆظ„ط§ ظٹظ†طھط¬ ظ‚ظٹظ…ط© طھظ†ط¨ط¤ ط¹ظ†ط¯ ظ†ظ‚طµ ط³طھط© ط£ظٹط§ظ… UTC ظ…طھطµظ„ط©.

ظ„طھط³ط¬ظٹظ„ ظ‚ط¨ظˆظ„/ط±ظپط¶ طھظˆطµظٹط© ط¨ظ…ظˆط§ظپظ‚ط© ط§ظ„ظ…ط´ط؛ظ‘ظ„ ظˆطھط±طھظٹط¨ ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ ظˆظپظ‚ ط³ط¬ظ„ ظ…ط­ظ„ظٹ ط§ط®طھظٹط§ط±ظٹطŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ AI-6](docs/AI_FEEDBACK_LEARNING.md). ظ„ط§ طھظڈط¬ظ…ط¹ ظ…ظ„ط§ط­ط¸ط§طھ ظ†طµظٹط©طŒ ظˆظ„ط§ ظٹطھطµظ„ ط§ظ„ظ†ط¸ط§ظ… ط¨ط§ظ„ط´ط¨ظƒط©ط› ط§ظ„ظ…ط¹ط¯ظ„ ط¥ط´ط§ط±ط© طھظپط¶ظٹظ„ ظ…ط­ط¯ظˆط¯ط© ظˆظ„ظٹط³ ظ‚ظٹط§ط³ظ‹ط§ ظ„ط¯ظ‚ط© ط§ظ„ط£ط³ط¨ط§ط¨.

ظ„طھط´ط؛ظٹظ„ ظ„ظˆط­ط© AI-7 ظ…ط­ظ„ظٹظ‹ط§ ظ…ط¹ API ظ„ظ„ظ‚ط±ط§ط،ط© ظپظ‚ط·طŒ ط§طھط¨ط¹ [ط¯ظ„ظٹظ„ ط§ظ„ظ„ظˆط­ط© ط§ظ„ظ…ط­ظ„ظٹط©](docs/AI_LOCAL_DASHBOARD.md). طھط¯ط¹ظ… ط§ظ„ظ„ظˆط­ط© ط£ظٹط¶ظ‹ط§ ظ…ط°ظƒط±ط§طھ ظ…ط´ط؛ظ‘ظ„ ظ…ط­ظ„ظٹط© ظپظٹ طھط®ط²ظٹظ† ط§ظ„ظ…طھطµظپط­ ظ…ط¹ ط§ظ„ط¨ط­ط« ظˆط§ظ„طھط«ط¨ظٹطھ ظˆط§ظ„ط£ط±ط´ظپط© ظˆط§ظ„ط§ط³طھط¹ط§ط¯ط© ط§ظ„ظ…ط¤ظƒط¯ط©ط› ظ„ط§ طھظڈط±ط³ظ„ ط§ظ„ظ…ط°ظƒط±ط§طھ ط¥ظ„ظ‰ ط§ظ„ط®ط§ط¯ظ… ط£ظˆ AI-6. ظٹظ…ظƒظ† طھظپط¹ظٹظ„ ط­ظپط¸ ظ…ظ„ط®طµ ظ…ط¬ظ…ظ‘ط¹ ظپظٹ Google Docs ط£ظˆ ط¬ط¯ظˆظ„ط© ظ…ظˆط¹ط¯ ظ…طھط§ط¨ط¹ط© ظپظٹ طھظ‚ظˆظٹظ… Google ط«ط§ظ†ظˆظٹ ط§ط®طھظٹط§ط±ظٹظ‹ط§ ط¨ط¹ط¯ ط¥ط¹ط¯ط§ط¯ OAuth Client ID. ظ„ط§ طھظ†ط´ط± ط§ظ„ظ„ظˆط­ط© ط£ظˆ طھط¹ط±ط¶ظ‡ط§ ط¹ط¨ط± ظ†ظپظ‚ط› ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظ†ط´ظˆط± ظٹط¨ظ‚ظ‰ طµظپط­ط© ط«ط§ط¨طھط© ط¨ظ„ط§ API.

ظٹظپط­طµ CI ط´ظٹظپط±ط© Python ط¨ط§ط³طھط®ط¯ط§ظ… BanditطŒ ظˆط§ظ„ط§ط¹طھظ…ط§ط¯ظٹط§طھ ط¨ط§ط³طھط®ط¯ط§ظ… `pip-audit`. ظ„طھط´ط؛ظٹظ„ ط§ظ„ظپط­ظˆطµ ظ…ط­ظ„ظٹظ‹ط§:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m bandit -r scripts -x scripts/check_site.py
pip-audit --requirement requirements-dev.txt
```

ظٹظپط­طµ GitHub Actions ط§ظ„ط£ط³ط±ط§ط± ط¨ط§ط³طھط®ط¯ط§ظ… Gitleaks CLI ظ…ط«ط¨طھ ط§ظ„ط¥طµط¯ط§ط± ظˆط§ظ„ط¨طµظ…ط©طŒ ظˆظٹطھط­ظ‚ظ‚ ظ…ظ† ط£ظ† ظ†ط·ط§ظ‚ Git ظˆظپط±ظˆظ‚ط§طھ commits ط§ظ„ط¯ظ…ط¬ ظٹط·ط§ط¨ظ‚ط§ظ† ط­ط¯ط« CI ظˆSHA ط§ظ„ظ…طµط¯ط±. ظٹط¶ظٹظپ ط§ظ„ظ…ظ„ط®طµ ط¯ظ„ظٹظ„ ط§ظ„ظ†ط·ط§ظ‚ ظˆط§ظ„ط¹ط¯ظ‘ط§ط¯ط§طھ ط¯ظˆظ† ط·ط¨ط§ط¹ط© ط§ظ„ط£ط³ط±ط§ط± ط£ظˆ ط±ظپط¹ طھظ‚ط±ظٹط± ط§ظ„ظ†طھط§ط¦ط¬. ط±ط§ط¬ط¹ [طھظپط§طµظٹظ„ ظ†ط·ط§ظ‚ Gitleaks ظˆط­ط¯ظˆط¯ظ‡](docs/CI.md) ظˆ[ظ†ط·ط§ظ‚ ظˆط¶ظˆط§ط¨ط· DevSecOps](docs/DEVSECOPS.md). ظ„ط§ ظٹط­طھط§ط¬ طھط´ط؛ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹ ط£ظˆ ط§ظ„ط§ط®طھط¨ط§ط±ط§طھ ط¥ظ„ظ‰ ظ…ظپط§طھظٹط­ ط£ظˆ ط­ط³ط§ط¨ط§طھ ط®ط¯ظ…ط§طھ ط®ط§ط±ط¬ظٹط©.

## ط§ظ„ط¥ط¹ط¯ط§ط¯ ظˆط§ظ„ط£ط³ط±ط§ط±

ط§ظ„ظ…ط´ط±ظˆط¹ ظ„ط§ ظٹظ‚ط±ط£ ظ…ظ„ظپط§طھ `.env` ظˆظ„ط§ ظٹط³طھط®ط¯ظ… ظ…طھط؛ظٹط±ط§طھ ط¨ظٹط¦ط© ظ…ط­ظ„ظٹط© ظ„طھط´ط؛ظٹظ„ ط§ظ„طµظپط­ط©. ط£ظڈظ†ط´ط¦ [.env.example](.env.example) ظƒظ…ط±ط¬ط¹ ظ„ط£ط³ظ…ط§ط، ط£ط³ط±ط§ط± ط§ظ„ط£طھظ…طھط© ط§ظ„ط§ط®طھظٹط§ط±ظٹط© ظپظ‚ط·ط› ظ„ط§ طھظ†ط³ط®ظ‡ ط¥ظ„ظ‰ ظ…ظ„ظپ ط¥ط¹ط¯ط§ط¯ط§طھ ظˆظ„ط§ طھط¶ط¹ ظپظٹظ‡ ظ‚ظٹظ…ظ‹ط§ ط­ظ‚ظٹظ‚ظٹط©.

طھظڈط¶ط§ظپ ط£ط³ط±ط§ط± ط§ظ„ط£طھظ…طھط© ط§ظ„ظ…ط·ظ„ظˆط¨ط© ظ…ظ† **Settings â†’ Secrets and variables â†’ Actions â†’ Secrets** ظپظٹ GitHubطŒ ظ„ط§ ظپظٹ ظ…ظ„ظپط§طھ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط£ظˆ ط³ط¬ظ„ط§طھ CI:

- `COPILOT_GITHUB_TOKEN`: ط§ط®طھظٹط§ط±ظٹ ظ„طھط´ط؛ظٹظ„ ظ…ط³ط§ط±ط§طھ ط§ظ„طھط­ظ‚ظٹظ‚ ط§ظ„ظ…ط¯ط¹ظˆظ…ط© ط¨ظ€Copilot. ط±ط§ط¬ط¹ [ط¥ط¹ط¯ط§ط¯ ظ…ط­ظ‚ظ‚ Copilot](docs/PHASE7_COPILOT_INVESTIGATOR.md) ظ„ظ„طµظ„ط§ط­ظٹط§طھ ط§ظ„ظ…ط·ظ„ظˆط¨ط©.
- `GH_AW_CI_TRIGGER_TOKEN`: ط§ط®طھظٹط§ط±ظٹ ط¥ط°ط§ ط§ط­طھط§ط¬طھ ط£طھظ…طھط© ط¥ظ†ط´ط§ط، PR ط¥ظ„ظ‰ طھط´ط؛ظٹظ„ CIط› ط§ط³طھط®ط¯ظ… ط§ط¹طھظ…ط§ط¯ظ‹ط§ ظ…ط­ط¯ظˆط¯ ط§ظ„طµظ„ط§ط­ظٹط§طھ.
- `GH_AW_GITHUB_TOKEN` ظˆ`GH_AW_GITHUB_MCP_SERVER_TOKEN`: ط§ط®طھظٹط§ط±ظٹط§ظ† ظ„ط¹ظ…ظ„ظٹط§طھ GitHub ط§ظ„طھظٹ طھطھط·ظ„ط¨ طµظ„ط§ط­ظٹط§طھ ط¥ط¶ط§ظپظٹط©ط› طھط³طھط®ط¯ظ… ط§ظ„طھط¯ظپظ‚ط§طھ `GITHUB_TOKEN` ط§ظ„ظ…ط¯ظ…ط¬ ظƒط®ظٹط§ط± ط§ط­طھظٹط§ط·ظٹ ط¹ظ†ط¯ ظ…ظ„ط§ط،ظ…طھظ‡.
- `GH_AW_DEFAULT_OTLP_HEADERS`: ط§ط®طھظٹط§ط±ظٹ ط¥ط°ط§ ط£ظڈط¹ط¯ظ‘ ط¥ط±ط³ط§ظ„ ط¨ظٹط§ظ†ط§طھ ط§ظ„ط±طµط¯ ط¥ظ„ظ‰ OTLP.

ظٹطµط¯ط± GitHub Actions ظ‚ظٹظ…ط© `GITHUB_TOKEN` طھظ„ظ‚ط§ط¦ظٹظ‹ط§ ظ„ظƒظ„ طھط´ط؛ظٹظ„ط› ظ„ط§ طھظ†ط´ط¦ظ‡ط§ ظٹط¯ظˆظٹظ‹ط§. ط¥ط¹ط¯ط§ط¯ Vertex AI ظٹط³طھط®ط¯ظ… ط§طھط­ط§ط¯ ظ‡ظˆظٹط© GitHub Actions ظ…ط¹ Google Cloud ظˆظ„ط§ ظٹط­طھط§ط¬ ظ…ظپطھط§ط­ ط­ط³ط§ط¨ ط®ط¯ظ…ط©. طھظڈط­ظپط¸ ظ…ط¹ط±ظپط§طھ ظ…ط´ط±ظˆط¹ Google ظˆظ…ط²ظˆظ‘ط¯ ط§ظ„ظ‡ظˆظٹط© ظˆط­ط³ط§ط¨ ط§ظ„ط®ط¯ظ…ط© ظƒظ€ **Variables** ط؛ظٹط± ط³ط±ظٹط©. ط±ط§ط¬ط¹ [ط¥ط¹ط¯ط§ط¯ Vertex AI](docs/VERTEX_AI_FALLBACK.md). ظٹظ…ظƒظ† ط¥ط¶ط§ظپط© ظ…طھط؛ظٹط±ط§طھ ط¥ط¹ط¯ط§ط¯ gh-aw ط؛ظٹط± ط§ظ„ط­ط³ط§ط³ط© ظ…ظ† طµظپط­ط© **Variables** ظ†ظپط³ظ‡ط§.

ظ„ط§ طھط¶ط¹ ط§ط¹طھظ…ط§ط¯ظ‹ط§ ط­ظ‚ظٹظ‚ظٹظ‹ط§ ظپظٹ `.env.example` ط£ظˆ ط§ظ„ظ…ط³طھظ†ط¯ط§طھ ط£ظˆ ط§ظ„ط´ظٹظپط±ط©. ط¥ط°ط§ ط³ط¨ظ‚ ظƒط´ظپ ط§ط¹طھظ…ط§ط¯طŒ ط£ط¨ط·ظ„ظ‡ ظˆط¯ظˆظ‘ط±ظ‡ ظ‚ط¨ظ„ ظ…طھط§ط¨ط¹ط© ط§ط³طھط®ط¯ط§ظ…ظ‡.

## ط§ظ„ظ…ط±ط§ظ‚ط¨ط© ط§ظ„ظ…ط­ظ„ظٹط© ط§ظ„ط§ط®طھظٹط§ط±ظٹط©

ظٹطھط¶ظ…ظ† ط§ظ„ظ…ط³طھظˆط¯ط¹ ط¥ط¹ط¯ط§ط¯ظ‹ط§ ظ…ط­ظ„ظٹظ‹ط§ ظ„ظ€Prometheus ظˆGrafana ظˆAlertmanager. Node Exporter ط§ط®طھظٹط§ط±ظٹ ظ„ظ…ط¶ظٹظپ LinuxطŒ ظƒظ…ط§ طھطھظˆظپط± ط¥ط¶ط§ظپط© OpenTelemetry Collector ظ…ط­ظ„ظٹط© ط§ط®طھظٹط§ط±ظٹط© ظ„طھط­ظˆظٹظ„ ظ…ط¬ظ…ظˆط¹ط© ط¶ظٹظ‚ط© ظ…ظ† ظ…ظ‚ط§ظٹظٹط³ OTLP ط¥ظ„ظ‰ Prometheus ط§ظ„ظ…ظˆط¬ظˆط¯. ط®ط¯ظ…ط© WSGI ظٹظ…ظƒظ†ظ‡ط§ ط¥ط±ط³ط§ظ„ Histogram ظˆط§ط­ط¯ ظ„ط²ظ…ظ† ط§ظ„ط·ظ„ط¨ ظ…ط­ظ„ظٹظ‹ط§ ط¨ط¹ط¯ طھظپط¹ظٹظ„ طµط±ظٹط­ط› ط§ظ„ظ‚ظٹط§ط³ ظ…ط¹ط·ظ‘ظ„ ط§ظپطھط±ط§ط¶ظٹظ‹ط§ ظˆط¨ظ„ط§ طھط³ظ…ظٹط§طھ ظ„ظ„ط·ظ„ط¨. ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ط«ط§ط¨طھ ظ„ط§ ظٹظˆظپظ‘ط± ظ†ظ‚ط·ط© `/metrics`. ط±ط§ط¬ط¹ [ط¯ظ„ظٹظ„ OpenTelemetry](docs/integrations/opentelemetry.md) ظ‚ط¨ظ„ طھط´ط؛ظٹظ„ ظ…ظ„ظپ طھط¹ط±ظٹظپ `otel`.

```sh
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f monitoring/compose.yml up --detach
```

ط§ظ„ظˆط§ط¬ظ‡ط§طھ ط§ظ„ظ…ط­ظ„ظٹط©: Prometheus <http://127.0.0.1:9090>طŒ Grafana <http://127.0.0.1:3000>طŒ Alertmanager <http://127.0.0.1:9093>. طھظ‡ظٹط¦ط© OpenTelemetry TLS ظˆط±ظ…ط² ط§ظ„ظˆطµظˆظ„ ط§ظ„ظ…ط­ظ„ظٹ ظˆط¨ط¯ط، ط§ظ„ظ…ظ„ظپ ط§ظ„ط§ط®طھظٹط§ط±ظٹ ظ…ظˆط¶ط­ط© ظپظٹ [ط§ظ„ط¯ظ„ظٹظ„](docs/integrations/opentelemetry.md). ظ„ط¥ط¶ط§ظپط© ظ…ظ‚ط§ظٹظٹط³ Linux:

```sh
docker compose --profile linux-host -f monitoring/compose.yml up --detach
```

ط¹ظ„ظ‰ Docker Desktop ظپظٹ Windows ط£ظˆ macOS ظٹظ‚ظٹط³ Node Exporter ط¢ظ„ط© Docker ط§ظ„ط§ظپطھط±ط§ط¶ظٹط©. ظ„ط§ ظٹط±ط³ظ„ Alertmanager طھظ†ط¨ظٹظ‡ط§طھ ظ„ط®ط¯ظ…ط§طھ ط®ط§ط±ط¬ظٹط©. ط±ط§ط¬ط¹ [ط¯ظ„ظٹظ„ ط§ظ„ظ…ط±ط§ظ‚ط¨ط©](docs/MONITORING.md) ظ„ظ„طھظپط§طµظٹظ„ ظˆط§ظ„ظ‚ظٹظˆط¯ ظˆط§ظ„طھط±ط§ط®ظٹطµ.

ظ„ط¥ظٹظ‚ط§ظپ ط¬ظ…ظٹط¹ ط§ظ„ظ…ظƒظˆظ†ط§طھ ظˆطھظ†ط¸ظٹظپ ظ…طھط؛ظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±:

```sh
docker compose --profile linux-host -f monitoring/compose.yml down
unset GRAFANA_ADMIN_PASSWORD
```

## ط§ظ„ظ†ط´ط±

ط§ظ„ظ†ط´ط± ط§ظ„ط­ط§ظ„ظٹ ط¥ظ„ظ‰ GitHub Pages:

1. ظپظٹ ط¥ط¹ط¯ط§ط¯ط§طھ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط§ظپطھط­ **Settings â†’ Pages** ظˆط§ط®طھط± **GitHub Actions** ظƒظ…طµط¯ط± ظ„ظ„ظ†ط´ط±.
2. ط§ط¯ظپط¹ ط§ظ„طھط؛ظٹظٹط± ط¥ظ„ظ‰ ظپط±ط¹طŒ ظˆط§ظپطھط­ Pull Request ط¥ظ„ظ‰ `main`.
3. ط§ظ†طھط¸ط± ظ†ط¬ط§ط­ ظپط­طµ `validate` ظˆط±ط§ط¬ط¹ ط§ظ„ظ…ط¹ط§ظٹظ†ط© ط§ظ„ظ‚ط§ط¨ظ„ط© ظ„ظ„طھظ†ط²ظٹظ„ ظپظٹ ظ…ظ„ط®طµ CI.
4. ط¨ط¹ط¯ ظ…ط±ط§ط¬ط¹ط© ظˆط¯ظ…ط¬ Pull RequestطŒ ظٹظ†ط´ط± ط³ظٹط± ط§ظ„ط¹ظ…ظ„ ط§ظ„طµظپط­ط© ظ…ظ† `main` ط¨ط¹ط¯ ظ†ط¬ط§ط­ CI.
5. ط±ط§ط¬ط¹ ط±ط§ط¨ط· ط§ظ„ظ†ط´ط± ظˆظ†طھظٹط¬ط© ظپط­طµ ط§ظ„طµط­ط© ظپظٹ GitHub Actions.

ظپط­طµ طµط­ط© ط§ظ„ظ†ط´ط± ظٹظ‚ط±ط£ `deployment.json` ظˆظٹط·ط§ط¨ظ‚ SHA ط§ظ„ظƒط§ظ…ظ„ ظ„ظ„ظ…طµط¯ط±. ط¹ظ†ط¯ ط¹ط·ظ„ ظ†ظ‚ظ„ ظ…ط¤ظ‚طھ ظٹط¹ظٹط¯ ط§ظ„ظ…ط­ط§ظˆظ„ط© 3 ظ…ط±ط§طھ ظƒط­ط¯ ط£ظ‚طµظ‰ ظپظ‚ط· (ظ…ظ‡ظ„ط© ط§طھطµط§ظ„ 5 ط«ظˆط§ظ†ظچ ظˆظ…ظ‡ظ„ط© ط¥ط¬ظ…ط§ظ„ظٹط© 20 ط«ط§ظ†ظٹط© ظ„ظƒظ„ ظ…ط­ط§ظˆظ„ط©طŒ ط¨طھط£ط®ظٹط± ط«ط§ظ†ظٹط© ط«ظ… ط«ط§ظ†ظٹطھظٹظ†)طŒ ظˆظ„ط§ ظٹط¹ظٹط¯ ط§ظ„ظ…ط­ط§ظˆظ„ط© ط¹ظ†ط¯ ط£ط®ط·ط§ط، HTTP ط£ظˆ ط¹ظ†ط¯ ط¹ط¯ظ… طھط·ط§ط¨ظ‚ SHA ط£ظˆ ط¹ظ†ط¯ ط¨ظٹط§ظ† ط؛ظٹط± طµط§ظ„ط­طŒ ظˆظ„ط§ ظٹط¹ط·ظ‘ظ„ ط§ظ„طھط­ظ‚ظ‚ ظ…ظ† TLS ط£ط¨ط¯ظ‹ط§. ط§ظ„ط­ط¯ظˆط¯ ظˆط§ظ„ظ…ط®ط§ط·ط± ط§ظ„ظ…طھط¨ظ‚ظٹط© ظ…ظˆط«ظ‚ط© ظپظٹ [ط¯ظ„ظٹظ„ CI](docs/CI.md).

ظ„ط§ ظٹط­طھط§ط¬ ظ†ط´ط± Pages ط§ظ„ط­ط§ظ„ظٹ ط¥ظ„ظ‰ ط£ط³ط±ط§ط± ظ†ط´ط±ط› طµظ„ط§ط­ظٹط§طھ ط§ظ„ظ†ط´ط± ظˆط¥ط«ط¨ط§طھ ط§ظ„ظ‡ظˆظٹط© طھظڈط¯ط§ط± ط¹ط¨ط± GitHub Actions ظˆOIDC. ط±ط§ط¬ط¹ [ط¯ظ„ظٹظ„ ط§ظ„ظ…ط¹ط§ظٹظ†ط© ظˆط§ظ„ظ†ط´ط± ظˆط§ظ„ط±ط¬ظˆط¹](docs/DEPLOYMENT.md) ظˆ[ط¯ظ„ظٹظ„ CI](docs/CI.md) ظ„ظ„طھظپط§طµظٹظ„.

## ط§ظ„طھط´ط؛ظٹظ„ ظˆط§ظ„طھظˆط«ظٹظ‚

- [CI documentation](docs/CI.md)
- [DevSecOps controls and scope](docs/DEVSECOPS.md)
- [Repository policy audit setup](docs/REPOSITORY_POLICY_AUDIT.md)
- [GitHub Pages DevOps roadmap](docs/GITHUB_PAGES_DEVOPS_ROADMAP.md)
- [AI model strategy](docs/AI_MODEL_STRATEGY.md)
- [AI provider resilience design](docs/AI_PROVIDER_RESILIENCE.md)
- [AI code review setup and limits](docs/AI_CODE_REVIEW.md)
- [Optional local coding-agent tool review](docs/FREE_CLAUDE_CODE_EVALUATION.md)
- [AI investigation acceptance and measured results](docs/INVESTIGATOR_ACCEPTANCE.md)
- [GitHub AI Scan setup and billing](docs/GITHUB_AI_SCAN.md)
- [AI and Agentic Workflow cost controls](docs/GITHUB_CODE_QUALITY_COSTS.md)
- [ظ…ط±ط¬ط¹ ط¥طµط¯ط§ط± Neovim ط§ظ„ظ„ظٹظ„ظٹ ظˆط£طµظˆظ„ظ‡](docs/NEOVIM_NIGHTLY.md)
- [iOS exploit claim triage](docs/IOS_EXPLOIT_CLAIM_TRIAGE.md)
- [Release & rollback runbook](docs/RELEASE_ROLLBACK.md)
- [ط§ظ„ظ†ط´ط± ظˆط§ظ„ط±ط¬ظˆط¹](docs/DEPLOYMENT.md)
- [ط§ظ„ط§ط³طھط¬ط§ط¨ط© ظ„ظ„ط­ظˆط§ط¯ط«](docs/INCIDENT_RESPONSE.md)
- [ط§ظ„ط£ظ…ط§ظ† ظˆط§ظ„ط¥ط¨ظ„ط§ط؛ ط¹ظ† ط§ظ„ط«ط؛ط±ط§طھ](SECURITY.md)
- [Security and code-quality review â€” 2026-11-16](docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md)
- [Stable baseline: v1.0.0](https://github.com/hamedonassar95/Devobs/releases/tag/v1.0.0)

ط¥ط¹ط¯ط§ط¯ AI DevKit ظ„ظ„ظ…ط³ط§ظ‡ظ…ظٹظ† ظˆظ…ط±ط§ط­ظ„ ط§ظ„ط¹ظ…ظ„ ظ…ظˆط«ظ‚ ظپظٹ [ط¯ظ„ظٹظ„ AI DevKit](docs/AI_DEVKIT.md). ظ‡ط°ط§ ط§ظ„ط¥ط¹ط¯ط§ط¯ ظ…ظ†ظپطµظ„ ط¹ظ† طھط´ط؛ظٹظ„ CI/CDط› ظ…ط±ظƒط² ظˆط­ط¯ط§طھ ط§ظ„ط£طھظ…طھط© ط§ظ„ظ‚ط§ط¨ظ„ط© ظ„ط¥ط¹ط§ط¯ط© ط§ظ„ط§ط³طھط®ط¯ط§ظ… ظ…ظˆط¬ظˆط¯ ظپظٹ [ظ…ط±ظƒط² ط§ظ„ط£طھظ…طھط©](docs/AUTOMATION_HUB.md).

- [Manual P01 evidence completeness gate](docs/P01_ACTIVATION_READINESS.md#p01-offline-evidence-gate-review-only): fails closed on missing or stale launch evidence, but cannot approve P01, launch SaaS, or access provider accounts.
- [Keycloak OIDC profile and local-only discovery/JWKS preflight](docs/P01_KEYCLOAK_OIDC_PROFILE.md): a disposable Keycloak 26.8.2 Compose fixture pinned by official Quay digest, loopback-only and without a bootstrap admin. Local HTTP results do not satisfy Devobs's HTTPS issuer policy or establish token compatibility/readiness.
- [P01 Keycloak Docker smoke evidence](docs/P01_KEYCLOAK_DOCKER_SMOKE_EVIDENCE.md): real localhost-only runtime evidence for the pinned Keycloak 26.8.2 image, with the realm imported and the discovery/JWKS preflight passing. Local HTTP still does not establish production issuer readiness.
- [P01 Keycloak HTTPS discovery and JWKS preflight](docs/P01_KEYCLOAK_HTTPS_PREFLIGHT.md): the offline checker targets the exact `https://localhost` issuer on standard port 443; the fixture binds `127.0.0.1:443` to Keycloak's internal HTTPS port 8443 and reuses the strict OIDC metadata verifier. The narrow exception recorded by merged PR #608 is effective only after this reconciliation PR is merged. Until this reconciliation PR is merged, the general secret-handling prohibition remains binding and no Keycloak runtime may start. After activation, every runtime test requires separate explicit owner approval for that run naming the full reviewed source SHA (40-character SHA), a unique Docker Compose project name, and exact test scope. It permits only automatic generation and internal use of disposable realm signing material for synthetic identities, using the pinned image and a local Unix socket Docker context; `ssh://`, `tcp://`, named-pipe, cloud, and remote endpoints are BLOCKED. No private-key inspection/export, credential or token logging, or raw secret-bearing logs are allowed. Live TLS and signed-token acceptance remain NOT_TESTED.

## Graphify integrations (offline, opt-in)

**Canonical:** `tools/graphify` pinned to `graphifyy` 0.9.113, with CLI entry
points `scripts/graphify/multi_repo.py` and
`scripts/graphify/repository_intelligence.py`. Use it for new work:

```sh
python3 scripts/graphify/multi_repo.py validate --manifest assets/graphify/multi_repo_manifest.json
python3 scripts/graphify/repository_intelligence.py verify-wheel --wheel <local-wheel>
python3 -m unittest discover -s tests/graphify -v
```

Privacy controls, provenance and measured local evidence are in
[the Graphify integration design](docs/architecture/graphify-integration.md) and
[repository intelligence](docs/architecture/repository-intelligence.md).

**Legacy:** `scripts/integrations/graphify_portfolio.py` is a backward-compatible
adapter for the earlier 0.9.112 review-only CLI. It contains no orchestration or
subprocess implementation: the behavior lives in `tools/graphify/portfolio.py`
and `tools/graphify/portfolio_execution.py`. It still prints a `DEPRECATED`
notice and identifies the canonical stack in JSON reports. Its historical
provenance and blocked rollout evidence are recorded in
[docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md](docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md).
Migration rules are in
[the consolidation plan](docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md).

```sh
python3 scripts/integrations/graphify_portfolio.py --json
python3 -m unittest discover -s tests -p 'test_graphify_portfolio.py' -v
```
- [Disposable Keycloak public OAuth client](docs/P01_KEYCLOAK_OIDC_PROFILE.md#disposable-local-public-oauth-client): one offline-validated Authorization Code + PKCE S256 client configuration with exact loopback redirects and an opt-in `devobs.read` scope. Live runtime remains NOT_TESTED and requires the reconciliation PR to be merged plus separate per-run owner approval. The exception does not authorize credential or token creation, hosted identity, production changes, paid AI inference, or deployment; P01 remains NO-GO and AI-9 remains BLOCKED.

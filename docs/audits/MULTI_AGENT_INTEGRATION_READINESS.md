# Multi-agent orchestrator integration readiness audit (2026-11-21)

**Audit branch:** `feature/orchestrator-integration-audit`
**Audit base:** `origin/main` `4763f1872ec154be2017cbe841fbaafc48ab5263`
**Implementation under review:** pushed branch `feature/multi-agent-work-orchestrator`, head `ef770c30985802c435ccb771510b04336652d81b`
**Merge base:** `37475b0d9f0b4ad43325809e0b4837116f7bbbfb`
**Branch position:** `main` ahead 2, orchestrator ahead 8
**Scope:** read-only architecture, scheduler, approval-gate, ownership, security, delivery, and test-coverage review. This report and the README link are the only files changed by this audit. No active agent implementation, workflow, policy file, or approval gate was modified.

## 1. Verdict

**INTEGRATION READINESS: NOT READY (VERIFIED).** The pushed orchestrator is a coherent advisory planner with fail-closed unit tests, but it is not integrated into CI or runtime, has no executor or authenticated delivery provider, is two commits behind the audited `main`, and has no pull request or human approval record. Its generated plans are explicitly `DRY_RUN`, `dispatched=False`, `apply=False`, with restricted actions left at `pending_human` (`devobs/orchestration/work_orchestrator.py:159,176-177,322,339-340` on the reviewed branch). No code path starts an agent, opens a socket, launches a subprocess, merges, deploys, or spends money.

The safest classification is therefore: **advisory planning prototype, not an operational orchestrator**. No release gate should be inferred from this audit. The ledger still reports `ai9-detection-quality: BLOCKED`, `codex-agent-runtime-acceptance: OPEN`, and `p01-managed-saas: BLOCKED`.

## 2. What exists today

### 2.1 Wired into CI or runtime (VERIFIED)

| Component | Evidence | Actual status |
| --- | --- | --- |
| `scripts/check_agent_spec.py` | `.github/workflows/ci.yml:291` | Executed by CI; validates static agent-spec policy. |
| `scripts/dispatch_rollback.py` | `.github/workflows/one-click-deploy.yml:211` | Used by the deployment rollback workflow; not a multi-agent dispatcher. |
| Existing agent-related unit tests | `.github/workflows/ci.yml:60-78` delegates `test_path: tests` to `.github/workflows/reusable-python-ci.yml:145-176` | `test_two_agent_tasks.py`, `test_agent_dispatch_preflight.py`, `test_agent_task_status_report.py`, `test_human_approval_gate.py`, and `test_codex_agent_config.py` run in CI. |
| `scripts/human_approval_gate.py::evaluate` | `scripts/recovery_pipeline.py:16,58` | Reused by the recovery pipeline as a deterministic record gate. |
| Scheduled workflow | `.github/workflows/repository-policy-audit.yml:4-5` | Only `cron: "17 8 * * 1"`; does not invoke orchestration. |
| Event workflow | `.github/workflows/repository-dispatch.yml:4` | `repository_dispatch` only; no orchestration consumer. |
| Codex roles | `.codex/config.toml:3-5`, `.codex/agents/devobs_*.toml` | Four task-scoped, read-only roles; `docs/CODEX_AGENT_OPERATING_MODEL.md:3,13` explicitly says they are not background workers. |

A repository-wide search found no `.github/` invocation of `check_two_agent_tasks.py`, `human_approval_gate.py`, `agent_dispatch_preflight.py`, `agent_task_status_report.py`, `work_orchestrator.py`, or `devobs.orchestration`. Their CI presence is unit-test discovery only.

### 2.2 Advisory/offline components on audited `main` (VERIFIED)

- `scripts/check_two_agent_tasks.py:1-10,128-353` validates a JSON task manifest, enforces ownership/conflicts/restricted actions, and returns `PASS/BLOCKED/FAIL` with exit `0/1/2`.
- `scripts/agent_dispatch_preflight.py:16-22,339-416` imports the canonical validator, detects local CLIs with `shutil.which` without invoking them, writes scoped instruction files, and prints human actions; it is `DRY_RUN` only.
- `tools/agent_task_status_report.py:24-34,138-162,217-281` classifies a manifest `PASS` as `PASS_CLAIM_UNVERIFIED`, never as verified runtime evidence, and displays stored commands without executing them.
- `scripts/human_approval_gate.py:19-41` accepts a caller-supplied record and checks `verification_status`, `pr_open`, `pr_merged`, `approver_is_human`, `approver_has_write`, and literal `APPROVE`.
- `agent-spec.yaml:11-124` inventories seven workflow-backed agents with `production_write: false`.
- `scripts/pr_readiness_gate.py`, `scripts/ci_failure_intelligence.py`, and their docs exist on `main` but are not invoked by a workflow.

### 2.3 Additions on the reviewed branch (VERIFIED)

The reviewed branch adds 11 files and `2292 insertions(+)`:

- `devobs/orchestration/task_registry.py` — versioned registry, optimistic `expected_version`, duplicate/dependency checks, and atomic `os.replace` persistence (`:277-469`).
- `devobs/orchestration/conflict_detector.py` — adapter around the canonical validator (`:21-24,92-145`).
- `devobs/orchestration/delivery_tracker.py` — caller-supplied GitHub/CI/approval evidence classifier that reuses the human gate (`:26-28,244-262`).
- `devobs/orchestration/work_orchestrator.py` — dependency-ordered `DRY_RUN` planner with injected capacity and no execution entry point (`:139-182,196-344`).
- `docs/agents/MULTI_AGENT_ORCHESTRATION.md` and four focused test modules.

There are no `.github/workflows` or `.codex` changes on the reviewed branch.

## 3. Scheduler and runtime integration gaps

| Gap | Evidence | Impact | Label |
| --- | --- | --- | --- |
| No scheduler implementation | `origin/feature/scheduler-integration-audit` records `ResourceConstrainedScheduler` as absent (`devobs/scheduling/`, `docs/agents/RESOURCE_SCHEDULER.md`, `tests/test_resource_scheduler.py`); reviewed branch has no scheduler. | Capacity is caller-supplied; no service chooses or dispatches work. | VERIFIED |
| No execution entry point | `tests/test_work_orchestrator.py:170-174` on the reviewed branch asserts the planner has no execution method; docs state no execute/apply/merge/deploy path. | A `PASS` plan is not execution. | VERIFIED |
| No registry-to-preflight/report bridge | No reviewed-branch test imports `build_preflight`, `build_report`, or `check_two_agent_tasks` alongside `TaskRegistry`; `TaskRegistry.to_manifest()` is never consumed outside tests. | The offline components remain separate tools. | VERIFIED |
| No workflow consumer | No `.github/` reference to the new package or the existing advisory scripts. | CI cannot gate on orchestration decisions. | VERIFIED |
| No authenticated delivery provider | `DeliveryEvidence` is caller-supplied (`delivery_tracker.py:1-6,57-74`). | GitHub/CI facts cannot be attested by the package. | VERIFIED |
| Compile scope omits `devobs` | `.github/workflows/ci.yml:75` lists only `["scripts","tests","tools"]`. | Package syntax is covered indirectly by test imports, not directly by CI compilation. | VERIFIED |

## 4. Approval gates and task ownership

**Canonical ownership rules (VERIFIED).** `scripts/check_two_agent_tasks.py::evaluate` is the single reused source for manifest transitions, enabled-agent checks, branch/file conflicts, dependencies, and `pending_human` restrictions. `agent_dispatch_preflight.py`, `agent_task_status_report.py`, `task_registry.py`, `conflict_detector.py`, `delivery_tracker.py`, and the separate approval-gates branch all import or adapt it.

**Known validator weaknesses remain relevant (VERIFIED from the existing audit).** [The two-agent security audit](TWO_AGENT_SECURITY_AUDIT_2026-11-21.md) records disabled owners on terminal tasks, incomplete PR-reference validation, self-asserted evidence, duplicate JSON keys, deep JSON, and shared mutable state among its findings. The new registry does not remove those underlying contract issues; it adds a second state surface with optimistic versioning but no cross-process lock test.

**Human gate limitations (VERIFIED static; impact ASSUMED until used).**

- `scripts/human_approval_gate.py:19-41` trusts caller-supplied booleans and string values; it does not bind an approval to a live GitHub review, a reviewer identity, write authority, or an exact reviewed SHA.
- `human_approval_gate.py:44-56` returns `0` even when the decision is `BLOCKED`. No current workflow calls its CLI, so this is a latent fail-open interface rather than an active CI bypass.
- On the reviewed branch `DeliveryTracker` gates on `approval_status` from the supplied record and blocks agent approval. Without an external authenticated binding, that check cannot prove human authorization.
- The reviewed branch classifies `base_branch` of `main` or `master` as `BLOCKED` (`delivery_tracker.py:38,210-214`). If the intent is staging-only evidence, this should be explicit; otherwise an otherwise complete PR targeting `main` will be falsely blocked.

**Current delivery gate state (VERIFIED).** No open PR exists and no PR exists for the orchestrator branch; therefore `pr_open` cannot be `true`. The only CI run for the reviewed head is a push event with `pull_requests: []`. The gate would be `BLOCKED`/`PENDING HUMAN APPROVAL`, never `HUMAN_APPROVED`.

## 5. Duplicates and divergence

| Concern | Canonical source | Overlap or conflict | Label |
| --- | --- | --- | --- |
| Manifest validation | `scripts/check_two_agent_tasks.py::evaluate` | Imported by five offline components; new registry/validator adapters preserve this canon. | VERIFIED |
| Task ownership | `assigned_agent`, `affected_files`, `branch` in the two-agent contract | `Task.owner` alias in `task_registry.py:70-106`; roles remain fixed to CODEX/OPENCODE. | VERIFIED |
| Human approval | `scripts/human_approval_gate.py::evaluate` | `feature/agent-approval-gates` adds a separate request/digest/fingerprint gate; `pr_readiness_gate.py` is a third readiness signal. No integration exists between them. | VERIFIED |
| Readiness evidence | `scripts/pr_readiness_gate.py` plus its docs on `main` | The reviewed branch deletes these files and the newer CI-failure-intelligence files when compared with current `main`. | VERIFIED |
| Planning/capacity | None on `main` | `WorkOrchestrator` fills a real gap, but remains advisory. | VERIFIED |

**Divergence blocker (VERIFIED).** `git merge-base` is `37475b0d…`; `git rev-list --left-right --count` is `2	8`. Merging the reviewed branch as-is into current `main` would remove `scripts/pr_readiness_gate.py`, `scripts/ci_failure_intelligence.py`, their tests/docs, and README sections added by the two newer `main` commits. That deletion requires an explicit owner decision, not an incidental rebase.

## 6. Security review

**Positive controls (VERIFIED).**

- `AGENTS.md:48-56` prohibits direct pushes to `main`, merge/deploy without approval, unapproved billing/AI, and agent self-approval.
- `.codex/config.toml:3-11` enables two concurrent threads per session with only a public read-only documentation MCP; all four role files are read-only and forbid edits, merges, deploys, secrets, and self-approval.
- No `socket`, `subprocess`, `urllib`, `requests`, or process/network call was found in the reviewed orchestration package or its imported helpers.
- Plans always set `mode=DRY_RUN`, `dispatched=False`, `apply=False`, and `merge/deploy/billing/production=pending_human`.
- CI uses least-privilege token settings for the Python job (`.github/workflows/ci.yml:26-28,68-78`); no unpinned third-party actions were found in the inspected scope.

**Gaps (VERIFIED unless noted).**

1. **No authorization binding.** The human gate checks fields supplied by the caller, not GitHub review state or exact SHA binding.
2. **Latent fail-open CLI.** `human_approval_gate.main()` returns `0` on `BLOCKED`; currently unused by workflows.
3. **Partial redaction.** `redact_secrets()` is applied to orchestrator events and `evidence_excerpt`, but `DeliveryUpdate.pr_reference`, task IDs, check names, and reasons use `sanitize_display()` only; `sanitize_display()` removes ANSI/control characters but does not redact token-like text. Existing tests cover only `notes`.
4. **Protected-branch false block.** `main`/`master` bases are classified `BLOCKED` by design, with a test asserting it; intent is undocumented.
5. **Ruleset enforcement UNVERIFIED.** Public branch data showed `main` marked protected but classic protection `enabled:false` with required checks `enforcement_level:"off"`; repository rulesets were not queried. Do not treat a configuration response as proof of enforced gates.
6. **Runtime truth ASSUMED.** Capacity and delivery evidence are supplied by callers; the package cannot attest to systems it never contacts.

Official field references: [list pull requests](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests), [get a branch](https://docs.github.com/en/rest/branches/branches?apiVersion=2022-11-28#get-a-branch), [list workflow runs](https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2022-11-28#list-workflow-runs-for-a-repository), and [workflow `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).

## 7. Test coverage and fresh verification

All commands below were run in this audit session. `python` is the correct interpreter on this Windows host; `python3` is unavailable.

```text
$ python scripts/milestone_ledger.py --summary
{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}
LEDGER_EXIT=0

$ python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
Ran 26 tests in 1.666s
OK
TWO_AGENT_EXIT=0

$ python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
Ran 15 tests in 5.550s
OK
DISPATCH_EXIT=0

$ python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
Ran 8 tests in 1.090s
OK
REPORT_EXIT=0

$ python -m unittest discover -s tests -p "test_human_approval_gate.py" -v
Ran 10 tests in 0.001s
OK
APPROVAL_EXIT=0

$ python -m unittest discover -s tests -p "test_codex_agent_config.py" -v
Ran 5 tests in 0.015s
OK
CONFIG_EXIT=0
```

The four reviewed-branch suites were run from their existing worktree at `C:\DevProjects\Devobs\.worktrees\feature-multi-agent-work-orchestrator` against the exact reviewed head:

```text
$ python -m unittest discover -s tests -p "test_work_orchestrator.py" -v
Ran 13 tests in 0.030s
OK
ORCH_EXIT=0

$ python -m unittest discover -s tests -p "test_task_registry.py" -v
Ran 10 tests in 0.041s
OK
REGISTRY_EXIT=0

$ python -m unittest discover -s tests -p "test_conflict_detector.py" -v
Ran 9 tests in 0.013s
OK
CONFLICT_EXIT=0

$ python -m unittest discover -s tests -p "test_delivery_tracker.py" -v
Ran 16 tests in 0.045s
OK
DELIVERY_EXIT=0
```

**Coverage gaps (VERIFIED).**

- No end-to-end test from registry → canonical validator → preflight → status report → plan.
- No test binds any component to a workflow or runtime consumer.
- No cross-process concurrency/file-lock test for `TaskRegistry._persist()`.
- No real GitHub/CI payload test for `DeliveryTracker`; all cases are synthetic mappings/dataclasses.
- No CLI test for `human_approval_gate.main()` file-read/JSON-error path.
- No test for integration between `feature/agent-approval-gates` and orchestration/delivery.
- `test_codex_agent_config.py` checks TOML structure and strings; it explicitly does not prove agents ran or that instructions enforce permissions.

Passing unit tests establish the listed function-level behavior only. They are not evidence of runtime dispatch, PR-event CI, or human approval.

## 8. Prioritized integration checklist (advisory only)

| Priority | Action | Guardrail |
| --- | --- | --- |
| P0 | Resolve the 2-behind divergence and obtain an explicit owner decision on the newer `main` files the branch deletes. | No force-push or silent deletion of readiness/CI-intelligence work. |
| P0 | Open a Draft PR for an exact reviewed SHA and run PR-event CI; then bind human approval to that PR, reviewer identity, write authority, and SHA. | No merge, deployment, or release-gate promotion from a push-only run. |
| P1 | Choose one canonical approval model and one canonical readiness-evidence model; document which of `human_approval_gate`, `feature/agent-approval-gates`, and `pr_readiness_gate` wins. | Do not stack inconsistent gates without an owner-approved contract. |
| P1 | Add a fail-closed CLI exit code to `human_approval_gate.main()` and a test for it. | Preserve advisory semantics until explicitly wired. |
| P1 | Apply `redact_secrets()` to every exported `DeliveryUpdate` field, not only `notes`/`evidence_excerpt`. | No secrets in reports, logs, or Git. |
| P1 | Add one end-to-end offline test for registry → validator → preflight → report → plan. | Keep it local, synthetic, and non-dispatching. |
| P2 | Decide and document the `main`/`master` delivery-block policy. | Do not weaken protected-branch policy without review. |
| P2 | Add `devobs` to compile scope only if the package is accepted; add a cross-process registry concurrency test. | Requires a separate reviewed code/CI change. |
| P2 | Add an authenticated evidence provider if delivery status must be live. | No credentials or production calls in this audit. |

No implementation change is authorized by this report. Each item needs a separate reviewed PR and, where applicable, explicit owner approval.

## 9. Delivery status

- **Draft PR for this audit:** BLOCKED. `gh` is unavailable (`GH_UNAVAILABLE`); the only remote is the public HTTPS URL. No authenticated local PR-creation method was available.
- **PR handoff:** https://github.com/hamedonassar95/Devobs/pull/new/feature/orchestrator-integration-audit
- **Orchestrator branch PR:** none. Public `GET /pulls?state=open&per_page=100` returned `[]`; `GET /pulls?head=hamedonassar95:feature/multi-agent-work-orchestrator&state=all` returned `[]`.
- **Orchestrator CI:** one run, ID `44893755867`, head SHA `ef770c30985802c435ccb771510b04336652d81b`, `event=push`, `status=completed`, `conclusion=success`, `pull_requests: []`. [Run](https://github.com/hamedonassar95/Devobs/actions/runs/44893755867) · [API](https://api.github.com/repos/hamedonassar95/Devobs/actions/runs/44893755867)
- **PR-event CI:** UNVERIFIED — no PR exists.
- **Audit-branch CI:** not available at report-writing time; status must be checked after the push by exact head SHA.

A push-event success is not a PR gate and does not authorize a merge.

## 10. Summary, diff, checks, assumptions

**Summary:** advisory orchestration is well-structured and unit-tested, but integration readiness is NOT achieved. The critical blockers are divergence from `main`, absence of any runtime/CI consumer, absence of authenticated delivery and approval binding, duplicate approval/readiness contracts, and no PR or human approval.

**Audit diff stat:**

```text
 README.md                                        |   2 +
 docs/audits/MULTI_AGENT_INTEGRATION_READINESS.md | 233 +++++++++++++++++++++++
 2 files changed, 235 insertions(+)
```

**Documentation check:** no repository-wide Markdown link checker is installed. A standard-library relative-link scan over the two changed files was used instead; it checks local relative targets and HTTPS scheme syntax but does not fetch every external destination.

```text
links_checked=183 invalid_targets=0
LINKCHECK_EXIT=0
```

**Checks not run:** full Python suite; live Codex/OpenCode runtime; PR-event CI; authenticated GitHub review/ruleset checks; Docker/Keycloak test; cloud, Render, Supabase, PostgreSQL, deployment, terraform, or paid AI actions; OpenArt generation; MCP handshake; actual agent dispatch. The historical full-suite baseline failures were not re-run.

**Open assumptions:** caller-supplied capacity and delivery evidence are truthful; public GitHub REST data was current at audit time; no hidden authenticated PR exists outside the public API view; the reviewed branch would discover its tests under current CI if merged, but no exact-SHA PR-event run exists to confirm it.

**Compliance:** no secret, token, environment value, deployment setting, production account, customer data, private key, or raw secret-bearing log was read or printed. No agent was dispatched; no merge, push to `main`, deploy, force-push, IAM change, cloud command, paid inference, scheduled work, or terraform apply was performed. The Keycloak disposable-runtime exception was not activated. Human approval remains required before any merge.

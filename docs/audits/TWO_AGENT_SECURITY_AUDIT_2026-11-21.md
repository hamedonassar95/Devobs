# Two-agent coordination foundation — independent security and reliability audit (2026-11-21)

**Audited revision:** `2d385b2b8cf2cce8a20944a72f5165aa17f2186c` (`origin/main` after
`git fetch origin main`; this is also the merge commit of PR #727).
**Audited change:** [PR #727](https://github.com/hamedonassar95/Devobs/pull/727),
exact head `d1131fd5e9e6f37e797727e6fbf4a623bacadd7c`.
**Working branch:** `feature/agent-coordination-security-audit`, created from the
audited revision in this session's isolated worktree. No other branch or worktree
was switched, modified, pushed or merged.
**Scope:** read-only inspection of `AGENTS.md`, `STATE.md`,
`docs/MILESTONE_LEDGER.json`, `docs/CODEX_AGENT_OPERATING_MODEL.md`,
`docs/agents/TWO_AGENT_COORDINATION.md`, `scripts/check_two_agent_tasks.py` and
`tests/test_two_agent_tasks.py`, plus fresh local verification and public CI
evidence. The only file added by this audit is this report. No application code,
CI workflow, agent dispatch file, permission, identity, hosted resource or secret
was created, read, modified or activated.

**Post-audit resolution (2026-11-21, VERIFIED):** AUD-02 was fixed by
[PR #732](https://github.com/hamedonassar95/Devobs/pull/732), merged from exact
head `4d192aa1c917c4ffe6a1901fd6ea01c3f23319f0` as
`37475b0d9f0b4ad43325809e0b4837116f7bbbfb` at `2026-11-21T03:54:16Z`.
Exact-head [CI 44863216408](https://github.com/hamedonassar95/Devobs/actions/runs/44863216408)
and exact-merge [CI 44863441002](https://github.com/hamedonassar95/Devobs/actions/runs/44863441002)
completed `success`; the exact-head run reports 12 jobs (9 succeeded, 3
scope-skipped). The fix adds `blocked` to `OWNED_STATUSES`/`RUNNING_STATUSES`,
reports `task_blocked` with `BLOCKED`/exit `1`, and adds five regression tests.
This historical report is preserved as the audited-revision record; AUD-02 is
resolved at selected base `4763f1872ec154be2017cbe841fbaafc48ab5263`, while
AUD-01 and AUD-03 through AUD-14 remain separate. This reconciliation changes
no validator behavior.

**Evidence labels:** **VERIFIED** = command output, repository source or public
API response recorded in this report; **INFERRED** = reasoned from verified
source with no runtime reproduction; **UNKNOWN** = not established by available
evidence. These correspond to the requested VERIFIED / INFERRED / UNKNOWN
classification.

**Official references used:**

- GitHub REST, get a pull request: <https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request>
- GitHub REST, list pull-request files: <https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files>
- GitHub REST, list check runs for a Git reference: <https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference>
- GitHub REST, list workflow runs for a repository (`head_sha`, `status`, `conclusion`): <https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository>
- GitHub REST, list jobs for a workflow run (`name`, `status`, `conclusion`): <https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run>
- GitHub REST, list issue comments: <https://docs.github.com/en/rest/issues/comments#list-issue-comments>
- Git reference-name rules (`git check-ref-format`): <https://git-scm.com/docs/git-check-ref-format>
- Windows file-name/case semantics: <https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>

## 1. Executive summary

- **PR #727 is VERIFIED merged** into `main` at `2d385b2…` on
  `2026-11-21T02:39:25Z`; the changed scope is 5 files, `+826 / −0`. Exact-head
  and exact-merge CI both passed their required checks. This is source/CI
  evidence, not proof that either agent ever ran.
- **No Critical finding; one High (AUD-02), resolved after this audit by PR
  #732.** The checker is an offline advisory validator: it makes no network
  call, starts no agent, executes no
  manifest-supplied command and grants no merge/deploy/billing/production
  authority. The High rating describes a bypass of an *advertised* safeguard,
  not code execution or production impact.
- **Five Medium findings (AUD-01, AUD-03, AUD-04, AUD-05, AUD-12):** completion
  evidence and transition history trust self-asserted manifest fields; disabled
  agents can own terminal tasks; branch strings are not validated as Git refs;
  and PR references are not bound to the task's repository.
- **Five VERIFIED Low findings** (case-sensitive path collisions, caller-supplied
  repository allowlist, stale PR narrative SHA, uncaught `RecursionError` on
  deeply nested JSON, silently collapsed duplicate JSON keys) **plus one
  INFERRED reliability risk** (no shared state/lock between concurrent manifest
  writers; `complete` immediately releases declared file/branch ownership).
- The three release gates are unchanged and were not re-evaluated as passed:
  **P01 BLOCKED / NO-GO, AI-9 BLOCKED, Codex runtime OPEN**
  (VERIFIED from `python scripts/milestone_ledger.py --summary`).
- **Next recommended fix at the audited revision:** AUD-02 first (a `blocked`
  task must report `BLOCKED` and remain in ownership checks), then
  AUD-01/AUD-12 (self-asserted evidence and history), in separate owner-reviewed
  PRs with regression tests. PR #732 completed the AUD-02 item after this audit;
  this report itself still did not change those files.

## 2. Baseline, merge verification and CI evidence

| Item | Evidence | Result | Label |
| --- | --- | --- | --- |
| Latest `origin/main` | `git fetch origin main`; `git rev-parse origin/main` | `2d385b2b8cf2cce8a20944a72f5165aa17f2186c` | VERIFIED |
| PR #727 state | public `GET /repos/hamedonassar95/Devobs/pulls/727` | `state=closed`, `merged=true`, `merged_at=2026-11-21T02:39:25Z`, `merge_commit_sha=2d385b2…`, base `main` at `799efe6…` | VERIFIED |
| PR #727 head | same API response | `head.sha=d1131fd5e9e6f37e797727e6fbf4a623bacadd7c`, branch `feature/two-agent-coordination`, 4 commits | VERIFIED |
| PR #727 scope | public `GET /pulls/727/files` | `README.md` +18, `docs/CODEX_AGENT_OPERATING_MODEL.md` +15, `docs/agents/TWO_AGENT_COORDINATION.md` +174, `scripts/check_two_agent_tasks.py` +350, `tests/test_two_agent_tasks.py` +269; total `+826 / −0` | VERIFIED |
| Milestone ledger | `python scripts/milestone_ledger.py --summary` (exit `0`) | `latest_pr: 717`, `merged_milestones: 304`, gates `ai9-detection-quality: BLOCKED`, `p01-managed-saas: BLOCKED`, `codex-agent-runtime-acceptance: OPEN` | VERIFIED |
| Duplicate-work check | `docs/MILESTONE_LEDGER.json`, `docs/audits/`, grep across `docs/` | No prior audit of the two-agent contract; ledger's latest recorded PR is #717, so #727 is not yet reconciled. This report does not amend the ledger. | VERIFIED |
| Focused unit tests | `python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v` (exit `0`) | `Ran 21 tests`, `OK`, 0 failures/errors/skips | VERIFIED |
| Adversarial probes | in-memory and `tempfile`-only Python probes of `evaluate()`/`main()` in this session | multiple crafted manifests accepted or misclassified; see sections 3 and 5 | VERIFIED |
| Patch hygiene | `git diff --check` (exit `0`) | no whitespace errors | VERIFIED |

**Exact-head CI (`d1131fd5…`, 32 public check runs): VERIFIED.** `validate` SUCCESS in
[runs 44856665216](https://github.com/hamedonassar95/Devobs/actions/runs/44856665216) and
[44856669816](https://github.com/hamedonassar95/Devobs/actions/runs/44856669816); Python 3.12,
`security`, `postgres-rls`, `terraform-validate`, `site-contract`, `change-impact`, container
build/smoke/scan and `node-tests` SUCCESS (Node skipped in one workflow by path selection);
[CodeQL](https://github.com/hamedonassar95/Devobs/runs/136700554504) SUCCESS ("No new alerts in
code changed by this pull request"); Vercel preview Ready. `production-release`,
`controlled-incident-drill` and `Advisory PR-Agent review` SKIPPED by scope. These checks
establish repository-level code quality only.

**Exact-merge CI (`2d385b2…`, 25 runs): VERIFIED.** In
[run 44857083109](https://github.com/hamedonassar95/Devobs/actions/runs/44857083109),
`validate`, Python 3.12/3.15, `node-tests`, `security`, `postgres-rls`, `terraform-validate`,
`site-contract`, container scan, Pages publish and `verify-production` SUCCESS; CodeQL
`Analyze (python/actions/javascript-typescript)` SUCCESS; incident drill and `claude`/`triage`
SKIPPED.

**Independent review gap (VERIFIED):** public PR comments show the `Advisory Codex review`
workflow succeeded but model inference was skipped because budget approval is absent; the
ChatGPT Codex Connector's cloud review **Failed** on head `d1131fd5…` ("You have reached your
Codex usage limits for code reviews"), with `security_review` status `null` (never run). No
billable inference, review retry or dispatch was performed here. A human review remains
necessary; this document is that read-only independent review.

## 3. Findings

| ID | Severity | Classification | Finding |
| --- | --- | --- | --- |
| AUD-01 | Medium | VERIFIED | `complete` status is accepted from self-asserted `PASS` evidence and an arbitrary 40-hex SHA; no command is executed and no SHA/PR is checked |
| AUD-02 | High | VERIFIED | `blocked` tasks yield `PASS` and are excluded from concurrent file/branch ownership checks, defeating two advertised safeguards with a legal status |
| AUD-03 | Medium | VERIFIED | A disabled/non-worker agent can own a `complete` or `blocked` task and the overall decision can still be `PASS` |
| AUD-04 | Medium | VERIFIED | Branch names such as `feature/../main` and `feature//x` pass validation; ownership conflicts use exact string equality |
| AUD-05 | Medium | VERIFIED | `pr_reference` may point at any GitHub repository, independent of the task's repository |
| AUD-06 | Low | VERIFIED | Path collision checks are case-sensitive although the documented host is Windows |
| AUD-07 | Low | VERIFIED | Repository allowlist is caller-supplied and accepts patterns such as `../..` |
| AUD-08 | Low | INFERRED | No lock, prior-state comparison or shared store protects concurrent manifest writers; `complete` releases file/branch ownership |
| AUD-09 | Low | VERIFIED | PR body's reported local-verification SHA differs from the merged head SHA |
| AUD-10 | Info | VERIFIED | Positive controls: fail-closed parsing, bounded inputs, human-gate enforcement and dependency/cycle checks work as documented |
| AUD-11 | Info | VERIFIED | Merge/CI evidence does not establish agent runtime, truthful evidence, hosted readiness or release-gate promotion |
| AUD-12 | Medium | VERIFIED | `previous_status` is self-asserted in the same record; transition checks prove internal consistency only, not real history |
| AUD-13 | Low | VERIFIED | Deeply nested JSON raises uncaught `RecursionError`: CLI exits `1` (documented as `BLOCKED`) with empty stdout instead of `FAIL` JSON |
| AUD-14 | Low | VERIFIED | Duplicate JSON keys are silently collapsed (last wins), so raw text can show a different status/owner than the evaluated object |

### AUD-01 — Self-asserted completion evidence (Medium, VERIFIED)

**Evidence.** `scripts/check_two_agent_tasks.py:215-239` checks only the *shape*
of `source_sha`, `commands`, `result` and `evidence`; `:235-237` requires a
non-empty string and `PASS` for `complete`, but never runs a command or checks
that the SHA/PR exists. `docs/agents/TWO_AGENT_COORDINATION.md:142-145` explicitly
states the checker cannot prove an agent ran or that evidence is truthful.
Fresh probe: a `complete` task with
`source_sha="dddddddddddddddddddddddddddddddddddddddd"`,
`commands=["echo FABRICATED_PASS"]` and evidence
`"FABRICATED evidence: tests passed without execution"` returned
`{"decision": "PASS", ...}` from `evaluate()` and exit `0` from `main()`.

**Impact.** A false `complete` record unlocks every dependent task
(`:89-101`, `:278-284`) and removes its files/branches from conflict detection
(`:32`, `:289-294`). This is a *misleading human operator* risk, not code
execution: the manifest is data and no command in it is ever run.

**Recommendation.** Do not present `PASS` evidence as verified. Require a
structured attestation (for example CI run ID + exact head SHA + check
conclusion captured by the trusted operator, and a separate human sign-off),
and compare `source_sha` against the operator's checked-out `HEAD` passed as an
explicit CLI argument. Keep the checker offline; do not add network calls or
agent dispatch to validate evidence.

### AUD-02 — `blocked` tasks bypass decision and ownership safeguards (High, VERIFIED)

**Evidence.** `docs/agents/TWO_AGENT_COORDINATION.md:110-114` documents
`BLOCKED` / exit `1` as "Valid contract, but a task is blocked or ownership
conflicts exist." The implementation skips every task whose status is
`complete` **or** `blocked` at `scripts/check_two_agent_tasks.py:275-277`, and
`blocked` is also absent from `OWNED_STATUSES` at `:32`, which gates both
conflict loops at `:289-294`. Two fresh probes:

```text
BLOCKED_ONLY
{'decision': 'PASS', 'errors': [], 'blocked_tasks': [], 'conflicts': [],
 'summary': {'tasks': 1, 'repositories': 1,
             'enabled_agents': ['CODEX', 'OPENCODE'], 'complete': 0}}

BLOCKED_CONFLICT (TASK-001 CODEX blocked + TASK-002 OPENCODE in_progress,
both declaring shared.py)
{"blocked_tasks": [], "conflicts": [], "decision": "PASS"}
```

`in_progress → blocked` is an allowed transition (`:27`), so this needs no
malformed input. The disabled-agent check at `:279-281` is skipped for the same
reason (see AUD-03).

**Impact.** A blocked task disappears from the operator-facing `blocked_tasks`
list and a manifest containing blocked work exits `0`. More seriously, a worker
can declare a shared file `blocked` and keep editing it while another worker
actively edits the same file, with **no** `concurrent_file_ownership` conflict.
This defeats the core advertised concurrent-worker guard with a legal status
value. Impact is misleading coordination evidence, not repository writes by the
checker.

**Recommendation.** Report every `status="blocked"` task in `blocked_tasks`
(e.g. reason `task_blocked`) and return `BLOCKED`; keep `complete` excluded.
Retain `blocked` tasks in ownership-conflict detection until an explicit
ownership-release marker exists, and apply the enabled-agent check to all
statuses. Add regression tests for both probes above, including exit `1`.
This is the smallest high-value source fix.

### AUD-03 — Disabled agent can own terminal tasks (Medium, VERIFIED)

**Evidence.** `docs/agents/TWO_AGENT_COORDINATION.md:84` says `assigned_agent`
"must exist in `agents` and be enabled." Validation at
`scripts/check_two_agent_tasks.py:184-188` only checks registration. The
enabled-agent check at `:279-281` is inside the loop that skips `complete` and
`blocked` tasks (`:275-277`). Probe: adding
`"FUTURE": {"enabled": false}` and assigning a `complete` task to `FUTURE`
returned `PASS` with `summary.enabled_agents == ["CODEX", "OPENCODE"]`, so the
disabled owner is not even visible in the summary.

**Impact.** Finished or blocked work can be attributed to an identity that the
contract says is unusable, while the decision remains `PASS`.

**Recommendation.** Enforce `enabled` for every assigned agent independent of
task status, or change the contract to permit historical references and add a
clear `summary.disabled_task_agents` field. Add a test for the terminal-status
case; the existing test at `tests/test_two_agent_tasks.py:196-208` covers only
`planned`.

### AUD-04 — Branch strings are not validated as Git refs (Medium, VERIFIED)

**Evidence.** `BRANCH_RE` at `scripts/check_two_agent_tasks.py:49` matches
`feature/../main` and `feature//x` because the suffix character class permits
dots and repeated slashes. Git's official ref-format rules prohibit `..` and
consecutive slashes (<https://git-scm.com/docs/git-check-ref-format>). Probes
c1-c3 in the QA evidence returned `PASS` for `feature/../main`, `feature//x`
and for two active tasks on `feature//x` versus `feature/x`; `:305` compares
branch strings only by exact equality, so the near-duplicate branches did not
raise `concurrent_branch_ownership`.

**Impact.** The branch-ownership guard can be evaded by syntactically different
spellings, and the documented "feature/fix/docs/chore branch" constraint is
weaker than Git's own rules. The checker never writes refs, so impact is
misleading coordination state rather than repository corruption.

**Recommendation.** Validate each suffix segment against a stricter pattern
(reject empty segments, `.`, `..`, leading/trailing dot, `..` anywhere) and
normalise/casefold branch keys before comparison. Add negative tests for the
three probe strings.

### AUD-05 — PR reference not bound to the task repository (Medium, VERIFIED)

**Evidence.** `PR_RE` at `scripts/check_two_agent_tasks.py:50-52` accepts any
`https://github.com/<owner>/<repo>/pull/<n>`; `:240-242` performs no comparison
with `task["repository"]`, whereas dependencies *are* repository-checked at
`:265-266`. Probes: a `complete` Devobs task with
`pr_reference="https://github.com/other-owner/other-repo/pull/999"` returned
`PASS`; `#0`, a 100-digit PR number, and
`https://github.com/other/x/pull/0` were also accepted (`decision: PASS`,
`errors: []`). The existing `complete()` test helper always uses `#123`, so
none of this is tested (`tests/test_two_agent_tasks.py:52-62`).

**Impact.** Completion evidence can cite an unrelated PR, further weakening the
already self-asserted completion claim (AUD-01).

**Recommendation.** Parse the URL and require its owner/repo to match the task's
repository. Require a positive, bounded PR number. For the `#number`
shorthand, require an explicit repository field or record that the number refers
to the task repository by convention.

### AUD-06 — Case-sensitive path conflicts (Low, VERIFIED)

**Evidence.** `_normal_path()` at `scripts/check_two_agent_tasks.py:59-71`
normalises `\\` to `/` and strips `./` but preserves case. Conflict detection at
`:299` intersects raw normalised strings. Probe: two active tasks claiming
`Shared/Module.py` and `shared/module.py` returned `PASS`. The documentation
explicitly targets Windows hosts (`docs/agents/TWO_AGENT_COORDINATION.md:128-130,165-170`),
where file-name lookup is typically case-insensitive
(<https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>).

**Impact.** On a case-insensitive filesystem, two workers can declare ownership
of the same physical file without a conflict being reported.

**Recommendation.** Compare path keys using `casefold()` (portable, also safer
on case-sensitive hosts) and add a case-only collision regression test.

### AUD-07 — Caller-supplied repository allowlist (Low, VERIFIED)

**Evidence.** `scripts/check_two_agent_tasks.py:133-142` accepts 1-50 arbitrary
`owner/repo` strings and `:182` accepts a task in any of them. A manifest with
`repositories=["../.."]` and a task in `"../.."` returned `PASS` (fresh probe).
The checker is never told the actual checkout remote.

**Impact.** A manifest can authorise work in unrelated repositories, or in a
string that is not a repository at all. Because the tool is advisory and never
writes files, this is a documentation/trust-boundary weakness only.

**Recommendation.** Add an operator-supplied `--expect-repository` check (or a
pinned constant) so `PASS` means "valid for *this* checkout", and tighten
`REPO_RE` to reject `.`/`..` components.

### AUD-08 — No shared concurrency state (Low, INFERRED)

**Evidence (source).** `OWNED_STATUSES` excludes `complete` and `blocked`
(`scripts/check_two_agent_tasks.py:32`); conflict checks only compare tasks in
that set (`:289-308`); `evaluate()` is stateless and returns immediately
(`:125-318`). The docs acknowledge the tool "cannot prove ... that files were
not changed outside the declared paths" (`:142-145`).

**Inference.** Two workers editing one manifest concurrently can each observe a
locally valid `PASS` with no lock or prior-manifest hash check, and a new task
can reuse a completed task's file without declaring a dependency. This was
**not** reproduced with a real multi-writer runtime, so it is INFERRED, not a
claimed exploit.

**Recommendation.** Keep one manifest per worker and merge via a reviewed,
hash-checked step; or add a `previous_manifest_sha` field verified against the
operator-provided prior file. Do not add file locking to a tool whose stated
contract is offline and read-only without a separate threat model.

### AUD-09 — Stale SHA in PR narrative (Low, VERIFIED)

**Evidence.** The PR #727 body states "Repo branch head at verification:
`21890b77d5b2848d952c9e8ab8927637a5b6ceb9`"; the merged head reported by the
same public API is `d1131fd5…`. **VERIFIED.** This is a four-commit PR, so the
branch advanced after that narrative was written.

**Impact.** The locally reported `PASS` in the PR body is not bound to the merged
tree. Exact-head CI on `d1131fd5…` did pass, so no current check is invalidated;
the observation is about evidence hygiene.

**Recommendation.** Record exact head/merge SHAs in the final PR description
after the last push, or generate the evidence block from the checked-out SHA.

### AUD-10 — Positive controls (Informational, VERIFIED)

The fresh suite passes 21/21 (`OK`, exit `0`) and the source confirms the
documented behaviour for ordinary malformed input: exact top-level/task key
sets (`:128-130`, `:172-173`), bounded manifest size/collections (`:35`,
`:133-165`, `:191-233`), invalid JSON/OSError/ValueError → `FAIL` exit `2`
(`:328-336`), unknown decisions → `2` (`:346`), duplicate IDs and dependency
cycles/unknown/cross-repository dependencies (`:178-181`, `:260-268`),
restricted approval values and task actions (`:157-161`, `:243-249`), unsafe
path spelling rejection (`:59-71`), self-dependency rejection (`:206-207`) and
caller-manifest non-mutation (`:170-171`; test at
`tests/test_two_agent_tasks.py:228-232`). No network, Git write, credential
read or scheduler call appears in the source. This "fail-closed" claim is
qualified by AUD-13: `RecursionError` is not among the caught exceptions.

### AUD-11 — Evidence limits / unchanged gates (Informational, VERIFIED)

Passing CI and this audit do **not** prove that CODEX or OPENCODE actually ran,
that manifest evidence is truthful, that a branch was protected, or that files
were not changed outside declared paths
(`docs/agents/TWO_AGENT_COORDINATION.md:142-145`). No agent was started here.
The ledger still reports P01 BLOCKED / NO-GO, AI-9 BLOCKED and Codex runtime
OPEN; the offline contract does not change them
(`docs/CODEX_AGENT_OPERATING_MODEL.md:22-28`,
`docs/agents/TWO_AGENT_COORDINATION.md:132-140`).

### AUD-12 — Transition history is self-asserted (Medium, VERIFIED)

**Evidence.** `scripts/check_two_agent_tasks.py:209-214` compares `status` with
`previous_status`, but both live in the same mutable record; the map at `:24-31`
is the only source of truth. Fresh probe:
`COMPLETE_PREV evidence_ready PASS []`; `blocked`, `planned` and `none` each gave
`FAIL ['disallowed status transition']`. A worker can jump straight to `complete`
by *claiming* `previous_status="evidence_ready"`; no such state need have existed.
The docs at `docs/agents/TWO_AGENT_COORDINATION.md:95-106` call transitions
"enforced", which overstates a single-record shape check.

**Impact.** Status history is not tamper-evident; with AUD-01, `complete` is purely
declarative. No direct production effect.

**Recommendation.** Validate against a prior trusted manifest revision or
operator-supplied event history, not a field in the same record; until then,
document transitions as shape checks and test "well-formed claim" vs "observed
transition".

### AUD-13 — Deeply nested JSON crashes with a misleading exit code (Low, VERIFIED)

**Evidence.** `main()` at `scripts/check_two_agent_tasks.py:328-336` catches
`OSError`, `UnicodeError` and `ValueError`, not `RecursionError`. Fresh CLI probe,
5,000 nested arrays in an OS temp file:
`DEEP_CLI_RC 1 STDOUT_LEN 0 STDERR_HEAD RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string`.
Depth 2,000 produced `FAIL` JSON; 5,000 and 10,000 crashed. Docs define exit `1`
as `BLOCKED` (`TWO_AGENT_COORDINATION.md:110-114`), so an exit-code wrapper
mislogs a parser crash as a blocked task.

**Impact.** A malformed manifest changes the decision category and emits no JSON.

**Recommendation.** Catch `RecursionError`/`MemoryError` in `main()` and emit `FAIL`
JSON with exit `2`; optionally bound nesting before parsing. Keep the size bound (`:35`).

### AUD-14 — Duplicate JSON keys are silently collapsed (Low, VERIFIED)

**Evidence.** `json.loads` at `scripts/check_two_agent_tasks.py:331` keeps the last
duplicate key. Raw text containing `"status": "evidence_ready", "status": "complete"`
parsed as `complete` and produced
`DUP_EVAL {"decision": "PASS", ..., "summary": {"complete": 1, ...}}`.
A raw-text reviewer can see a different status than the checker evaluated; the
key-set checks (`:128-130`, `:172-173`) run after parsing.

**Impact.** Reviewer and scripted consumer disagree about the same file; no code executes.

**Recommendation.** Parse with `object_pairs_hook`, return `FAIL`/exit `2` on any
duplicate key, and add a conflicting-duplicate-`status` test.

## 4. Concurrent-worker safeguard assessment

**Present and VERIFIED:** duplicate task ID rejection; self/duplicate/cyclic and
unknown/cross-repository dependency rejection; transitive incomplete-dependency
reporting; active same-file and same-branch conflict detection; disabled-agent
blocking for active tasks; immutable `pending_human` approval fields; rejection
of `merge`, `deploy`, `billing` and `production` as requested actions; bounded
input sizes; fail-closed handling of ordinary parse errors and unknown decisions.

**Absent or weakened at the audited revision:** authenticity of completion
evidence (AUD-01) and of transition history (AUD-12); correct classification
and ownership retention for `blocked` tasks (AUD-02, resolved later by PR #732);
enablement enforcement for terminal tasks (AUD-03);
semantic branch normalisation (AUD-04); PR-repo binding and bounded PR numbers
(AUD-05); case-insensitive path equality (AUD-06); checkout binding (AUD-07);
shared state/lock/durable ownership (AUD-08); parser crash classification
(AUD-13); duplicate-key rejection (AUD-14); protected-path denylist — the
checker accepts paths such as `.git/config` or workflow files as declared
`affected_files`, relying on the separate human gate and existing CI for
protection (source VERIFIED, no policy bypass demonstrated).

## 5. Test coverage gaps and fresh verification

**Fresh commands and final output (all run in this session, exit codes recorded):**

```text
$ python scripts/milestone_ledger.py --summary
{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}
LEDGER_EXIT=0

$ python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
... 21 named tests, all "ok" ...
Ran 21 tests in 0.500s

OK
UNITTEST_EXIT=0

$ git diff --check
DIFFCHECK_EXIT=0
```

Note: adding a trailing `.` to `milestone_ledger.py --summary` is invalid: argparse
exits `2` with `error: unrecognized arguments: .`. Use the command above verbatim.

**Adversarial probe results (fresh, this session; manifests confined to
`tempfile`; exact observed lines):**

```text
BLOCKED_CONFLICT {"blocked_tasks": [], "conflicts": [], "decision": "PASS"}
COMPLETE_PREV evidence_ready PASS []
PRREF #0 PASS []
PRREF #9999999999999999999 PASS []
DUP_PARSED_STATUS complete
DUP_EVAL {"blocked_tasks": [], "conflicts": [], "decision": "PASS", "errors": [], "summary": {"complete": 1, ...}}
DEEP_CLI_RC 1 STDOUT_LEN 0 STDERR_HEAD RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string
```

Additional VERIFIED specialist probes also returned `PASS` for: a complete task on a
disabled extra agent; `Shared/Module.py` vs `shared/module.py`; `feature/../main`,
`feature//x`, and `feature//x` vs `feature/x`; a cross-repository PR URL; and fabricated
`PASS` evidence with an arbitrary SHA. All probes were data-only; no agent, network call
or manifest-supplied command was executed.

**Coverage gaps (VERIFIED at the audited revision):** no test for a
`blocked`-status decision or blocked-task file conflict (both added by PR #732);
a disabled agent on `complete`; case-only path collisions; malformed
branches; cross-repository/zero/unbounded PR references; fabricated PASS with arbitrary
SHA; self-asserted `previous_status` rewrites; 5,000-deep JSON; duplicate JSON keys;
512 KiB/collection bounds; exact key-set rejection; unknown/cross-repository dependency
IDs; or duplicate normalised paths in one task. These are gaps, not proof of runtime
failure; section 3 supplies the missing behavioural evidence.

## 6. Prioritised remediation recommendations (advisory only)

| Priority | Finding | Owner action | Guardrail |
| --- | --- | --- | --- |
| RESOLVED | AUD-02 | PR #732 reports `blocked` tasks, returns `BLOCKED`/exit `1`, keeps them in ownership conflict checks, and adds five regression tests | Historical recommendation was a separate reviewed PR; no CI or permission changes |
| P1 | AUD-01, AUD-12 | Stop describing self-asserted `PASS`/`previous_status` as verified; require structured attestation and operator-bound prior state | Keep checker offline; no agent dispatch or paid inference |
| P2 | AUD-03, AUD-04, AUD-05 | Enforce enabled owners for all statuses; validate Git ref syntax and normalise keys; bind PR URL and bound PR number | Add negative tests from section 5 |
| P2 | AUD-13, AUD-14 | Catch recursion/memory errors as `FAIL` JSON; reject duplicate JSON keys | Preserve documented exit-code contract |
| P3 | AUD-06, AUD-07 | Casefold path keys; add `--expect-repository` bound to the checkout | Preserve advisory-only semantics |
| P3 | AUD-08, AUD-09 | Per-worker manifests with reviewed hash-checked merge; freeze exact SHAs in PR text | Requires a separate threat model, not a silent behaviour change |
| Informational | AUD-10, AUD-11 | Reuse existing CI/CodeQL/Trivy/RLS gates and human approval; record #727 in the ledger only after fresh SHA/CI verification | Do not relabel P01, AI-9 or Codex runtime as passed from this report |

## 7. Limits, open assumptions and compliance

- **UNKNOWN:** whether CODEX or OPENCODE ever executed; whether any operator
  manifest exists; whether protected branch rules were active for PR #727's
  merge; whether evidence fields in real manifests are truthful.
- **INFERRED:** AUD-08 only. No multi-writer runtime or agent dispatch was run.
- **Checks not run:** no new CI run for this audit branch, no full Python suite,
  no hosted/provider checks, no Codex/OpenCode runtime, no MCP handshake, no
  Docker/Keycloak test, no GitLab/GitBook/Render action. The earlier full-suite
  baseline failures recorded in `docs/audits/DEVOBS_ROOT_CAUSE_AUDIT.md` are
  historical and were not re-run here.
- **Compliance:** no secret, token, environment value or deployment setting was
  read or printed; no paid service, external agent service, scheduled work, IAM
  or production change was enabled; no `gh`/API write was attempted from this
  report; no other worktree or active branch was modified; no merge or deploy
  was performed. The repository's `password-store`-style credential helper was
  not queried or used to read secrets.

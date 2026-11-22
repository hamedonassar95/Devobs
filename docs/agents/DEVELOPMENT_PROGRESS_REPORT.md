# Offline development progress report

**VERIFIED baseline:** `a9e6e1b1626d8efc1960a8eec52bf412e018c0c6`, reviewed
2026-11-22. The tool is a deterministic projection of two approved local JSON
sources. It creates no task registry, dashboard service, runtime dependency,
network connection, agent dispatch, approval, commit or deployment.

## Existing capabilities and ownership

Inspection found no equivalent combined milestone/task/approval report with
Markdown output. Reuse is intentional:

| Existing source | Reused behavior |
| --- | --- |
| [Milestone ledger validator](../../scripts/milestone_ledger.py) | `validate()` owns milestone/gate schema, duplicate IDs/PRs, SHA/run references and ledger counts |
| [Task status report](../../tools/agent_task_status_report.py) | `build_report()` owns advisory task rows, blocked/dependency/conflict decisions and verification-claim classification |
| [Two-agent contract](../../scripts/check_two_agent_tasks.py) | Used through the task reporter; retains transitions, ownership and mandatory pending-human restrictions |
| [AgentDust reader](../../scripts/agentdust_readonly_adapter.py) | Secure bounded regular-file reads and file-change detection |
| [Output guard](../../tools/agent_output_guard.py) | Existing strict JSON policy, quiet CLI errors and bounded canonical credential checks |

The [ledger](../MILESTONE_LEDGER.json), [STATE](../../STATE.md), active PRs,
worktrees and [agent workflow](../AI_MULTI_AGENT_WORKFLOW.md) were inspected.
The ledger summary is **304 recorded milestones, latest recorded PR 717, three
unresolved gates**. It is incomplete relative to newer Git history; the tool must
not fill gaps by guessing. An open PR is never inferred to be merged.

No active task-manifest ownership registry was found. README ownership could not
be proved clear, so README and all existing files remain unchanged. Only the
reporter, its tests and this document are added. No OpenCode task/file is claimed
or modified. Existing milestone and task files remain their respective authorities.

## Usage

From the trusted Devobs checkout, select approved evidence explicitly:

```sh
python tools/development_progress_report.py --milestones docs/MILESTONE_LEDGER.json --tasks /path/to/approved-tasks.json
python tools/development_progress_report.py --milestones docs/MILESTONE_LEDGER.json --tasks /path/to/approved-tasks.json --format markdown
python tools/development_progress_report.py --help
```

The default format is compact, sorted JSON. Markdown prints safe tables to stdout.
The tool never saves, rewrites or uploads a report; the caller may redirect stdout
to its own destination. It never searches for manifests, reads STATE at runtime,
queries Git/GitHub, or runs commands found in evidence.

## Supported input schemas

1. **Milestone ledger schema 1**, exactly as accepted by the existing validator:
   `schema_version`, `repository`, `disclaimer`, nonempty `milestones` and `gates`.
   Each milestone records a unique ID, supported area, title, increasing PR number,
   distinct full head/merge SHAs, CI run ID, verification text and limitations.
   Gates retain `OPEN` or `BLOCKED`, source document, reason and next action.
   Existing source-document existence checks still apply in the trusted checkout.
2. **Two-agent manifest schema 1**, as documented in
   [the existing contract](TWO_AGENT_COORDINATION.md): `schema_version`,
   `repositories`, `agents`, `approval`, nonempty `tasks`. Tasks preserve the
   canonical fields/transitions; approvals remain `pending_human`. The manifest
   must authorize the ledger repository. It may contain other authorized
   repositories; those task rows stay explicitly scoped to their repository and
   cannot inherit the Devobs ledger's PR records.

Inputs must be explicit UTF-8 `.json` regular files. The ledger cap is **2 MiB**;
the task cap remains the canonical **512 KiB**. Existing strict JSON rejects
duplicate keys, non-finite numbers, excessive integer/depth/node sizes and unsafe
decoded controls. Symlink paths, special files and detected read-time changes
fail closed. Secure reads require the existing POSIX/no-follow APIs; unsupported
platforms, including native Windows, return FAIL with no weaker fallback.

The loader reuses private helper APIs inside this repository; changes to those
helpers require regression testing. Missing helpers, malformed/missing files,
invalid contracts or unexpected exceptions produce fixed error codes, never raw
paths, input values or tracebacks. No partial successful counts are emitted after
an input failure.

## Output meaning and evidence distinctions

| Field / section | Meaning |
| --- | --- |
| `input_validation: VERIFIED` | Local schemas passed their existing validators; not a live project claim |
| `completed_milestones` | Ledger's recorded merged milestones only; all live evidence stays UNVERIFIED |
| `pending_milestones` | Ledger's OPEN gates; planned tasks remain in agent task rows |
| `blocked_milestones` | Ledger's BLOCKED gates, with recorded reasons and source references |
| `agent_tasks` | Existing task reporter's advisory states, blockers and `PASS_CLAIM_UNVERIFIED` labels |
| `available_verification` | Structured ledger run/SHA references and task command counts/result/evidence-presence claims; never fresh CI results |
| `outstanding_owner_approvals` | Existing manifest restrictions, projected without granting authority |
| `next_recommended_task` | One deterministic advisory ID/action category; never an executable instruction |

An exact repository + PR + head/merge SHA match is labelled `RECORDED_MATCH`.
The live merge/CI status still remains **UNVERIFIED**. Missing, foreign, stale,
noncanonical or unusually long PR references cannot create a matching record.
An unrecorded `complete` task stays a local completion claim, not an extra merged
milestone. Raw verification commands, evidence excerpts and free-text gate actions
are omitted. Only structured references/counts are projected.

No generation timestamp, input filename or automatically collected host metadata
is emitted. Approved recorded prose can still contain local paths; review it
before sharing. Task/gate/evidence rows,
nested dependencies/reasons and approvals have stable ordering. Recorded text is
bounded, credential-redacted and terminal-sanitized; Markdown metacharacters/HTML
are escaped. This is heuristic redaction, not proof that arbitrary input is safe
to disclose. Select approved JSON only; never select credential stores, private
keys, customer data or production evidence without its required authorization.

## Advisory priority and exit codes

Within the ledger repository, consider only canonically unblocked tasks, with
task ID as tie-break: continue `in_progress`; review `evidence_ready`; verify an
unlinked `complete` claim; then consider `planned`. Otherwise recommend reviewing
the first blocked gate, or first open gate, by ID. A blocked/conflicted/dependency-
blocked task is never selected. Other repositories remain visible but do not
become this repository's recommended task. No source state is changed.

| Report status | Exit | Meaning |
| --- | --- | --- |
| `BLOCKED` | 1 | A supplied ledger gate or canonical task report is blocked |
| `UNVERIFIED` | 2 | Structurally valid report without known blockers; live evidence remains unavailable |
| `FAIL` | 3 | Invalid/missing input, unsupported reader or validator failure |

There is deliberately **no offline readiness-success exit 0**. `--help` alone
exits 0. Nonzero report exits do not imply broken report generation: read the
structured status. The pending-human operation restrictions are always displayed;
their presence does not independently block unrelated local development.
Local PASS claims are never counted as GitHub CI or authorization.

## Verification and sanitized example

```sh
python -m unittest discover -s tests -p "test_development_progress_report.py" -v
python -m compileall -q tools
python tools/development_progress_report.py --help
git diff --check
```

The [tests](../../tests/test_development_progress_report.py) use only synthetic
JSON and exercise the actual [reporter](../../tools/development_progress_report.py),
including both CLI formats. Existing ledger/task/coordination checks must also
pass; missing platform or runtime checks are reported NOT RUN.

**VERIFIED local results (2026-11-22, Linux):**

| Check | Result |
| --- | --- |
| Required focused unittest command above | 22 tests; OK |
| `python -m unittest tests.test_agent_task_status_report tests.test_two_agent_tasks tests.test_milestone_ledger -q` | 120 tests; OK |
| `/workspace/work/devobs-venv/bin/python -m unittest discover -s tests -q` | 1724 tests; OK (skipped=37) |
| Compileall, CLI help and diff whitespace commands above | Exit 0 |
| `/workspace/work/devobs-venv/bin/python -m bandit -q tools/development_progress_report.py` | Exit 0; no findings |
| `python tools/agent_output_guard.py --workspace . tools/development_progress_report.py tests/test_development_progress_report.py docs/agents/DEVELOPMENT_PROGRESS_REPORT.md` | PASS for all three files |
| Documentation validation | 11 relative links resolve; balanced fences; synthetic JSON excerpt matches fixture output |
| Native Windows verification | NOT RUN; the secure POSIX reader is not supported on native Windows |

These are local verification results, not GitHub CI or production acceptance.
The full suite's 37 skips remain skips; they do not establish runtime coverage.

Sanitized **synthetic excerpt**, not actual repository/agent acceptance:

```json
{"input_validation":"VERIFIED","status":"UNVERIFIED","live_evidence_status":"UNVERIFIED","summary":{"recorded_completed_milestones":1,"pending_milestones":1,"blocked_milestones":0,"agent_tasks":1,"completed_task_claims":0,"blocked_tasks":0,"latest_recorded_pr":12},"next_recommended_task":{"kind":"PLAN_TASK","id":"TASK-001","evidence_status":"UNVERIFIED","advisory":true}}
```

Counts describe only supplied records, not total roadmap completeness. No live
agent, merge, CI, deployment, paid service or production gate is accepted by this
report. Keep ordinary human review and independent evidence verification.
Rollback is a reviewed three-file revert; source authorities remain untouched.

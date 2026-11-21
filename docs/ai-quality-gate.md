# AI Quality and Agent Coordination Gate

Status: **offline, additive, advisory-only; `DRY_RUN` is the only mode**. The
gate never merges, deploys, dispatches an agent, changes Git state, bills,
touches production, or grants an approval.

Source base: `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f` (`origin/main`, merge
of PR #739). Branch: `feature/ai-quality-coordination-gate`. This document does
not change P01 (NO-GO), AI-9 (BLOCKED), or Codex runtime acceptance (OPEN).

## Purpose

The gate gives one bounded, reproducible answer to four questions on every
change:

1. Are deterministic checks and evidence present and consistent?
2. Is there unfinished or conflicting agent work (blocked tasks, duplicate
   ownership, dependency cycles, duplicate verification claims)?
3. Are CI failures classified from evidence rather than guessed?
4. Is any consequential action still waiting for a human?

It produces a **structured JSON decision with audit events and evidence IDs**,
plus an optional explanatory advisory note. The advisory note can never change
the decision or create authority.

## What it reuses instead of duplicating

| Existing component | Role kept authoritative |
| --- | --- |
| `scripts/check_two_agent_tasks.py` | Task contract: unique IDs, transitions, ownership conflicts, dependency cycles, restricted actions. |
| `devobs/integration_control/` | PR readiness, security, evidence, coordination components and report schema. |
| `devobs/integration_control/hardening.py` | Approval evidence, unsafe retry and destructive-action diagnostics. |
| `devobs/integration_control/control_events.py` | Bounded, redacted local event boundary. |
| `scripts/ci_failure_intelligence.py` | CI failure classification, signatures and redaction. |
| `scripts/human_approval_gate.py` | Human approval semantics; explicit approval is the only authority. |
| `devobs/integration_control/advisory.py` | `AdvisoryProvider` protocol and non-influencing advisory contract. |

The new package only normalizes those results into one closed schema. None of
the files above was modified.

## Modules added

| Path | Role |
| --- | --- |
| `devobs/ai_quality_gate/models.py` | Closed result schema, bounds, digest and fail-closed validation. |
| `devobs/ai_quality_gate/engine.py` | Composition, decision aggregation, CI normalization, audit events. |
| `devobs/ai_quality_gate/adapter.py` | Deterministic offline `LocalExplanatoryAdapter` (no network, no tools). |
| `devobs/ai_quality_gate/cli.py` | `DRY_RUN`-only CLI, JSON/Markdown rendering, exit codes. |
| `examples/ai_quality_gate/` | Passing snapshot, CI run and CI jobs fixtures. |
| `tests/ai_quality_gate/` | Behavioral, schema, adapter and CLI tests. |

## Decision contract

| Decision | Exit code | Meaning |
| --- | ---: | --- |
| `PASS` | 0 | No blocker or unverified finding; still only `PENDING_HUMAN`. |
| `BLOCKED` | 1 | A deterministic blocker exists (conflict, cycle, unauthorized action, code CI failure). |
| `UNVERIFIED` | 2 | Evidence is missing or a CI failure is infra/ambiguous; no conclusion claimed. |
| `INVALID` | 3 | Input, schema or engine failed; the gate failed closed. |

Any unexpected exception produces `INVALID` with an `GATE_INTERNAL_ERROR`
finding. There is no exit code or result that authorizes a consequential action.

## Authority invariants (enforced by schema validation)

- `mode` is always `DRY_RUN`; any other value is rejected.
- `merge_authorized` is always `false`.
- `human_approval` is always `PENDING_HUMAN`.
- `offline` is always `true`.
- `advisory.influenced_decision` is always `false`.
- Every restricted action (`merge`, `deploy`, `billing`, `production`) is listed
  with status `PENDING_HUMAN`.
- `gate_digest` is a SHA-256 over every other field; tampering fails validation.
- Advisory providers receive only closed finding codes and an optional source
  SHA — never repository text, logs, tokens or secrets. Secret-like output is
  discarded, and output is bounded to 600 characters.

## Usage

```sh
python -m devobs.ai_quality_gate \
  --input examples/ai_quality_gate/snapshot.json \
  --ci-run-json examples/ai_quality_gate/ci_run.json \
  --ci-jobs-json examples/ai_quality_gate/ci_jobs.json \
  --format json

python -m devobs.ai_quality_gate \
  --input examples/ai_quality_gate/snapshot.json \
  --format markdown

python -m unittest discover -s tests/ai_quality_gate -p "test_*.py" -v
```

On hosts where `python3` is unavailable use `python`; the code is Python 3.12
compatible and standard-library only. `--mode` accepts only `DRY_RUN`.

Optional inputs:

| Flag | Content |
| --- | --- |
| `--approval-evidence` | Local JSON list of human approval records (checked, never trusted as authority). |
| `--retry-policy` | Local JSON retry policy used by hardening diagnostics. |

### Minimal passing result (excerpt)

```json
{
  "schema_version": "ai-quality-gate/1.0",
  "mode": "DRY_RUN",
  "decision": "PASS",
  "merge_authorized": false,
  "human_approval": "PENDING_HUMAN",
  "offline": true,
  "checks": {
    "passed": ["approval", "ci_failures", "coordination", "evidence", "pr_readiness", "security"],
    "failed": [],
    "skipped": []
  },
  "consequential_actions": [
    {"action": "merge", "status": "PENDING_HUMAN"},
    {"action": "deploy", "status": "PENDING_HUMAN"},
    {"action": "billing", "status": "PENDING_HUMAN"},
    {"action": "production", "status": "PENDING_HUMAN"}
  ],
  "advisory": {"provider": "injected_advisory", "status": "accepted", "influenced_decision": false}
}
```

## Gate finding codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `CONCURRENT_FILE_OWNERSHIP` | BLOCKER | Two active tasks claim the same file. |
| `CONCURRENT_BRANCH_OWNERSHIP` | BLOCKER | Two active tasks claim the same branch. |
| `BLOCKED_TASK_RETAINS_OWNERSHIP` | BLOCKER | A blocked task still owns files or branch. |
| `UNRESOLVED_DEPENDENCY` | BLOCKER | Prerequisite task is not complete. |
| `INVALID_DEPENDENCY_GRAPH` | BLOCKER | Dependency cycle or unknown reference. |
| `UNSAFE_RETRY_LOOP` | BLOCKER | Duplicate verification claim or repeated attempt digest. |
| `UNAUTHORIZED_ACTION_REQUESTED` | BLOCKER | Restricted or destructive action requested. |
| `CI_FAILURE_CODE` | BLOCKER | Evidence-classified code failure. |
| `CI_FAILURE_UNVERIFIED` | UNVERIFIED | Infrastructure or unverified failure. |
| `CI_FAILURE_AMBIGUOUS` | UNVERIFIED | No confident classification. |
| `CI_FAILURE_FLAKY_OR_EXTERNAL` | UNVERIFIED | Flaky/external classification; re-run needs review. |
| `GATE_INTERNAL_ERROR` | BLOCKER | Unexpected engine failure; result is `INVALID`. |

All underlying integration-control and hardening codes are preserved verbatim
in `findings`; this table lists the gate-level additions.

## CI integration

The advisory gate is executed inside the existing `security` job of
`.github/workflows/ci.yml` against the checked-in offline fixtures. It:

- uses the existing read-only checkout (`persist-credentials: false`);
- adds no new action, no new required check and no new permission;
- does not alter the `validate` aggregation or any branch protection rule;
- writes the validated decision to the step log and job summary only.

Because `validate` already requires `security`, a genuine regression in the
gate (or its fixtures) fails the existing required check. The gate never
creates a bypass path.

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `INVALID` / `GATE_INTERNAL_ERROR` | Malformed snapshot or unexpected input shape. | Re-check the fixture with the integration-control CLI; fix the input, not the schema. |
| `UNVERIFIED` with `CI_FAILURE_UNVERIFIED` | Infra/unclassified failure fixtures. | Confirm evidence before attributing failure to code; add a classified fixture to test code failures. |
| `BLOCKED` with `CONCURRENT_FILE_OWNERSHIP` | Two active tasks share a path. | Assign one owner or split the paths; re-run the gate. |
| `BLOCKED` with `INVALID_DEPENDENCY_GRAPH` | Dependency cycle. | Remove the cycle or unknown task ID. |
| `BLOCKED` with `UNSAFE_RETRY_LOOP` | Reused verification digest. | Provide fresh, unique completion evidence. |
| Advisory note is empty or `discarded` | Provider emitted no bounded text or secret-like material. | Expected fail-closed behavior; inspect only the deterministic findings. |
| `python3: command not found` on Windows | Interpreter name differs on this host. | Use `python` with the same arguments. |
| Non-`DRY_RUN` mode rejected | No execution mode exists by design. | Remove `--mode EXECUTE`; the gate is advisory only. |

## Verification matrix

| Check | Command | Evidence |
| --- | --- | --- |
| Targeted gate tests | `python -m unittest discover -s tests/ai_quality_gate -p "test_*.py" -v` | 23 tests, `OK`, exit 0. |
| Integration-control regression | `python -m unittest discover -s tests/integration_control -p "test_*.py" -v` | 48 tests, `OK`, exit 0 (fresh run after all commits). |
| Related existing suites | `python -m unittest tests.test_action_pins tests.test_two_agent_tasks tests.test_ci_failure_intelligence tests.test_human_approval_gate tests.test_agent_dispatch_preflight` | 67 tests, `OK`, exit 0. |
| Full suite vs baseline | `python -m unittest discover -s tests -p "test_*.py" -v` | 1419 tests, `FAILED (failures=47, errors=123, skipped=44)`, exit 1. Pre-change baseline: 1396 tests, `FAILED (failures=47, errors=123, skipped=44)`. The 23 added tests pass; failure/error/skip counts are unchanged. |
| Compile | `python -m compileall -q devobs/ai_quality_gate tests/ai_quality_gate` | exit 0. |
| Deterministic CLI JSON | `python -m devobs.ai_quality_gate --input examples/ai_quality_gate/snapshot.json --format json` | `PASS`, `DRY_RUN`, `merge_authorized=false`, exit 0. |
| CI-step invariant replay | In-process `validate_result` plus DRY_RUN/offline/no-authority field checks on CLI JSON | `PASS schema=True`, exit 0. |
| Action pin policy | `python scripts/check_action_pins.py` | 48 workflow/template files, exit 0 (fresh run after CI edit). |
| Workflow YAML parse | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` | 11 jobs, 15 security steps, exit 0. |
| Whitespace | `git diff --check HEAD~6..HEAD` | exit 0. |
| Hosted required checks | `.github/workflows/ci.yml` `validate` on the exact head SHA | Pending hosted run for this branch. |

The full-suite failure is pre-existing and unchanged in kind and count; the
example failure is `tests/test_stage_site.py` requiring `GITHUB_WORKSPACE`,
which is a CI-only environment variable. No new failure is attributable to
this change. Local evidence is reported with exact commands and exit codes.

## Limitations and open gates

- The gate evaluates **bounded local snapshots and CI fixtures**. It does not
  ingest live GitHub PR data in this PR: that needs a network/credential data
  source, which is outside `DRY_RUN` and requires separate owner approval.
- No billable inference is enabled. `LocalExplanatoryAdapter` is deterministic;
  opt-in paid adapters elsewhere in the repository are not wired here.
- Audit events are structured records inside the result and CI step log. There
  is no long-lived tamper-proof sink in this additive change.
- AI-9 remains `BLOCKED`, P01 remains `NO-GO`/`BLOCKED`, and Codex runtime
  acceptance remains `OPEN`. A `PASS` here is not evidence that those gates
  passed and is not merge approval.

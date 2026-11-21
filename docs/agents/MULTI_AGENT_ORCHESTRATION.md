# Multi-agent work orchestrator (advisory, DRY_RUN only)

**Scope:** a local Python package that records intended multi-agent work,
detects coordination conflicts, builds a dependency-ordered DRY_RUN plan from
injected capacity evidence, and classifies caller-supplied GitHub delivery
evidence.

**Non-goals:** it does not start an agent, open a process, call GitHub, change
Git state, push or force-push, create or merge a PR, deploy, bill, change
repository settings, read secrets, or grant approval. There is no dispatch,
execute, apply, merge, or deploy entry point. `DRY_RUN` is the only mode.

A `PASS` plan is advisory coordination evidence. It is not proof that an agent
ran, that tests were truthful, that CI passed, that delivery completed, or that
a human approved a release. P01 remains **NO-GO / BLOCKED**, AI-9 remains
**BLOCKED**, and Codex runtime acceptance remains **OPEN**.

## Evidence labels used here

- **VERIFIED (local):** behavior covered by the new unit tests in this branch.
  The exact commands and final output are recorded in the PR verification
  report; a repository file is not itself runtime proof.
- **UNVERIFIED:** live agent startup, authenticated GitHub delivery, CI on a
  PR event, protected-branch enforcement, deployment, and human approval.
- **ASSUMED:** the caller supplies truthful, current, read-only capacity and
  GitHub evidence. The package cannot attest to an external system it never
  contacts.

## Why this layer exists

`scripts/check_two_agent_tasks.py::evaluate()` is the existing source of truth
for manifest validity, status transitions, dependency order, branch/file
ownership, restricted actions, and completion evidence. The orchestrator wraps
it rather than copying those rules:

- `TaskRegistry` normalizes task records into that manifest shape and rejects
  duplicate IDs, unsafe paths, missing/cyclic dependencies, illegal
  transitions, and incomplete evidence before atomic persistence.
- `ConflictDetector` calls the canonical `evaluate()` and converts its
  `blocked_tasks` and `conflicts` into sanitized findings.
- `WorkOrchestrator` consumes those findings and an injected capacity snapshot
  to produce an ordered plan. There is no supported scheduler service in this
  repository, so capacity is supplied by the caller, never discovered through
  a hidden network call.
- `DeliveryTracker` classifies evidence supplied by the caller and reuses
  `scripts/human_approval_gate.py::evaluate()` for human-approval checks.

## Components

| Module | Responsibility | Fail-closed behavior |
| --- | --- | --- |
| `devobs/orchestration/task_registry.py` | Versioned task records, optional JSON store, canonical manifest export | Invalid task state, corrupt store, stale expected version, or unknown ID raises a typed error. |
| `devobs/orchestration/conflict_detector.py` | Adapter over the canonical validator | Validator exception, malformed result, unknown decision, or policy `FAIL` returns `FAIL`. |
| `devobs/orchestration/work_orchestrator.py` | Dependency ordering, injected capacity guards, observability, safety flags | Invalid capacity or unexpected planning exception returns `FAIL`; blocked tasks are never assigned. |
| `devobs/orchestration/delivery_tracker.py` | Idempotent classification of GitHub delivery evidence | API failure, failed/pending CI, protected base branch, SHA mismatch, or missing/stale human approval becomes `BLOCKED`/`UNVERIFIED`. |

### Registry model

`Task` uses orchestration-facing names that map to the canonical manifest:
`owner` → `assigned_agent`, `task_id` → `id`, and `affected_files`,
`dependencies`, `status`, `previous_status`, `source_sha`, `verification`,
`pr_reference`, and `requested_actions` keep their contract meaning.

`TaskRegistry(path)` persists a bounded JSON document with schema
`orchestration/task-registry/v1`. Writes use `tempfile.NamedTemporaryFile` and
`os.replace`, documented by Python as atomic on the same filesystem:
[`tempfile.NamedTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile)
and [`os.replace`](https://docs.python.org/3/library/os.html#os.replace).
A missing, empty, oversized, corrupt, duplicate-key, or wrong-schema file is
refused. No temporary file remains after a successful or failed write.

`update(..., expected_version=n)` is an optimistic-concurrency guard and is
idempotent: applying the same unchanged state twice does not bump the version.

### Delivery evidence model

`DeliveryEvidence` is supplied by the caller. The tracker performs no I/O.
The GitHub field names it models are documented in the official REST references
for [pull request state](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)
and [check run `status` / `conclusion`](https://docs.github.com/en/rest/checks/runs#get-a-check-run).

| Evidence | Required for `DELIVERED` | Failure classification |
| --- | --- | --- |
| `pr_reference`, `pr_state` | Valid PR reference and `open` | Missing → `UNVERIFIED`; invalid/not open → `BLOCKED`. |
| `head_sha`, `expected_sha` | Both present, exact 40-hex, equal | Missing → `UNVERIFIED`; mismatch/invalid → `BLOCKED`. |
| `branch`, `base_branch` | Allowed task branch; base must not be `main`/`master` | Missing → `UNVERIFIED`; protected base → `BLOCKED`. |
| `required_checks`, `checks` | Every required check completed with `SUCCESS` | Missing/pending → `UNVERIFIED`; failure → `BLOCKED`. |
| `approval`, `approved_sha` | Existing gate result `HUMAN_APPROVED` bound to the head SHA | Missing/stale/agent approval → `BLOCKED`. |
| `api_error` | Absent | Any value → `BLOCKED` as `github_api_failure` without echoing the detail. |

Recorded retry snapshots are keyed by a SHA-256 digest of the evidence. Replaying
identical evidence returns the existing classification and does not add history.
Partial delivery is reported as `PARTIAL` when at least one task is delivered
and at least one is blocked.

### Observability and redaction

`OrchestrationPlan.to_dict()` exposes `mode`, `decision`, ordered assignments,
blocked tasks, sanitized events, approval state, safety flags, delivery
classification, errors, and summary counts. Every event and evidence excerpt
passes through `sanitize_display` from the existing status-report utility and a
local redactor for common credential shapes (GitHub PAT/fine-grained tokens,
`sk-` keys, AWS access-key IDs, Bearer headers, and JWT-like strings). Raw
token text is replaced with `[REDACTED]`.

The plan always includes:

```text
mode=DRY_RUN
dispatched=false
apply=false
safety.executor_enabled=false
safety.network_calls_allowed=false
safety.mutations_allowed=false
approval.{merge,deploy,billing,production}=pending_human
```

## Usage

```python
from devobs.orchestration import (
    CapacitySnapshot,
    DeliveryTracker,
    Task,
    TaskRegistry,
    WorkOrchestrator,
)

registry = TaskRegistry("tasks.json")
registry.add(Task(
    task_id="TASK-001",
    owner="CODEX",
    branch="feature/task-001",
    repository="hamedonassar95/Devobs",
    affected_files=("src/module.py",),
    dependencies=(),
    status="planned",
    previous_status="none",
    source_sha=None,
    verification={"commands": [], "result": "PENDING", "evidence": ""},
    pr_reference=None,
    requested_actions=("code_change",),
))

capacity = CapacitySnapshot(
    global_slots=2,
    owner_slots={"CODEX": 1, "OPENCODE": 1},
    source="operator-supplied snapshot",
)
plan = WorkOrchestrator(registry, capacity, DeliveryTracker()).plan()
assert plan.mode == "DRY_RUN"
assert plan.dispatched is False
print(plan.to_dict())
```

This example only builds a plan. The human operator still decides whether to
start any worker, in an isolated worktree, and must separately review evidence.

## Test coverage

New regressions cover: duplicate IDs, missing/cyclic dependencies, unsafe
paths, illegal transitions, stale updates, atomic persistence and corrupt state;
shared file/branch conflicts and dependency-sequenced reuse; API failures,
failed/pending CI, protected branches, missing/stale approval, partial delivery,
idempotent retries, and secret redaction; capacity exhaustion, dependency order,
validator failure, no-socket/no-subprocess behavior, and absence of execution
entry points.

```sh
python -m unittest discover -s tests -p "test_task_registry.py" -v
python -m unittest discover -s tests -p "test_conflict_detector.py" -v
python -m unittest discover -s tests -p "test_delivery_tracker.py" -v
python -m unittest discover -s tests -p "test_work_orchestrator.py" -v
```

## Human controls that remain mandatory

1. Review the plan, exact source SHA, branch, files, and approval binding.
2. Run fresh tests and the existing validators/CI; do not accept a manifest
   `PASS` as verification.
3. Keep `merge`, `deploy`, `billing`, and `production` as `pending_human`.
4. Complete the repository's Phase 8 PENDING HUMAN APPROVAL gate before any
   merge or deployment.
5. Never put tokens, private keys, customer data, or production environment
   values into registry records or delivery evidence.

## Limitations

**UNVERIFIED:** an actual Codex/OpenCodex process, authenticated GitHub state,
branch-protection settings, CI on a PR event, protected deployment, or human
approval. A passing local test suite only verifies the advisory library in this
checkout. Capacity numbers are trusted input; a false snapshot produces a
misleading plan without changing the orchestrator's safety guarantees.

# Intelligent multi-agent orchestration engine (advisory, offline-first)

**Status:** IMPLEMENTED AS AN OFFLINE PLANNER; INTEGRATION BLOCKED.
**Base:** `origin/main` `c244ab2368d43ca1f7b9cee949650bc377747258`
(rebased from `4763f1872ec154be2017cbe841fbaafc48ab5263`; no merge).
**Branch:** `feature/intelligent-agent-orchestration`.

This document describes a deterministic planner that turns the existing
[two-agent manifest contract](../agents/TWO_AGENT_COORDINATION.md) into an
auditable `DRY_RUN` preview. It does **not** start agents, open sockets, launch
subprocesses, alter Git state, merge, deploy, bill, spend AI credits, or grant
approval. A `PASS` preview is a statement about local inputs only.

## 1. Why this exists

The repository already has separate advisory tools: the canonical manifest
validator, dispatch preflight, status report, and Phase 8 human approval gate.
They were not composed into a single deterministic plan. This engine adds that
composition without modifying those protected tools:

- `scripts/check_two_agent_tasks.py` remains the source of truth for schema,
  status transitions, enabled workers, dependencies, file/branch ownership, and
  restricted actions.
- `scripts/agent_dispatch_preflight.py` and `tools/agent_task_status_report.py`
  remain unchanged and can consume the coordinator's canonical manifest.
- `scripts/human_approval_gate.py` remains the base authorization gate; this
  package adds exact-preview and scope binding around it.
- `agent-spec.yaml` remains the policy source; this package reads it strictly
  and does not read environment variables, credentials, or hosted state.

## 2. Components

| Path | Responsibility |
| --- | --- |
| `devobs/orchestration/models.py` | Immutable task, capacity, budget, assignment, block, approval, and plan exports. Exports always set `dispatched=False` and `apply=False`. |
| `devobs/orchestration/policy_adapter.py` | Strict local parse of `agent-spec.yaml`; budget, retry, provider-call, and production-mutation evaluation. |
| `devobs/orchestration/audit.py` | Credential redaction, bounded sanitization, stable scope fingerprints, structured timestamp-free events, and conservative failure classification. |
| `devobs/orchestration/planner.py` | Dependency validation, deterministic topological order, optional critical-path priority, ownership enforcement, capacity scheduling, retry handling, and fail-closed plans. |
| `devobs/orchestration/coordinator.py` | Thin facade: manifest → plan → sanitized preview; approval binding to exact fingerprint, reviewed SHA, task IDs, and actions. |
| `tests/orchestration/` | Offline behavioral coverage for validation, planning, policy, audit, approval, and read-only behavior. |

## 3. Planning rules

1. Tasks are sorted by ID before planning, so input order cannot change the
   output.
2. Unknown dependencies, self-dependencies, duplicate IDs, and cycles produce
   `FAIL` with no assignments.
3. The canonical validator is invoked on the exact canonical manifest. A
   malformed or unknown validator response produces `FAIL`.
4. An unresolved dependency that points to another planned task is sequencing,
   not a hard block. The topological order guarantees the dependency appears
   first.
5. Shared file or branch ownership from the validator becomes an
   `ownership_conflict` block for every involved task.
6. Capacity is caller-supplied. Both global slots and per-owner slots must be
   present for an owner's task to be scheduled. Exhaustion blocks rather than
   queues silently.
7. If `CapacitySnapshot.supports_priority` is true, ready tasks are ordered by
   longest downstream path, then transitive downstream count, then ID. If it is
   false, ordering is purely lexicographic and deterministic.
8. Billable work requires explicit `BudgetSnapshot.approved=True`. Cost caps and
   provider-call caps are enforced when supplied; unknown cost with a dollar cap
   fails closed.
9. The current `agent-spec.yaml` disallows production mutations. That remains a
   hard block even if a caller supplies a positive budget approval.
10. Only explicitly transient failure codes (`timeout`, `rate_limited`,
    `temporary_network`, `provider_unavailable`, `conflict_retry`) may be
    retried, and only below the policy retry limit. Unknown, terminal, and
    policy failures are never retried by this package.
11. Any unexpected exception is converted into a `FAIL` plan with no partial
    assignments.

## 4. Read-only preview

```python
import json
from pathlib import Path

from devobs.orchestration import Coordinator

manifest = json.loads(Path("tasks.json").read_text(encoding="utf-8"))
coordinator = Coordinator.from_manifest(manifest)
preview = coordinator.preview()
print(json.dumps(preview, sort_keys=True, indent=2))
```

The returned object contains:

- `mode: "DRY_RUN"`, `dispatched: false`, `apply: false`;
- ordered `assignments` and explicit `blocked` tasks with reason codes;
- `approval` entries for merge, deploy, billing, and production fixed at
  `pending_human`;
- `safety` flags that record the absence of an executor, network, mutations,
  and repository state changes;
- `events`: sequence-numbered, sanitized, timestamp-free audit records;
- `fingerprint`: SHA-256 over the canonical unsigned preview.

A preview is never an execution grant. `Planner` and `Coordinator` intentionally
have no `execute`, `dispatch`, `apply`, `run`, `merge`, or `deploy` method.

## 5. Approval binding

`Coordinator.approve(preview, record)` reuses
`scripts/human_approval_gate.py::evaluate`, requiring `VERIFIED`, literal
`APPROVE`, human approver with write authority, an open unmerged PR, and then
additionally requires:

- `scope_fingerprint` equal to the preview fingerprint;
- `reviewed_sha`, an exact 40-character lowercase commit SHA;
- `approved_task_ids`, exactly matching the preview's assigned tasks;
- `approved_actions`, exactly matching those tasks' requested actions;
- a preview that is still `DRY_RUN`, unapplied, undispatched, with all
  restricted approvals still `pending_human`.

The result is an advisory record, not a merge or deployment authorization.

**Security limitation (UNRESOLVED):** the base gate and the added fields are
caller-supplied. This package does not query GitHub, verify reviewer identity,
confirm write authority, or bind to a live PR review. An authenticated delivery
and approval provider remains a separate reviewed integration task.

## 6. Offline behavior and redaction

All exported strings pass through `sanitize()`, which removes ANSI/control
characters, bounds length, and replaces common credential shapes (Bearer
tokens, GitHub tokens, JWTs, API keys, `token=`/`password=` assignments, and
private-key blocks) with `[REDACTED]`. Events contain a sequence and a plan ID,
never a wall-clock timestamp, so identical inputs produce identical audit
trails and fingerprints.

## 7. Verification

```sh
python -m unittest discover -s tests/orchestration -v
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
python -m unittest discover -s tests -p "test_human_approval_gate.py" -v
python -m compileall -q devobs/orchestration tests/orchestration
git diff --check
```

Tests cover: dependency validation, cycles, deterministic order, critical-path
priority, file/branch conflicts, global and owner capacity, budget approval,
caps and unmeasured cost, production mutation denial, retry classification,
structured audit events, redaction, fingerprint stability, unknown validator
responses, approval binding, canonical preflight/status-report composition, and
the absence of execution entry points.

The full repository suite was attempted on this Windows host and is **BLOCKED
as an environment signal**: `python -m unittest discover -s tests` ran 1337
tests and reported `FAILED (failures=47, errors=123, skipped=38)`; no
orchestration test appeared among the failures or errors. The failures
include missing executables (`FileNotFoundError: [WinError 2]`), Git timeout
guards (`Git unavailable or timed out`), and missing `GITHUB_WORKSPACE` staging
preconditions. None of the 27 orchestration tests failed. Full-suite promotion
requires the repository CI runtime, not this local sandbox.

## 8. Integration blockers

| Blocker | Status | Required owner decision |
| --- | --- | --- |
| No CI or runtime consumer invokes the package | BLOCKED | Approve a separate workflow/CLI integration change. |
| No authenticated GitHub/CI evidence provider | BLOCKED | Choose a least-privilege provider and approve its scope. |
| Approval booleans are caller-supplied | BLOCKED | Choose the canonical live approval binding contract. |
| Unmerged `feature/multi-agent-work-orchestrator` has overlapping advisory files | BLOCKED | Decide whether to replace, reconcile, or archive that branch. |
| `gh` CLI is unavailable in the agent environment | BLOCKED | Provide authenticated access or open the Draft PR manually from the exact pushed SHA. |
| P01, AI-9, and Codex runtime acceptance gates | UNCHANGED | Do not infer promotion from this offline planner. |

No merge, deployment, production change, paid inference, or release-gate change
is authorized by this document.

# Integration Control Plane Hardening Architecture

Status: **offline, additive, advisory-only; no execution or merge authority**.

Source base: `cfa1e17ee1575da90a0bb4fe30800c6df3b68668` (`origin/main`, squash
merge of PR #738). Branch: `feature/intelligent-integration-plane-hardening`.
This document does not change P01, AI-9, or Codex runtime gates.

## Purpose

The hardening layer closes four gaps in the merged integration control plane
without duplicating its authoritative rules:

1. caller-supplied approval evidence is checked explicitly but never treated as
   authority;
2. restricted and destructive task actions receive a deterministic finding code;
3. unsafe retry patterns are detected from one snapshot or caller-supplied prior
   attempt digests;
4. optional local observability reuses the merged incident event boundary only
   when it imports cleanly.

It does not replace `scripts/check_two_agent_tasks.py`,
`scripts/pr_readiness_gate.py`, `scripts/human_approval_gate.py`, or
`devobs/incidents/observability.py`. Those modules remain the canonical rule
sources and were not modified.

## Modules

| Path | Role |
| --- | --- |
| `devobs/integration_control/hardening.py` | Pure diagnostic functions, `harden_report()`, and `evaluate_hardened()`. |
| `devobs/integration_control/control_events.py` | Optional bounded event adapter and offline fallback sinks. |
| `devobs/integration_control/__main__.py` | Adds optional `--approval-evidence` and `--retry-policy` inputs. |

### Compatibility invariants

- `IntegrationControlPlane.evaluate()` signature and behavior are unchanged.
- Exported names in `devobs/integration_control/__init__.py` are unchanged.
- The report schema remains `integration-control/1.0`; no top-level, component,
  finding, or advisory key was added.
- `merge_authorized` is always `false`; `human_approval` is always
  `PENDING_HUMAN`; `offline` is always `true`.
- `harden_report()` deep-copies its inputs and is idempotent: applying it twice
  to the same snapshot yields the same report digest.
- No workflow consumes the CLI automatically. This remains a library/CLI
  artifact and documentation contract.

## Hardened diagnostic codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `HARDENING_MANIFEST_DIGEST` | ADVISORY | Stable SHA-256 prefix for the task manifest. Not an approval. |
| `APPROVAL_EVIDENCE_PRESENT` | ADVISORY | Caller supplied a structurally valid approval record. Still non-authoritative. |
| `APPROVAL_EVIDENCE_MISSING` | UNVERIFIED | No caller-supplied record for one of `merge`, `deploy`, `billing`, or `production`. |
| `APPROVAL_EVIDENCE_PENDING` | UNVERIFIED | The caller-supplied record is still pending. |
| `APPROVAL_EVIDENCE_INVALID` | BLOCKER | Record shape, options, timestamps, IDs, or canonical gate semantics failed. |
| `APPROVAL_EVIDENCE_REJECTED` | BLOCKER | Caller-supplied evidence records a human rejection. |
| `UNAUTHORIZED_ACTION_REQUESTED` | BLOCKER | A task requested a restricted or destructive action. |
| `UNSAFE_RETRY_LOOP` | BLOCKER | Duplicate non-complete retry claims or a repeated prior-attempt digest. |
| `RETRY_POLICY_INVALID` | BLOCKER | Retry policy failed closed validation. |
| `HARDENING_INTERNAL_ERROR` | BLOCKER | Unexpected hardening failure; decision is forced to `BLOCKED`. |

Approval-evidence checks are **opt-in**: pass an evidence file. Without that
file, legacy fixtures remain `PROCEED_TO_HUMAN_REVIEW`. With an evidence file,
missing records produce `UNVERIFIED`, never an authorization.

## Approval evidence contract

Each record must use exactly these keys:

```json
{
  "action": "merge",
  "approval": "APPROVE",
  "verification_status": "VERIFIED",
  "pr_open": true,
  "pr_merged": false,
  "approver_is_human": true,
  "approver_has_write": true,
  "evidence_ids": ["APPROVAL_MERGE_001"],
  "recorded_at": "2026-11-21T01:00:00Z"
}
```

Validation rules:

- `action` is one of the four restricted actions declared by the canonical
  coordination contract.
- `approval` is `APPROVE`, `REJECT`, or `PENDING`.
- `verification_status` is `VERIFIED` or `PENDING`.
- Four authority attributes must be exact booleans.
- `evidence_ids` has 1–20 bounded uppercase IDs.
- `recorded_at` must be an ISO-8601 instant with offset or `Z`.
- The canonical `scripts.human_approval_gate.evaluate()` semantics are applied
  to the authority attributes, but its `authorized` result is deliberately
  ignored for control-plane decisions.

A `HUMAN_APPROVED` gate result produces only
`APPROVAL_EVIDENCE_PRESENT`. It never changes `decision`, `merge_authorized`,
or `human_approval`.

## Retry-loop contract

Default policy: at most one non-complete task may claim a given
`(repository, verification.commands, verification.evidence)` tuple. A repeated
claim produces `UNSAFE_RETRY_LOOP`.

Callers may supply:

```json
{
  "max_identical_retries": 1,
  "prior_attempt_digests": ["<64 lowercase hex digest>"]
}
```

If the current manifest digest appears in `prior_attempt_digests`, the same
`UNSAFE_RETRY_LOOP` blocker is emitted. Values are bounded; invalid policies
become `RETRY_POLICY_INVALID`.

Circular dependency prevention remains delegated to the canonical
`check_two_agent_tasks` validator. No cycle logic was duplicated.

## Prohibited actions

Restricted actions are `merge`, `deploy`, `billing`, and `production`.
Destructive actions are `bypass_branch_protection`, `delete`, `destroy`,
`disable_checks`, `drop_database`, `force_push`, `publish_release`,
`reset_hard`, and `terraform_apply`. Any such `requested_actions` entry emits
`UNAUTHORIZED_ACTION_REQUESTED` in addition to the canonical validator finding.

## Observability

`control_events.py` imports `devobs.incidents.observability` read-only. When
available, it reuses `sanitize_event`, `MemoryEventSink`, and `NullEventSink`
and the allowlisted names `validation_completed`, `approval_required`,
`evidence_missing`, and `report_generated`. If the import is unavailable or
unstable, it uses an equivalent in-process fallback and reports
`EVENT_INTERFACE = "offline_fallback"`.

Events are derived only from a validated report. No raw task text, approval
attribute values, PR text, network response, or repository secret is copied
into an event. No sink transmits or persists events outside the process unless
a caller explicitly supplies such a sink; the CLI supplies none.

## Decision precedence

Hardening findings are additive:

1. `BLOCKER` → `BLOCKED`;
2. `UNVERIFIED` → `UNVERIFIED` (unless already `BLOCKED`);
3. otherwise the base decision is preserved.

A hardening result can never remove a base finding or downgrade a base
decision. `INVALID` input reports are returned unchanged because no valid task
manifest is available to inspect.

## Ownership and non-changes

Modified on this branch: `hardening.py` (new), `control_events.py` (new),
`__main__.py`, their tests, these docs, and one README link.

Deliberately not modified: `scripts/check_two_agent_tasks.py`, its tests and
spec; `scripts/human_approval_gate.py`; `devobs/incidents/observability.py`;
`scripts/pr_readiness_gate.py`; existing integration-control report/collector/
engine/report modules; and active worktrees on other branches.

## Limitations and risks

- Approval evidence, retry priors, branch observations, and CI payloads are
  caller-supplied. Structural validation cannot prove reviewer identity, write
  authority, or that a head SHA is current.
- Cross-run retry detection requires the caller to supply prior attempt
  digests; there is no durable state or scheduler.
- The optional event interface is not a distributed tracing backend. The
  repository documents that no generic tracing sink exists.
- Other unmerged branches claim overlapping integration-control paths with
  different vocabularies. Owner reconciliation is required before merge.
- No workflow invokes the CLI. Adoption is manual until a reviewed workflow
  change is approved.

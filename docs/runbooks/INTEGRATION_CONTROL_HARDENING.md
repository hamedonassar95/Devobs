# Integration Control Hardening Runbook

Scope: offline, deterministic operation of the hardening diagnostics documented
in [INTEGRATION_CONTROL_HARDENING.md](../architecture/INTEGRATION_CONTROL_HARDENING.md).
No network, agent dispatch, merge, deployment, billing action, destructive
action, or branch-protection change is approved by this runbook.

## 1. Preconditions

- Work from an isolated feature worktree on
  `feature/intelligent-integration-plane-hardening`.
- Confirm a clean tree and the expected base:

```powershell
git status --porcelain=v1 --branch
git rev-parse HEAD origin/main
python scripts/milestone_ledger.py --summary
```

- The base for this branch is `cfa1e17ee1575da90a0bb4fe30800c6df3b68668`.
  P01 and AI-9 remain `BLOCKED`; Codex runtime acceptance remains `OPEN`.

## 2. Baseline verification

```powershell
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
python -m unittest tests.test_two_agent_tasks -v
python -m unittest tests.test_python_source_coverage tests.test_python_dependency_automation -v
python -m unittest discover -s tests/incidents -p "test_observability.py" -v
python -m compileall -q devobs/integration_control tests/integration_control
git diff --check
```

Expected final lines for the first command on the reviewed SHA:

```text
Ran 48 tests in <duration>s

OK
```

## 3. Run one hardened snapshot

```powershell
python -m devobs.integration_control --input snapshot.json --format json
```

Optional evidence inputs:

```powershell
python -m devobs.integration_control `
  --input snapshot.json `
  --format json `
  --approval-evidence approval-evidence.json `
  --retry-policy retry-policy.json
```

Both optional files are local UTF-8 JSON, loaded with the same strict parser as
the snapshot (bounded size, duplicate-key rejection, no non-finite constants).

### Approval-evidence file

```json
[
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
]
```

Supply one record for each of `merge`, `deploy`, `billing`, and `production`.
A record that satisfies the canonical human gate yields only
`APPROVAL_EVIDENCE_PRESENT`; it does **not** authorize anything.

### Retry-policy file

```json
{
  "max_identical_retries": 1,
  "prior_attempt_digests": []
}
```

The current manifest digest is emitted as `HARDENING_MANIFEST_DIGEST` in the
report findings message. Copy its full digest into `prior_attempt_digests` only
when the operator has independently confirmed that the identical snapshot is a
repeat attempt.

## 4. Exit codes

| Code | Decision | Operator action |
| --- | --- | --- |
| 0 | `PROCEED_TO_HUMAN_REVIEW` | Technical readiness only. Continue normal human review. |
| 1 | `BLOCKED` | Do not execute. Read findings and resolve the blocker. |
| 2 | `UNVERIFIED` | Do not treat as approval. Supply bounded evidence or re-run after evidence exists. |
| 3 | `INVALID` | Fix the input envelope or encoding; no manifest was evaluated. |

Unreadable optional files fail closed: an unreadable approval file produces
`APPROVAL_EVIDENCE_INVALID`; an unreadable retry policy produces
`RETRY_POLICY_INVALID`.

## 5. Finding interpretation

- `HARDENING_MANIFEST_DIGEST`: identify which manifest was evaluated. Advisory.
- `APPROVAL_EVIDENCE_*`: explicit approval-record diagnostics. Never authority.
- `UNAUTHORIZED_ACTION_REQUESTED`: task contract asked for a restricted or
  destructive action. Remove or separately approve through the existing human
  process; this tool grants nothing.
- `UNSAFE_RETRY_LOOP`: duplicate non-complete retry claims or a repeated prior
  attempt. Stop the loop; do not re-dispatch.
- `BLOCKED_TASK_RETAINS_OWNERSHIP`, `CONCURRENT_FILE_OWNERSHIP`, and
  `CONCURRENT_BRANCH_OWNERSHIP`: canonical validator findings. Ownership stays
  with the blocked or running task until a reviewed release.
- `HARDENING_INTERNAL_ERROR`: fail closed; capture the run ID and report digest,
  then escalate. Do not retry blindly because repeated digests are blockers.

## 6. Observability

The adapter is a library API; the CLI supplies no sink by default.

```python
from devobs.integration_control.control_events import emit_control_events, make_memory_sink

sink = make_memory_sink()
emit_control_events(report, sinks=[sink])
```

Use `EVENT_INTERFACE` to confirm whether the merged incident observability
boundary or the offline fallback is active. Events contain only bounded report
metadata and allowlisted names. Never place credentials, tokens, private keys,
or customer data in a report or event field.

## 7. Secret handling

- Use synthetic or sanitized evidence only.
- Never paste tokens, credentials, or private keys into fixture JSON.
- If `SECRET_MATERIAL_DETECTED` appears, discard the source, replace the input
  with sanitized data, and re-run. Do not copy raw input into the PR body.
- Do not start Keycloak or generate signing material. The local exception is
  inactive until the owner's reconciliation PR is merged and each run receives
  separate explicit approval.

## 8. PR delivery

- Push only the reviewed feature branch. Never push directly to `main`.
- Open the pull request as a **Draft**. Do not mark it ready for review, enable
  auto-merge, merge, or deploy without explicit owner approval.
- Include the head SHA, exact test commands/final lines, hosted CI evidence,
  `git diff --stat`, and outstanding risks.

GitHub documents the UI path as **Create Draft Pull Request** in
[Creating a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request),
and the REST body field `draft` in
[Create a pull request](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request).

## 9. Outstanding risks

- Caller-supplied evidence is not proof of identity, authority, or live state.
- No scheduler consumes retry priors; cross-run loops require operator input.
- Other active branches overlap integration-control paths and must be
  reconciled by the owner.
- Hosted CI is authoritative for security scanning; local Bandit/Ruff/pip-audit
  modules are not installed in this environment.

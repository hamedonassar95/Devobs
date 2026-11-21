# Offline agent approval gates (DRY_RUN only)

**Scope.** This gate validates one recorded human approval against one proposed
Devobs agent task. It is an additive layer over the existing
[two-agent offline task contract](TWO_AGENT_COORDINATION.md) and reuses
`scripts/check_two_agent_tasks.py` as the manifest rule source of truth. It does
not create a second policy engine.

It reads one local JSON request, prints one structured verdict, and exits. It
never starts an agent, executes a stored command, calls a network service,
changes Git or cloud state, creates or reads credentials, grants IAM, or records
a merge, deploy, billing, production or Phase 8 decision. `ALLOW` is advisory
validation evidence only; every human gate remains pending and separate.

## Run

```sh
python -m devobs.agent_security.approval_gates --request /path/to/request.json
python -m unittest discover -s tests -p "test_agent_approval_gates.py" -v
```

Exit codes are fail-closed:

| Code | Decision | Meaning |
| --- | --- | --- |
| `0` | `ALLOW` | The approval matched the request; no authority was granted. |
| `1` | `DENY` | The approval, task, action, scope or policy state failed validation. |
| `2` | `UNVERIFIED` | Required evidence or the shared validator was unavailable. |

A missing, malformed, oversized, symlinked, BOM-prefixed or duplicate-key input
file produces `DENY` with reason `malformed_request`. Missing policy state
produces `UNVERIFIED`, never `ALLOW`.

## Request shape

The request must be UTF-8 JSON of at most 512 KiB with exactly these keys:

```json
{
  "schema_version": 1,
  "mode": "DRY_RUN",
  "task_id": "TASK-001",
  "requested_action": "code_change",
  "manifest": { "...": "the existing two-agent task manifest" },
  "approval": {
    "schema_version": 1,
    "approval_id": "APR-001",
    "task_id": "TASK-001",
    "agent": "CODEX",
    "action": "code_change",
    "scope": {
      "repository": "OWNER/REPO",
      "branch": "feature/example",
      "affected_files": ["devobs/agent_security/approval_gates.py"],
      "source_sha": null
    },
    "task_fingerprint": "sha256:<64 lowercase hex chars>",
    "policy_version": 3,
    "issued_at": "2026-11-21T09:00:00Z",
    "expires_at": "2026-11-21T10:30:00Z"
  },
  "policy_state": {
    "schema_version": 1,
    "status": "ACTIVE",
    "version": 3,
    "active_approvals": ["APR-001"],
    "revoked_approvals": [],
    "consumed_approvals": []
  },
  "evaluated_at": "2026-11-21T10:00:00Z"
}
```

The caller owns the approval registry and supplies `policy_state`. The validator
never fetches it. Revocation and consumption outrank `active_approvals`: an
approval ID that appears in `revoked_approvals` is denied as `approval_revoked`,
and one that appears in `consumed_approvals` is denied as `approval_replayed`,
even if it is still listed as active. Put a one-time approval ID in
`consumed_approvals` after its first accepted use.

`task_fingerprint` is a deterministic SHA-256 digest of the canonical task
identity: ID, repository, assigned agent, branch, normalized affected files,
status, source SHA and sorted requested actions. It is staleness evidence, not
a signature, token or approval grant.

## Checks

Every `ALLOW` must pass all of these:

1. **Request shape and DRY_RUN mode.** Unknown keys, wrong types and modes
   other than `DRY_RUN` fail closed.
2. **Shared contract.** The manifest must return `PASS` from the existing
   two-agent validator with no conflicts or blocked tasks. An exception or
   unknown validator decision yields `UNVERIFIED`.
3. **Task identity.** `task_id` must name exactly one valid task in the
   manifest and match the approval's `task_id`.
4. **Requested action.** The action must be one of `code_change`, `review`,
   `test` or `documentation`, must appear in the task's `requested_actions`,
   and must equal the approval's `action`. `merge`, `deploy`, `billing` and
   `production` are always denied here and remain human-only.
5. **Approval scope and staleness.** Repository, branch, affected files and
   source SHA must exactly match the current task, and the task fingerprint
   must still match. Branch, file or source changes invalidate the approval.
6. **Agent and state.** The approval agent must match the task's assigned
   worker, and the task must be in `planned` or `in_progress`.
7. **Time.** `evaluated_at` must be within the approval's validity window and
   the lifetime must be positive and at most seven days.
8. **Current policy state.** Policy status must be `ACTIVE`, the policy version
   must match, the approval ID must be active, and it must be neither revoked
   nor consumed.

Reasons are stable codes such as `missing_approval`, `approval_expired`,
`approval_not_yet_valid`, `approval_lifetime_too_long`,
`approval_action_mismatch`, `unauthorized_action`, `action_not_requested`,
`restricted_action_requested`, `cross_task_authorization_denied`,
`approval_agent_mismatch`, `task_not_actionable`, `stale_approval`,
`approval_revoked`, `approval_replayed`, `approval_not_active`,
`policy_state_inactive`, `policy_version_mismatch`, `unknown_task`,
`task_identity_invalid`, `contract_validation_failed`, `validator_unavailable`
and `missing_required_evidence`.

## Structured output and audit

The result contains the decision, sorted reason codes, checks, advisory
authorization block, shared validator decision, bounded summary, one audit
event, fixed human-approval actions, and errors. The authorization block always
sets `execution_granted: false`, `approval_granted: false`, `executor: null`,
`scope: "advisory_only"` and `mode: "DRY_RUN"`.

The single audit event contains only `event`, `decision`, `reason_codes`,
`task_id`, `agent`, `action`, `approval_id`, `approval_digest`,
`policy_version`, `mode` and `source`. Identifiers are redacted unless they
match the shared contract; free-form task evidence is never copied into the
verdict. `approval_digest` is a SHA-256 digest of the bounded approval record,
not its contents. Repeated evaluation of the same input is byte-for-byte
deterministic and does not mutate the request.

## Boundaries

- This is not a task executor. There is no production dispatch path.
- `ALLOW` never approves a merge, deployment, billing change, production
  change, IAM change, secret access, paid inference or Phase 8 human gate.
- The validator does not verify signatures or identity-provider tokens. A
  trusted caller must own the approval registry and present it as policy state.
- It does not change the existing two-agent manifest schema, validator exit
  codes, CI, Pages, Vercel or release gates.
- P01 remains NO-GO/BLOCKED, AI-9 remains BLOCKED and Codex runtime acceptance
  remains OPEN.

## ملخص عربي

هذه البوابة تفحص موافقة بشرية واحدة مقابل مهمة واحدة محليًا وبوضع `DRY_RUN`
فقط. ترفض الموافقة المفقودة أو المنتهية أو المكررة أو المسحوبة أو القديمة أو
المخصصة لمهمة أخرى، ولا تبدأ وكيلًا ولا تنفّذ أمرًا ولا تمنح أي موافقة بشرية.
نتيجة `ALLOW` مجرد دليل فحص استشاري؛ بوابات الدمج والنشر والفوترة والإنتاج
وصيانة الأسرار والمرحلة الثامنة تبقى قرارات بشرية منفصلة.

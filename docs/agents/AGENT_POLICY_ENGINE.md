# Agent Security Policy Engine (advisory, read-only)

**Scope:** a deterministic policy gate for *proposed* multi-agent actions. It
wraps the existing [two-agent manifest contract](TWO_AGENT_COORDINATION.md),
reuses `scripts/check_two_agent_tasks.py` as the rule source of truth, and adds
deny-by-default checks before a human starts any worker.

It is not an executor, scheduler, credential issuer or approval mechanism. It
never starts an agent, runs a stored command, writes a file, changes Git state,
calls a network service or grants merge, deploy, billing, production or Phase 8
approval. `ALLOW` is advisory evidence for review, **not** an execution grant:
every result has `authorization.execution_granted: false`.

## Request contract

The CLI reads one bounded UTF-8 JSON file (maximum 512 KiB, no byte-order mark,
no duplicate JSON keys). Exact required keys are `schema_version`, `mode` and
`manifest`; optional-but-required evidence keys are `agent_permissions` and
`locks`. Unknown keys fail closed.

```json
{
  "schema_version": 1,
  "mode": "DRY_RUN",
  "manifest": {
    "schema_version": 1,
    "repositories": ["hamedonassar95/Devobs"],
    "agents": {
      "CODEX": {"enabled": true},
      "OPENCODE": {"enabled": true}
    },
    "approval": {
      "merge": "pending_human",
      "deploy": "pending_human",
      "billing": "pending_human",
      "production": "pending_human"
    },
    "tasks": []
  },
  "agent_permissions": {
    "CODEX": ["code_change", "review", "test", "documentation"],
    "OPENCODE": ["review", "documentation"]
  },
  "locks": [
    {"path": "docs/shared.md", "owner": "TASK-001"}
  ]
}
```

- `mode` must be exactly `DRY_RUN`; there is no execute mode.
- `agent_permissions` must declare every agent registered in the manifest.
  Values may contain only the four approved task actions. A disabled agent
  must declare no permissions.
- `locks` must be an explicit list of `{path, owner}` entries. `path` must be a
  unique repository-relative path using the shared validator's path rules;
  `owner` must be a task ID declared in the manifest. An empty list is valid
  and means the caller explicitly declares no external locks.
- `manifest` must satisfy the complete two-agent contract. Restricted actions
  (`merge`, `deploy`, `billing`, `production`) are never valid in a task.

## Checks

| Check | Deny or unverified when |
| --- | --- |
| Request shape | Required keys missing, unknown keys present, wrong schema version, malformed JSON or duplicate keys. |
| DRY_RUN | `mode` is anything other than `DRY_RUN`. |
| Declared permissions | Permission evidence absent, mismatched to registered agents, malformed, or granted to a disabled agent. |
| Task authorization | Assigned agent unregistered/disabled, status not `planned` or `in_progress`, or action outside the agent's declared permissions. |
| Unauthorized operations | Restricted or unknown action requested by any task. |
| File ownership/locks | A lock path is held by a different task; lock evidence is malformed or names an unknown owner. |
| Protected refs | Branch is `main`, `master`, `develop`, `release`, malformed, or contains traversal/empty ref components. |
| Human gates | Any approval field is not `pending_human`. |
| Shared contract | Validator returns `FAIL`/`BLOCKED`, raises, is unavailable, or returns an unknown decision. |

Completed tasks are historical evidence and are excluded from proposed-action
checks. Every other status is denied as not actionable. The shared validator's
conflict and blocked-task results are also surfaced as reason codes.

## Decisions and exit codes

| Decision | Exit | Meaning |
| --- | ---: | --- |
| `ALLOW` | 0 | All checks passed. Advisory only; a human must still review and approve. |
| `DENY` | 1 | A confirmed violation was found. Never authorizing. |
| `UNVERIFIED` | 2 | Required evidence is missing/unreadable or the validator outcome is unknown. Never authorizing. |

`UNVERIFIED` is never equivalent to `ALLOW`. If both definitive denials and
missing evidence are present, the result is `DENY` and all reason codes are
reported.

## Usage

```sh
python -m devobs.security.agent_policy --help
python -m devobs.security.agent_policy --request /path/to/policy-request.json
python -m unittest discover -s tests -p "test_agent_policy.py" -v
```

The command prints one sorted JSON object to stdout and returns the exit code
above. It accepts only a local request path; there is no network, Git or agent
interface.

## Structured result

```json
{
  "policy": "devobs_agent_security_policy",
  "schema_version": 1,
  "decision": "DENY",
  "reason_codes": ["human_approval_altered"],
  "authorization": {
    "execution_granted": false,
    "scope": "advisory_only",
    "mode": "DRY_RUN",
    "human_approval_required": true,
    "executor": null
  },
  "validator_decision": "FAIL",
  "summary": {
    "tasks": 1,
    "active_tasks": 1,
    "agents": ["CODEX", "OPENCODE"],
    "locks": 0,
    "reasons": 1
  },
  "audit_events": [
    {
      "event": "agent_policy_evaluation",
      "decision": "DENY",
      "reason_codes": ["human_approval_altered"],
      "task_ids": ["TASK-001"],
      "agents": ["CODEX", "OPENCODE"],
      "counts": {"tasks": 1, "active_tasks": 1, "locks": 0, "reasons": 1},
      "source": "devobs_agent_security_policy"
    }
  ]
}
```

Audit events are deterministic and sanitized. They contain only the event name,
decision, reason codes, sanitized task IDs, agent names, counts and source. They
do **not** contain command strings, verification evidence, file paths, branch
names, approval values, tokens, logs or free-form request text. Evaluation is
side-effect-free and sorts all reason codes and identifiers.

## Troubleshooting

| Reason code | Action |
| --- | --- |
| `malformed_request` | Fix the root keys, schema version and JSON encoding; reject BOM and duplicate keys. |
| `dry_run_required` | Set `mode` to `DRY_RUN`; no execute mode exists. |
| `missing_required_evidence` | Provide `agent_permissions` and `locks` (use `[]` for no locks). |
| `invalid_permission_evidence` | Declare every registered agent and only approved task actions. |
| `invalid_lock_evidence` | Use normalized repository-relative paths and existing task IDs as owners. |
| `unauthorized_agent` / `agent_not_enabled` | Assign tasks only to registered, enabled worker roles. |
| `action_not_declared` / `unauthorized_operation` | Remove the action or declare it for that agent; restricted actions are never allowed. |
| `lock_conflict` / `ownership_conflict` | Reassign the file or release the lock through a reviewed change. |
| `protected_branch_violation` | Use a valid `feature/`, `fix/`, `docs/` or `chore/` ref. |
| `human_approval_altered` | Restore all four approval fields to `pending_human`. |
| `contract_validation_failed` / `contract_blocked` | Fix the shared two-agent manifest first, then rerun. |
| `validator_unavailable` / `validator_decision_unknown` | Restore `scripts/check_two_agent_tasks.py`; never bypass it. |

## Human gates and limitations

`ALLOW` does not prove that an agent actually ran, that evidence is truthful,
that Git state was unchanged outside declared files, or that a hosted policy
was enforced. It is a local pre-execution check for a human operator. P01 stays
**BLOCKED / NO-GO**, AI-9 **BLOCKED**, and Codex runtime acceptance **OPEN**.
Existing CI, CodeQL, Trivy, tenant-isolation checks and Phase 8 approval remain
mandatory.

## الاستخدام بالعربية — ملخص

محرك السياسات هذا يفحص الطلبات المقترحة قبل تشغيل أي وكيل. يعيد القرار
`ALLOW` أو `DENY` أو `UNVERIFIED` مع رموز أسباب منظمة. لا يشغّل أوامر، لا
يتصل بالإنترنت، لا يغيّر Git، ولا يمنح صلاحية دمج أو نشر. الوضع `DRY_RUN`
إلزامي، وقيمة `UNVERIFIED` ليست إذنًا أبدًا. سجلات التدقيق مُطهّرة ولا تحتوي
أسرارًا أو أوامر أو مسارات.

## Rollback

Remove the three commits from this branch in reverse order
(`docs`, `feat`, `test`). No runtime state, hosted configuration, secret or
production system is changed by this feature.

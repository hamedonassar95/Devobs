# Offline agent security audit (advisory; no agents started)

**Scope:** a read-only safety layer over the local two-worker task manifest defined
in [TWO_AGENT_COORDINATION.md](TWO_AGENT_COORDINATION.md). The engine reuses
`scripts/check_two_agent_tasks.py` as the contract source of truth and adds
independent findings for coordination risks that should be reviewed *before* a
human starts `CODEX` or `OPENCODE`.

It reads one local JSON file and prints one JSON result. It never starts an
agent, executes a manifest command, calls a network service, changes Git state,
writes files, grants an approval or promotes a release gate. A `PASS` result is
advisory coordination evidence only.

## Usage

```sh
python -m devobs.agents.security_audit --manifest /path/to/tasks.json
python devobs/agents/security_audit.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_agent_security_audit.py" -v
```

On Windows hosts where `python3` is unavailable, use `python`; both commands run
the same Python 3.12-compatible standard-library code. The only CLI argument is
`--manifest`, the path to an existing UTF-8 JSON manifest (maximum 512 KiB).

## Manifest input

The accepted manifest is the same bounded contract as the two-agent checker:
exact top-level keys `schema_version`, `repositories`, `agents`, `approval` and
`tasks`. Duplicate JSON keys, unknown top-level fields, oversized files, invalid
UTF-8 (including a byte-order mark), unreadable paths and deeply nested JSON fail
closed. See
[TWO_AGENT_COORDINATION.md](TWO_AGENT_COORDINATION.md#contract) for the task-field
contract.

## Structured result

| Field | Meaning |
| --- | --- |
| `audit_type` | Always `advisory_agent_security_audit`. |
| `schema_version` | Audit result schema, currently `1`. |
| `decision` | `PASS`, `BLOCKED` or `FAIL`. |
| `read_only`, `dispatched` | Always `true` and `false`; the engine has no dispatch path. |
| `source_label` | Sanitized manifest path supplied by the operator. |
| `findings` | Ordered list of `{id, category, severity, title, evidence, recommendation}`. |
| `summary` | Task count, finding count and counts by severity. |
| `validator` | Unmodified `check_two_agent_tasks.evaluate` result for the same manifest. |
| `errors` | Sanitized shared-contract or parse errors. |
| `human_approval_actions` | Reminder list printed for every decision, including `PASS`. |

Every finding carries a bounded, printable `evidence` object. Evidence values are
derived from manifest data or the shared validator; no command output, token,
credential, secret or raw log is collected.

## Findings

| Category | Severity | Trigger |
| --- | --- | --- |
| `duplicate_task_ownership` | HIGH | The same task ID is assigned more than once, with all agents and branches listed. |
| `conflicting_file_assignments` | HIGH | Two non-complete tasks in the same repository declare the same path, compared case-insensitively, without a dependency order. Blocked tasks retain ownership under the shared contract. |
| `protected_branch_violation` | HIGH | A task uses `main`, `master`, `release`, `develop`, an invalid ref namespace, an empty ref component or traversal such as `feature/../main`. |
| `missing_dependency` | HIGH | A task references an unknown task ID. |
| `blocked_dependency` | MEDIUM | A transitive dependency is not `complete`. |
| `missing_human_approval` | CRITICAL | Any `merge`, `deploy`, `billing` or `production` approval field is missing or not `pending_human`, or a task requests a restricted action. |
| `stale_task_assignment` | HIGH | An `evidence_ready` or `complete` task lacks a 40-hex `source_sha`, non-empty verification commands, `PASS` result or non-empty evidence. |
| `contract_validation_failure` | CRITICAL | The shared validator returned one or more errors. |
| `invalid_manifest` | CRITICAL | The manifest could not be parsed safely. |
| `contract_unavailable` | CRITICAL | The shared validator could not be imported. |

The protected-ref check adds traversal and empty-component rejection on top of
the validator's branch pattern. [Git's reference-name rules](https://git-scm.com/docs/git-check-ref-format)
are the platform basis for treating those forms as unsafe.

## Decisions and exit codes

| Decision | Exit | Rule |
| --- | --- | --- |
| `PASS` | 0 | Shared validator says `PASS` and there are no findings. |
| `BLOCKED` | 1 | No CRITICAL finding and no validator failure, but at least one finding or validator `BLOCKED`. |
| `FAIL` | 2 | Any CRITICAL finding, shared validator `FAIL`, unreadable manifest or unavailable validator. |

The engine fails closed on absent or unexpected evidence: malformed task fields
produce a `CRITICAL` contract finding instead of a traceback, and every exit path
emits the JSON result described above. It does not silently downgrade a failure
to `PASS`.

## Human gates and limitations

- This audit does **not** verify that an agent ran, that claimed evidence is
  truthful, that a remote branch is actually protected, or that files were not
  changed outside the declared paths.
- `PASS` never permits merging, deployment, billing, production access, IAM
  changes, secret access or billable inference.
- Existing CI, CodeQL, Trivy, tenant-isolation checks and Phase 8 owner approval
  remain mandatory. P01 stays **BLOCKED / NO-GO**, AI-9 **BLOCKED**, and Codex
  runtime acceptance **OPEN**; this tool changes none of them.
- The audit is a coordination guard for a human operator, not an enforcement,
  authorization or deployment boundary.

## Rollback

Remove `devobs/agents/security_audit.py`, `tests/test_agent_security_audit.py`
and this document, and restore the README paragraph that was added with them.
No runtime state, hosted configuration or repository permission is changed by
the audit, so removing the files fully removes the feature.

## استخدام بالعربية — ملخص

هذه الأداة تفحص ملف المهام المحلي قبل أن يقرر الإنسان تشغيل أي عامل. تقرأ JSON
محليًا فقط وتُبلغ عن تكرار الملكية وتعارض الملفات والفروع المحمية والتبعيات
المفقودة أو المعطلة وتغيير موافقات الإنسان والأدلة القديمة. لا تشغّل وكيلًا ولا
تتصل بالإنترنت ولا تمنح صلاحية دمج أو نشر أو فوترة أو إنتاج. نتيجة `PASS` ليست
موافقة؛ بوابات P01 وAI-9 وتشغيل Codex تبقى كما هي.

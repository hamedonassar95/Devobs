# Offline two-agent task coordination (CODEX + OPENCODE)

**Scope:** a local, offline contract for assigning independent development tasks
to two distinct worker roles. The checker validates a JSON manifest; it does not
start, dispatch, authenticate, schedule or pay for any agent. A passing result is
advisory coordination evidence, not merge approval, runtime acceptance or a
release gate decision.

## Roles

| Role | Name in manifest | Boundary |
| --- | --- | --- |
| Worker A | `CODEX` | Owns only its declared tasks, branch and files. |
| Worker B | `OPENCODE` | Independent worker; never inherits `CODEX` ownership. |

Both roles are registered and enabled by default. A future agent name may be
declared with `"enabled": false`, but it is not usable until a separately
reviewed contract change explicitly enables it. Declaring a new agent does not
grant it tasks.

## Contract

The manifest is a UTF-8 JSON file, at most 512 KiB. Unknown or missing top-level
fields fail closed. Exact top-level keys: `schema_version`, `repositories`,
`agents`, `approval`, `tasks`.

```json
{
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
  "tasks": [
    {
      "id": "TASK-001",
      "repository": "hamedonassar95/Devobs",
      "assigned_agent": "CODEX",
      "branch": "feature/example-codex",
      "affected_files": ["shared/module.py"],
      "dependencies": [],
      "status": "complete",
      "previous_status": "evidence_ready",
      "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "verification": {
        "commands": ["python -m unittest discover -s tests -v"],
        "result": "PASS",
        "evidence": "offline local tests: 21 passed"
      },
      "pr_reference": "#123",
      "requested_actions": ["code_change", "test"]
    },
    {
      "id": "TASK-002",
      "repository": "hamedonassar95/Devobs",
      "assigned_agent": "OPENCODE",
      "branch": "feature/example-opencode",
      "affected_files": ["shared/module.py"],
      "dependencies": ["TASK-001"],
      "status": "planned",
      "previous_status": "none",
      "source_sha": null,
      "verification": {"commands": [], "result": "PENDING", "evidence": ""},
      "pr_reference": null,
      "requested_actions": ["review"]
    }
  ]
}
```

### Task fields

| Field | Rule |
| --- | --- |
| `id` | Unique, uppercase, 3-64 chars (`A-Z0-9_-`). |
| `repository` | Must be listed in `repositories`. Tasks may span authorized repositories. |
| `assigned_agent` | Must exist in `agents` and be enabled. |
| `branch` | Non-`main` `feature/`, `fix/`, `docs/` or `chore/` branch. |
| `affected_files` | Non-empty unique repository-relative paths; `..`, absolute and drive paths are rejected. `\\` is normalised to `/`. |
| `dependencies` | Task IDs in the same repository; no self-reference, duplicates or cycles. |
| `status` | One of `planned`, `in_progress`, `evidence_ready`, `complete`, `blocked`. |
| `previous_status` | `none` or a status; the pair must be an allowed transition. |
| `source_sha` | `null` or 40 lowercase hex characters; required for `evidence_ready` and `complete`. |
| `verification` | `commands` (bounded strings), `result` (`PENDING`, `PASS`, `FAIL`), `evidence` (bounded text). |
| `pr_reference` | `null`, `#<number>` or a `https://github.com/<owner>/<repo>/pull/<number>` URL. |
| `requested_actions` | From `code_change`, `review`, `test`, `documentation`. |

### Allowed status transitions

- `none` → `planned`
- `planned` → `planned`, `in_progress`, `blocked`
- `in_progress` → `in_progress`, `evidence_ready`, `blocked`
- `evidence_ready` → `evidence_ready`, `complete`, `in_progress`, `blocked`
- `blocked` → `blocked`, `planned`, `in_progress`
- `complete` → `complete` (terminal; no other transition)

A task may be marked `complete` only with a 40-character `source_sha` and
`verification.result` of `PASS` with at least one command and non-empty evidence.
A `PASS` result is invalid while the task is still `planned` or `in_progress`.

## Checks and exit codes

| Decision | Exit | Meaning |
| --- | --- | --- |
| `PASS` | 0 | Contract valid; no conflicts and no unresolved dependencies. |
| `BLOCKED` | 1 | Valid contract, but a task is blocked or ownership conflicts exist. |
| `FAIL` | 2 | Invalid contract or unreadable manifest; never treated as approval. |

The tool reports `blocked_tasks` (`task_blocked`, `unresolved_dependency`,
`agent_not_enabled`) and `conflicts` (`concurrent_file_ownership`,
`concurrent_branch_ownership`). Every task with `status: "blocked"` is reported
with reason `task_blocked` and its unresolved dependencies; a manifest containing
blocked work returns `BLOCKED` (exit 1), never `PASS`. Blocked tasks keep their
declared files and branch until a separately reviewed release mechanism removes
or reassigns them, so a blocked task sharing a file or branch with active work is
reported as a conflict. Dependency-ordered tasks sharing a file are allowed while
the predecessor is `complete`; two active or blocked tasks on the same file or
branch are blocked. Transitive incomplete dependencies are reported for each
blocked task. Completed tasks are excluded from active ownership checks.

```sh
python scripts/check_two_agent_tasks.py --help
python scripts/check_two_agent_tasks.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
```

On Windows hosts where `python3` is unavailable, use `python`; both invoke the
same Python 3.12-compatible code. The checker uses only the standard library and
makes no network request, Git write, credential read or scheduled action.

## Local dispatch preflight (no dispatch)

[The agent dispatch operating guide](AGENT_DISPATCH_OPERATING_GUIDE.md) adds a
local advisory layer on top of this validator:

```sh
python scripts/agent_dispatch_preflight.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
```

The preflight reuses `check_two_agent_tasks.evaluate` as the rule source of
truth. It detects whether `codex` and `opencode` are present on the local
`PATH` without invoking them, prepares separate `CODEX_instructions.md` and
`OPENCODE_instructions.md` files, and prints five human-approval actions.
`DRY_RUN` is the default and only mode; there is no dispatch command. A missing
required CLI, a conflict, or an unauthorized task blocks instruction creation.
`PASS` (0), `BLOCKED` (1) and `FAIL` (2) keep the same advisory meaning as the
checker and never grant approval.

## Human gates and limitations

`approval.merge`, `approval.deploy`, `approval.billing` and `approval.production`
must all be `pending_human`. A task that requests those actions fails closed.
Nothing in this manifest or its PASS result permits merging, deployment, billing,
production access, IAM changes, secret access or AI inference. Existing CI,
CodeQL, Trivy, tenant-isolation checks and the Phase 8 human approval remain in
force. P01 remains **BLOCKED / NO-GO**, AI-9 **BLOCKED**, and Codex runtime
acceptance **OPEN**; this offline contract changes none of them.

The checker cannot prove that a claimed agent actually ran, that evidence is
truthful, that a branch was protected, or that files were not changed outside the
declared paths. It is a coordination guard for a human operator, not an
authorization or enforcement boundary.

## الاستخدام بالعربية — دليل مختصر

الغرض من هذا الفحص هو **تنسيق مهام يدوية فقط** بين عاملين منفصلين: `CODEX`
و`OPENCODE`. الأداة تقرأ ملف JSON محليًا وتتحقق من الفروع والملفات والتبعيات
والأدلة، لكنها **لا تشغّل أي وكيل** ولا تتصل بالإنترنت ولا تمنح صلاحية دمج أو
نشر أو فوترة أو تغيير إنتاج.

1. أنشئ ملف مهام محليًا وفق العقد الموضح أعلاه، واجعل كل مهمة تملك معرّفًا
   فريدًا وفرعًا مستقلًا وقائمة ملفات واضحة.
2. اربط المهام بالتبعيات؛ إذا كانت مهمة تعتمد على أخرى غير مكتملة فتظهر
   `BLOCKED` ولا يجوز اعتبارها جاهزة.
3. لا تسمح لعاملين بتعديل الملف نفسه في الوقت نفسه؛ الفحص يمنع التعارض ويسمح
   بالتسلسل عند اكتمال المهمة السابقة. المهمة `blocked` تبقى مالكة لملفاتها
   وفرعها حتى إصدار مراجع منفصل، وتُبلغ عنها النتيجة `BLOCKED` وليس `PASS`.
4. لا تُعلَّم مهمة `complete` إلا بعد `source_sha` صحيح و`verification.result`
   بقيمة `PASS` مع أمر ودليل مكتوب.
5. قيم `approval` الأربع تبقى `pending_human` دائمًا؛ موافقة الإنسان مطلوبة قبل
   أي دمج أو نشر أو فوترة أو تغيير إنتاج.

أوامر التحقق على Windows:

```powershell
python scripts\check_two_agent_tasks.py --manifest .\tasks.json
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
```

نتائج `PASS` و`BLOCKED` و`FAIL` تعني على الترتيب: صالح بلا تعارض، صالح لكنه
محجوز، أو عقد غير صالح. النتيجة `PASS` ليست إذنًا بالدمج. لا تُشفّر الأسرار
أو بيانات العملاء داخل ملف المهام؛ استخدم مساراتًا محلية وأدلة نصية مُطهّرة فقط.

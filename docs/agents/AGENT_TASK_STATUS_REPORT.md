# Offline agent task-status report (advisory only)

**Scope:** `tools/agent_task_status_report.py` is a read-only, offline reporter for
the existing two-worker task manifest contract. It reuses
`scripts/check_two_agent_tasks.py` definitions and validator, then presents an
independent advisory view. It does not start an agent, fetch GitHub data,
execute manifest commands, change Git state, read credentials, or grant merge,
deploy, billing or production approval.

**Evidence policy:** all output is labelled **ADVISORY LOCAL DATA**. A manifest
value of `verification.result = "PASS"` is only a claim. The reporter classifies
it as `PASS_CLAIM_UNVERIFIED`, never `VERIFIED`. Fresh commands, an exact source
SHA, reviewed CI evidence and the Phase 8 human gate remain necessary. Existing
P01 (`NO-GO`), AI-9 (`BLOCKED`) and Codex runtime acceptance (`OPEN`) gates are
unchanged.

## Input

One local UTF-8 JSON manifest, at most 512 KiB, following
[the two-agent contract](TWO_AGENT_COORDINATION.md). Only the `--manifest` path
is read. The path is not expanded from environment variables and the file is
never modified.

## Run

```powershell
python tools/agent_task_status_report.py --manifest .\tasks.json
python tools/agent_task_status_report.py --manifest .\tasks.json --json-only
python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
```

On hosts where `python3` is available, `python3` is equivalent. The script uses
Python 3.12 standard library modules only.

### Output channels

| Mode | stdout | stderr |
| --- | --- | --- |
| default | sanitized human-readable advisory report | one compact JSON summary |
| `--json-only` | one compact JSON summary | empty |

The JSON summary is always encoded with `ensure_ascii=True` and sorted keys, so
it is safe to consume as a single line. Exit codes match the existing contract:
`0` = advisory `PASS`, `1` = advisory `BLOCKED`, `2` = `FAIL` (invalid manifest,
unexpected validator shape, or missing shared contract).

## Displayed fields

For every task the report shows: task ID, assigned worker, repository, branch,
status, dependencies, blocked flag and reasons, unresolved dependencies, PR
reference, and verification evidence state. A separate blocked-task section keeps
blocked work visible even when the validator incorrectly returns `PASS`; the JSON
summary records both `validator_decision` and `effective_decision`.

Blocked reasons are derived independently from:

- explicit `status = "blocked"`;
- unresolved direct or transitive dependencies;
- `FAIL`, invalid, incomplete or status-incompatible PASS claims;
- validator `blocked_tasks` and `conflicts`.

## Sanitization

All untrusted strings are passed through `sanitize_display` before human output
and through the same sanitizer before JSON serialization. ANSI CSI/OSC sequences,
ESC bytes, C0/C1 controls, Unicode format/bidi controls, newlines and long input
are removed, collapsed or bounded. No stored verification command is executed or
reprinted. Treat the sanitized evidence excerpt as data, not as proof.

## Verification

```powershell
python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
python -m unittest discover -s tests -p "test_python_source_coverage.py" -v
python -m unittest discover -s tests -p "test_python_dependency_automation.py" -v
git diff --check
```

Bandit is pinned to `bandit==1.9.4` in `requirements-dev.txt` and hash-locked in
`requirements-dev.lock`. Run the repository security scan with the pinned
environment:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
python -m bandit -r scripts tools -x scripts/check_site.py
```

Pip documents `-r` and `--require-hashes` in its
[`pip install` reference](https://pip.pypa.io/en/stable/cli/pip_install/).
Bandit's official getting-started documentation describes recursive scanning
with [`-r`](https://bandit.readthedocs.io/en/latest/start.html#getting-started),
and its configuration documentation explains exclusions and `-c` config files
([Bandit Configuration](https://bandit.readthedocs.io/en/latest/config.html)).
Use `python -m bandit -h` for the exact `-x` and `-q` flag descriptions in the
pinned version.

**Windows hash-lock note:** `requirements-dev.lock` was generated without the
Windows-only `colorama` dependency of Bandit 1.9.4. A hash-checked install on
Windows therefore fails unless `colorama==0.4.6` is pinned in a temporary
combined requirements file outside the repository, using the published wheel
SHA256 `4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6`
from [PyPI](https://pypi.org/project/colorama/0.4.6/). Do not modify the tracked
lock file to work around this host-specific resolution difference.

## Limitations

- Local manifest text can be false or stale; the reporter cannot confirm an
  agent ran, CI passed, an SHA matches a remote commit, or evidence is truthful.
- Dependency and conflict detection reflects manifest state at read time only.
- The tool does not compare against GitHub, hosted CI, protected branch rules,
  CodeQL, Trivy or tenant-isolation checks.
- A successful run grants no approval and does not open any gate.

## الاستخدام بالعربية — تقرير حالة المهام

هذه الأداة **`ADVISORY LOCAL DATA`**؛ أي أنها تقرأ ملف مهام JSON محليًا فقط
وتعرض حالة المهام للمراجعة البشرية. هي **لا تشغّل وكلاء**، ولا تتصل بـGitHub،
ولا تنفّذ الأوامر المخزّنة في الملف، ولا تمنح صلاحية دمج أو نشر أو فوترة أو
تغيير إنتاج. بوابات P01 وAI-9 وتشغيل Codex تبقى كما هي.

### التشغيل

```powershell
python tools\agent_task_status_report.py --manifest .\tasks.json
python tools\agent_task_status_report.py --manifest .\tasks.json --json-only
python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
```

- الوضع الافتراضي: التقرير المقروء يظهر في stdout، وملخص JSON في stderr.
- مع `--json-only`: يظهر ملخص JSON فقط في stdout ولا شيء في stderr.
- رمز الخروج `0` يعني حالة استشارية `PASS`، و`1` يعني توجد مهام محجوبة،
  و`2` يعني أن الملف غير صالح أو تعذّر إنشاء التقرير.

### ما يعرضه التقرير

يعرض لكل مهمة: المعرّف، العامل المكلّف، المستودع، الفرع، الحالة، التبعيات،
ما إذا كانت محجوبة وأسباب الحجب، التبعيات غير المحلولة، مرجع PR، وحالة دليل
التحقق. تظهر المهام المحجوبة في قسم مستقل حتى لو أعاد الفاحص القديم `PASS`
خطأً. يعرض الملخص كلا من `validator_decision` و`effective_decision`.

### قاعدة الدليل

قيمة `PASS` داخل الملف ليست دليلًا على التحقق؛ التقرير يسميها
`PASS_CLAIM_UNVERIFIED` فقط. لا يُعتبر أي عمل `VERIFIED` بمجرد وجود كلمة `PASS`
في الملف. يلزم دائمًا SHA دقيق وأوامر جديدة ومراجعة CI وموافقة إنسان قبل أي
دمج أو نشر. التقرير ينظّف تسلسلات التحكم الطرفية والنصوص غير الموثوقة قبل
عرضها، لكنه لا يتحقق من صدق المحتوى.

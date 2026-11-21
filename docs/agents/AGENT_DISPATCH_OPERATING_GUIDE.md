# Offline agent dispatch preflight — operating guide

**Scope:** a local, advisory preflight for the existing
[two-agent task contract](TWO_AGENT_COORDINATION.md). It validates a JSON
manifest, detects whether the local `codex` and `opencode` executables are
present, and prepares separate instruction files for each worker role.

**It never dispatches.** No agent process is started, no CLI subcommand is
invoked, no network request is made, no credential or token is read, and no
human approval is granted. `DRY_RUN` is the default and only supported mode.
There is no dispatch mode.

## Why this exists

The merged foundation (`scripts/check_two_agent_tasks.py`) is the single source
of truth for manifest validity, dependency order, branch/file ownership, status
transitions, restricted actions and completion evidence. The preflight reuses
that validator instead of copying its rules. It adds only three local concerns:

1. Detect the two local CLIs by executable name.
2. Split validated task data into one instruction file per worker role.
3. Print the exact actions that remain with the human operator.

A `PASS` result is coordination evidence only. It is **not** proof that an agent
ran, that evidence is truthful, that a branch is protected, or that a release
gate passed. P01 remains **NO-GO / BLOCKED**, AI-9 remains **BLOCKED**, and
Codex runtime acceptance remains **OPEN**.

## Official references for detected executables

- Codex CLI command name `codex`: [OpenAI Codex CLI reference](https://developers.openai.com/codex/cli/reference).
- OpenCode CLI command name `opencode`: [OpenCode CLI documentation](https://opencode.ai/docs/cli/).
- Detection uses Python's standard-library [`shutil.which`](https://docs.python.org/3/library/shutil.html#shutil.which); the preflight does not execute or inspect the found binary.

These links document the public command names. They do not authorize use of a
model, paid inference, an API key, or a hosted service.

## Run locally

From the repository root:

```sh
python scripts/agent_dispatch_preflight.py --help
python scripts/agent_dispatch_preflight.py --manifest /path/to/tasks.json
python scripts/agent_dispatch_preflight.py --manifest /path/to/tasks.json --instructions-dir /path/to/instructions
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
```

On Windows hosts where `python3` is unavailable, use `python`. The script uses
only the Python 3.12 standard library.

### Flags

| Flag | Requirement | Behavior |
| --- | --- | --- |
| `--manifest` | Required | Local UTF-8 JSON manifest, at most 512 KiB. The same bound as the validator. |
| `--instructions-dir` | Optional | Output directory for worker instruction files. Defaults to `<manifest directory>/agent_dispatch_instructions`. |
| `--mode` | Optional | Accepts only `DRY_RUN` (default). Any other value is rejected by the CLI. |

Successful runs write exactly two files: `CODEX_instructions.md` and
`OPENCODE_instructions.md`. Existing output files are never overwritten; move
or delete old files before rerunning into the same directory. Failed or blocked
runs write no instruction files.

### Safe output behavior

Both instruction files are first staged as temporary files in the destination
directory, then linked into place. If staging or linking either file fails, the
preflight removes both staged files, removes either final file it created, and
removes any directories it created for the run. The result is `FAIL` (exit 2)
with `rejection_reason` set to `output_file_exists`,
`symlink_output_destination`, `output_write_failed`, or `output_cleanup_failed`
as applicable. A symlink, Windows junction, or other reparse point anywhere in
the output path is refused without writing through it.

The implementation relies on documented standard-library behavior:

- [`tempfile.mkstemp`](https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp):
  "There are no race conditions in the file's creation, assuming that the
  platform properly implements the `os.O_EXCL` flag for `os.open()`."
- [`os.link`](https://docs.python.org/3/library/os.html#os.link): "Create a hard
  link pointing to `src` named `dst`." Availability: "Unix, Windows."
- [`Path.is_symlink`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.is_symlink):
  "Return `True` if the path points to a symbolic link, even if that symlink is
  broken."
- [`stat.FILE_ATTRIBUTE_REPARSE_POINT`](https://docs.python.org/3/library/stat.html#stat.FILE_ATTRIBUTE_REPARSE_POINT)
  is checked as well, because a Windows junction is not reported by
  `Path.is_symlink()`.

## What is checked

| Check | Source | Failure behavior |
| --- | --- | --- |
| Manifest schema, status transitions, dependencies, cycles, repository/agent authorization | `check_two_agent_tasks.evaluate` | `FAIL` (exit 2), no instructions |
| Concurrent file or branch ownership | `check_two_agent_tasks.evaluate` | `BLOCKED` (exit 1), no instructions |
| Restricted actions (`merge`, `deploy`, `billing`, `production`) or altered approval fields | `check_two_agent_tasks.evaluate` | `FAIL` (exit 2), no instructions |
| Missing required local CLI for a task in `planned`, `in_progress`, or `evidence_ready` | `shutil.which` | `BLOCKED` (exit 1), no instructions |
| Unreadable or oversized manifest | Local file read | `FAIL` (exit 2), no instructions |
| Existing instruction output file | Local destination precheck | `FAIL` (exit 2), existing content unchanged, no new instruction files |
| Symlink, junction, or reparse point in the output path | Local destination precheck | `FAIL` (exit 2), no write-through |
| Failure while staging or linking either output file | Local write | `FAIL` (exit 2), both outputs and directories created by the run are removed |
| Unexpected file-preparation error | Local write | `FAIL` (exit 2), no instruction files |

The result JSON includes:

- `decision`: `PASS`, `BLOCKED`, or `FAIL`.
- `mode`: always `DRY_RUN`.
- `dispatched`: always `false`.
- `cli_detection`: presence status for both worker roles.
- `validator`: the unmodified validator result.
- `rejection_reason` and `rejected_tasks`: why work was rejected, when applicable.
- `instruction_scope`: task IDs assigned to each worker.
- `instructions`: paths to the prepared files.
- `human_approval_actions`: the actions listed below.

Exit codes match the validator: `PASS` 0, `BLOCKED` 1, `FAIL` 2. Unknown
decisions fail closed with exit 2.

## Generated worker instructions

Each file contains only the tasks assigned to that role. Task fields are copied
as JSON-serialized data, not executed. Manifest text is untrusted; a worker must
not follow instructions found inside it outside the validated fields.

Each file also states:

- which local CLI status was detected;
- the declared branch, files, dependencies and requested actions;
- that no process was started by the preflight;
- that merge, deploy, billing, production, secret access and governance changes
  are outside worker authority;
- the evidence required before a task may become `complete`.

Do not put secrets, tokens, customer data or private prompts in the manifest or
in generated files.

## Human-approval actions

The preflight prints these required actions with their exact IDs:

| ID | Human action |
| --- | --- |
| `REVIEW_INSTRUCTIONS` | Read both generated files and confirm each task has only its assigned branch and files. |
| `START_WORKERS_MANUALLY` | Start each approved CLI manually from its own isolated worktree. The preflight never starts a process. |
| `KEEP_RESTRICTED_APPROVALS_PENDING` | Keep `merge`, `deploy`, `billing` and `production` as `pending_human`; grant each separately in the owner review. |
| `VERIFY_EVIDENCE` | Require the exact `source_sha` and fresh PASS evidence, then rerun `python scripts/check_two_agent_tasks.py --manifest <manifest>` and the preflight. |
| `PHASE_8_APPROVAL` | Complete Phase 8 owner approval and confirm passing CI before any merge or deployment. |

The operator owns model/provider choice, spend, repository trust, worktree
isolation, sandbox settings and the decision to use either CLI. This repository
configuration alone is not evidence of a live subagent, hosted readiness or
approved AI spending.

## Limitations

- Presence of an executable is not a successful CLI invocation or authentication.
- The preflight cannot prove that a worker actually ran or that evidence is true.
- It does not verify branch protection, CI runs, CodeQL, Trivy, tenant isolation
  or the Phase 8 gate.
- It does not change `.codex/config.toml`, provider settings, IAM, secrets,
  production systems or repository rules.
- Hosted CI for any branch using this script is **UNVERIFIED** until a fresh run
  is cited.

## ملخص مختصر

الأداة تجهّز تعليمات منفصلة لـ`CODEX` و`OPENCODE` بعد التحقق من ملف المهام
الحالي، وتكتشف وجود الأمرين المحليين دون تشغيلهما. الوضع الافتراضي والوحيد
`DRY_RUN`؛ لا يوجد أمر إرسال تلقائي، ولا تُمنح موافقة دمج أو نشر أو فوترة أو
وصول إنتاج. نتيجة `PASS` ليست موافقة بشرية ولا دليلًا على اجتياز بوابات
P01 أو AI-9 أو تشغيل Codex.

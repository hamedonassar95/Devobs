# Local development-progress report — quickstart (OpenCode, 2026-11-22)

**Purpose:** run the existing, read-only [development progress reporter](../../tools/development_progress_report.py)
on a local computer and review the result. This is an **offline advisory projection** of two
explicitly selected local JSON files. It creates no task registry, starts no agent, makes no
network call, changes no Git state and grants no approval.

**Status: `PENDING HUMAN APPROVAL`.** A local `PASS`, `BLOCKED` or `UNVERIFIED` report is not
GitHub CI evidence, project readiness, a merged milestone, runtime acceptance or a release gate.
An open PR is never counted as merged work.

## 1. Ownership and allowed scope

This quickstart, the [synthetic example manifest](../../examples/agents/development-progress.tasks.example.json)
and the [validation record](../verification/opencode-local-progress-validation.md) are the only
files owned by this task. `README.md`, `STATE.md`, `docs/MILESTONE_LEDGER.json`, the reporter,
its tests and all existing authority files stay untouched. Before editing, verify that the three
paths are absent on `origin/main` and unowned by other branches; see the validation record.

**The example JSON is educational synthetic data.** It is not a live approved task manifest, not
an agent dispatch record, not evidence of work performed and not an authorization. Every approval
is `pending_human`; the task is `planned` with `previous_status: none`, `verification.result:
PENDING`, empty `commands` and `evidence`, and `null` `source_sha` / `pr_reference`.

## 2. Prerequisites actually checked on this host

| Item | This host | Implication |
| --- | --- | --- |
| Operating system | Windows 10 Pro, build 19045 | Native Windows cannot use the POSIX secure reader |
| `python3` | Microsoft Store stub, `python3 -c` exits 9009 | Use `python` (3.12.10) for local runs here; do not install a new interpreter |
| `python` | Python 3.12.10 | All commands below were executed with `python` |
| WSL | Not installed (`wsl --status` exit 50; no `Lxss` registry key) | Linux/WSL runs are `BLOCKED`; do not install WSL or a distribution |
| Git Bash | `MINGW64_NT-10.0-19045` (Windows kernel) | Not a Linux environment; does not satisfy the reader requirement |

The reporter reuses a bounded, no-follow secure reader that requires POSIX `O_NOFOLLOW`,
`O_DIRECTORY`, `O_CLOEXEC`, `O_NONBLOCK` and `dir_fd` support. On native Windows it must fail
closed. **Never replace the symlink check with an ordinary read, and never weaken path
protection to make a Windows test pass.** ([Reader source](../../scripts/agentdust_readonly_adapter.py);
[WSL install docs](https://learn.microsoft.com/windows/wsl/install).)

## 3. Commands — use the example only

Run from a trusted checkout on a supported Linux/WSL host, in this order. `python3` is the
documented spelling; on this Windows host substitute `python` and expect the fail-closed result
documented in section 5.

```sh
# 0. Confirm interpreter (Python docs: https://docs.python.org/3/using/cmdline.html)
python3 --version

# 1. Validate the synthetic example contract (expected PASS / exit 0)
python3 scripts/check_two_agent_tasks.py --manifest examples/agents/development-progress.tasks.example.json

# 2. Focused and existing validators
python3 -m unittest discover -s tests -p "test_development_progress_report.py" -v
python3 -m unittest tests.test_agent_task_status_report tests.test_two_agent_tasks tests.test_milestone_ledger -v
python3 -m compileall -q tools
python3 tools/development_progress_report.py --help

# 3. JSON report (structured, sorted output to stdout)
python3 tools/development_progress_report.py \
  --milestones docs/MILESTONE_LEDGER.json \
  --tasks examples/agents/development-progress.tasks.example.json \
  --format json

# 4. Markdown report (safe tables to stdout)
python3 tools/development_progress_report.py \
  --milestones docs/MILESTONE_LEDGER.json \
  --tasks examples/agents/development-progress.tasks.example.json \
  --format markdown

# 5. Guard all three new files (never edit a file to satisfy the guard)
python3 tools/agent_output_guard.py --workspace . \
  examples/agents/development-progress.tasks.example.json \
  docs/agents/LOCAL_PROGRESS_QUICKSTART.md \
  docs/verification/opencode-local-progress-validation.md

# 6. Whitespace check
git diff --check
```

The reporter flags are defined in its own source and project documentation
([CLI source](../../tools/development_progress_report.py),
[documented usage](DEVELOPMENT_PROGRESS_REPORT.md)); `unittest` and `compileall` follow the
[Python standard library CLI](https://docs.python.org/3/library/unittest.html#command-line-interface)
and [compileall reference](https://docs.python.org/3/library/compileall.html).
`git diff --check` is documented by [git-diff](https://git-scm.com/docs/git-diff).

## 4. Reading the result

| Exit | Report status | Meaning |
| ---: | --- | --- |
| 0 | — | `--help` or contract `PASS` only; never a readiness-success report |
| 1 | `BLOCKED` | Structurally valid report; a recorded gate or canonical task is blocked — an expected valid outcome |
| 2 | `UNVERIFIED` | Structurally valid report without known blockers; live evidence still unavailable — also an expected valid outcome |
| 3 | `FAIL` | Invalid/missing input, unsupported reader or validator failure — a real failure that must not be converted to success |

There is deliberately **no offline success exit 0** for a report. Read the structured `status`
field, not only the exit code. `input_validation: VERIFIED` means only that the two local schemas
passed their existing validators. `RECORDED_MATCH` is a repository/PR/SHA correspondence in the
ledger, never fresh merge proof. Live merge/CI status stays `UNVERIFIED`.

With the current ledger the two `BLOCKED` gates (`ai9-detection-quality`,
`p01-managed-saas`) and one `OPEN` gate (`codex-agent-runtime-acceptance`) are expected to make a
**valid** report `BLOCKED` (exit 1). Do not relabel those gates.

## 5. Observed result on this host (summary)

The example contract itself returns `PASS` / exit 0, the 120 existing validator tests pass, and
`compileall`, `--help` and `git diff --check` exit 0. The reporter cannot read inputs on native
Windows: both JSON and Markdown runs return `status: FAIL`, `errors:
["INPUT_UNAVAILABLE_OR_INVALID"]`, exit **3**. Two successive runs produced byte-identical output,
which proves only that the *failure* is deterministic. A valid `BLOCKED`/`UNVERIFIED` report and
its determinism remain **UNVERIFIED** until run on Linux/WSL. Exact commands, exit codes, hashes
and the focused-test Windows failures are in the [validation record](../verification/opencode-local-progress-validation.md).

## 6. Real task data and disclosure boundary

Do **not** read an actual task manifest unless the owner explicitly identifies and approves that
file for this run. When no approved manifest is available, use only the synthetic example and
record the limitation. The tool reads only the two paths passed on the command line; it omits raw
commands/evidence excerpts, escapes Markdown and redacts recognized credential patterns, but that
redaction is heuristic. Review any approved prose before sharing a report.

Rollback is a reviewed revert of the three owned files. No hosted setting, gate, secret, token,
production service or deployment is touched by this procedure.

**Final status: `PENDING HUMAN APPROVAL`.**

# Offline worktree coordination inspector (advisory only)

**Scope:** `devobs/coordination/worktree_inspector.py` is a read-only, offline
inspector for the local Git worktrees used by parallel Devobs sessions. It finds
overlapping uncommitted files, duplicate branch attachments, stale/abandoned
worktree candidates, and dependency or PR-target claims from an optional local
two-agent task manifest. It emits one bounded JSON document on stdout.

It **never** deletes, resets, prunes, checks out, fetches, commits or otherwise
modifies any worktree. It does not connect to GitHub, run stored commands, read
credentials or environment values, execute agents, or grant merge, deploy,
billing or production approval. All work remains subject to the Phase 8 human
gate and the existing P01/AI-9/Codex-runtime gates.

## Reuse boundary

The inspector reuses existing reviewed code instead of duplicating rules:

- `tools/agent_task_status_report.py::sanitize_display` bounds and sanitizes
  every emitted string (ANSI, control and bidi characters, whitespace, length).
- `scripts/check_two_agent_tasks.py::evaluate` is the source of truth for
  manifest conflicts and blocked tasks. Manifest-derived findings are labelled
  `UNVERIFIED` because manifest text is a local claim, not proof.

Git discovery is new because no equivalent local worktree inspector exists.

## Run

```powershell
python -m devobs.coordination.worktree_inspector --repo-root . --base main
python -m devobs.coordination.worktree_inspector --repo-root . --manifest .\tasks.json --stale-days 30
python -m unittest tests.test_worktree_inspector -v
```

On hosts with `python3`, it is equivalent. Only the Python 3.12 standard library
is used. Paths in the report are shown relative to the repository parent; no
absolute home directory, token or environment value is emitted.

## Classification and exit codes

| Classification | Meaning |
| --- | --- |
| `VERIFIED` | Directly observed from read-only Git porcelain output. |
| `UNVERIFIED` | A local claim or an inference that needs human review. |
| `BLOCKED` | Missing metadata, an unsafe path, or a failed Git read. |

| Exit | Meaning |
| --- | --- |
| `0` | Inspection completed with no findings. |
| `1` | Inspection completed; advisory findings require human review. |
| `2` | Failed closed; the JSON report contains a `BLOCKED` finding. |

A failed read produces structured JSON, never an empty success. Git stderr and
exit-code details are intentionally reduced to a reason code so raw provider or
host data cannot leak into the report.

## Findings

| Category | Classification | Evidence |
| --- | --- | --- |
| `overlapping_changed_files` | `VERIFIED` | Two worktrees have uncommitted changes to the same normalized repository-relative path. |
| `duplicate_worktree_branch` | `VERIFIED` | `git worktree list --porcelain` attaches one branch to several worktrees. |
| `prunable_worktree` / `worktree_read_failed` | `BLOCKED` | Git reports stale metadata or a read command failed; no cleanup is attempted. |
| `no_unique_work` / `stale_worktree_candidate` / `detached_worktree` / `locked_worktree` | `UNVERIFIED` | Ahead/behind counts, commit timestamp and porcelain flags are observed, but "abandoned" is an inference. |
| `manifest_declared_overlap` / `manifest_dependency_block` / `duplicate_pr_target` | `UNVERIFIED` | Claimed by the local manifest and validated by the shared checker. |

## Report shape

Top-level keys: `schema_version`, `report_type`, `advisory`, `evidence_policy`,
`repository`, `manifest`, `summary`, `worktrees`, `findings`. Each finding has
`id`, `classification`, `category`, `detail` and `evidence`. The output is
`ensure_ascii=True` and sorted, so it is safe to pipe to another local checker.

## Limitations

- The inspector cannot prove that a worktree is actually in use; a stale
  candidate is evidence for review, never authority to remove anything.
- Uncommitted paths are compared by path only; file contents are never read.
- Manifest claims can be false or stale. CI, protected-branch rules and hosted
  PR state are deliberately not queried.
- `scripts/assess_change.py` currently classifies Python source under
  `scripts/`, `tests/` and `tools/` only. This module is executed by the new
  test file, so its syntax is exercised there; direct CI compilation of the
  `devobs/` tree is not configured and was not changed by this work.

## Verification

```powershell
python -m py_compile devobs/coordination/__init__.py devobs/coordination/worktree_inspector.py tests/test_worktree_inspector.py
python -m unittest tests.test_worktree_inspector -v
python -m unittest tests.test_two_agent_tasks -v
python -m unittest tests.test_agent_task_status_report -v
python -m unittest tests.test_python_source_coverage -v
python -m unittest tests.test_python_dependency_automation -v
git diff --check
```

Ruff is not configured in this repository (only `.ruff_cache/` is ignored), so
no Ruff command was run. Bandit is pinned in `requirements-dev.txt`; if the
pinned environment is available, run
`python -m bandit -r scripts tools -x scripts/check_site.py` from the repo root.
The inspector uses fixed argv entries, no shell and `# nosec B404`/`B603`-style
rationale comments for its `subprocess` calls.

## الاستخدام بالعربية

هذه الأداة **للمراجعة المحلية فقط**. تقرأ فروع worktrees المحلية وتغيّرات الملفات
غير الملتزمة دون تعديل أي شيء، وتُنتج تقرير JSON مصنّفًا: `VERIFIED` لما لاحظته
Git مباشرة، و`UNVERIFIED` للادعاءات المحلية، و`BLOCKED` عند تعذّر القراءة. لا
تمنح الأداة إذنًا بالدمج أو النشر، ولا تحذف أو تنظف أي worktree.

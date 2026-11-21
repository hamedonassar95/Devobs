"""Read-only inspector for local Git worktrees used by parallel Devobs sessions.

It discovers worktrees, compares uncommitted file sets and branch attachments,
and reports stale/integration evidence as a bounded JSON document. It never
deletes, resets, prunes, checks out, fetches or otherwise mutates Git state, and
it never reads or emits credentials or environment values.

Every finding is labelled VERIFIED (direct Git observation), UNVERIFIED (a local
claim or inference) or BLOCKED (missing metadata or a failed read). Findings are
advisory: none of them grants merge, deploy, billing or production approval.
"""
import argparse
import json
from datetime import datetime, timezone
import re
import shutil
import subprocess  # nosec B404 - fixed Git executable, argv only, no shell.
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.check_two_agent_tasks import evaluate  # noqa: E402
from tools.agent_task_status_report import sanitize_display  # noqa: E402

SCHEMA_VERSION = 1
REPORT_TYPE = "advisory_local_worktree_coordination"
CLASSIFICATIONS = ("VERIFIED", "UNVERIFIED", "BLOCKED")
EXIT_PASS, EXIT_BLOCKED, EXIT_FAIL = 0, 1, 2
MAX_MANIFEST_BYTES = 512 * 1024
MAX_FINDINGS = 200
GIT_TIMEOUT_SECONDS = 20
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
BRANCH_RE = re.compile(r"^refs/heads/[A-Za-z0-9._/-]+$")


class InspectorError(Exception):
    """A fail-closed read error with a sanitized, non-secret reason."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _git(directory, *arguments, runner=None):
    """Run one read-only Git command; never expose stderr or the environment."""
    runner = runner or subprocess.run
    executable = shutil.which("git")
    if not executable:
        raise InspectorError("git_unavailable")
    try:
        result = runner(
            [executable, "-C", str(directory), *arguments],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=GIT_TIMEOUT_SECONDS, check=False, shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise InspectorError("git_read_failed") from None
    if result.returncode != 0:
        raise InspectorError("git_nonzero_exit")
    return result.stdout


def _clean(value, limit=200):
    if isinstance(value, Path):
        value = str(value)
    return sanitize_display(value, limit=limit)


def _display_path(value, root):
    """Show a path relative to the repository parent; never emit absolute homes."""
    try:
        return Path(value).resolve().relative_to(root.parent).as_posix()
    except (ValueError, OSError):
        return Path(value).name


def _safe_path(value):
    """Return a normalized repository-relative path, or None when unsafe."""
    if not isinstance(value, str) or not value or len(value) > 500:
        return None
    candidate = value.replace("\\", "/")
    if " -> " in candidate:
        candidate = candidate.split(" -> ", 1)[1]
    while candidate.startswith("./"):
        candidate = candidate[2:]
    candidate = candidate.rstrip("/")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        return None
    parts = candidate.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return "/".join(parts)


def parse_worktrees(text):
    """Parse `git worktree list --porcelain`; fail closed on unknown fields."""
    records = []
    for block in text.strip().split("\n\n"):
        record = {"path": "", "head": "", "branch": "", "detached": False,
                  "locked": False, "prunable": False}
        for line in block.splitlines():
            if not line:
                continue
            if line.startswith("worktree "):
                record["path"] = line[len("worktree "):]
            elif line.startswith("HEAD "):
                record["head"] = line[len("HEAD "):]
            elif line.startswith("branch "):
                record["branch"] = line[len("branch "):]
            elif line == "detached":
                record["detached"] = True
            elif line.startswith("locked"):
                record["locked"] = True
            elif line.startswith("prunable"):
                record["prunable"] = True
            else:
                raise InspectorError("unexpected_worktree_metadata")
        if not record["path"] or not SHA_RE.fullmatch(record["head"]):
            raise InspectorError("incomplete_worktree_metadata")
        if record["branch"] and not BRANCH_RE.fullmatch(record["branch"]):
            raise InspectorError("unexpected_branch_ref")
        records.append(record)
    if not records:
        raise InspectorError("no_worktrees_reported")
    return records


def parse_status(text):
    """Parse `git status --porcelain=v1`; ignore file contents entirely."""
    changes = []
    for line in text.splitlines():
        if len(line) < 4:
            raise InspectorError("unexpected_status_metadata")
        code, raw = line[:2], line[3:]
        path = _safe_path(raw)
        if path is None:
            raise InspectorError("unsafe_changed_path")
        changes.append({"status": _clean(code, 4), "path": path})
    return changes


def _finding(findings, classification, category, detail, **evidence):
    if len(findings) >= MAX_FINDINGS:
        raise InspectorError("finding_limit_exceeded")
    findings.append({
        "id": f"F{len(findings) + 1:03d}",
        "classification": classification,
        "category": category,
        "detail": _clean(detail, 300),
        "evidence": {key: _clean(value, 300) if isinstance(value, str) else value
                     for key, value in evidence.items()},
    })


def _base_sha(root, base, runner):
    for ref in (f"refs/heads/{base}", f"refs/remotes/origin/{base}"):
        try:
            value = _git(root, "rev-parse", "--verify", ref, runner=runner).strip()
        except InspectorError:
            continue
        if SHA_RE.fullmatch(value):
            return value
    raise InspectorError("base_ref_unavailable")


def _manifest_evidence(manifest_path, findings):
    """Reuse the reviewed two-agent validator; treat its data as a local claim."""
    try:
        raw = manifest_path.read_bytes()
    except OSError:
        raise InspectorError("manifest_unreadable") from None
    if not raw or len(raw) > MAX_MANIFEST_BYTES:
        raise InspectorError("manifest_size_invalid")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise InspectorError("manifest_invalid_json") from None
    result = evaluate(manifest)
    if not isinstance(result, dict) or result.get("decision") not in ("PASS", "BLOCKED", "FAIL"):
        raise InspectorError("validator_shape_unexpected")
    if result["decision"] == "FAIL":
        raise InspectorError("manifest_contract_invalid")
    tasks = manifest.get("tasks", [])
    by_pr = {}
    for task in tasks:
        reference = task.get("pr_reference")
        if isinstance(reference, str):
            by_pr.setdefault(reference, []).append(task.get("id"))
    for reference, task_ids in sorted(by_pr.items()):
        if len(task_ids) > 1:
            _finding(findings, "UNVERIFIED", "duplicate_pr_target",
                     "Two local task claims share a PR reference.",
                     pr_reference=reference, task_ids=",".join(map(str, task_ids)))
    for item in result.get("conflicts", []):
        _finding(findings, "UNVERIFIED", "manifest_declared_overlap",
                 "Local manifest declares an ownership conflict.",
                 reason=item if isinstance(item, str) else json.dumps(item, sort_keys=True))
    for item in result.get("blocked_tasks", []):
        _finding(findings, "UNVERIFIED", "manifest_dependency_block",
                 "Local manifest declares a blocked task or dependency.",
                 reason=item if isinstance(item, str) else json.dumps(item, sort_keys=True))
    return {"decision": result["decision"], "task_count": len(tasks)}


def inspect(repo_root, base="main", manifest_path=None, stale_days=30, runner=None):
    """Return a bounded coordination report; never mutate any worktree."""
    runner = runner or subprocess.run
    findings = []
    root = Path(repo_root).resolve()
    manifest = None
    if manifest_path is not None:
        manifest = _manifest_evidence(Path(manifest_path), findings)
    if not root.is_dir():
        raise InspectorError("repository_root_missing")

    try:
        base_commit = _base_sha(root, base, runner)
        records = parse_worktrees(_git(root, "worktree", "list", "--porcelain", runner=runner))
    except InspectorError:
        raise

    now = datetime.now(timezone.utc)
    views = []
    for record in records:
        path = Path(record["path"])
        try:
            changes = parse_status(_git(path, "status", "--porcelain=v1",
                                        "--untracked-files=normal", "--", runner=runner))
            counts = _git(root, "rev-list", "--left-right", "--count",
                          f"{base}...{record['branch'] or record['head']}", runner=runner).split()
            if len(counts) != 2 or not all(value.isdigit() for value in counts):
                raise InspectorError("unexpected_revision_counts")
            behind, ahead = (int(counts[0]), int(counts[1]))
            committed = _git(root, "log", "-1", "--format=%cI",
                             record["branch"] or record["head"], runner=runner).strip()
            has_date = False
            try:
                age_days = (now - datetime.fromisoformat(committed)).days
                has_date = True
            except ValueError:
                age_days = -1
        except InspectorError as error:
            _finding(findings, "BLOCKED", "worktree_read_failed",
                     "A worktree could not be inspected without Git errors.",
                     path=_display_path(record["path"], root), reason=error.reason)
            changes, behind, ahead, committed, age_days, has_date = [], 0, 0, "", -1, False
        views.append({**record, "changes": changes, "behind": behind, "ahead": ahead,
                      "last_commit": committed, "age_days": age_days})

    branches, files = {}, {}
    for view in views:
        label = _clean(_display_path(view["path"], root), 160)
        if view["branch"]:
            branches.setdefault(view["branch"], []).append(label)
        for change in view["changes"]:
            files.setdefault(change["path"], []).append(label)
        if view["prunable"]:
            _finding(findings, "BLOCKED", "prunable_worktree",
                     "Git reports stale worktree metadata; no cleanup was performed.",
                     path=label)
        if view["locked"]:
            _finding(findings, "UNVERIFIED", "locked_worktree",
                     "Git reports a locked worktree; human review is required.", path=label)
        if view["detached"]:
            _finding(findings, "UNVERIFIED", "detached_worktree",
                     "Worktree HEAD is detached; branch ownership is unknown.", path=label)
        if not view["changes"] and view["ahead"] == 0 and view["branch"] and not view["branch"].endswith("/" + base):
            _finding(findings, "UNVERIFIED", "no_unique_work",
                     "Branch has no commits ahead of base and no uncommitted changes.",
                     path=label, branch=view["branch"], behind=view["behind"])
        if has_date and view["age_days"] >= stale_days and not view["changes"] and view["ahead"] > 0:
            _finding(findings, "UNVERIFIED", "stale_worktree_candidate",
                     "Last commit is older than the configured staleness threshold.",
                     path=label, age_days=view["age_days"], threshold=stale_days)

    for branch, paths in sorted(branches.items()):
        if len(paths) > 1:
            _finding(findings, "VERIFIED", "duplicate_worktree_branch",
                     "The same branch is attached to more than one worktree.",
                     branch=branch, paths=",".join(paths))
    for path, paths in sorted(files.items()):
        if len(paths) > 1:
            _finding(findings, "VERIFIED", "overlapping_changed_files",
                     "Two or more worktrees have uncommitted changes to one file.",
                     file=path, paths=",".join(paths))

    counts = {label: sum(1 for item in findings if item["classification"] == label)
              for label in CLASSIFICATIONS}
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "advisory": True,
        "evidence_policy": (
            "VERIFIED means direct local Git observation; UNVERIFIED means a local "
            "claim or inference; BLOCKED means missing metadata or a failed read. "
            "No finding grants merge, deploy, billing or production approval."
        ),
        "repository": {"root": _clean(_display_path(root, root)), "base": _clean(base),
                       "base_sha": base_commit},
        "manifest": manifest,
        "summary": {"worktrees": len(views), "findings": len(findings), **counts},
        "worktrees": [{
            "path": _clean(_display_path(view["path"], root), 260), "branch": _clean(view["branch"]),
            "head_sha": view["head"], "ahead": view["ahead"], "behind": view["behind"],
            "last_commit": view["last_commit"], "uncommitted_changes": view["changes"],
            "locked": view["locked"], "prunable": view["prunable"], "detached": view["detached"],
        } for view in views],
        "findings": findings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="Repository root to inspect.")
    parser.add_argument("--base", default="main", help="Base branch for ahead/behind evidence.")
    parser.add_argument("--manifest", help="Optional local two-agent task manifest.")
    parser.add_argument("--stale-days", type=int, default=30, help="Staleness threshold (>= 1).")
    args = parser.parse_args(argv)
    if args.stale_days < 1 or args.stale_days > 3650:
        parser.error("--stale-days must be between 1 and 3650")
    try:
        report = inspect(Path(args.repo_root), base=args.base,
                         manifest_path=args.manifest, stale_days=args.stale_days)
    except InspectorError as error:
        report = {
            "schema_version": SCHEMA_VERSION, "report_type": REPORT_TYPE,
            "advisory": True, "repository": {"root": _clean(args.repo_root), "base": _clean(args.base),
                                             "base_sha": ""},
            "manifest": None,
            "summary": {"worktrees": 0, "findings": 1, "VERIFIED": 0, "UNVERIFIED": 0, "BLOCKED": 1},
            "worktrees": [],
            "findings": [{"id": "F001", "classification": "BLOCKED",
                          "category": "inspection_failed", "detail": "Inspection failed closed.",
                          "evidence": {"reason": error.reason}}],
        }
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    if report["summary"]["BLOCKED"]:
        return EXIT_FAIL
    return EXIT_BLOCKED if report["summary"]["findings"] else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())

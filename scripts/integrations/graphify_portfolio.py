"""Dry-run-first, offline Graphify portfolio orchestrator (review-only).

This module discovers authorized local checkouts of ``hamedonassar95`` GitHub
repositories, reports whether each one is eligible for an offline code graph,
and, only in explicit ``--execute`` mode, runs a pinned Graphify release with
``--code-only`` and no LLM backend.

Safety contract:

* Dry-run is the default; dry-run never creates a directory or a file.
* ``--execute`` also requires ``--only <repository>`` so no repository is
  scanned implicitly.
* Graph output is written under an external output root. An output root that
  resolves inside a source repository, or inside the repository being scanned,
  is refused before anything runs.
* ``GRAPHIFY_BACKEND=none`` and ``GRAPHIFY_QUERY_LOG_DISABLE=1`` are set for
  the child process, and provider credential variables are blanked so an LLM
  backend cannot be selected implicitly.
* No upload, publish, deployment, scheduler, repository hook, ``graphify
  install`` or ``--global`` merge is ever performed.
* The repository working tree is snapshotted before and after extraction; any
  change, or any ``graphify-out`` directory created inside the repository, is
  reported as a failure rather than a success.

The pinned release rejects ``--backend none`` with ``unknown backend 'none'``;
the supported offline switch is the documented ``GRAPHIFY_BACKEND=none``
environment variable (``graphify/extract`` reads it to skip LLM work).
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

POLICY = "devobs-graphify-portfolio-v1"
PINNED_GRAPHIFY_VERSION = "0.9.112"
AUTHORIZED_OWNER = "hamedonassar95"
ROLLOUT_BRANCHES = ("main", "master")
DEFAULT_TIMEOUT_SECONDS = 900
PROVIDER_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENAI_API_KEY",
)

_REMOTE_PATTERNS = (
    re.compile(
        r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
    ),
    re.compile(
        r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?$"
    ),
    re.compile(
        r"^ssh://git@github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?$"
    ),
)


class PortfolioError(Exception):
    """A policy or preflight refusal that must stop the run."""


@dataclasses.dataclass(frozen=True)
class Repository:
    name: str
    path: pathlib.Path
    remote: str
    owner: str | None
    remote_name: str | None
    branch: str | None
    head: str | None
    dirty: bool
    reasons: tuple[str, ...]

    @property
    def authorized(self) -> bool:
        return self.owner == AUTHORIZED_OWNER

    @property
    def eligible(self) -> bool:
        return not self.reasons

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "remote": self.remote,
            "owner": self.owner,
            "remote_name": self.remote_name,
            "branch": self.branch,
            "head": self.head,
            "dirty": self.dirty,
            "authorized": self.authorized,
            "eligible": self.eligible,
            "blocked_reasons": list(self.reasons),
        }


def parse_github_remote(url: str) -> tuple[str, str] | None:
    """Return ``(owner, name)`` for a github.com remote, else ``None``."""
    value = (url or "").strip()
    for pattern in _REMOTE_PATTERNS:
        match = pattern.match(value)
        if match:
            owner = match.group("owner")
            name = match.group("name")
            if name.endswith(".git"):
                name = name[: -len(".git")]
            return owner, name
    return None


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    """True when *path* is *parent* or lives underneath it."""
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, ValueError):
        return False
    return True


def _git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.returncode != 0:
        raise PortfolioError(f"git {' '.join(args)} failed: {(result.stderr or '').strip()}")
    return result.stdout


def inspect_repository(path: pathlib.Path) -> Repository:
    """Read local git metadata only; never contacts the remote."""
    path = path.resolve()
    reasons: list[str] = []
    if not (path / ".git").exists():
        raise PortfolioError(f"{path} is not a git checkout")

    remote = ""
    try:
        remote = _git(path, "config", "--get", "remote.origin.url").strip()
    except PortfolioError:
        reasons.append("no origin remote")
    parsed = parse_github_remote(remote)
    owner = parsed[0] if parsed else None
    remote_name = parsed[1] if parsed else None

    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD").strip() or None
    head = _git(path, "rev-parse", "HEAD").strip() or None
    dirty = bool(_git(path, "status", "--porcelain", "--untracked-files=all").strip())

    if parsed is None:
        reasons.append("origin is not a supported github.com remote")
    elif owner != AUTHORIZED_OWNER:
        reasons.append(f"origin owner '{owner}' is not {AUTHORIZED_OWNER}")

    if branch not in ROLLOUT_BRANCHES:
        reasons.append(f"branch '{branch}' is not one of {', '.join(ROLLOUT_BRANCHES)}")
    if dirty:
        reasons.append("working tree has uncommitted changes")

    return Repository(
        name=path.name,
        path=path,
        remote=remote,
        owner=owner,
        remote_name=remote_name,
        branch=branch,
        head=head,
        dirty=dirty,
        reasons=tuple(reasons),
    )


def discover(root: pathlib.Path, extra_paths: list[pathlib.Path] | None = None):
    """Discover candidate checkouts under *root* plus explicit extra paths.

    Linked worktrees (``.git`` is a file) are skipped with a recorded reason so a
    worktree of the same repository is not reported as a second project.
    """
    if not root.exists() or not root.is_dir():
        raise PortfolioError(f"scan root does not exist or is not a directory: {root}")
    found: list[Repository] = []
    skipped: list[dict] = []
    seen: set[pathlib.Path] = set()
    names: dict[str, pathlib.Path] = {}

    def register(repository: Repository) -> None:
        if repository.name in names:
            raise PortfolioError(
                f"duplicate repository name '{repository.name}' for "
                f"{names[repository.name]} and {repository.path}"
            )
        names[repository.name] = repository.path
        found.append(repository)
        seen.add(repository.path)

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        marker = child / ".git"
        if not marker.exists():
            continue
        if marker.is_file():
            skipped.append({"name": child.name, "path": str(child), "reason": "linked worktree or submodule"})
            continue
        try:
            repository = inspect_repository(child)
        except PortfolioError as exc:
            skipped.append({"name": child.name, "path": str(child), "reason": str(exc)})
            continue
        register(repository)

    for extra in extra_paths or []:
        path = extra.resolve()
        if path in seen:
            continue
        register(inspect_repository(path))

    return found, skipped


def validate_output_root(output_root: pathlib.Path, repositories: list[Repository]) -> pathlib.Path:
    """Refuse an output root that could write into a source repository."""
    resolved = output_root.expanduser().resolve()
    for repository in repositories:
        if is_within(resolved, repository.path) or is_within(repository.path, resolved):
            raise PortfolioError(
                f"output root {resolved} overlaps the source repository {repository.path}"
            )
    return resolved


def plan(repositories: list[Repository], output_root: pathlib.Path, selected: list[str]) -> list[dict]:
    """Build a side-effect-free plan for the requested repositories."""
    by_name = {repository.name: repository for repository in repositories}
    unknown = [name for name in selected if name not in by_name]
    if unknown:
        raise PortfolioError(f"unknown repository selection: {', '.join(sorted(unknown))}")
    if selected:
        chosen = [by_name[name] for name in selected]
    else:
        chosen = repositories

    actions = []
    for repository in chosen:
        out_dir = output_root / repository.name / (repository.head or "unknown")
        actions.append(
            {
                "repository": repository,
                "output_dir": out_dir,
                "would_execute": repository.eligible and bool(selected),
                "eligible": repository.eligible,
                "blocked_reasons": list(repository.reasons),
                "existing_output": out_dir.exists(),
            }
        )
    return actions


def _run(argv, env, cwd, timeout, run):
    return run(
        argv,
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def graphify_version(binary: str, run=subprocess.run) -> str:
    result = _run([binary, "--version"], dict(os.environ), pathlib.Path.cwd(), 120, run)
    if result.returncode != 0:
        raise PortfolioError(f"cannot read graphify version (exit {result.returncode})")
    token = (result.stdout or result.stderr or "").strip().split()
    if not token:
        raise PortfolioError("graphify --version produced no output")
    return token[-1]


def build_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env["GRAPHIFY_BACKEND"] = "none"
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    for key in PROVIDER_KEY_VARS:
        env[key] = ""
    return env


def _tail(text: str | None, limit: int = 40) -> list[str]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[-limit:]


def execute_repository(
    repository: Repository,
    output_root: pathlib.Path,
    binary: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    run=subprocess.run,
) -> dict:
    """Run one offline extraction and write local run evidence.

    Any failure is reported as ``status: failed`` with ``exit_code`` 3 by the
    caller; this function never turns a missing or partial artifact into a pass.
    """
    if not repository.eligible:
        raise PortfolioError(
            f"{repository.name} is not eligible: {'; '.join(repository.reasons)}"
        )

    out_dir = output_root.resolve() / repository.name / str(repository.head)
    if is_within(out_dir, repository.path):
        raise PortfolioError(f"refusing output inside source repository: {out_dir}")
    if out_dir.exists():
        raise PortfolioError(f"output directory already exists, refusing to overwrite: {out_dir}")

    version = graphify_version(binary, run=run)
    if version != PINNED_GRAPHIFY_VERSION:
        raise PortfolioError(
            f"graphify {version} is not the pinned {PINNED_GRAPHIFY_VERSION}"
        )

    before_status = _git(repository.path, "status", "--porcelain", "--untracked-files=all")
    before_head = _git(repository.path, "rev-parse", "HEAD").strip()
    stray_before = (repository.path / "graphify-out").exists()
    out_dir.mkdir(parents=True, exist_ok=False)

    argv = [
        binary,
        "extract",
        str(repository.path),
        "--code-only",
        "--out",
        str(out_dir),
    ]
    env = build_environment()
    started = datetime.datetime.now(datetime.timezone.utc)
    record: dict = {
        "policy": POLICY,
        "graphify_version": version,
        "repository": repository.as_dict(),
        "command": argv,
        "environment": {
            "GRAPHIFY_BACKEND": env["GRAPHIFY_BACKEND"],
            "GRAPHIFY_QUERY_LOG_DISABLE": env["GRAPHIFY_QUERY_LOG_DISABLE"],
            "provider_key_variables_blanked": list(PROVIDER_KEY_VARS),
        },
        "started_at": started.isoformat(),
        "network_uploads": False,
        "hooks_installed": False,
    }

    failure: str | None = None
    try:
        result = _run(argv, env, repository.path, timeout, run)
    except (OSError, subprocess.SubprocessError) as exc:
        result = None
        failure = f"extraction did not complete: {exc}"
    finished = datetime.datetime.now(datetime.timezone.utc)
    record["finished_at"] = finished.isoformat()
    record["duration_seconds"] = round((finished - started).total_seconds(), 3)

    graph_path = out_dir / "graphify-out" / "graph.json"
    record["graph"] = None
    if result is not None:
        record["exit_code"] = result.returncode
        record["stdout_tail"] = _tail(result.stdout)
        record["stderr_tail"] = _tail(result.stderr)
        if result.returncode != 0:
            failure = failure or f"graphify exited {result.returncode}"
    if failure is None and not graph_path.is_file():
        failure = "graphify did not write graph.json"

    if failure is None:
        payload = graph_path.read_bytes()
        try:
            graph = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            failure = f"graph.json is not valid JSON: {exc}"
        else:
            record["graph"] = {
                "path": str(graph_path),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "nodes": len(graph.get("nodes") or []),
                "edges": len(graph.get("links") or []),
            }

    after_status = _git(repository.path, "status", "--porcelain", "--untracked-files=all")
    after_head = _git(repository.path, "rev-parse", "HEAD").strip()
    repo_unchanged = before_status == after_status and before_head == after_head
    stray_output = (repository.path / "graphify-out").exists() and not stray_before
    record["repository_unchanged"] = repo_unchanged
    record["stray_graphify_out_in_repository"] = stray_output
    if not repo_unchanged:
        failure = failure or "repository changed during extraction"
    if stray_output:
        failure = failure or "graphify-out was created inside the source repository"

    record["status"] = "failed" if failure else "extracted"
    record["failure"] = failure
    (out_dir / "run.json").write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return record


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[2].parent)
    parser.add_argument("--repo", type=pathlib.Path, action="append", default=[], help="extra checkout path")
    parser.add_argument("--out-root", type=pathlib.Path, default=pathlib.Path.home() / ".devobs" / "graphify-portfolio")
    parser.add_argument("--only", action="append", default=[], help="repository name to select (repeatable)")
    parser.add_argument("--graphify", default="graphify", help="graphify executable")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--execute", action="store_true", help="run extraction; requires --only")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        repositories, skipped = discover(args.root, args.repo)
        if not repositories:
            raise PortfolioError(f"no git checkouts discovered under {args.root}")
        output_root = validate_output_root(args.out_root, repositories)
        if args.execute and not args.only:
            raise PortfolioError("--execute requires at least one explicit --only <repository>")
        actions = plan(repositories, output_root, args.only)

        binary = args.graphify
        if args.execute:
            for action in actions:
                if not action["eligible"]:
                    raise PortfolioError(
                        f"{action['repository'].name} is not eligible: "
                        f"{'; '.join(action['blocked_reasons'])}"
                    )
                if action["existing_output"]:
                    raise PortfolioError(
                        f"output directory already exists, refusing to overwrite: {action['output_dir']}"
                    )
            binary = shutil.which(args.graphify) or args.graphify
            if not pathlib.Path(binary).is_file() and shutil.which(binary) is None:
                raise PortfolioError(f"graphify executable not found: {args.graphify}")

        results = []
        for action in actions:
            entry = {
                "name": action["repository"].name,
                "eligible": action["eligible"],
                "blocked_reasons": action["blocked_reasons"],
                "output_dir": str(action["output_dir"]),
            }
            if args.execute:
                entry["run"] = execute_repository(
                    action["repository"], output_root, binary, timeout=args.timeout
                )
            results.append(entry)

        report = {
            "policy": POLICY,
            "mode": "execute" if args.execute else "dry-run",
            "graphify": {
                "expected_version": PINNED_GRAPHIFY_VERSION,
                "offline_environment": {"GRAPHIFY_BACKEND": "none", "GRAPHIFY_QUERY_LOG_DISABLE": "1"},
                "command_template": "graphify extract <path> --code-only --out <external-dir>",
            },
            "scan_root": str(args.root.resolve()),
            "output_root": str(output_root),
            "repositories": [repository.as_dict() for repository in repositories],
            "skipped_paths": skipped,
            "plan": results,
        }
        failed = [entry for entry in results if entry.get("run", {}).get("status") == "failed"]
        report["status"] = "failed" if failed else ("executed" if args.execute else "dry-run")

        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
        else:
            print(f"{POLICY} mode={report['mode']} status={report['status']}")
            for repository in repositories:
                state = "ELIGIBLE" if repository.eligible else "BLOCKED"
                detail = "" if repository.eligible else f" ({'; '.join(repository.reasons)})"
                print(f"  {state:8} {repository.name} [{repository.branch}] {repository.head}{detail}")
            for entry in results:
                if "run" in entry:
                    run = entry["run"]
                    print(f"  RUN {entry['name']}: {run['status']} -> {run.get('graph')}")
        return 3 if failed else 0
    except (PortfolioError, OSError) as exc:
        print(f"GRAPHIFY_PORTFOLIO_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

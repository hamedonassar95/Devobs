"""Execution and CLI layer for the canonical Graphify portfolio contract.

This module preserves the legacy review-only subprocess behavior behind an
explicit contract while keeping orchestration definitions in ``portfolio``. It
never downloads, installs, uploads, deploys or changes Graphify global state.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess  # nosec B404 - fixed-argv Git and pinned local Graphify only
import sys
from collections.abc import Sequence

from .common import is_within
from .portfolio import (
    LEGACY_PORTFOLIO_CONTRACT,
    PortfolioContract,
    PortfolioError,
    _git,
    discover,
    plan,
    validate_output_root,
)

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


def build_environment(
    base: dict[str, str] | None = None,
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env["GRAPHIFY_BACKEND"] = "none"
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    for key in contract.provider_key_vars:
        env[key] = ""
    return env


def _tail(text: str | None, limit: int = 40) -> list[str]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[-limit:]


def execute_repository(
    repository: Repository,
    output_root: pathlib.Path,
    binary: str,
    timeout: int | None = None,
    run=subprocess.run,
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> dict:
    """Run one offline extraction and write local run evidence."""
    if not repository.eligible:
        raise PortfolioError(
            f"{repository.name} is not eligible: {'; '.join(repository.reasons)}"
        )
    if timeout is None:
        timeout = contract.default_timeout_seconds

    out_dir = output_root.resolve() / repository.name / str(repository.head)
    if is_within(out_dir, repository.path):
        raise PortfolioError(f"refusing output inside source repository: {out_dir}")
    if out_dir.exists():
        raise PortfolioError(f"output directory already exists, refusing to overwrite: {out_dir}")

    version = graphify_version(binary, run=run)
    if version != contract.pinned_version:
        raise PortfolioError(
            f"graphify {version} is not the pinned {contract.pinned_version}"
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
    env = build_environment(contract=contract)
    started = datetime.datetime.now(datetime.timezone.utc)
    record: dict = {
        "policy": contract.policy,
        "graphify_version": version,
        "repository": repository.as_dict(),
        "command": argv,
        "environment": {
            "GRAPHIFY_BACKEND": env["GRAPHIFY_BACKEND"],
            "GRAPHIFY_QUERY_LOG_DISABLE": env["GRAPHIFY_QUERY_LOG_DISABLE"],
            "provider_key_variables_blanked": list(contract.provider_key_vars),
        },
        "started_at": started.isoformat(),
        "network_egress_verification": "not_verified",
        "hooks_installed": False,
    }

    failure: str | None = None
    try:
        result = _run(argv, env, repository.path, timeout, run)
    except (OSError, subprocess.SubprocessError):
        result = None
        failure = "extraction did not complete (execution error)"
    finished = datetime.datetime.now(datetime.timezone.utc)
    record["finished_at"] = finished.isoformat()
    record["duration_seconds"] = round((finished - started).total_seconds(), 3)

    graph_path = out_dir / "graphify-out" / "graph.json"
    record["graph"] = None
    if result is not None:
        record["exit_code"] = result.returncode
        if result.returncode != 0:
            failure = failure or f"graphify exited {result.returncode}"
    if failure is None and not graph_path.is_file():
        failure = "graphify did not write graph.json"

    if failure is None:
        payload = graph_path.read_bytes()
        try:
            graph = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            failure = "graph.json is not valid JSON"
        else:
            if (
                not isinstance(graph, dict)
                or not isinstance(graph.get("nodes"), list)
                or not isinstance(graph.get("links"), list)
            ):
                failure = "graph.json has an invalid graph structure"
            else:
                record["graph"] = {
                    "path": str(graph_path),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "nodes": len(graph["nodes"]),
                    "edges": len(graph["links"]),
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


def build_parser(
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=contract.description,
        epilog=contract.notice or None,
    )
    parser.add_argument("--root", type=pathlib.Path, default=contract.default_root)
    parser.add_argument("--repo", type=pathlib.Path, action="append", default=[], help="extra checkout path")
    parser.add_argument("--out-root", type=pathlib.Path, default=contract.default_out_root)
    parser.add_argument("--only", action="append", default=[], help="repository name to select (repeatable)")
    parser.add_argument("--graphify", default="graphify", help="graphify executable")
    parser.add_argument("--timeout", type=int, default=contract.default_timeout_seconds)
    parser.add_argument("--execute", action="store_true", help="run extraction; requires --only")
    parser.add_argument("--json", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> int:
    args = build_parser(contract).parse_args(argv)
    if contract.notice:
        print(contract.notice, file=sys.stderr)
    try:
        repositories, skipped = discover(args.root, args.repo, contract=contract)
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
                    action["repository"], output_root, binary, timeout=args.timeout, contract=contract
                )
            results.append(entry)

        report = {
            "policy": contract.policy,
            "legacy": contract.legacy,
            "deprecation_notice": contract.notice,
            "canonical": contract.canonical,
            "mode": "execute" if args.execute else "dry-run",
            "graphify": {
                "expected_version": contract.pinned_version,
                "offline_environment": {"GRAPHIFY_BACKEND": "none", "GRAPHIFY_QUERY_LOG_DISABLE": "1"},
                "command_template": contract.command_template,
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
            print(f"{contract.policy} mode={report['mode']} status={report['status']}")
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

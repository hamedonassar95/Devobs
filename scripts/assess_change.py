#!/usr/bin/env python3
"""Select affected CI checks and publish an explainable change-risk estimate."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - Git is invoked with a fixed executable and no shell.
from collections import Counter
from pathlib import Path, PurePosixPath


ROOT = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["/usr/bin/git", *args],  # nosec B603 - arguments are separate argv entries; shell execution is disabled.
        cwd=ROOT,
        check=check,
        capture_output=True,
    )


def has_commit(commit: str) -> bool:
    return bool(commit) and git("cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode == 0


def diff_paths(base: str) -> list[str]:
    output = git(
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=ACMRTD",
        base,
        "HEAD",
    ).stdout
    return [os.fsdecode(path) for path in output.split(b"\0") if path]


def event_changed_paths() -> tuple[list[str] | None, str | None]:
    if os.environ.get("VALIDATION_PROFILE") == "rollback":
        return None, None

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not Path(event_path).is_file():
        return None, None
    with open(event_path, encoding="utf-8") as event_file:
        event = json.load(event_file)

    if event_name == "pull_request":
        base = event.get("pull_request", {}).get("base", {}).get("sha", "")
        if has_commit(base):
            return diff_paths(base), base
        return None, None

    if event_name == "push":
        before = event.get("before", "")
        if before and set(before) == {"0"}:
            return None, None
        if has_commit(before):
            return diff_paths(before), before

        commits = event.get("commits")
        if isinstance(commits, list) and commits:
            changed = set()
            for commit in commits:
                changed.update(commit.get("added", []))
                changed.update(commit.get("modified", []))
                changed.update(commit.get("removed", []))
            return sorted(changed), None

    return None, None


def tracked_paths() -> list[str]:
    output = git("ls-files", "-z").stdout
    return [os.fsdecode(path) for path in output.split(b"\0") if path]


def changed_line_count(base: str | None) -> int:
    if not base:
        return 0
    output = git("diff", "--numstat", "--no-renames", base, "HEAD").stdout
    total = 0
    for line in output.splitlines():
        columns = line.split(b"\t", 2)
        if len(columns) < 2:
            continue
        for value in columns[:2]:
            if value.isdigit():
                total += int(value)
    return total


def recent_touch_counts() -> Counter[str]:
    output = git(
        "log",
        "--since=90 days ago",
        "--name-only",
        "--format=",
        "-z",
    ).stdout
    return Counter(os.fsdecode(path) for path in output.split(b"\0") if path)


def is_python(path: PurePosixPath) -> bool:
    return path.suffix == ".py" and path.parts[:1] in {("scripts",), ("tests",)}


def is_node(path: PurePosixPath) -> bool:
    return (
        path.suffix in {".js", ".cjs", ".mjs"}
        and path.parts[:1] in {("scripts",), ("tests",)}
    ) or path.name in {"package.json", "package-lock.json"}


def is_python_dependency(path: PurePosixPath) -> bool:
    return path.name in {
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "requirements.txt",
        "requirements-dev.txt",
    }


def risk_signals(paths: list[str], lines: int, history: Counter[str], full_scan: bool) -> tuple[int, list[str]]:
    if full_scan:
        return 80, ["No reliable change base; all checks are selected as a safe fallback"]

    score = 0
    signals = []
    pure_paths = [PurePosixPath(path) for path in paths]

    sensitive = any(
        path.parts[:2] in {(".github", "workflows"), (".github", "actions")}
        or path.name in {"Dockerfile", "package-lock.json", "pyproject.toml"}
        or path.as_posix().startswith(("scripts/dispatch_rollback", "scripts/recovery_"))
        for path in pure_paths
    )
    if sensitive:
        score += 45
        signals.append("Deployment, security, or workflow configuration changed (+45)")

    if any(is_python_dependency(path) for path in pure_paths):
        score += 30
        signals.append("Python dependency manifest changed (+30)")

    if any(is_python(path) or is_node(path) for path in pure_paths):
        score += 25
        signals.append("Application or test code changed (+25)")
    elif any(path.as_posix() == "index.html" or path.parts[:1] == ("assets",) for path in pure_paths):
        score += 15
        signals.append("Published site content changed (+15)")

    if len(paths) >= 10:
        score += 10
        signals.append(f"{len(paths)} files changed (+10)")

    if lines >= 1000:
        score += 30
        signals.append(f"{lines} lines changed (+30)")
    elif lines >= 500:
        score += 20
        signals.append(f"{lines} lines changed (+20)")
    elif lines >= 100:
        score += 10
        signals.append(f"{lines} lines changed (+10)")

    repeated = max((history[path] for path in paths), default=0)
    if repeated >= 10:
        score += 20
        signals.append(f"A changed file had {repeated} commits in the last 90 days (+20)")
    elif repeated >= 5:
        score += 10
        signals.append(f"A changed file had {repeated} commits in the last 90 days (+10)")

    return min(score, 100), signals or ["No elevated change-risk signals detected"]


def main() -> None:
    paths, base = event_changed_paths()
    full_scan = paths is None
    if full_scan:
        paths = tracked_paths()

    if paths is None:
        raise RuntimeError("Could not determine changed paths for CI analysis.")
    paths = sorted(set(paths))
    lines = changed_line_count(base)
    history = recent_touch_counts()
    score, signals = risk_signals(paths, lines, history, full_scan)
    level = "high" if score >= 60 else "medium" if score >= 25 else "low"

    python_required = full_scan or level == "high" or any(
        is_python(PurePosixPath(path)) or is_python_dependency(PurePosixPath(path))
        for path in paths
    )
    node_required = full_scan or level == "high" or any(
        is_node(PurePosixPath(path)) for path in paths
    )

    outputs = {
        "python_required": str(python_required).lower(),
        "node_required": str(node_required).lower(),
        "risk_score": str(score),
        "risk_level": level,
    }
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output_file:
        for name, value in outputs.items():
            output_file.write(f"{name}={value}\n")

    summary = [
        "## Change impact and deployment risk",
        "",
        f"- Risk estimate: **{level}** ({score}/100)",
        f"- Changed files considered: {len(paths)}",
        f"- Python test suite: {'selected' if python_required else 'skipped (unrelated changes)'}",
        f"- Node guard tests: {'selected' if node_required else 'skipped (unrelated changes)'}",
        "- Security scan and published-site contract checks remain required.",
        "- This is an explainable, local heuristic based on file class, change size, and 90-day file churn; it is advisory and does not call an external AI service or block deployment.",
        "",
        "Signals:",
        *[f"- {signal}" for signal in signals],
    ]
    if paths:
        summary.extend(["", "Changed paths:", *[f"- `{path}`" for path in paths[:30]]])
        if len(paths) > 30:
            summary.append(f"- … and {len(paths) - 30} more")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(summary) + "\n")


if __name__ == "__main__":
    main()

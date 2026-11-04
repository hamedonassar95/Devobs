"""Run actionlint against hand-authored GitHub Actions workflow sources."""

from __future__ import annotations

# The wrapper passes the pinned CLI a fixed argv list; this call never uses a shell.
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_SUFFIXES = {".yml", ".yaml"}
GENERATED_LOCK_SUFFIX = ".lock.yml"


def list_authored_workflows(repository_root: Path = ROOT) -> list[str]:
    """Return direct workflow YAML sources, excluding generated gh-aw locks."""
    workflow_directory = repository_root / ".github" / "workflows"
    if not workflow_directory.is_dir():
        raise FileNotFoundError(f"GitHub Actions workflow directory is missing: {workflow_directory}")

    candidates = [
        path
        for path in workflow_directory.iterdir()
        if path.suffix in WORKFLOW_SUFFIXES
    ]
    symlinks = [path.name for path in candidates if path.is_symlink()]
    if symlinks:
        raise ValueError(f"Workflow YAML sources must not be symbolic links: {', '.join(sorted(symlinks))}")

    workflow_files = sorted(
        path.relative_to(repository_root).as_posix()
        for path in candidates
        if path.is_file() and not path.name.endswith(GENERATED_LOCK_SUFFIX)
    )
    if not workflow_files:
        raise ValueError("No hand-authored GitHub Actions workflow files were found.")
    return workflow_files


def run_actionlint(
    binary: str,
    repository_root: Path = ROOT,
    process_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    workflow_files = list_authored_workflows(repository_root)
    print(
        f"Running actionlint on {len(workflow_files)} hand-authored workflow files; "
        f"excluding generated {GENERATED_LOCK_SUFFIX} files."
    )
    result = process_runner(
        [binary, "-color=false", *workflow_files],
        cwd=repository_root,
        check=False,
    )
    return result.returncode


def main(arguments: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if len(arguments) != 1:
        print("Usage: python3 scripts/lint_authored_workflows.py <actionlint-binary>", file=sys.stderr)
        return 2
    try:
        return run_actionlint(arguments[0])
    except (OSError, ValueError) as error:
        print(f"actionlint workflow validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

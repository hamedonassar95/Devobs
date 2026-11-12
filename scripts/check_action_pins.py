"""Reject mutable references to remote GitHub Actions.

Workflow lock files and agent workflow templates are included because they can
also introduce executable Actions definitions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<reference>[^\s#]+)")
REMOTE_ACTION_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./-]+)?@"
    r"(?P<sha>[0-9a-fA-F]{40})$"
)
DOCKER_ACTION_PATTERN = re.compile(r"^docker://\S+@sha256:[0-9a-fA-F]{64}$")
PULL_REQUEST_TARGET_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])pull_request_target(?![A-Za-z0-9_-])"
)


def workflow_sources() -> list[Path]:
    """Return checked-in workflow and workflow-authoring files."""
    suffixes = {".md", ".yaml", ".yml"}
    return sorted(
        path
        for path in WORKFLOW_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )


def mutable_action_references() -> list[tuple[Path, int, str]]:
    """Return remote Actions references that are not pinned to immutable IDs."""
    violations: list[tuple[Path, int, str]] = []
    for path in workflow_sources():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_PATTERN.match(line)
            if not match:
                continue

            reference = match.group("reference")
            if reference.startswith("./"):
                continue
            if REMOTE_ACTION_PATTERN.fullmatch(reference):
                continue
            if DOCKER_ACTION_PATTERN.fullmatch(reference):
                continue
            violations.append((path.relative_to(REPOSITORY_ROOT), line_number, reference))
    return violations


def pull_request_target_references(
    workflow_root: Path = WORKFLOW_ROOT,
) -> list[tuple[Path, int]]:
    """Find non-comment pull_request_target references in workflow YAML."""
    if not workflow_root.is_dir():
        raise FileNotFoundError(f"Workflow directory not found: {workflow_root}")

    violations: list[tuple[Path, int]] = []
    workflow_files = sorted(
        path
        for path in workflow_root.rglob("*")
        if path.suffix.lower() in {".yaml", ".yml"}
    )
    for path in workflow_files:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Workflow source must be a regular file: {path}")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code_line = line.strip()
            if code_line.startswith("#"):
                continue
            if PULL_REQUEST_TARGET_REFERENCE_PATTERN.search(code_line):
                violations.append((path, line_number))
    return violations


def main() -> int:
    trigger_violations = pull_request_target_references()
    if trigger_violations:
        print("pull_request_target is not allowed in checked-in workflow YAML:")
        for path, line_number in trigger_violations:
            print(f"  {path}:{line_number}")
        return 1

    violations = mutable_action_references()
    if violations:
        print("Remote GitHub Actions must use a full commit SHA or image digest:")
        for path, line_number, reference in violations:
            print(f"  {path}:{line_number}: {reference}")
        return 1

    checked_files = len(workflow_sources())
    print(f"Action pin check passed for {checked_files} workflow and template files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

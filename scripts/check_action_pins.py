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


def main() -> int:
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

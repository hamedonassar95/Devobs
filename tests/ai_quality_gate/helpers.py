"""Deterministic offline fixtures shared by the AI quality gate tests."""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any

EXAMPLES = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples"
    / "ai_quality_gate"
)
HEAD_SHA = "a" * 40


def _load(name: str) -> Any:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def snapshot() -> dict[str, Any]:
    """Return the canonical passing integration-control snapshot."""
    return _load("snapshot.json")


def ci_run() -> dict[str, Any]:
    """Return offline CI run metadata with no failures."""
    return _load("ci_run.json")


def ci_jobs() -> dict[str, Any]:
    """Return offline CI jobs with no failures."""
    return _load("ci_jobs.json")


def failing_ci(log: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return offline CI fixtures containing one failed step with ``log``."""
    run = ci_run()
    run["conclusion"] = "failure"
    jobs = {
        "jobs": [{
            "name": "python-tests",
            "conclusion": "failure",
            "steps": [{
                "name": "Run tests",
                "conclusion": "failure",
                "log": log,
            }],
        }],
    }
    return run, jobs


def second_task(
    first: dict[str, Any],
    *,
    task_id: str = "AQC02",
    files: list[str] | None = None,
    branch: str = "feature/ai-quality-gate-second",
    dependencies: list[str] | None = None,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a distinct task from the fixture's first task."""
    task = copy.deepcopy(first)
    task["id"] = task_id
    task["assigned_agent"] = "CODEX"
    task["branch"] = branch
    task["affected_files"] = list(
        files or ["devobs/ai_quality_gate/engine.py"]
    )
    task["dependencies"] = list(dependencies or [])
    if verification is not None:
        task["verification"] = copy.deepcopy(verification)
    return task

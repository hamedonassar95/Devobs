"""Conflict detection adapter around the canonical two-agent validator.

This module is advisory and read-only. It never starts work, mutates a task
registry, calls GitHub, changes Git state, or grants approval.
"""

from __future__ import annotations

import copy
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in ("scripts", "tools"):
    _path = str(_ROOT / _folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent_task_status_report import sanitize_display  # noqa: E402
from check_two_agent_tasks import evaluate  # noqa: E402

from .task_registry import OrchestrationError, TaskRegistry  # noqa: E402

KNOWN_DECISIONS = frozenset(("PASS", "BLOCKED", "FAIL"))


@dataclass(frozen=True)
class ConflictFinding:
    """A sanitized validator finding tied to specific tasks."""

    kind: str
    reason: str
    task_ids: tuple[str, ...]
    files: tuple[str, ...] = ()
    branches: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class ConflictReport:
    """A fail-closed view of coordination policy results."""

    decision: str
    errors: tuple[str, ...]
    findings: tuple[ConflictFinding, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "errors": list(self.errors),
            "findings": [
                {
                    "kind": finding.kind,
                    "reason": finding.reason,
                    "task_ids": list(finding.task_ids),
                    "files": list(finding.files),
                    "branches": list(finding.branches),
                    "dependencies": list(finding.dependencies),
                    "detail": finding.detail,
                }
                for finding in self.findings
            ],
            "summary": copy.deepcopy(self.summary),
        }


def _failure(errors: tuple[str, ...]) -> ConflictReport:
    return ConflictReport("FAIL", errors, (), {})


def _text_list(value: Any, limit: int = 100) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(sanitize_display(item, limit=limit) for item in value)


def _source_manifest(source: TaskRegistry | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(source, TaskRegistry):
        return source.to_manifest()
    if isinstance(source, Mapping):
        try:
            return copy.deepcopy(dict(source))
        except Exception as exc:  # untrusted mappings may fail during copying
            raise OrchestrationError("manifest could not be copied") from exc
    raise OrchestrationError("source must be a TaskRegistry or manifest mapping")


class ConflictDetector:
    """Evaluate registry state with the existing validator policy engine."""

    def __init__(self, source: TaskRegistry | Mapping[str, Any]):
        self.source = source

    def evaluate(self) -> ConflictReport:
        try:
            manifest = _source_manifest(self.source)
        except Exception as exc:
            return _failure((f"invalid source: {type(exc).__name__}",))
        try:
            result = evaluate(manifest)
        except Exception as exc:  # fail closed on validator defects as well
            return _failure((f"validator failure: {type(exc).__name__}",))
        if not isinstance(result, dict):
            return _failure(("validator returned an unexpected shape",))
        decision = result.get("decision")
        if decision not in KNOWN_DECISIONS:
            return _failure(("validator returned an unknown decision",))

        errors = tuple(
            sanitize_display(item, limit=500)
            for item in result.get("errors", [])
            if isinstance(item, (str, int, float, bool))
        )
        if decision == "FAIL":
            return ConflictReport("FAIL", errors or ("validator failed",), (),
                                  self._summary(result))

        findings: list[ConflictFinding] = []
        for item in result.get("conflicts", []):
            if not isinstance(item, Mapping):
                continue
            findings.append(ConflictFinding(
                kind="conflict",
                reason=sanitize_display(item.get("reason"), limit=100),
                task_ids=_text_list(item.get("tasks")),
                files=_text_list(item.get("files")),
                branches=_text_list(item.get("branches")),
                detail=sanitize_display(item.get("detail"), limit=300),
            ))
        for item in result.get("blocked_tasks", []):
            if not isinstance(item, Mapping):
                continue
            task_id = sanitize_display(item.get("task"), limit=80)
            findings.append(ConflictFinding(
                kind="blocked_task",
                reason=sanitize_display(item.get("reason"), limit=100),
                task_ids=(task_id,) if task_id else (),
                dependencies=_text_list(item.get("dependencies")),
                detail=sanitize_display(item.get("detail"), limit=300),
            ))
        return ConflictReport(decision, errors, tuple(findings), self._summary(result))

    @staticmethod
    def _summary(result: Mapping[str, Any]) -> dict[str, Any]:
        summary = result.get("summary", {})
        if not isinstance(summary, Mapping):
            return {}
        def safe_value(value: Any) -> Any:
            if isinstance(value, bool) or isinstance(value, (int, float)):
                return value
            return sanitize_display(value, limit=200)

        return {
            sanitize_display(str(key), limit=80): safe_value(value)
            for key, value in summary.items()
        }


__all__ = ["ConflictDetector", "ConflictFinding", "ConflictReport"]

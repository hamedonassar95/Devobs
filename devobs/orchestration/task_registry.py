"""Durable, fail-closed registry for advisory multi-agent work.

Public field names are orchestration-oriented (for example ``owner``), but
persisted records and validation use the exact two-agent manifest contract.
The registry never grants execution or approval authority.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass, fields, replace
from typing import Any, Iterable, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from check_two_agent_tasks import (  # noqa: E402
    ALLOWED_TRANSITIONS,
    APPROVAL_VALUE,
    BRANCH_RE,
    ID_RE,
    MAX_MANIFEST_BYTES,
    NO_STATUS,
    REPO_RE,
    RESTRICTED_ACTIONS,
    SHA_RE,
    STATUSES,
    TASK_KEYS,
    VERIFICATION_RESULTS,
    WORKER_ROLES,
    _has_cycle,
    _normal_path,
    evaluate,
)

SCHEMA_VERSION = "orchestration/task-registry/v1"
_APPROVED_TASK_ACTIONS = ("code_change", "review", "test", "documentation")


class OrchestrationError(ValueError):
    """Base class for bounded, fail-closed orchestration failures."""


class ValidationError(OrchestrationError):
    """A task does not satisfy the canonical contract."""


class DuplicateTaskError(OrchestrationError):
    """A task ID is already registered."""


class DependencyError(OrchestrationError):
    """Dependencies are unknown, cyclic, or otherwise unsatisfiable."""


class TransitionError(OrchestrationError):
    """A requested status transition is not allowed by policy."""


class StoreError(OrchestrationError):
    """Registry state is missing, corrupt, stale, or unwritable."""


@dataclass(frozen=True)
class Task:
    """One advisory work item using repository-facing field names."""

    task_id: str
    owner: str
    branch: str
    repository: str
    affected_files: tuple[str, ...]
    dependencies: tuple[str, ...]
    status: str
    previous_status: str
    source_sha: str | None
    verification: dict[str, Any]
    pr_reference: str | None
    requested_actions: tuple[str, ...]

    def to_manifest_record(self) -> dict[str, Any]:
        """Return the exact canonical manifest shape expected by the validator."""
        return {
            "id": self.task_id,
            "repository": self.repository,
            "assigned_agent": self.owner,
            "branch": self.branch,
            "affected_files": list(self.affected_files),
            "dependencies": list(self.dependencies),
            "status": self.status,
            "previous_status": self.previous_status,
            "source_sha": self.source_sha,
            "verification": {
                "commands": list(self.verification["commands"]),
                "result": self.verification["result"],
                "evidence": self.verification["evidence"],
            },
            "pr_reference": self.pr_reference,
            "requested_actions": list(self.requested_actions),
        }

    @classmethod
    def from_manifest_record(cls, record: Mapping[str, Any]) -> "Task":
        verification = record.get("verification")
        if not isinstance(verification, Mapping):
            raise ValidationError("invalid verification record")
        return cls(
            task_id=record["id"],
            owner=record["assigned_agent"],
            branch=record["branch"],
            repository=record["repository"],
            affected_files=tuple(record["affected_files"]),
            dependencies=tuple(record["dependencies"]),
            status=record["status"],
            previous_status=record["previous_status"],
            source_sha=record["source_sha"],
            verification=dict(verification),
            pr_reference=record["pr_reference"],
            requested_actions=tuple(record["requested_actions"]),
        )


@dataclass(frozen=True)
class TaskSnapshot:
    """A versioned view of a registered task."""

    task: Task
    version: int


@dataclass(frozen=True)
class UpdateResult:
    """The outcome of an idempotent registry update."""

    task: Task
    version: int
    changed: bool


def _text(value: Any, limit: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= limit


def _tuple_of_text(value: Any, field: str, limit: int = 200) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ValidationError(f"{field} must be a bounded sequence of strings")
    items = tuple(value)
    if any(not _text(item, limit) for item in items):
        raise ValidationError(f"{field} must contain bounded non-empty strings")
    return items


def _normalize_task(task: Task) -> Task:
    if not isinstance(task, Task):
        raise ValidationError("task must be a Task instance")
    if not ID_RE.fullmatch(task.task_id):
        raise ValidationError("invalid task id")
    if not REPO_RE.fullmatch(task.repository):
        raise ValidationError("invalid repository")
    if task.owner not in WORKER_ROLES:
        raise ValidationError("owner must be a registered worker role")
    if not BRANCH_RE.fullmatch(task.branch) or task.branch.startswith("main"):
        raise ValidationError("invalid or protected branch")
    if task.status not in STATUSES or task.previous_status not in (NO_STATUS,) + STATUSES:
        raise ValidationError("invalid status")
    # Evidence-ready is always an evidence assertion first; reject an
    # unattributable claim before discussing how the task got there.
    if task.status == "evidence_ready" and task.source_sha is None:
        raise ValidationError("source_sha is required for reviewed work")
    if task.status not in ALLOWED_TRANSITIONS[task.previous_status]:
        raise TransitionError("disallowed status transition")
    if task.source_sha is not None and not SHA_RE.fullmatch(task.source_sha):
        raise ValidationError("source_sha must be null or 40 lowercase hex characters")

    paths = []
    for value in task.affected_files:
        normalized = _normal_path(value)
        if normalized is None:
            raise ValidationError("affected_files must be repository-relative paths")
        paths.append(normalized)
    if not paths or len(paths) > 100 or len(set(paths)) != len(paths):
        raise ValidationError("affected_files must be a non-empty unique bounded list")

    dependencies = _tuple_of_text(task.dependencies, "dependencies")
    if len(dependencies) > 50 or len(set(dependencies)) != len(dependencies):
        raise ValidationError("dependencies must be a unique bounded list")
    if any(not ID_RE.fullmatch(dep) for dep in dependencies):
        raise ValidationError("invalid dependency id")
    if task.task_id in dependencies:
        raise ValidationError("self dependency is not allowed")

    verification = task.verification
    if (
        not isinstance(verification, Mapping)
        or set(verification) != {"commands", "result", "evidence"}
    ):
        raise ValidationError("invalid verification fields")
    commands = _tuple_of_text(verification["commands"], "verification commands", 500)
    if len(commands) > 20:
        raise ValidationError("too many verification commands")
    evidence = verification["evidence"]
    result = verification["result"]
    if result not in VERIFICATION_RESULTS:
        raise ValidationError("invalid verification result")
    if not isinstance(evidence, str) or len(evidence) > 4000:
        raise ValidationError("verification evidence must be bounded text")
    if task.status in ("evidence_ready", "complete") and task.source_sha is None:
        raise ValidationError("source_sha is required for reviewed work")
    if task.status == "complete" and (
        result != "PASS" or not commands or not evidence.strip()
    ):
        raise ValidationError("complete requires PASS commands and evidence")
    if result == "PASS" and task.status not in ("evidence_ready", "complete"):
        raise ValidationError("PASS evidence requires evidence_ready or complete status")

    pr = task.pr_reference
    if pr is not None and not _text(pr, 200):
        raise ValidationError("invalid pr_reference")

    actions = _tuple_of_text(task.requested_actions, "requested_actions", 100)
    allowed_actions = _APPROVED_TASK_ACTIONS + RESTRICTED_ACTIONS
    if any(action not in allowed_actions for action in actions):
        raise ValidationError("invalid requested_actions")
    if any(action in RESTRICTED_ACTIONS for action in actions):
        raise ValidationError("restricted actions require separate human approval")

    return replace(
        task,
        affected_files=tuple(paths),
        dependencies=dependencies,
        verification={"commands": list(commands), "result": result, "evidence": evidence},
        requested_actions=actions,
    )


def _candidate_graph(records: Mapping[str, Task], candidate: Task) -> dict[str, dict]:
    graph = {
        task_id: {
            "repository": task.repository,
            "dependencies": list(task.dependencies),
        }
        for task_id, task in records.items()
    }
    graph[candidate.task_id] = {
        "repository": candidate.repository,
        "dependencies": list(candidate.dependencies),
    }
    return graph


def _check_dependencies(graph: Mapping[str, dict]) -> None:
    for task_id, record in graph.items():
        for dependency in record["dependencies"]:
            if dependency not in graph:
                raise DependencyError(f"unknown dependency {dependency} for {task_id}")
            if graph[dependency]["repository"] != record["repository"]:
                raise DependencyError(f"dependency {dependency} crosses repositories")
    if _has_cycle(graph):
        raise DependencyError("dependency cycle")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("duplicate JSON key")
        result[key] = value
    return result


class TaskRegistry:
    """In-memory registry with optional atomic JSON persistence."""

    def __init__(self, path: str | pathlib.Path | None = None):
        self.path = pathlib.Path(path) if path is not None else None
        self._tasks: dict[str, TaskSnapshot] = {}
        if self.path is not None and self.path.exists():
            self._load()
        elif self.path is not None and self.path.is_symlink():
            raise StoreError("invalid registry path")

    def _load(self) -> None:
        if self.path is None or self.path.is_symlink():
            raise StoreError("invalid registry path")
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise StoreError("registry read failed") from exc
        if not raw or len(raw) > MAX_MANIFEST_BYTES:
            raise StoreError("registry file is empty or too large")
        try:
            payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("invalid registry JSON") from exc
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "tasks"}:
            raise StoreError("invalid registry structure")
        if payload["schema_version"] != SCHEMA_VERSION:
            raise StoreError("unsupported registry schema")
        records = payload["tasks"]
        if not isinstance(records, list) or len(records) > 200:
            raise StoreError("registry task list is invalid")

        tasks: dict[str, TaskSnapshot] = {}
        for item in records:
            expected_keys = TASK_KEYS | {"version"}
            if not isinstance(item, dict) or set(item) != expected_keys:
                raise StoreError("invalid registry record")
            version = item["version"]
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise StoreError("invalid task version")
            record = {key: value for key, value in item.items() if key != "version"}
            try:
                task = _normalize_task(Task.from_manifest_record(record))
            except OrchestrationError as exc:
                raise StoreError(f"invalid persisted task: {exc}") from exc
            if task.task_id in tasks:
                raise StoreError("duplicate persisted task")
            tasks[task.task_id] = TaskSnapshot(task, version)

        graph = {
            task_id: {
                "repository": snapshot.task.repository,
                "dependencies": list(snapshot.task.dependencies),
            }
            for task_id, snapshot in tasks.items()
        }
        try:
            _check_dependencies(graph)
            self._assert_policy(tasks)
        except OrchestrationError as exc:
            raise StoreError(f"invalid persisted graph: {exc}") from exc
        self._tasks = tasks

    def _manifest_tasks(
        self, tasks: Mapping[str, TaskSnapshot], candidate: Task | None = None
    ) -> list[dict[str, Any]]:
        records = {
            task_id: snapshot.task.to_manifest_record()
            for task_id, snapshot in tasks.items()
        }
        if candidate is not None:
            records[candidate.task_id] = candidate.to_manifest_record()
        return list(records.values())

    def _assert_policy(
        self, tasks: Mapping[str, TaskSnapshot], candidate: Task | None = None
    ) -> None:
        manifest = {
            "schema_version": 1,
            "repositories": sorted({task.repository for task in
                                    (snap.task for snap in tasks.values())}),
            "agents": {role: {"enabled": True} for role in WORKER_ROLES},
            "approval": {action: APPROVAL_VALUE for action in RESTRICTED_ACTIONS},
            "tasks": self._manifest_tasks(tasks, candidate),
        }
        if candidate is not None and candidate.repository not in manifest["repositories"]:
            manifest["repositories"].append(candidate.repository)
        result = evaluate(manifest)
        if result.get("decision") == "FAIL":
            raise ValidationError("; ".join(result.get("errors", [])) or "policy validation failed")
        if result.get("decision") != "BLOCKED":
            # PASS is valid for conflict-free work; BLOCKED conflicts are the
            # conflict detector's responsibility and must not be hidden here.
            if result.get("decision") != "PASS":
                raise ValidationError("validator returned an unknown decision")

    def add(self, task: Task) -> TaskSnapshot:
        candidate = _normalize_task(task)
        graph = _candidate_graph(
            {task_id: snap.task for task_id, snap in self._tasks.items()}, candidate
        )
        _check_dependencies(graph)
        if candidate.task_id in self._tasks:
            raise DuplicateTaskError(f"duplicate task id {candidate.task_id}")
        self._assert_policy(self._tasks, candidate)
        snapshot = TaskSnapshot(candidate, 1)
        self._tasks[candidate.task_id] = snapshot
        self._persist()
        return snapshot

    def update(
        self,
        task_id: str,
        changes: Mapping[str, Any],
        *,
        expected_version: int | None = None,
    ) -> UpdateResult:
        current = self.get(task_id)
        if expected_version is not None and expected_version != current.version:
            raise StoreError("stale expected_version")
        if not isinstance(changes, Mapping):
            raise ValidationError("changes must be a mapping")
        allowed = {field.name for field in fields(Task)} - {"task_id"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValidationError(f"unknown update fields: {', '.join(sorted(unknown))}")
        if "status" in changes:
            new_status = changes["status"]
            if new_status != current.task.status:
                changes = dict(changes)
                changes["previous_status"] = current.task.status
        candidate = _normalize_task(replace(current.task, **dict(changes)))
        if candidate == current.task:
            return UpdateResult(candidate, current.version, False)

        remaining = dict(self._tasks)
        remaining[task_id] = TaskSnapshot(candidate, current.version)
        self._assert_policy(remaining)
        snapshot = TaskSnapshot(candidate, current.version + 1)
        self._tasks[task_id] = snapshot
        self._persist()
        return UpdateResult(snapshot.task, snapshot.version, True)

    def get(self, task_id: str) -> TaskSnapshot:
        try:
            return self._tasks[task_id]
        except (KeyError, TypeError) as exc:
            raise StoreError("unknown task id") from exc

    def list(self) -> tuple[TaskSnapshot, ...]:
        return tuple(self._tasks.values())

    def to_manifest(self) -> dict[str, Any]:
        """Export the canonical offline manifest for downstream reuse."""
        return {
            "schema_version": 1,
            "repositories": sorted({snap.task.repository for snap in self._tasks.values()}),
            "agents": {role: {"enabled": True} for role in WORKER_ROLES},
            "approval": {action: APPROVAL_VALUE for action in RESTRICTED_ACTIONS},
            "tasks": [snap.task.to_manifest_record() for snap in self._tasks.values()],
        }

    def _persist(self) -> None:
        if self.path is None:
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "tasks": [
                {**snapshot.task.to_manifest_record(), "version": snapshot.version}
                for snapshot in self._tasks.values()
            ],
        }
        temporary: pathlib.Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = pathlib.Path(handle.name)
                json.dump(payload, handle, ensure_ascii=True, sort_keys=True, indent=2)
                handle.write("\n")
            os.replace(temporary, self.path)
        except OSError as exc:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            raise StoreError("registry write failed") from exc


__all__ = [
    "DependencyError",
    "DuplicateTaskError",
    "OrchestrationError",
    "StoreError",
    "Task",
    "TaskRegistry",
    "TaskSnapshot",
    "TransitionError",
    "UpdateResult",
    "ValidationError",
]

"""Read-only, offline-first repository state collection boundary.

This module never opens a network connection, executes a command, reads
credentials, or imports a provider named by external input. A caller supplies a
local snapshot mapping, a callable, or an object exposing ``collect(request)``.
Untrusted PR/workflow text is treated as data and returned only after redaction.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from .models import MAX_FILES, MAX_STRING
from .validation import ValidationError, as_mapping, norm_repo, norm_text, redact

MAX_REQUEST_FIELDS = 20
MAX_STATE_FIELDS = 100
MAX_KEY_LENGTH = 200
MAX_STATE_DEPTH = 12


class CollectionError(ValueError):
    """Raised when local state collection is unavailable, unsafe, or malformed."""


@runtime_checkable
class StateProvider(Protocol):
    """Local provider contract. Implementations must be supplied by the caller."""

    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class _CallableProvider:
    def __init__(self, fn: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self._fn = fn

    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._fn(request)


class OfflineSnapshotProvider:
    """Provider backed by an in-memory snapshot; performs no I/O."""

    def __init__(self, snapshot: Mapping[str, Any]) -> None:
        self._snapshot = as_mapping(snapshot, "snapshot")

    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        normalized = _normalize_request(request)
        _ensure_bounded(self._snapshot)
        repo, pr_number = _snapshot_identity(self._snapshot)
        if repo is None or pr_number is None:
            raise CollectionError("snapshot identity missing")
        if repo != normalized["repository"] or pr_number != normalized["pr_number"]:
            raise CollectionError("snapshot identity does not match request")

        requested_sha = normalized["head_sha"]
        pr = self._snapshot.get("pr", self._snapshot)
        snapshot_sha = pr.get("head_sha", self._snapshot.get("head_sha")) if isinstance(pr, Mapping) else self._snapshot.get("head_sha")
        if requested_sha and isinstance(snapshot_sha, str):
            if snapshot_sha.strip().lower() != requested_sha.lower():
                raise CollectionError("snapshot head sha does not match request")
        return self._snapshot


def _normalize_request(request: Any) -> dict[str, Any]:
    req = as_mapping(request, "request")
    if len(req) > MAX_REQUEST_FIELDS:
        raise CollectionError("request has too many fields")
    repository = norm_repo(req.get("repository"))
    if not repository:
        raise CollectionError("request.repository must be OWNER/REPO")
    pr_number = req.get("pr_number")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        raise CollectionError("request.pr_number must be a positive integer")
    head_sha = norm_text(req.get("head_sha"), "request.head_sha", 80)
    if head_sha is not None and len(head_sha) != 40:
        raise CollectionError("request.head_sha must be 40-char hex")
    return {"repository": repository, "pr_number": pr_number, "head_sha": head_sha.lower() if head_sha else None}


def _snapshot_identity(state: Mapping[str, Any]) -> tuple[str | None, int | None]:
    pr = state.get("pr", state)
    identity = pr if isinstance(pr, Mapping) else {}
    repo = identity.get("repository", state.get("repository"))
    pr_number = identity.get("pr_number", state.get("pr_number"))
    repo_value = norm_repo(repo) if repo is not None else None
    pr_value = pr_number if isinstance(pr_number, int) and not isinstance(pr_number, bool) and pr_number > 0 else None
    return repo_value, pr_value


def _ensure_bounded(value: Any, path: str = "state", depth: int = 0, nodes: list[int] | None = None) -> None:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_FILES:
        raise CollectionError("state exceeds node limit")
    if depth > MAX_STATE_DEPTH:
        raise CollectionError(f"{path} exceeds depth limit")
    if isinstance(value, Mapping):
        if len(value) > MAX_STATE_FIELDS:
            raise CollectionError(f"{path} has too many fields")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_KEY_LENGTH:
                raise CollectionError(f"{path} has invalid field name")
            _ensure_bounded(item, f"{path}.{key}", depth + 1, nodes)
    elif isinstance(value, (list, tuple)):
        if len(value) > MAX_FILES:
            raise CollectionError(f"{path} exceeds list limit")
        for idx, item in enumerate(value):
            _ensure_bounded(item, f"{path}[{idx}]", depth + 1, nodes)
    elif isinstance(value, str) and len(value) > MAX_STRING * 2:
        raise CollectionError(f"{path} exceeds string limit")


def collect_repository_state(provider: Any, request: Mapping[str, Any]) -> dict[str, Any]:
    """Collect a bounded, redacted snapshot for later deterministic evaluation.

    ``provider`` must be a local mapping, callable, or object with ``collect``.
    Passing a provider name string is rejected: no dynamic import or shell
    execution is performed from request data.
    """

    normalized = _normalize_request(request)
    if isinstance(provider, Mapping):
        source: StateProvider = OfflineSnapshotProvider(provider)
    else:
        collect = getattr(provider, "collect", None)
        if callable(collect):
            source = provider
        elif callable(provider):
            source = _CallableProvider(provider)
        else:
            raise CollectionError("provider must be a mapping, callable, or expose collect()")

    try:
        state = source.collect(normalized)
    except CollectionError:
        raise
    except ValidationError as exc:
        raise CollectionError(f"invalid provider response: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - fail closed without leaking provider details
        raise CollectionError(f"provider unavailable: {exc.__class__.__name__}") from exc

    state_map = as_mapping(state, "provider response")
    _ensure_bounded(state_map)
    repo, pr_number = _snapshot_identity(state_map)
    if repo != normalized["repository"] or pr_number != normalized["pr_number"]:
        raise CollectionError("provider response identity does not match request")
    return redact(state_map)

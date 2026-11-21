"""Normalize and validate portfolio health inputs. Fail-closed, read-only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from scripts.ci_failure_intelligence import redact_secrets

from .models import EVIDENCE_STATES, FRESH, STALE, UNKNOWN, MAX_ID, MAX_ITEMS, MAX_STRING, clip


class CollectionError(ValueError):
    pass


def redact_obj(value: Any, key_hint: str = "", depth: int = 0) -> Any:
    if depth > 8:
        return "[TRUNCATED]"
    sensitive = {"token", "secret", "password", "authorization", "api_key", "apikey", "credential", "private_key"}
    if key_hint.lower() in sensitive:
        return "[REDACTED]"
    if isinstance(value, str):
        return clip(redact_secrets(value))
    if isinstance(value, Mapping):
        out = {}
        for k, v in list(value.items())[:MAX_ITEMS]:
            ks = str(k)[:MAX_ID]
            out[ks] = redact_obj(v, ks, depth + 1)
        return out
    if isinstance(value, list):
        return [redact_obj(v, key_hint, depth + 1) for v in value[:MAX_ITEMS]]
    if isinstance(value, tuple):
        return [redact_obj(v, key_hint, depth + 1) for v in value[:MAX_ITEMS]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return clip(value)


def parse_iso(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts or len(ts) > 64:
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def evidence_freshness(observed_at: Any, *, now: datetime, max_age_seconds: int) -> str:
    dt = parse_iso(observed_at)
    if dt is None:
        return UNKNOWN
    age = (now - dt).total_seconds()
    if age < 0:
        return STALE
    return FRESH if age <= max_age_seconds else STALE


def normalize_evidence(raw: Any, *, now: datetime, max_age_seconds: int) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CollectionError("evidence must be a list")
    if len(raw) > MAX_ITEMS:
        raise CollectionError("evidence exceeds limit")
    out = []
    seen = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise CollectionError(f"evidence[{i}] must be object")
        eid = str(item.get("evidence_id", "")).strip()[:MAX_ID]
        if not eid:
            raise CollectionError(f"evidence[{i}].evidence_id required")
        if eid in seen:
            raise CollectionError(f"duplicate evidence_id: {eid}")
        seen.add(eid)
        observed_at = item.get("observed_at", "")
        freshness = evidence_freshness(observed_at, now=now, max_age_seconds=max_age_seconds)
        status = str(item.get("status", freshness)).upper()
        if status not in EVIDENCE_STATES:
            status = freshness
        rec = {
            "evidence_id": eid,
            "source": clip(item.get("source", ""), 500),
            "kind": clip(item.get("kind", "unknown"), MAX_ID),
            "observed_at": clip(observed_at, 64),
            "status": status if status in EVIDENCE_STATES else freshness,
            "freshness": freshness,
            "sha": clip(item.get("sha", ""), 64),
            "details": redact_obj(item.get("details", {})),
        }
        if not rec["source"]:
            rec["status"] = UNKNOWN
            rec["freshness"] = UNKNOWN
        out.append(rec)
    return out


def normalize_components(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CollectionError("components must be a list")
    if len(raw) > MAX_ITEMS:
        raise CollectionError("components exceeds limit")
    out = []
    seen = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise CollectionError(f"components[{i}] must be object")
        name = str(item.get("name", "")).strip()[:200]
        if not name:
            raise CollectionError(f"components[{i}].name required")
        if name in seen:
            raise CollectionError(f"duplicate component: {name}")
        seen.add(name)
        deps = item.get("dependencies", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            raise CollectionError(f"components[{i}].dependencies must be list")
        out.append({
            "name": name,
            "status": clip(item.get("status", UNKNOWN), MAX_ID).upper(),
            "owner": clip(item.get("owner", ""), 200),
            "dependencies": [str(d)[:200] for d in deps[:MAX_ITEMS]],
            "evidence_ids": [str(e)[:MAX_ID] for e in (item.get("evidence_ids") or [])[:MAX_ITEMS]],
            "details": redact_obj(item.get("details", {})),
        })
    return out


def normalize_ci(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CollectionError("ci_checks must be a list")
    if len(raw) > MAX_ITEMS:
        raise CollectionError("ci_checks exceeds limit")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise CollectionError(f"ci_checks[{i}] must be object")
        out.append({
            "name": clip(item.get("name", f"check-{i}"), 200),
            "status": clip(item.get("status", UNKNOWN), MAX_ID).upper(),
            "required": bool(item.get("required", False)),
            "evidence_id": clip(item.get("evidence_id", ""), MAX_ID),
            "url": clip(item.get("url", ""), 500),
            "log_excerpt": clip(redact_secrets(str(item.get("log_excerpt", ""))), 1000),
            "details": redact_obj(item.get("details", {})),
        })
    return out


def normalize_prs(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CollectionError("pull_requests must be a list")
    if len(raw) > MAX_ITEMS:
        raise CollectionError("pull_requests exceeds limit")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise CollectionError(f"pull_requests[{i}] must be object")
        blockers = item.get("blockers", [])
        if blockers is None:
            blockers = []
        if not isinstance(blockers, list):
            raise CollectionError(f"pull_requests[{i}].blockers must be list")
        out.append({
            "number": item.get("number"),
            "title": clip(item.get("title", ""), 300),
            "head_sha": clip(item.get("head_sha", ""), 64),
            "status": clip(item.get("status", UNKNOWN), MAX_ID).upper(),
            "draft": bool(item.get("draft", False)),
            "approval_state": clip(item.get("approval_state", UNKNOWN), MAX_ID).upper(),
            "mergeable": clip(item.get("mergeable", UNKNOWN), MAX_ID).upper(),
            "blockers": [clip(b, 300) for b in blockers[:MAX_ITEMS]],
            "evidence_ids": [str(e)[:MAX_ID] for e in (item.get("evidence_ids") or [])[:MAX_ITEMS]],
            "details": redact_obj(item.get("details", {})),
        })
    return out


def normalize_ownership(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {"status": UNKNOWN, "active_agents": [], "task_manifest": None}
    if not isinstance(raw, Mapping):
        raise CollectionError("ownership must be object")
    agents = raw.get("active_agents", [])
    if agents is None:
        agents = []
    if not isinstance(agents, list):
        raise CollectionError("ownership.active_agents must be list")
    norm_agents = []
    for i, a in enumerate(agents[:MAX_ITEMS]):
        if not isinstance(a, Mapping):
            raise CollectionError(f"ownership.active_agents[{i}] must be object")
        paths = a.get("owned_paths", [])
        if paths is None:
            paths = []
        if not isinstance(paths, list):
            raise CollectionError(f"ownership.active_agents[{i}].owned_paths must be list")
        norm_agents.append({
            "agent": clip(a.get("agent", ""), 120),
            "branch": clip(a.get("branch", ""), 200),
            "worktree": clip(a.get("worktree", ""), 500),
            "owned_paths": [str(p)[:500] for p in paths[:MAX_ITEMS]],
        })
    manifest = raw.get("task_manifest")
    return {
        "status": clip(raw.get("status", UNKNOWN), MAX_ID).upper(),
        "active_agents": norm_agents,
        "task_manifest": redact_obj(manifest) if isinstance(manifest, Mapping) else (None if manifest is None else "INVALID"),
    }


def normalize_security(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CollectionError("security_findings must be a list")
    if len(raw) > MAX_ITEMS:
        raise CollectionError("security_findings exceeds limit")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise CollectionError(f"security_findings[{i}] must be object")
        out.append({
            "id": clip(item.get("id", f"sec-{i}"), MAX_ID),
            "severity": clip(item.get("severity", "HIGH"), 20).upper(),
            "status": clip(item.get("status", "OPEN"), 40).upper(),
            "component": clip(item.get("component", ""), 200),
            "message": clip(redact_secrets(str(item.get("message", ""))), 1000),
            "evidence_id": clip(item.get("evidence_id", ""), MAX_ID),
        })
    return out


def collect_snapshot(raw: Any, *, now: datetime | None = None, max_age_seconds: int = 86400) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CollectionError("snapshot must be object")
    now = now or datetime.now(timezone.utc)
    max_age_seconds = int(max_age_seconds)
    if max_age_seconds < 1 or max_age_seconds > 365 * 24 * 3600:
        raise CollectionError("max_age_seconds out of range")
    deps = raw.get("dependencies", [])
    if deps is None:
        deps = []
    if not isinstance(deps, list):
        raise CollectionError("dependencies must be a list")
    return {
        "schema_version": clip(raw.get("schema_version", 1), 32),
        "repository": clip(raw.get("repository", ""), 200),
        "generated_at": clip(raw.get("generated_at", ""), 64),
        "evidence": normalize_evidence(raw.get("evidence"), now=now, max_age_seconds=max_age_seconds),
        "components": normalize_components(raw.get("components")),
        "ci_checks": normalize_ci(raw.get("ci_checks")),
        "pull_requests": normalize_prs(raw.get("pull_requests")),
        "ownership": normalize_ownership(raw.get("ownership")),
        "security_findings": normalize_security(raw.get("security_findings")),
        "dependencies": [str(d)[:200] for d in deps[:MAX_ITEMS]],
        "approval": redact_obj(raw.get("approval")) if isinstance(raw.get("approval"), Mapping) else raw.get("approval"),
        "metadata": redact_obj(raw.get("metadata", {})),
    }
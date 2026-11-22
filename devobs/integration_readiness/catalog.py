"""Bounded local catalog loading and structural normalization."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    MAX_CATALOG_BYTES,
    MAX_INTEGRATIONS,
    MAX_ITEMS,
    MAX_SHORT_STRING,
    MAX_STRING,
    CatalogError,
)
from .security import redact_text, valid_date, valid_identifier, valid_sha

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "integration_readiness"
    / "catalog.v1.json"
)

_TOP_LEVEL = frozenset({
    "schema_version", "profile", "scope_sha", "evaluation_date",
    "component_versions", "tool_availability", "integrations", "unrecognized_top_level",
})
_CATEGORIES = frozenset({
    "ai", "ci", "data", "delivery", "identity", "iac", "observability", "runtime", "security",
})
_STATUSES = frozenset({"active", "blocked", "deprecated", "planned"})


def _text(value: Any, field: str, *, limit: int = MAX_STRING, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"invalid_{field}")
    if not allow_empty and not value.strip():
        raise CatalogError(f"invalid_{field}")
    if len(value) > limit:
        raise CatalogError(f"{field}_too_large")
    return value.strip()


def _list(value: Any, field: str, *, limit: int = MAX_ITEMS) -> list[Any]:
    if not isinstance(value, list):
        raise CatalogError(f"invalid_{field}")
    if len(value) > limit:
        raise CatalogError(f"{field}_too_large")
    return value


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"invalid_{field}")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    return [_text(item, field, limit=MAX_SHORT_STRING) for item in _list(value, field)]


def _object_list(value: Any, field: str) -> list[dict[str, Any]]:
    return [_mapping(item, field) for item in _list(value, field)]


def _normalize_integration(raw: Any) -> dict[str, Any]:
    item = _mapping(raw, "integration")
    identifier = item.get("id")
    if not valid_identifier(identifier):
        raise CatalogError("invalid_integration_id")
    result: dict[str, Any] = {
        "id": identifier,
        "name": _text(item.get("name"), "integration_name", limit=MAX_SHORT_STRING),
        "category": _text(item.get("category"), "integration_category", limit=MAX_SHORT_STRING),
        "status": _text(item.get("status"), "integration_status", limit=MAX_SHORT_STRING),
        "version": _text(item.get("version"), "integration_version", limit=MAX_SHORT_STRING),
        "owner": _text(item.get("owner"), "integration_owner", limit=MAX_SHORT_STRING),
        "license": item.get("license"),
        "owned_paths": _string_list(item.get("owned_paths", []), "owned_paths"),
        "required_config": _string_list(item.get("required_config", []), "required_config"),
        "config": _mapping(item.get("config", {}), "config"),
        "requirements": _object_list(item.get("requirements", []), "requirements"),
        "dependencies": _object_list(item.get("dependencies", []), "dependencies"),
        "security_requirements": _object_list(
            item.get("security_requirements", []), "security_requirements"
        ),
        "required_tools": _string_list(item.get("required_tools", []), "required_tools"),
        "evidence": _object_list(item.get("evidence", []), "evidence"),
        "deprecated": item.get("deprecated", False),
        "support_until": item.get("support_until"),
        "requires_human_approval": item.get("requires_human_approval", False),
        "approval": item.get("approval"),
        "notes": item.get("notes", ""),
    }
    for key in ("category", "status"):
        if result[key] not in (_CATEGORIES if key == "category" else _STATUSES):
            raise CatalogError(f"invalid_integration_{key}")
    for key in ("deprecated", "requires_human_approval"):
        if not isinstance(result[key], bool):
            raise CatalogError(f"invalid_{key}")
    for key in ("support_until", "notes"):
        if result[key] is not None and not isinstance(result[key], str):
            raise CatalogError(f"invalid_{key}")
        if isinstance(result[key], str) and len(result[key]) > MAX_STRING:
            raise CatalogError(f"{key}_too_large")
    if result["license"] is not None and not isinstance(result["license"], str):
        raise CatalogError("invalid_license")
    if result["approval"] is not None and not isinstance(result["approval"], dict):
        raise CatalogError("invalid_approval")
    return result


def normalize_catalog(raw: Any) -> dict[str, Any]:
    """Validate catalog structure and return a bounded normalized copy."""
    encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    if len(encoded.encode("utf-8")) > MAX_CATALOG_BYTES:
        raise CatalogError("input_too_large")
    payload = _mapping(raw, "catalog")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise CatalogError("invalid_schema_version")
    profile = _text(payload.get("profile"), "profile", limit=MAX_SHORT_STRING)
    scope_sha = _text(payload.get("scope_sha"), "scope_sha", limit=MAX_SHORT_STRING)
    if not valid_sha(scope_sha):
        raise CatalogError("invalid_scope_sha")
    evaluation_date = _text(payload.get("evaluation_date"), "evaluation_date", limit=MAX_SHORT_STRING)
    if not valid_date(evaluation_date):
        raise CatalogError("invalid_evaluation_date")
    component_versions = _mapping(payload.get("component_versions"), "component_versions")
    for name, version in component_versions.items():
        _text(name, "component_name", limit=MAX_SHORT_STRING)
        _text(version, "component_version", limit=MAX_SHORT_STRING)
    tool_availability = _mapping(payload.get("tool_availability"), "tool_availability")
    for name, available in tool_availability.items():
        _text(name, "tool_name", limit=MAX_SHORT_STRING)
        if not isinstance(available, bool):
            raise CatalogError("invalid_tool_availability")
    integrations = payload.get("integrations")
    if not isinstance(integrations, list):
        raise CatalogError("invalid_integrations")
    if len(integrations) > MAX_INTEGRATIONS:
        raise CatalogError("too_many_integrations")
    normalized_integrations = [_normalize_integration(item) for item in integrations]
    identifiers = [item["id"] for item in normalized_integrations]
    if len(set(identifiers)) != len(identifiers):
        raise CatalogError("duplicate_integration_id")
    return {
        "schema_version": schema_version,
        "profile": profile,
        "scope_sha": scope_sha.lower(),
        "evaluation_date": evaluation_date,
        "component_versions": dict(component_versions),
        "tool_availability": dict(tool_availability),
        "integrations": normalized_integrations,
        "unrecognized_top_level": sorted(set(payload) - _TOP_LEVEL),
    }


def load_catalog(path: str | Path | None = None) -> dict[str, Any]:
    """Load and normalize a local JSON catalog without network access."""
    catalog_path = Path(path) if path is not None else DEFAULT_FIXTURE_PATH
    try:
        if not catalog_path.is_file():
            raise CatalogError("catalog_not_found")
        if catalog_path.stat().st_size > MAX_CATALOG_BYTES:
            raise CatalogError("input_too_large")
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except CatalogError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"catalog_read_error:{redact_text(exc.__class__.__name__, 80)}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"malformed_json:{redact_text(exc.msg, 120)}") from exc
    return normalize_catalog(raw)


__all__ = ["DEFAULT_FIXTURE_PATH", "load_catalog", "normalize_catalog"]

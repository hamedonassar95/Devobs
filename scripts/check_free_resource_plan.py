#!/usr/bin/env python3
"""Validate Devobs's existing no-cost repository capability plan, offline.

A checked-in file is not evidence of a running, licensed, or free hosted service.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "strategy" / "DEVOBS_FREE_RESOURCE_PLAN.json"

# Explicit allowlist prevents an edited plan from silently adding paid providers.
EXPECTED = {"ci": (
    ".github/workflows/ci.yml",
    "REPOSITORY_WORKFLOW"
  ),
  "pages": (
    ".github/workflows/deploy-pages.yml",
    "REPOSITORY_WORKFLOW"
  ),
  "prometheus": (
    "monitoring/prometheus.yml",
    "LOCAL_OPTIONAL"
  ),
  "grafana": (
    "monitoring/grafana/provisioning/datasources/prometheus.yml",
    "LOCAL_OPTIONAL"
  ),
  "alertmanager": (
    "monitoring/alertmanager/alertmanager.yml",
    "LOCAL_OPTIONAL"
  ),
  "opentelemetry": (
    "monitoring/otel-collector-config.yaml",
    "LOCAL_OPTIONAL"
  ),
  "local-model-templates": (
    "models/docker-compose.yml",
    "LOCAL_OPTIONAL"
  ),
  "cloudevents": (
    "scripts/integrations/cloudevents_ci_adapter.mjs",
    "OFFLINE_ADVISORY"
  ),
  "alertmanager-bridge": (
    "scripts/integrations/alertmanager_adapter.mjs",
    "OFFLINE_ADVISORY"
  ),
  "otlp-bridge": (
    "scripts/integrations/otlp_error_rate_adapter.mjs",
    "OFFLINE_ADVISORY"
  ),
  "cineforge-triage": (
    "scripts/integrations/cineforge_ci_runner_triage.mjs",
    "OFFLINE_ADVISORY"
  ),
  "kubernetes-examples": (
    "k8s/README.md",
    "REFERENCE_ONLY"
  )
}
DENY_FLAGS = (
    "external_connections_allowed", "paid_operations_allowed",
    "provider_changes_allowed", "secrets_access_allowed",
    "production_deploy_allowed", "automatic_merge_allowed", "hosted_saas_ready",
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_plan(path: Path = PLAN) -> Any:
    if not path.is_file() or path.stat().st_size > 16384:
        raise ValueError("missing or oversized resource plan")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def validate_plan(data: Any, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != {"schema_version", "repository", "review_date", "policy", "resources"}:
        return ["resource plan has unexpected or missing fields"]
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        errors.append("invalid schema_version")
    if data["repository"] != "hamedonassar95/Devobs":
        errors.append("invalid repository")
    if data["review_date"] != "2026-11-15":
        errors.append("invalid reviewed baseline date; review a new plan version")
    policy = data["policy"]
    if not isinstance(policy, dict) or set(policy) != {"free_only", *DENY_FLAGS}:
        errors.append("missing or unexpected policy fields")
    else:
        if policy["free_only"] is not True:
            errors.append("free_only must stay true")
        for field in DENY_FLAGS:
            if policy[field] is not False:
                errors.append(field + " must stay false")
    resources = data["resources"]
    if not isinstance(resources, list):
        return errors + ["resources must be a list"]
    ids: set[str] = set()
    if len(resources) != len(EXPECTED):
        errors.append("unexpected resource count")
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != {"id", "path", "execution_mode"}:
            errors.append("invalid resource fields")
            continue
        name = resource["id"]
        if not isinstance(name, str) or name not in EXPECTED or name in ids:
            errors.append("unknown or duplicate resource id")
            continue
        ids.add(name)
        path, mode = EXPECTED[name]
        if resource["path"] != path or resource["execution_mode"] != mode:
            errors.append("unexpected path or execution mode for " + name)
            continue
        candidate = root / path
        if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve()):
            errors.append("checked-in capability path missing or unsafe: " + name)
    if ids != set(EXPECTED):
        errors.append("missing allowed resources")
    return errors


def main(args: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if args is None else args)
    if args not in ([], ["--json"]):
        print("FAIL: optional flag is --json only", file=sys.stderr)
        return 2
    try:
        plan = load_plan()
        errors = validate_plan(plan)
    except (OSError, UnicodeError, ValueError) as exc:
        print("FAIL: invalid free resource plan (" + str(exc) + ")", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print("FAIL: " + error, file=sys.stderr)
        return 1
    summary = {
        "result": "PASS",
        "repository_files_verified": len(EXPECTED),
        "monthly_spend_verified": False,
        "external_runtime_verified": False,
        "hosted_saas_ready": False,
        "automatic_activation": False,
    }
    if args == ["--json"]:
        print(json.dumps(summary, sort_keys=True))
    else:
        print("PASS: " + str(len(EXPECTED)) + " checked-in paths; free-only guards preserved. "
              "Runtime, hosting cost, and SaaS readiness NOT VERIFIED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

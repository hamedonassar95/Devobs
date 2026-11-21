"""Repository capability inventory for integration verification."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .models import (
    ABSENT,
    CAPABILITY_BLOCKED,
    ComponentRecord,
    DOCUMENTATION_ONLY,
    IMPLEMENTED_AND_TESTED,
    IMPLEMENTED_UNVERIFIED,
    MAX_COMPONENTS,
    PARTIALLY_IMPLEMENTED,
)


KNOWN_COMPONENTS = [
    {"name": "two_agent_task_contract", "paths": ["scripts/check_two_agent_tasks.py", "docs/agents/TWO_AGENT_COORDINATION.md"], "tests": ["tests/test_two_agent_tasks.py"], "deps": []},
    {"name": "pr_readiness_gate_cli", "paths": ["scripts/pr_readiness_gate.py", "docs/agents/PR_READINESS_GATE.md"], "tests": ["tests/test_pr_readiness_gate.py"], "deps": ["two_agent_task_contract"]},
    {"name": "incident_intelligence_library", "paths": ["devobs/incident_intelligence"], "tests": ["tests/test_incident_intelligence.py"], "deps": []},
    {"name": "incident_intelligence_engine", "paths": ["devobs/incidents", "docs/architecture/INCIDENT_INTELLIGENCE_ENGINE.md"], "tests": ["tests/incidents"], "deps": ["incident_intelligence_library"]},
    {"name": "ci_failure_intelligence", "paths": ["scripts/ci_failure_intelligence.py", "docs/agents/CI_FAILURE_INTELLIGENCE.md"], "tests": ["tests/test_ci_failure_intelligence.py"], "deps": []},
    {"name": "integration_control_plane", "paths": ["devobs/integration_control", "docs/architecture/INTEGRATION_CONTROL_PLANE.md"], "tests": ["tests/integration_control"], "deps": ["two_agent_task_contract", "pr_readiness_gate_cli"]},
    {"name": "pr_readiness_engine", "paths": ["devobs/pr_readiness", "docs/architecture/PR_READINESS_ENGINE.md"], "tests": ["tests/pr_readiness"], "deps": ["two_agent_task_contract"]},
    {"name": "agent_dispatch_preflight", "paths": ["scripts/agent_dispatch_preflight.py", "docs/agents/AGENT_DISPATCH_OPERATING_GUIDE.md"], "tests": ["tests/test_agent_dispatch_preflight.py"], "deps": ["two_agent_task_contract"]},
    {"name": "agent_task_status_report", "paths": ["tools/agent_task_status_report.py", "docs/agents/AGENT_TASK_STATUS_REPORT.md"], "tests": ["tests/test_agent_task_status_report.py"], "deps": ["two_agent_task_contract"]},
    {"name": "model_router_provider_adapters", "paths": ["tools/cost-aware-model-router"], "tests": ["tests/test_cost_aware_model_router.py"], "deps": []},
    {"name": "tracing_anomaly_detection", "paths": ["scripts", "docs/observability", "docs/runbooks"], "tests": ["tests"], "deps": [], "keyword": "trace|anomaly|otel|observability"},
    {"name": "security_ownership_policy", "paths": ["AGENTS.md", "docs/security", "scripts/check_two_agent_tasks.py"], "tests": ["tests/test_two_agent_tasks.py"], "deps": []},
]


def _exists(repo_root: Path, rel: str) -> bool:
    return (repo_root / rel).exists()


def _discover_tests(repo_root: Path, tests: list[str], keyword: str | None = None) -> list[str]:
    found = [t for t in tests if _exists(repo_root, t)]
    if keyword and not found:
        for p in (repo_root / "tests").glob("**/*"):
            name = p.name.lower()
            if any(k in name for k in keyword.split("|")):
                found.append(str(p.relative_to(repo_root)).replace("\\", "/"))
                if len(found) >= 5:
                    break
    return sorted(set(found))


def build_inventory(repo_root: Path, *, ownership_by_component: Mapping[str, str] | None = None, extra_components: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    ownership_by_component = dict(ownership_by_component or {})
    components = []
    defs = list(KNOWN_COMPONENTS) + list(extra_components or [])
    for spec in defs[:MAX_COMPONENTS]:
        name = str(spec.get("name", "")).strip()
        paths = [str(p) for p in spec.get("paths", [])]
        tests = [str(t) for t in spec.get("tests", [])]
        deps = [str(d) for d in spec.get("deps", [])]
        path_exists = [p for p in paths if _exists(repo_root, p)]
        doc_only = path_exists and all(p.endswith('.md') or '/docs/' in p.replace('\\','/') for p in path_exists)
        tests_found = _discover_tests(repo_root, tests, spec.get("keyword"))
        if not path_exists:
            status = ABSENT
            evidence_type = "none"
        elif doc_only:
            status = DOCUMENTATION_ONLY
            evidence_type = "documentation"
        elif tests_found:
            status = IMPLEMENTED_UNVERIFIED
            evidence_type = "code+tests_present_unverified"
        else:
            status = PARTIALLY_IMPLEMENTED
            evidence_type = "code_without_tests"
        owner = ownership_by_component.get(name, "main" if status != ABSENT else "unowned")
        if spec.get("blocked"):
            status = CAPABILITY_BLOCKED
        record = ComponentRecord(
            name=name,
            source_path=";".join(path_exists[:5]) or ";".join(paths[:2]),
            owning_branch=owner,
            evidence_type=evidence_type,
            test_coverage="present" if tests_found else "missing",
            integration_dependencies=tuple(deps),
            verification_status=status,
            details={"expected_paths": paths, "paths_present": path_exists, "tests_found": tests_found},
        )
        components.append(record.as_dict())
    return components

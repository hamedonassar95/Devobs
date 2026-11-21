"""Deterministic offline orchestration for integration readiness decisions."""

from __future__ import annotations

from typing import Any

from .advisory import AdvisoryProvider, assess_advisory
from .collector import collect
from .coordination import assess_coordination
from .evidence import EvidenceRegistry
from .models import (
    BLOCKED,
    BLOCKER,
    INVALID,
    POLICY_VERSION,
    PROCEED,
    UNVERIFIED,
    UNVERIFIED_SEVERITY,
    ComponentResult,
    ControlError,
    Finding,
)
from .policy import assess_approvals, assess_branches
from .pr_adapter import assess_pr
from .report import finalize_report

CHECK_NAMES = (
    "pr_readiness",
    "coordination",
    "approval",
    "branch_observations",
    "evidence",
    "security",
)


class IntegrationControlPlane:
    """Coordinate offline evidence into one advisory, fail-closed decision."""

    def __init__(self, *, advisory_provider: AdvisoryProvider | None = None) -> None:
        self._advisory_provider = advisory_provider

    @staticmethod
    def _failure_report(run_id: str, code: str) -> dict[str, Any]:
        finding = Finding(code, BLOCKER, "integration_control")
        return finalize_report({
            "schema_version": "integration-control/1.0",
            "run_id": run_id if run_id else "unverified",
            "decision": INVALID,
            "merge_authorized": False,
            "human_approval": "PENDING_HUMAN",
            "offline": True,
            "source_sha": None,
            "expected_head_sha": None,
            "findings": [finding.to_record()],
            "checks": {"passed": [], "failed": ["input"], "skipped": list(CHECK_NAMES)},
            "components": {
                "pr_readiness": {"status": "SKIPPED", "gate_status": "NOT_EVALUATED",
                                 "evidence_ids": []},
                "coordination": {"status": "SKIPPED", "decision": "NOT_EVALUATED",
                                 "conflicts": [], "blocked_tasks": []},
                "evidence": {"accepted_ids": [], "rejected": 0},
                "security": {"secret_redactions": 0, "unsafe_sources": 0},
            },
            "advisory": {
                "provider": "disabled", "status": "disabled",
                "notes": ["Deterministic policy only."], "influenced_decision": False,
            },
            "warnings": [POLICY_VERSION],
        })

    def evaluate(self, document: Any) -> dict[str, Any]:
        run_id = ""
        try:
            normalized, collected_findings = collect(document)
            run_id = str(normalized["run_id"])
            return self._evaluate_normalized(normalized, collected_findings)
        except ControlError as exc:
            return self._failure_report(run_id, exc.code)
        except Exception:  # noqa: BLE001 - unexpected failures never produce success.
            return self._failure_report(run_id, "INTERNAL_ERROR")

    def _evaluate_normalized(
        self,
        snapshot: dict[str, Any],
        collected_findings: tuple[Finding, ...],
    ) -> dict[str, Any]:
        registry = EvidenceRegistry()
        findings: list[Finding] = list(collected_findings)
        rejected = 0
        for artifact in snapshot["artifacts"]:
            accepted, duplicate = registry.add_artifact(artifact)
            if accepted:
                continue
            rejected += 1
            if duplicate is not None:
                findings.append(duplicate)

        components: tuple[ComponentResult, ...] = (
            assess_pr(snapshot["github"], snapshot["expected_head_sha"]),
            assess_coordination(snapshot["coordination"]),
            assess_approvals(snapshot["approval"]),
            assess_branches(snapshot["branch_observations"]),
        )
        for component in components:
            findings.extend(component.findings)
            for record in component.details.get("evidence_records", ()) if component.details else ():
                if not isinstance(record, dict):
                    continue
                accepted, duplicate = registry.add(record)
                if not accepted and duplicate is not None:
                    rejected += 1
                    findings.append(duplicate)

        secret_redactions = sum(
            1 for item in findings if item.code == "SECRET_MATERIAL_DETECTED"
        )
        evidence_component = self._status_component(
            "evidence", findings, lambda code: code == "DUPLICATE_EVIDENCE",
        )
        security_component = self._status_component(
            "security", findings, lambda code: code == "SECRET_MATERIAL_DETECTED",
        )
        all_components = components + (evidence_component, security_component)

        passed = sorted(
            component.check_passed for component in all_components
            if component.check_passed is not None
        )
        failed = sorted(
            component.check_failed for component in all_components
            if component.check_failed is not None
        )
        skipped = sorted(set(CHECK_NAMES) - set(passed) - set(failed))

        if any(item.severity == BLOCKER for item in findings):
            decision = BLOCKED
        elif any(item.severity == UNVERIFIED_SEVERITY for item in findings):
            decision = UNVERIFIED
        else:
            decision = PROCEED

        advisory = assess_advisory(
            self._advisory_provider,
            untrusted_text_present=bool(snapshot["untrusted_text_present"]),
            finding_codes=tuple(item.code for item in findings),
            source_sha=snapshot["expected_head_sha"],
        )
        pr_component, coordination_component, approval_component, branch_component = components
        return finalize_report({
            "schema_version": "integration-control/1.0",
            "run_id": snapshot["run_id"],
            "decision": decision,
            "merge_authorized": False,
            "human_approval": "PENDING_HUMAN",
            "offline": True,
            "source_sha": snapshot["expected_head_sha"],
            "expected_head_sha": snapshot["expected_head_sha"],
            "findings": [item.to_record() for item in findings],
            "checks": {"passed": passed, "failed": failed, "skipped": skipped},
            "components": {
                "pr_readiness": {
                    "status": pr_component.status,
                    "gate_status": pr_component.details.get("gate_status", "NOT_EVALUATED")
                    if pr_component.details else "NOT_EVALUATED",
                    "evidence_ids": list(pr_component.evidence_ids),
                },
                "coordination": {
                    "status": coordination_component.status,
                    "decision": coordination_component.details.get("decision", "NOT_EVALUATED")
                    if coordination_component.details else "NOT_EVALUATED",
                    "conflicts": list(coordination_component.details.get("conflicts", []))
                    if coordination_component.details else [],
                    "blocked_tasks": list(coordination_component.details.get("blocked_tasks", []))
                    if coordination_component.details else [],
                },
                "evidence": {
                    "accepted_ids": list(registry.accepted_ids),
                    "rejected": rejected,
                },
                "security": {
                    "secret_redactions": secret_redactions,
                    "unsafe_sources": 0,
                },
            },
            "advisory": advisory,
            "warnings": [POLICY_VERSION, "ci_evidence_is_technical_only"],
        })

    @staticmethod
    def _status_component(
        name: str,
        findings: tuple[Finding, ...] | list[Finding],
        matcher: Any,
    ) -> ComponentResult:
        if any(matcher(item.code) for item in findings):
            return ComponentResult(
                name=name,
                status="BLOCKED",
                findings=(),
                check_failed=name,
            )
        return ComponentResult(
            name=name,
            status="PASS",
            findings=(),
            check_passed=name,
        )

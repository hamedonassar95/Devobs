"""Deterministic offline fixtures for integration-control hardening tests."""

from __future__ import annotations

from typing import Any

from scripts.check_two_agent_tasks import RESTRICTED_ACTIONS

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/integration_control
    import helpers as h

APPROVAL_TIME = "2026-11-21T01:00:00Z"


def approval_record(
    action: str = "merge",
    *,
    approval: str = "APPROVE",
    verification_status: str = "VERIFIED",
    pr_open: bool = True,
    pr_merged: bool = False,
    approver_is_human: bool = True,
    approver_has_write: bool = True,
    evidence_ids: list[str] | None = None,
    recorded_at: str = APPROVAL_TIME,
) -> dict[str, Any]:
    return {
        "action": action,
        "approval": approval,
        "verification_status": verification_status,
        "pr_open": pr_open,
        "pr_merged": pr_merged,
        "approver_is_human": approver_is_human,
        "approver_has_write": approver_has_write,
        "evidence_ids": list(evidence_ids or [f"APPROVAL_{action.upper()}_001"]),
        "recorded_at": recorded_at,
    }


def complete_approval_set(**kwargs: Any) -> list[dict[str, Any]]:
    return [approval_record(action, **kwargs) for action in RESTRICTED_ACTIONS]


def retry_policy(
    *,
    max_identical_retries: int = 1,
    prior_attempt_digests: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "max_identical_retries": max_identical_retries,
        "prior_attempt_digests": list(prior_attempt_digests or []),
    }


def duplicate_retry_manifest() -> dict[str, Any]:
    """Two non-complete tasks claiming identical verification work."""
    first = h.task("HARD01", files=["devobs/integration_control/hardening.py"])
    second = h.task(
        "HARD02",
        agent="CODEX",
        branch="feature/hardening-second",
        files=["devobs/integration_control/control_events.py"],
    )
    return h.manifest(first, second)


def snapshot() -> dict[str, Any]:
    return h.snapshot()

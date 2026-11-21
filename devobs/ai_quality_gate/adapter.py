"""Offline explanatory advisory adapter.

The adapter implements the existing ``AdvisoryProvider`` protocol
(``assess(context) -> str``). It receives only closed finding codes and a source
SHA from the control plane; it never receives repository text, logs, credentials
or secrets, and it makes no network call. Its output is still passed through the
control plane's redaction and is strictly advisory.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_ADVISORY_CHARS = 600
MAX_CODES = 20
DEFAULT_EXPLANATION = (
    "Review the cited finding and its attached evidence before taking any action."
)

EXPLANATIONS = {
    "CONCURRENT_FILE_OWNERSHIP": (
        "Two active tasks claim the same file; assign one owner or split the paths."
    ),
    "CONCURRENT_BRANCH_OWNERSHIP": (
        "Two active tasks claim the same branch; isolate each task in its own branch."
    ),
    "BLOCKED_TASK_RETAINS_OWNERSHIP": (
        "A blocked task still owns its files and branch; release or reassign it after review."
    ),
    "UNRESOLVED_DEPENDENCY": (
        "A prerequisite task is not complete; finish it and re-run the gate before proceeding."
    ),
    "AGENT_NOT_ENABLED": (
        "The assigned worker is not enabled; use a registered, enabled worker role."
    ),
    "INVALID_DEPENDENCY_GRAPH": (
        "The task dependency graph is invalid; remove the cycle or unknown reference."
    ),
    "COORDINATION_MANIFEST_INVALID": (
        "The task manifest violates the two-agent contract; correct the reported field."
    ),
    "UNSAFE_RETRY_LOOP": (
        "Repeated identical verification claims form a retry loop; supply fresh evidence."
    ),
    "UNAUTHORIZED_ACTION_REQUESTED": (
        "A task requested a restricted or destructive action; keep it pending human approval."
    ),
    "DUPLICATE_EVIDENCE": (
        "Duplicate evidence was submitted; use a unique ID and digest for each artifact."
    ),
    "SECRET_MATERIAL_DETECTED": (
        "Secret-like material was detected and redacted; remove it from the source input."
    ),
    "HUMAN_APPROVAL_MISSING": (
        "One or more restricted approvals are absent; all four must remain pending_human."
    ),
    "SECURITY_POLICY_VIOLATION": (
        "An approval or action violates policy; do not bypass the human gate."
    ),
    "CI_FAILURE_CODE": (
        "A code-category CI failure was classified from evidence; inspect the failing step."
    ),
    "CI_FAILURE_UNVERIFIED": (
        "A CI failure is unverified or infrastructure-related; confirm before attributing it to code."
    ),
    "CI_FAILURE_AMBIGUOUS": (
        "A CI failure has no confident classification; gather more evidence rather than guessing."
    ),
    "CI_FAILURE_FLAKY_OR_EXTERNAL": (
        "A CI failure was classified as flaky or external; re-run only after human review."
    ),
}


class LocalExplanatoryAdapter:
    """Deterministic offline advisory provider with bounded, safe output."""

    def assess(self, context: Mapping[str, Any]) -> str:
        """Return bounded explanations for the supplied closed finding codes."""
        if not isinstance(context, Mapping):
            return ""
        raw = context.get("finding_codes", ())
        if not isinstance(raw, (list, tuple, set, frozenset)):
            return ""
        codes = sorted(
            {str(code)[:64] for code in raw if isinstance(code, str)}
        )[:MAX_CODES]
        lines = [
            f"{code}: {EXPLANATIONS.get(code, DEFAULT_EXPLANATION)}"
            for code in codes
        ]
        return "\n".join(lines)[:MAX_ADVISORY_CHARS]

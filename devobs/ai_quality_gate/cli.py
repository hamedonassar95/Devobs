"""CLI for the advisory, read-only AI quality gate.

Only ``DRY_RUN`` is accepted. The command reads bounded local JSON fixtures,
prints one structured result, and never starts an agent, runs a shell command
from the input, calls a network service, changes Git state or grants approval.
"""

from __future__ import annotations

import argparse
from typing import Any, Sequence

from devobs.integration_control.security import load_document

from .adapter import LocalExplanatoryAdapter
from .engine import AIQualityGate
from .models import (
    BLOCKED,
    INVALID,
    MODE_DRY_RUN,
    PASS,
    UNVERIFIED,
    render_gate_json,
)

EXIT_CODES = {
    PASS: 0,
    BLOCKED: 1,
    UNVERIFIED: 2,
    INVALID: 3,
}


def _load_optional(path: str | None) -> Any:
    if path is None:
        return None
    return load_document(path)


def render_markdown(result: dict[str, Any]) -> str:
    """Return a bounded human-readable view of a validated gate result."""
    lines = [
        "# AI quality gate decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Mode: `{result['mode']}`",
        "- Merge authorized: `false`",
        f"- Human approval: `{result['human_approval']}`",
        "- Offline: `true`",
        f"- Source SHA: `{result['source_sha'] or 'unverified'}`",
        f"- Gate digest: `{result['gate_digest']}`",
        "",
        "## Checks",
        "",
        f"- Passed: {', '.join(result['checks']['passed']) or 'none'}",
        f"- Failed: {', '.join(result['checks']['failed']) or 'none'}",
        f"- Skipped: {', '.join(result['checks']['skipped']) or 'none'}",
        "",
        "## Coordination",
        "",
        f"- Decision: `{result['coordination']['decision']}`",
        f"- Conflicts: {', '.join(result['coordination']['conflicts']) or 'none'}",
        f"- Blocked tasks: {', '.join(result['coordination']['blocked_tasks']) or 'none'}",
        "",
        "## CI failures",
        "",
        f"- Category: `{result['ci_failures']['overall_category']}`",
        f"- Classified findings: {len(result['ci_failures']['findings'])}",
        f"- Repeated signatures: {result['ci_failures']['repeated_count']}",
        "",
        "## Findings",
        "",
    ]
    if result["findings"]:
        for item in result["findings"]:
            lines.append(
                f"- `{item['severity']}` `{item['code']}` ({item['source']})"
            )
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Evidence and audit",
        "",
        f"- Accepted evidence IDs: {len(result['evidence_ids'])}",
        f"- Audit events: {len(result['audit_events'])}",
        f"- Advisory provider: `{result['advisory']['provider']}`",
        "- Influenced deterministic decision: `false`",
        "",
        "## Consequential actions",
        "",
    ])
    for item in result["consequential_actions"]:
        lines.append(f"- {item['action']}: `{item['status']}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one bounded offline snapshot with the advisory AI quality "
            "gate. DRY_RUN is the only supported mode."
        ),
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to a local UTF-8 integration-control snapshot",
    )
    parser.add_argument("--ci-run-json", help="Optional offline CI run metadata")
    parser.add_argument("--ci-jobs-json", help="Optional offline CI jobs payload")
    parser.add_argument(
        "--approval-evidence",
        help="Optional local JSON list of explicit human-approval evidence records",
    )
    parser.add_argument("--retry-policy", help="Optional local JSON retry policy")
    parser.add_argument(
        "--format", choices=("json", "markdown"), default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--mode", choices=(MODE_DRY_RUN,), default=MODE_DRY_RUN,
        help="Only DRY_RUN is supported; no execution mode exists",
    )
    args = parser.parse_args(argv)

    try:
        snapshot = load_document(args.input)
        ci_run = _load_optional(args.ci_run_json)
        ci_jobs = _load_optional(args.ci_jobs_json)
        approval_evidence = _load_optional(args.approval_evidence)
        retry_policy = _load_optional(args.retry_policy)
    except Exception:  # noqa: BLE001 - unreadable inputs fail closed.
        result = AIQualityGate().evaluate(None)
    else:
        result = AIQualityGate(
            advisory_provider=LocalExplanatoryAdapter(),
        ).evaluate(
            snapshot,
            ci_run=ci_run,
            ci_jobs=ci_jobs,
            approval_evidence=approval_evidence,
            retry_policy=retry_policy,
        )

    print(
        render_gate_json(result) if args.format == "json" else render_markdown(result)
    )
    return EXIT_CODES.get(str(result["decision"]), 3)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["EXIT_CODES", "main", "render_markdown"]

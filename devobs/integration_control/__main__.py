"""CLI for one offline integration-control snapshot."""

from __future__ import annotations

import argparse
from typing import Any, Sequence

from .engine import IntegrationControlPlane
from .hardening import harden_report
from .models import BLOCKED, INVALID, PROCEED, UNVERIFIED
from .report import render_report_json, render_report_markdown
from .security import load_document

EXIT_CODES = {
    PROCEED: 0,
    BLOCKED: 1,
    UNVERIFIED: 2,
    INVALID: 3,
}
UNREADABLE_OPTION = {"__unreadable__": True}


def _load_optional(path: str | None) -> Any:
    if path is None:
        return None
    try:
        return load_document(path)
    except Exception:  # noqa: BLE001 - optional evidence failures fail closed.
        return dict(UNREADABLE_OPTION)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one bounded offline integration snapshot. No network is used.",
    )
    parser.add_argument("--input", required=True, help="Path to a local UTF-8 JSON snapshot")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--approval-evidence",
        help="Optional local JSON list of explicit human-approval evidence records",
    )
    parser.add_argument(
        "--retry-policy",
        help="Optional local JSON retry bound and prior-attempt digest list",
    )
    args = parser.parse_args(argv)
    try:
        document = load_document(args.input)
    except Exception:  # noqa: BLE001 - malformed input must fail closed.
        document = None

    approval_evidence = _load_optional(args.approval_evidence)
    retry_policy = _load_optional(args.retry_policy)
    report = harden_report(
        IntegrationControlPlane().evaluate(document),
        document,
        approval_evidence=approval_evidence,
        retry_policy=retry_policy,
    )
    text = render_report_json(report) if args.format == "json" else render_report_markdown(report)
    print(text)
    return EXIT_CODES.get(str(report["decision"]), 3)


if __name__ == "__main__":
    raise SystemExit(main())

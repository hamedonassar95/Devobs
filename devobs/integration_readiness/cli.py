"""Read-only command-line entry point for offline integration readiness checks."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .evaluator import evaluate_catalog
from .models import BLOCKED, NEEDS_APPROVAL, POLICY_VIOLATION, ReadinessError
from .reporting import render_diagnostic, render_json_report, render_markdown_report
from .security import redact_text

_BLOCKING_DECISIONS = frozenset({POLICY_VIOLATION, BLOCKED, NEEDS_APPROVAL})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m devobs.integration_readiness.cli",
        description="Evaluate a local versioned integration readiness catalog without network access.",
    )
    parser.add_argument("--input", default=None, help="Path to a local JSON catalog fixture.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--allow-findings",
        action="store_true",
        help="Return exit code 0 even when the report has blocking findings.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = evaluate_catalog(_load(args.input))
    except ReadinessError as exc:
        sys.stderr.write(render_diagnostic(exc.code, str(exc)))
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI must never leak tracebacks
        sys.stderr.write(render_diagnostic("internal_error", exc.__class__.__name__))
        return 2
    renderer = render_markdown_report if args.format == "markdown" else render_json_report
    sys.stdout.write(renderer(report))
    if args.allow_findings:
        return 0
    return 1 if report.get("decision") in _BLOCKING_DECISIONS else 0


def _load(path: str | None) -> dict[str, object]:
    from .catalog import load_catalog

    return dict(load_catalog(path))


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

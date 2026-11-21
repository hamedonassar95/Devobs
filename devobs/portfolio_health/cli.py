"""CLI for offline integration portfolio health dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import evaluate_portfolio_health
from .report import render_json_report, render_markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate integration portfolio health (offline, read-only)")
    parser.add_argument("--input", required=True, help="Path to JSON snapshot")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--max-age-seconds", type=int, default=86400)
    args = parser.parse_args(argv)

    try:
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        report = {
            "schema_version": "portfolio-health/1.0",
            "readiness": "UNKNOWN",
            "advisory_only": True,
            "human_review_required": True,
            "findings": [{"code": "INVALID_INPUT", "severity": "CRITICAL", "category": "input", "message": f"Invalid JSON: {type(exc).__name__}", "remediation": "Provide valid JSON snapshot."}],
        }
        out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out, end="")
        return 2

    report = evaluate_portfolio_health(raw, max_age_seconds=args.max_age_seconds)
    out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out, end="")
    return 0 if report.get("readiness") == "READY_FOR_HUMAN_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
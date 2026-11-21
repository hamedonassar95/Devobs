"""CLI for production readiness intelligence (offline)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .readiness_engine import evaluate_production_readiness
from .reporting import render_json_report, render_markdown_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Offline production readiness intelligence report")
    p.add_argument("--input", required=True)
    p.add_argument("--format", choices=["json", "markdown"], default="json")
    p.add_argument("--output")
    args = p.parse_args(argv)
    try:
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        report = {"schema_version": "production-readiness/1.0", "status": "UNKNOWN", "findings": [{"code": "INVALID_INPUT", "severity": "CRITICAL", "category": "input", "message": f"Invalid JSON: {type(exc).__name__}"}], "advisory_only": True, "human_approval_required": True}
        out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
        if args.output: Path(args.output).write_text(out, encoding="utf-8")
        else: print(out, end="")
        return 2
    report = evaluate_production_readiness(raw)
    out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
    if args.output: Path(args.output).write_text(out, encoding="utf-8")
    else: print(out, end="")
    return 0 if report.get("status") == "READY_FOR_HUMAN_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
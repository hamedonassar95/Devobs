"""CLI for offline integration verification hub."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import evaluate_hub
from .reporting import render_json_report, render_markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic integration verification hub")
    parser.add_argument("--input", required=True, help="JSON input file")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--repo-root", default=".", help="Repository root for discovery")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        report = {
            "schema_version": 1,
            "decision": "INSUFFICIENT_EVIDENCE",
            "human_review_required": True,
            "findings": [{"code": "MALFORMED_INPUT", "severity": "HIGH", "category": "input", "message": f"Invalid JSON: {exc.__class__.__name__}", "inferred": False}],
        }
        out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out, end="")
        return 2

    report = evaluate_hub(payload, repo_root=args.repo_root)
    out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out, end="")
    decision = report.get("decision")
    if decision == "READY_FOR_HUMAN_REVIEW":
        return 0
    if decision == "BLOCKED":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

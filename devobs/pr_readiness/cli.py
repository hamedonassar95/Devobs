"""CLI for deterministic PR readiness evaluation.

Offline, read-only. Never calls external APIs, never merges.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policy import evaluate_pr_readiness
from .report import render_json_report, render_markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate PR readiness evidence (offline, deterministic)")
    parser.add_argument("--input", required=True, help="Path to JSON evidence file")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Optional output file")
    args = parser.parse_args(argv)

    try:
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        report = {
            "schema_version": 1,
            "engine": "devobs.pr_readiness",
            "decision": "INSUFFICIENT_EVIDENCE",
            "readiness_decision": {"decision": "INSUFFICIENT_EVIDENCE", "reasons": ["invalid_input"], "human_review_required": True},
            "human_review_required": True,
            "recommended_next_action": "Provide valid JSON evidence file.",
            "findings": [{"code": "INVALID_INPUT", "severity": "error", "category": "evidence", "message": f"Invalid input: {exc.__class__.__name__}", "evidence": {}}],
        }
        out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out, end="")
        return 2

    report = evaluate_pr_readiness(raw)
    out = render_json_report(report) if args.format == "json" else render_markdown_report(report)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out, end="")
    decision = report.get("readiness_decision", {}).get("decision")
    if decision == "READY_FOR_HUMAN_REVIEW":
        return 0
    if decision == "BLOCKED":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

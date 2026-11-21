#!/usr/bin/env python3
"""CLI for deterministic integration readiness reporting.

Read-only. Never merges, deploys, or executes evidence content.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from devobs.integration_control.reporting import build_readiness_report, render_json, render_markdown  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate integration readiness from JSON evidence")
    parser.add_argument("--input", required=True, help="Path to JSON evidence file")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Optional output file path")
    args = parser.parse_args(argv)

    in_path = Path(args.input)
    try:
        raw = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        report = {
            "schema_version": 1,
            "report_type": "integration_readiness",
            "readiness": "UNKNOWN",
            "recommended_next_action": "Provide valid JSON evidence input.",
            "verification_results": [{"name": "input", "state": "BLOCKED", "message": f"Invalid input: {exc.__class__.__name__}", "details": {}}],
            "human_approval_requirements": {"required": True, "state": "BLOCKED_OR_UNKNOWN"},
        }
        out = render_json(report) if args.format == "json" else render_markdown(report)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out, end="")
        return 2

    report = build_readiness_report(raw)
    out = render_json(report) if args.format == "json" else render_markdown(report)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out, end="")
    decision = report.get("readiness")
    return 0 if decision == "READY_FOR_HUMAN_REVIEW" else 1 if decision == "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

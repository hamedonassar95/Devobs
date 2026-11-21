"""CLI for one offline integration-control snapshot."""

from __future__ import annotations

import argparse
from typing import Sequence

from .engine import IntegrationControlPlane
from .models import BLOCKED, INVALID, PROCEED, UNVERIFIED
from .report import render_report_json, render_report_markdown
from .security import load_document

EXIT_CODES = {
    PROCEED: 0,
    BLOCKED: 1,
    UNVERIFIED: 2,
    INVALID: 3,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one bounded offline integration snapshot. No network is used.",
    )
    parser.add_argument("--input", required=True, help="Path to a local UTF-8 JSON snapshot")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        document = load_document(args.input)
    except Exception:  # noqa: BLE001 - malformed input must fail closed.
        document = None
    report = IntegrationControlPlane().evaluate(document)
    text = render_report_json(report) if args.format == "json" else render_report_markdown(report)
    print(text)
    return EXIT_CODES.get(str(report["decision"]), 3)


if __name__ == "__main__":
    raise SystemExit(main())

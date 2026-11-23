"""Read-only CLI for the offline provider evaluation harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import EvaluationEngine, build_default_configs
from .gate import evaluate_gate
from .models import FixtureSet
from .pricing import PricingCatalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline-first AI provider evaluation (no network, no credentials).",
    )
    parser.add_argument("--fixtures", required=True, type=Path,
                        help="Path to the provider case fixture JSON.")
    parser.add_argument("--pricing", required=True, type=Path,
                        help="Path to the configurable pricing JSON.")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Evaluate the deterministic quality gate; exit 0=PASS, 1=BLOCKED, 2=INVALID.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        fixture = FixtureSet.from_mapping(json.loads(
            args.fixtures.read_text(encoding="utf-8")))
        catalog = PricingCatalog.from_mapping(json.loads(
            args.pricing.read_text(encoding="utf-8")))
        report = EvaluationEngine(catalog).evaluate(fixture, build_default_configs())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Fail closed with a fixed diagnostic; never echo file content or secrets.
        print(json.dumps({"status": "INVALID", "reason": str(exc)[:120]}))
        return 2
    if args.gate:
        result = evaluate_gate(report)
        print(json.dumps(result.to_dict(), sort_keys=True))
        return result.exit_code
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Summarize downloaded GitHub Copilot usage NDJSON without network or writes."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class MetricsInputError(ValueError):
    """A safe diagnostic for malformed or unsupported metrics input."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MetricsInputError("duplicate_json_key")
        result[key] = value
    return result


def _count(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise MetricsInputError(f"invalid_count:{field}")
    return value


def summarize_metrics(paths: list[Path]) -> dict[str, Any]:
    """Aggregate the documented BYOK fields, failing closed on bad records."""
    if not paths:
        raise MetricsInputError("no_input_files")

    report: dict[str, Any] = {
        "records": 0,
        "records_with_byok_metrics": 0,
        "records_with_unavailable_byok_metrics": 0,
        "days": set(),
        "requests": 0,
        "prompt_tokens": 0,
        "output_tokens": 0,
        "byok_kinds": defaultdict(
            lambda: {"requests": 0, "prompt_tokens": 0, "output_tokens": 0}
        ),
        "surfaces": defaultdict(
            lambda: {"requests": 0, "prompt_tokens": 0, "output_tokens": 0}
        ),
    }

    for path in paths:
        if not path.is_file():
            raise MetricsInputError("input_file_not_found")
        try:
            source = path.open("r", encoding="utf-8")
        except (OSError, UnicodeError):
            raise MetricsInputError("input_file_unreadable") from None

        try:
            with source:
                for line_number, line in enumerate(source, 1):
                    if len(line) > 1_000_000:
                        raise MetricsInputError(f"record_too_large:{path.name}:{line_number}")
                    if not line.strip():
                        raise MetricsInputError(f"blank_line:{path.name}:{line_number}")
                    try:
                        row = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
                    except (json.JSONDecodeError, MetricsInputError):
                        raise MetricsInputError(f"invalid_json:{path.name}:{line_number}") from None
                    if not isinstance(row, dict):
                        raise MetricsInputError(f"invalid_record:{path.name}:{line_number}")

                    report["records"] += 1
                    if report["records"] > 1_000_000:
                        raise MetricsInputError("too_many_records")
                    day = row.get("day")
                    if day is not None:
                        if not isinstance(day, str) or not ISO_DAY.fullmatch(day):
                            raise MetricsInputError(f"invalid_day:{path.name}:{line_number}")
                        try:
                            date.fromisoformat(day)
                        except ValueError:
                            raise MetricsInputError(f"invalid_day:{path.name}:{line_number}") from None
                        report["days"].add(day)

                    byok = row.get("totals_by_local_byok")
                    if byok is None:
                        report["records_with_unavailable_byok_metrics"] += 1
                        continue
                    if not isinstance(byok, list):
                        raise MetricsInputError(f"invalid_byok_metrics:{path.name}:{line_number}")

                    report["records_with_byok_metrics"] += 1
                    for entry in byok:
                        if not isinstance(entry, dict):
                            raise MetricsInputError(f"invalid_byok_entry:{path.name}:{line_number}")
                        kind = entry.get("byok_kind")
                        surface = entry.get("surface")
                        if not isinstance(kind, str) or not SAFE_LABEL.fullmatch(kind):
                            raise MetricsInputError(f"invalid_byok_kind:{path.name}:{line_number}")
                        if not isinstance(surface, str) or not SAFE_LABEL.fullmatch(surface):
                            raise MetricsInputError(f"invalid_surface:{path.name}:{line_number}")

                        requests = _count(entry.get("request_count"), "request_count")
                        token_usage = entry.get("token_usage")
                        if not isinstance(token_usage, dict):
                            raise MetricsInputError(f"invalid_token_usage:{path.name}:{line_number}")
                        prompt_tokens = _count(
                            token_usage.get("prompt_tokens_sum"), "prompt_tokens_sum"
                        )
                        output_tokens = _count(
                            token_usage.get("output_tokens_sum"), "output_tokens_sum"
                        )

                        report["requests"] += requests
                        report["prompt_tokens"] += prompt_tokens
                        report["output_tokens"] += output_tokens
                        for dimension, value in (("byok_kinds", kind), ("surfaces", surface)):
                            if value not in report[dimension] and len(report[dimension]) >= 256:
                                raise MetricsInputError("too_many_metric_categories")
                            totals = report[dimension][value]
                            totals["requests"] += requests
                            totals["prompt_tokens"] += prompt_tokens
                            totals["output_tokens"] += output_tokens
        except (OSError, UnicodeError):
            raise MetricsInputError("input_file_unreadable") from None

    if report["records"] == 0:
        raise MetricsInputError("no_records")
    if report["records_with_byok_metrics"] == 0:
        raise MetricsInputError("no_usable_byok_metrics")

    report["days"] = sorted(report["days"])
    for key in ("byok_kinds", "surfaces"):
        report[key] = dict(sorted(report[key].items()))
    return report


def render_report(report: dict[str, Any]) -> str:
    days = report["days"]
    day_range = f"{days[0]} to {days[-1]}" if days else "not included in input"
    known = report["records_with_byok_metrics"]
    records = report["records"]
    unknown = report["records_with_unavailable_byok_metrics"]
    coverage = f"{known}/{records} records"
    if unknown:
        coverage += f"; {unknown} unavailable"

    lines = [
        "GitHub Copilot usage metrics (read-only)",
        f"Report days: {day_range}",
        f"Records with BYOK metrics: {coverage}",
        f"BYOK requests: {report['requests']}",
        f"Prompt tokens: {report['prompt_tokens']}",
        f"Output tokens: {report['output_tokens']}",
        "Breakdown by BYOK kind:",
    ]
    for kind, totals in report["byok_kinds"].items():
        lines.append(
            f"  {kind}: {totals['requests']} requests, "
            f"{totals['prompt_tokens']} prompt tokens, "
            f"{totals['output_tokens']} output tokens"
        )
    lines.append("Breakdown by client surface:")
    for surface, totals in report["surfaces"].items():
        lines.append(
            f"  {surface}: {totals['requests']} requests, "
            f"{totals['prompt_tokens']} prompt tokens, "
            f"{totals['output_tokens']} output tokens"
        )
    lines.extend(
        [
            "USD cost: not available from these usage metrics; the model provider may bill separately.",
            "Budget gate: unchanged. This report does not approve spending or enable AI.",
            "Coverage note: client telemetry can be unavailable or undercount usage.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize downloaded Copilot usage NDJSON locally; no API calls or settings writes."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        metavar="NDJSON",
        help="NDJSON report file; repeat for disjoint shards from one report",
    )
    args = parser.parse_args(argv)
    try:
        report = summarize_metrics([Path(item) for item in args.input])
    except MetricsInputError as error:
        print(f"Copilot metrics report failed: {error}", file=sys.stderr)
        return 1
    print(render_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

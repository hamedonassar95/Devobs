#!/usr/bin/env python3
"""Create a bounded horizontal-capacity recommendation from workload metrics.

The tool reads metrics as data and never contacts or changes a cloud provider.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty RFC 3339 timestamp.")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid RFC 3339 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset.")
    return parsed.astimezone(timezone.utc)


def integer(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer of at least {minimum}.")
    return value


def percent_samples(value: Any, field: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty array of percentages.")
    result = []
    for sample in value:
        if isinstance(sample, bool) or not isinstance(sample, (int, float)):
            raise ValueError(f"{field} must contain only numbers from 0 to 100.")
        try:
            sample = float(sample)
        except OverflowError as exc:
            raise ValueError(f"{field} must contain only finite numbers from 0 to 100.") from exc
        if not math.isfinite(sample) or not 0 <= sample <= 100:
            raise ValueError(f"{field} must contain only finite numbers from 0 to 100.")
        result.append(sample)
    return result


def percentile_95(samples: list[float]) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 2)


def read_metrics(metrics_path: Path, repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve(strict=True)
    path = metrics_path if metrics_path.is_absolute() else root / metrics_path
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("metrics_file must resolve to a file inside the checked-out repository.") from exc
    if not resolved.is_file():
        raise ValueError("metrics_file must identify a regular JSON file.")
    if resolved.stat().st_size > 1_048_576:
        raise ValueError("metrics_file must be at most 1 MiB.")
    try:
        with resolved.open(encoding="utf-8") as source:
            document = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read metrics JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Metrics JSON must be an object.")
    return document


def hold(current: int, reason: str, cpu_p95: float | None = None,
         memory_p95: float | None = None, sample_count: int = 0) -> dict[str, Any]:
    return {
        "decision": "hold",
        "recommended_replicas": current,
        "reason": reason,
        "cpu_p95_percent": cpu_p95,
        "memory_p95_percent": memory_p95,
        "sample_count": sample_count,
        "apply": False,
    }


def recommend(
    metrics: dict[str, Any],
    *,
    minimum_replicas: int,
    maximum_replicas: int,
    target_cpu_percent: float,
    target_memory_percent: float,
    downscale_fraction: float,
    scale_up_threshold: float,
    max_scale_up_percent: float,
    minimum_samples: int,
    minimum_downscale_window_minutes: int,
    cooldown_minutes: int,
    maximum_age_minutes: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    schema_version = metrics.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
        raise ValueError("schema_version must be 1.")
    current = integer(metrics.get("current_replicas"), "current_replicas", 1)
    observed_at = parse_timestamp(metrics.get("observed_at"), "observed_at")
    window_minutes = integer(metrics.get("window_minutes"), "window_minutes", 1)
    cpu_samples = percent_samples(metrics.get("cpu_utilization_percent"), "cpu_utilization_percent")
    memory_samples = percent_samples(metrics.get("memory_utilization_percent"), "memory_utilization_percent")
    if len(cpu_samples) != len(memory_samples):
        raise ValueError("CPU and memory metric arrays must contain paired observations of equal length.")
    sample_count = len(cpu_samples)
    last_scaled_raw = metrics.get("last_scaled_at")
    last_scaled_at = parse_timestamp(last_scaled_raw, "last_scaled_at") if last_scaled_raw is not None else None
    cpu_p95 = percentile_95(cpu_samples)
    memory_p95 = percentile_95(memory_samples)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    result = {
        "decision": "hold",
        "recommended_replicas": current,
        "reason": "No scaling change is justified by the current policy.",
        "cpu_p95_percent": cpu_p95,
        "memory_p95_percent": memory_p95,
        "sample_count": sample_count,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "window_minutes": window_minutes,
        "apply": False,
    }

    if current < minimum_replicas or current > maximum_replicas:
        return hold(current, "Current replicas are outside the configured bounds; reconcile policy before scaling.",
                    cpu_p95, memory_p95, sample_count)
    age_minutes = (now - observed_at).total_seconds() / 60
    if age_minutes < -1:
        return hold(current, "Metrics timestamp is in the future; no scaling recommendation was made.",
                    cpu_p95, memory_p95, sample_count)
    if age_minutes > maximum_age_minutes:
        return hold(current, f"Metrics are stale ({age_minutes:.1f} minutes old); no scaling recommendation was made.",
                    cpu_p95, memory_p95, sample_count)
    if sample_count < minimum_samples:
        return hold(current, f"Only {sample_count} paired observations are available; {minimum_samples} are required.",
                    cpu_p95, memory_p95, sample_count)

    cpu_ratio = cpu_p95 / target_cpu_percent
    memory_ratio = memory_p95 / target_memory_percent
    load_ratio = max(cpu_ratio, memory_ratio)
    if load_ratio > scale_up_threshold:
        if current == maximum_replicas:
            return hold(current, "The workload is above target and already at max_replicas; review the configured ceiling.",
                        cpu_p95, memory_p95, sample_count)
        calculated = math.ceil(current * load_ratio)
        step_limit = max(1, math.floor(current * max_scale_up_percent / 100))
        recommended = min(maximum_replicas, current + step_limit, max(current + 1, calculated))
        result.update({
            "decision": "scale_up",
            "recommended_replicas": recommended,
            "reason": (f"p95 utilization is {load_ratio:.2f}× the tighter target; increase by a bounded step "
                       f"from {current} to {recommended} replicas."),
        })
        return result

    cpu_low = cpu_p95 <= target_cpu_percent * downscale_fraction
    memory_low = memory_p95 <= target_memory_percent * downscale_fraction
    if cpu_low and memory_low and current > minimum_replicas:
        if window_minutes < minimum_downscale_window_minutes:
            return hold(current, (f"The observation window is {window_minutes} minutes; "
                                  f"at least {minimum_downscale_window_minutes} are required to scale down."),
                        cpu_p95, memory_p95, sample_count)
        if last_scaled_at is None:
            return hold(current, "Low load is sustained, but last_scaled_at is missing; scale down is blocked.",
                        cpu_p95, memory_p95, sample_count)
        minutes_since_scale = (now - last_scaled_at).total_seconds() / 60
        if minutes_since_scale < 0:
            return hold(current, "last_scaled_at is in the future; scale down is blocked.",
                        cpu_p95, memory_p95, sample_count)
        if minutes_since_scale < cooldown_minutes:
            return hold(current, f"Scale-down cooldown is active ({minutes_since_scale:.1f}/{cooldown_minutes} minutes).",
                        cpu_p95, memory_p95, sample_count)
        recommended = max(minimum_replicas, current - 1)
        result.update({
            "decision": "scale_down",
            "recommended_replicas": recommended,
            "reason": (f"Both p95 metrics are below {downscale_fraction:.0%} of target and cooldown elapsed; "
                       f"reduce by one replica from {current} to {recommended}."),
        })
        return result

    if current == minimum_replicas and cpu_low and memory_low:
        result["reason"] = "Both p95 metrics are low, but the workload is already at min_replicas."
    return result


def positive_number(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0")
    return number


def fraction(value: str) -> float:
    number = positive_number(value)
    if number > 1:
        raise argparse.ArgumentTypeError("must be greater than 0 and at most 1")
    return number


def nonnegative_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-file", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--min-replicas", type=int, default=1)
    parser.add_argument("--max-replicas", type=int, required=True)
    parser.add_argument("--target-cpu-percent", type=positive_number, default=65.0)
    parser.add_argument("--target-memory-percent", type=positive_number, default=75.0)
    parser.add_argument("--downscale-fraction", type=fraction, default=0.5)
    parser.add_argument("--scale-up-threshold", type=positive_number, default=1.05)
    parser.add_argument("--max-scale-up-percent", type=positive_number, default=50.0)
    parser.add_argument("--minimum-samples", type=int, default=6)
    parser.add_argument("--minimum-downscale-window-minutes", type=nonnegative_integer, default=30)
    parser.add_argument("--cooldown-minutes", type=nonnegative_integer, default=30)
    parser.add_argument("--maximum-age-minutes", type=nonnegative_integer, default=20)
    return parser


def write_outputs(result: dict[str, Any]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"decision={result['decision']}\n")
            output.write(f"recommended_replicas={result['recommended_replicas']}\n")
            output.write(f"reason={result['reason']}\n")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Capacity recommendation\n\n")
            summary.write(f"- Decision: **{result['decision']}**\n")
            summary.write(f"- Recommended replicas: **{result['recommended_replicas']}**\n")
            summary.write(f"- CPU p95: {result.get('cpu_p95_percent')}%\n")
            summary.write(f"- Memory p95: {result.get('memory_p95_percent')}%\n")
            summary.write(f"- Reason: {result['reason']}\n")
            summary.write("- This action only reports a recommendation; it does not change a provider or deploy a workload.\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.min_replicas < 1 or args.max_replicas < args.min_replicas:
        parser.error("replica bounds must satisfy 1 <= min_replicas <= max_replicas")
    if args.minimum_samples < 1:
        parser.error("minimum_samples must be at least 1")
    if args.max_scale_up_percent > 100:
        parser.error("max_scale_up_percent must be at most 100")
    if args.target_cpu_percent > 100 or args.target_memory_percent > 100:
        parser.error("target utilization percentages must be at most 100")

    try:
        metrics = read_metrics(args.metrics_file, args.repository_root)
        result = recommend(
            metrics,
            minimum_replicas=args.min_replicas,
            maximum_replicas=args.max_replicas,
            target_cpu_percent=args.target_cpu_percent,
            target_memory_percent=args.target_memory_percent,
            downscale_fraction=args.downscale_fraction,
            scale_up_threshold=args.scale_up_threshold,
            max_scale_up_percent=args.max_scale_up_percent,
            minimum_samples=args.minimum_samples,
            minimum_downscale_window_minutes=args.minimum_downscale_window_minutes,
            cooldown_minutes=args.cooldown_minutes,
            maximum_age_minutes=args.maximum_age_minutes,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    write_outputs(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

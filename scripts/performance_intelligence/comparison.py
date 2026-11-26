"""Offline, fail-closed comparison of two compatible performance reports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import tempfile
from typing import Any

from . import pyperformance_reporting, reporting, resource_reporting
from .benchmark_engine import BENCHMARK_NAMES
from .pyperformance_contract import OUTPUT_NAMES

SCHEMA_VERSION = 1
MIN_STATISTICAL_SAMPLES = 20
ALPHA = 0.05
MAX_REPORT_BYTES = 5 * 1024 * 1024
COMPARISON_KEYS = frozenset({
    "schema_version", "comparison_kind", "metric", "baseline", "candidate", "platform",
    "architecture", "measurement_mode", "same_host_confirmed", "alpha", "benchmarks",
})
ROW_KEYS = frozenset({
    "benchmark_id", "benchmark_name", "baseline_mean", "candidate_mean", "delta_percent",
    "confidence_interval_low_percent", "confidence_interval_high_percent", "baseline_sample_count",
    "candidate_sample_count", "welch_t", "p_value", "adjusted_p_value", "status",
})
CSV_FIELDS = (
    "comparison_kind", "metric", "baseline_source_sha", "candidate_source_sha",
    "baseline_python_version", "candidate_python_version", "platform", "architecture",
    "benchmark_id", "benchmark_name", "baseline_mean", "candidate_mean", "delta_percent",
    "confidence_interval_low_percent", "confidence_interval_high_percent", "baseline_sample_count",
    "candidate_sample_count", "welch_t", "p_value", "adjusted_p_value", "status",
)


class ComparisonValidationError(ValueError):
    """Fixed error for incompatible or malformed comparison reports."""


class ComparisonWriteError(OSError):
    """Fixed error for unsafe or conflicting comparison destinations."""


def _normalize_summary(summary: object) -> dict[str, Any]:
    if type(summary) is not dict:
        raise ComparisonValidationError("invalid_report")
    try:
        if summary.get("metric") == resource_reporting.METRIC:
            resource_reporting.validate_summary(summary)
            metric = "peak_private_bytes"
            mean_key = "mean_bytes"
            deviation_key = "standard_deviation_bytes"
        elif summary.get("suite_name") == "pyperformance":
            pyperformance_reporting.validate_summary(summary)
            metric = "execution_time_seconds"
            mean_key = "mean_seconds"
            deviation_key = "standard_deviation_seconds"
        else:
            reporting.validate_summary(summary)
            metric = "execution_time_seconds"
            mean_key = "mean_seconds"
            deviation_key = "standard_deviation_seconds"
    except (reporting.ReportValidationError, pyperformance_reporting.ReportValidationError,
            resource_reporting.ResourceReportError, TypeError, KeyError):
        raise ComparisonValidationError("invalid_report") from None
    rows = {}
    for row in summary["benchmarks"]:
        mean = row[mean_key]
        deviation = row[deviation_key]
        count = row["sample_count"]
        if (isinstance(mean, bool) or not isinstance(mean, (int, float))
                or not math.isfinite(mean) or mean <= 0
                or isinstance(deviation, bool) or not isinstance(deviation, (int, float))
                or not math.isfinite(deviation) or deviation < 0
                or type(count) is not int or count < MIN_STATISTICAL_SAMPLES):
            raise ComparisonValidationError("insufficient_or_invalid_samples")
        rows[row["benchmark_id"]] = {
            "benchmark_id": row["benchmark_id"], "benchmark_name": row["benchmark_name"],
            "mean": float(mean), "standard_deviation": float(deviation), "sample_count": count,
        }
    if not rows:
        raise ComparisonValidationError("empty_suite")
    suite_name = summary.get("suite_name", "devobs")
    suite_version = summary.get("suite_version", "1")
    suite_source_sha = summary.get("suite_source_sha", summary["source_sha"])
    return {
        "source_sha": summary["source_sha"], "python_version": summary["python_version"],
        "platform": summary["platform"], "architecture": summary["architecture"],
        "measurement_mode": summary["measurement_mode"], "suite_name": suite_name,
        "suite_version": suite_version, "suite_source_sha": suite_source_sha,
        "metric": metric, "rows": rows,
    }


def _beta_fraction(a: float, b: float, x: float) -> float:
    """Continued fraction used by the regularized incomplete beta function."""
    max_iterations = 200
    epsilon = 3e-14
    floor = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < floor:
        d = floor
    d = 1.0 / d
    h = d
    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < floor:
            d = floor
        c = 1.0 + aa / c
        if abs(c) < floor:
            c = floor
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < floor:
            d = floor
        c = 1.0 + aa / c
        if abs(c) < floor:
            c = floor
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            return h
    raise ComparisonValidationError("statistical_calculation_failed")


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    factor = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                      + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1) / (a + b + 2):
        return factor * _beta_fraction(a, b, x) / a
    return 1.0 - factor * _beta_fraction(b, a, 1.0 - x) / b


def _student_cdf(value: float, degrees_freedom: float) -> float:
    if value == 0:
        return 0.5
    x = degrees_freedom / (degrees_freedom + value * value)
    tail = 0.5 * _regularized_beta(x, degrees_freedom / 2, 0.5)
    return 1 - tail if value > 0 else tail


def _student_critical_975(degrees_freedom: float) -> float:
    low, high = 0.0, 1.0
    while _student_cdf(high, degrees_freedom) < 0.975 and high < 256:
        high *= 2
    for _ in range(80):
        mid = (low + high) / 2
        if _student_cdf(mid, degrees_freedom) < 0.975:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _welch(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float | None]:
    mean_a = baseline["mean"]
    mean_b = candidate["mean"]
    count_a = baseline["sample_count"]
    count_b = candidate["sample_count"]
    var_a = baseline["standard_deviation"] ** 2 / count_a
    var_b = candidate["standard_deviation"] ** 2 / count_b
    standard_error = math.sqrt(var_a + var_b)
    difference = mean_b - mean_a
    if standard_error == 0:
        statistic = None
        p_value = 1.0 if difference == 0 else 0.0
        margin = 0.0
    else:
        denominator = (var_a * var_a / (count_a - 1)) + (var_b * var_b / (count_b - 1))
        if denominator <= 0:
            raise ComparisonValidationError("statistical_calculation_failed")
        degrees_freedom = (var_a + var_b) ** 2 / denominator
        statistic = difference / standard_error
        p_value = min(1.0, max(0.0, 2 * (1 - _student_cdf(abs(statistic), degrees_freedom))))
        margin = _student_critical_975(degrees_freedom) * standard_error
    scale = 100.0 / mean_a
    return {
        "welch_t": statistic,
        "p_value": p_value,
        "delta_percent": difference * scale,
        "confidence_interval_low_percent": (difference - margin) * scale,
        "confidence_interval_high_percent": (difference + margin) * scale,
    }


def _holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda key: p_values[key])
    adjusted: dict[str, float] = {}
    previous = 0.0
    total = len(ordered)
    for rank, key in enumerate(ordered):
        value = min(1.0, (total - rank) * p_values[key])
        previous = max(previous, value)
        adjusted[key] = previous
    return adjusted


def compare_summaries(baseline_summary: object, candidate_summary: object, *,
                      same_host_confirmed: bool = False,
                      allow_python_version_change: bool = False) -> dict[str, Any]:
    if same_host_confirmed is not True:
        raise ComparisonValidationError("same_host_confirmation_required")
    if type(allow_python_version_change) is not bool:
        raise ComparisonValidationError("invalid_comparison_options")
    baseline = _normalize_summary(baseline_summary)
    candidate = _normalize_summary(candidate_summary)
    for key in ("metric", "suite_name", "suite_version", "platform", "architecture", "measurement_mode"):
        if baseline[key] != candidate[key]:
            raise ComparisonValidationError("incompatible_reports")
    if (baseline["suite_name"] == "pyperformance"
            and baseline["suite_source_sha"] != candidate["suite_source_sha"]):
        raise ComparisonValidationError("incompatible_suite_revision")
    if baseline["python_version"] != candidate["python_version"] and not allow_python_version_change:
        raise ComparisonValidationError("python_version_change_requires_opt_in")
    if baseline["measurement_mode"] != "statistical":
        raise ComparisonValidationError("statistical_reports_required")
    if set(baseline["rows"]) != set(candidate["rows"]):
        raise ComparisonValidationError("benchmark_set_mismatch")

    raw_rows: dict[str, dict[str, Any]] = {}
    p_values = {}
    for benchmark_id in sorted(baseline["rows"]):
        base_row = baseline["rows"][benchmark_id]
        candidate_row = candidate["rows"][benchmark_id]
        if base_row["benchmark_name"] != candidate_row["benchmark_name"]:
            raise ComparisonValidationError("benchmark_identity_mismatch")
        stats = _welch(base_row, candidate_row)
        row = {
            "benchmark_id": benchmark_id,
            "benchmark_name": base_row["benchmark_name"],
            "baseline_mean": base_row["mean"],
            "candidate_mean": candidate_row["mean"],
            **stats,
            "baseline_sample_count": base_row["sample_count"],
            "candidate_sample_count": candidate_row["sample_count"],
            "adjusted_p_value": 1.0,
            "status": "NO_DETECTED_CHANGE",
        }
        raw_rows[benchmark_id] = row
        p_values[benchmark_id] = stats["p_value"]
    adjusted = _holm_adjust(p_values)
    for benchmark_id, row in raw_rows.items():
        row["adjusted_p_value"] = adjusted[benchmark_id]
    if (baseline["python_version"] != candidate["python_version"]
            and baseline["source_sha"] != candidate["source_sha"]):
        comparison_kind = "mixed"
    elif baseline["python_version"] != candidate["python_version"]:
        comparison_kind = "python_version"
    elif baseline["source_sha"] != candidate["source_sha"]:
        comparison_kind = "source_revision"
    else:
        comparison_kind = "repeatability"
    for row in raw_rows.values():
        if row["adjusted_p_value"] < ALPHA:
            if comparison_kind == "repeatability":
                row["status"] = "REPEATABILITY_VARIATION"
            elif row["delta_percent"] > 0:
                row["status"] = "REGRESSION"
            elif row["delta_percent"] < 0:
                row["status"] = "IMPROVEMENT"
    result = {
        "schema_version": SCHEMA_VERSION,
        "comparison_kind": comparison_kind,
        "metric": baseline["metric"],
        "baseline": {key: baseline[key] for key in (
            "source_sha", "python_version", "suite_name", "suite_version", "suite_source_sha",
        )},
        "candidate": {key: candidate[key] for key in (
            "source_sha", "python_version", "suite_name", "suite_version", "suite_source_sha",
        )},
        "platform": baseline["platform"],
        "architecture": baseline["architecture"],
        "measurement_mode": baseline["measurement_mode"],
        "same_host_confirmed": True,
        "alpha": ALPHA,
        "benchmarks": list(raw_rows.values()),
    }
    validate_comparison(result)
    return result


def validate_comparison(result: object) -> None:
    if type(result) is not dict or set(result) != COMPARISON_KEYS:
        raise ComparisonValidationError("invalid_comparison_schema")
    if type(result["schema_version"]) is not int or result["schema_version"] != SCHEMA_VERSION:
        raise ComparisonValidationError("incompatible_comparison_schema")
    if (not isinstance(result["comparison_kind"], str)
            or result["comparison_kind"] not in {"source_revision", "python_version", "repeatability", "mixed"}):
        raise ComparisonValidationError("invalid_comparison_kind")
    if not isinstance(result["metric"], str) or result["metric"] not in {"execution_time_seconds", "peak_private_bytes"}:
        raise ComparisonValidationError("invalid_metric")
    if result["measurement_mode"] != "statistical" or result["same_host_confirmed"] is not True:
        raise ComparisonValidationError("invalid_comparison_evidence")
    if not isinstance(result["platform"], str) or result["platform"] not in {"linux", "macos", "windows"}:
        raise ComparisonValidationError("invalid_platform")
    if not isinstance(result["architecture"], str) or result["architecture"] not in {"x86_64", "aarch64", "x86", "unknown"}:
        raise ComparisonValidationError("invalid_architecture")
    for side in ("baseline", "candidate"):
        item = result[side]
        if (type(item) is not dict or set(item) != {
                "source_sha", "python_version", "suite_name", "suite_version", "suite_source_sha",
        }
                or not isinstance(item["source_sha"], str) or len(item["source_sha"]) != 40
                or any(char not in "0123456789abcdef" for char in item["source_sha"])
                or not isinstance(item["python_version"], str)
                or not re.fullmatch(r"3\.(?:12|15)\.\d{1,3}", item["python_version"])
                or not isinstance(item["suite_name"], str)
                or item["suite_name"] not in {"devobs", "pyperformance"}
                or not isinstance(item["suite_version"], str)
                or not isinstance(item["suite_source_sha"], str)
                or len(item["suite_source_sha"]) != 40
                or any(char not in "0123456789abcdef" for char in item["suite_source_sha"])):
            raise ComparisonValidationError("invalid_comparison_identity")
    if (result["baseline"]["suite_name"] != result["candidate"]["suite_name"]
            or result["baseline"]["suite_version"] != result["candidate"]["suite_version"]
            or result["baseline"]["suite_source_sha"] != result["candidate"]["suite_source_sha"]
            and result["baseline"]["suite_name"] == "pyperformance"):
        raise ComparisonValidationError("incompatible_comparison_identity")
    expected_kind = (
        "mixed" if result["baseline"]["python_version"] != result["candidate"]["python_version"]
        and result["baseline"]["source_sha"] != result["candidate"]["source_sha"]
        else "python_version" if result["baseline"]["python_version"] != result["candidate"]["python_version"]
        else "source_revision" if result["baseline"]["source_sha"] != result["candidate"]["source_sha"]
        else "repeatability"
    )
    if result["comparison_kind"] != expected_kind:
        raise ComparisonValidationError("invalid_comparison_kind")
    if isinstance(result["alpha"], bool) or not isinstance(result["alpha"], (int, float)) or result["alpha"] != ALPHA:
        raise ComparisonValidationError("invalid_alpha")
    rows = result["benchmarks"]
    if type(rows) is not list or not rows:
        raise ComparisonValidationError("empty_suite")
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != ROW_KEYS
                or not isinstance(row["benchmark_id"], str)
                or row["benchmark_id"] in seen or not isinstance(row["benchmark_name"], str)):
            raise ComparisonValidationError("invalid_comparison_row")
        if result["baseline"]["suite_name"] == "devobs":
            identity_valid = BENCHMARK_NAMES.get(row["benchmark_id"]) == row["benchmark_name"]
        else:
            name = row["benchmark_id"][len("pyperformance."):-3] if (
                row["benchmark_id"].startswith("pyperformance.") and row["benchmark_id"].endswith(".v1")
            ) else ""
            identity_valid = name in OUTPUT_NAMES and row["benchmark_name"] == name
        if not identity_valid:
            raise ComparisonValidationError("invalid_comparison_identity")
        seen.add(row["benchmark_id"])
        for key in ("baseline_mean", "candidate_mean", "delta_percent",
                    "confidence_interval_low_percent", "confidence_interval_high_percent",
                    "p_value", "adjusted_p_value"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ComparisonValidationError("invalid_comparison_value")
        if row["welch_t"] is not None and (
            isinstance(row["welch_t"], bool) or not isinstance(row["welch_t"], (int, float))
            or not math.isfinite(row["welch_t"])
        ):
            raise ComparisonValidationError("invalid_comparison_value")
        if not 0 <= row["p_value"] <= 1 or not 0 <= row["adjusted_p_value"] <= 1:
            raise ComparisonValidationError("invalid_p_value")
        if (type(row["baseline_sample_count"]) is not int or row["baseline_sample_count"] < MIN_STATISTICAL_SAMPLES
                or type(row["candidate_sample_count"]) is not int
                or row["candidate_sample_count"] < MIN_STATISTICAL_SAMPLES
                or not isinstance(row["status"], str)
                or row["status"] not in {
                    "REGRESSION", "IMPROVEMENT", "NO_DETECTED_CHANGE", "REPEATABILITY_VARIATION",
                }):
            raise ComparisonValidationError("invalid_comparison_row")
        if row["baseline_mean"] <= 0 or row["candidate_mean"] <= 0:
            raise ComparisonValidationError("invalid_comparison_value")
        if row["confidence_interval_low_percent"] > row["confidence_interval_high_percent"]:
            raise ComparisonValidationError("invalid_confidence_interval")
        expected_status = "NO_DETECTED_CHANGE"
        if row["adjusted_p_value"] < ALPHA:
            if result["comparison_kind"] == "repeatability":
                expected_status = "REPEATABILITY_VARIATION"
            else:
                expected_status = "REGRESSION" if row["delta_percent"] > 0 else (
                    "IMPROVEMENT" if row["delta_percent"] < 0 else "NO_DETECTED_CHANGE"
                )
        if row["status"] != expected_status:
            raise ComparisonValidationError("invalid_comparison_status")


def _load_report(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
        raise ComparisonValidationError("invalid_report_path")
    try:
        data = path.read_bytes()
        parsed = json.loads(data)
        _normalize_summary(parsed)
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ComparisonValidationError("invalid_report") from None
    return parsed, hashlib.sha256(data).hexdigest()


def _load_report_pair(baseline_path: pathlib.Path,
                      candidate_path: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline, baseline_digest = _load_report(baseline_path)
    candidate, candidate_digest = _load_report(candidate_path)
    if baseline_digest == candidate_digest:
        raise ComparisonValidationError("identical_reports")
    return baseline, candidate


def _output_paths(output_dir: pathlib.Path, result: dict[str, Any]) -> tuple[pathlib.Path, pathlib.Path]:
    baseline_version = result["baseline"]["python_version"].replace(".", "")
    candidate_version = result["candidate"]["python_version"].replace(".", "")
    prefix = (f"devobs-compare-{result['baseline']['source_sha'][:8]}-{baseline_version}-"
              f"{result['candidate']['source_sha'][:8]}-{candidate_version}")
    return pathlib.Path(output_dir) / f"{prefix}.json", pathlib.Path(output_dir) / f"{prefix}.csv"


def _csv_bytes(result: dict[str, Any]) -> bytes:
    validate_comparison(result)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in result["benchmarks"]:
        writer.writerow({
            "comparison_kind": result["comparison_kind"], "metric": result["metric"],
            "baseline_source_sha": result["baseline"]["source_sha"],
            "candidate_source_sha": result["candidate"]["source_sha"],
            "baseline_python_version": result["baseline"]["python_version"],
            "candidate_python_version": result["candidate"]["python_version"],
            "platform": result["platform"], "architecture": result["architecture"], **row,
        })
    return stream.getvalue().encode()


def write_comparison_report(result: dict[str, Any], output_dir: pathlib.Path,
                            overwrite: bool = False) -> tuple[pathlib.Path, pathlib.Path]:
    validate_comparison(result)
    output_dir = pathlib.Path(output_dir).resolve()
    root = pathlib.Path(__file__).resolve().parents[2]
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if output_dir == root or root in output_dir.parents:
        raise ComparisonWriteError("repository_output_forbidden")
    if output_dir != temp_root and temp_root not in output_dir.parents:
        raise ComparisonWriteError("temporary_output_required")
    paths = _output_paths(output_dir, result)
    try:
        reporting._atomic_write(
            ((paths[0], (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()),
             (paths[1], _csv_bytes(result))),
            overwrite,
        )
    except reporting.ReportWriteError as exc:
        raise ComparisonWriteError(str(exc)) from None
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=pathlib.Path)
    parser.add_argument("candidate", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path,
                        default=pathlib.Path(tempfile.gettempdir()) / "devobs-performance-comparisons")
    parser.add_argument("--same-host-confirmed", action="store_true",
                        help="confirm that both runs used the same physical host")
    parser.add_argument("--allow-python-version-change", action="store_true",
                        help="explicitly compare different Python releases")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        baseline, candidate = _load_report_pair(args.baseline, args.candidate)
        result = compare_summaries(
            baseline, candidate, same_host_confirmed=args.same_host_confirmed,
            allow_python_version_change=args.allow_python_version_change,
        )
        outputs = write_comparison_report(result, args.output_dir, args.overwrite)
    except (ComparisonValidationError, ComparisonWriteError, OSError, ValueError):
        print("Comparison failed closed; check report compatibility and output destination.", file=sys.stderr)
        return 2
    for path in outputs:
        print(f"Wrote {path.name}")
    for row in result["benchmarks"]:
        print(f"{row['benchmark_id']}: {row['status']} ({row['delta_percent']:+.2f}%)")
    print("Statistics are advisory and do not gate CI or deployments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

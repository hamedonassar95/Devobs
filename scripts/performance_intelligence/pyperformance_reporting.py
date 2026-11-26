"""Privacy-minimized report contract for the pinned optional pyperformance suite."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import pathlib
import statistics
import tempfile
from dataclasses import dataclass
from typing import Iterable

from .pyperformance_contract import (
    OUTPUT_NAMES,
    PY_PERFORMANCE_COMMIT,
    PY_PERFORMANCE_VERSION,
)

SCHEMA_VERSION = 1
SUMMARY_KEYS = frozenset({
    "schema_version", "source_sha", "suite_name", "suite_version", "suite_source_sha",
    "python_version", "platform", "architecture", "measurement_mode", "benchmarks",
})
ROW_KEYS = frozenset({
    "benchmark_id", "benchmark_name", "mean_seconds", "median_seconds",
    "standard_deviation_seconds", "sample_count",
})
CSV_FIELDS = (
    "schema_version", "source_sha", "suite_name", "suite_version", "suite_source_sha",
    "python_version", "platform", "architecture", "measurement_mode", "benchmark_id",
    "benchmark_name", "mean_seconds", "median_seconds", "standard_deviation_seconds",
    "sample_count",
)
NATIVE_KEYS = frozenset({"version", "metadata", "benchmarks"})


class ReportValidationError(ValueError):
    """Fixed, non-sensitive report validation error."""


class ReportWriteError(OSError):
    """Fixed error for unsafe or conflicting report destinations."""


@dataclass(frozen=True)
class PyPerformanceResult:
    benchmark_name: str
    samples_seconds: tuple[float, ...]


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def validate_results(results: object, expected_names: set[str] | frozenset[str]) -> None:
    if type(results) is not list or not results:
        raise ReportValidationError("empty_suite")
    if type(expected_names) not in (set, frozenset) or not expected_names:
        raise ReportValidationError("empty_expected_suite")
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, PyPerformanceResult):
            raise ReportValidationError("invalid_benchmark_result")
        name = result.benchmark_name
        samples = result.samples_seconds
        if (not isinstance(name, str) or name not in OUTPUT_NAMES or name not in expected_names
                or name in seen or type(samples) is not tuple or len(samples) < 2):
            raise ReportValidationError("invalid_benchmark_identity_or_samples")
        seen.add(name)
        for value in samples:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value <= 0):
                raise ReportValidationError("invalid_duration")
    if seen != set(expected_names):
        raise ReportValidationError("incomplete_benchmark_suite")


def _validate_metadata(metadata: dict[str, object]) -> None:
    required = {
        "source_sha", "suite_source_sha", "python_version", "platform", "architecture",
        "measurement_mode",
    }
    if type(metadata) is not dict or set(metadata) != required:
        raise ReportValidationError("invalid_metadata_fields")
    if not _sha(metadata["source_sha"]) or metadata["suite_source_sha"] != PY_PERFORMANCE_COMMIT:
        raise ReportValidationError("invalid_source_revision")
    version = metadata["python_version"]
    if (not isinstance(version, str) or len(version) > 24
            or not version.startswith("3.12.")
            or not all(part.isdigit() for part in version.split("."))
            or len(version.split(".")) != 3):
        raise ReportValidationError("invalid_python_version")
    if not isinstance(metadata["platform"], str) or metadata["platform"] not in {"linux", "macos", "windows"}:
        raise ReportValidationError("invalid_platform")
    if (not isinstance(metadata["architecture"], str)
            or metadata["architecture"] not in {"x86_64", "aarch64", "x86", "unknown"}):
        raise ReportValidationError("invalid_architecture")
    if (not isinstance(metadata["measurement_mode"], str)
            or metadata["measurement_mode"] not in {"smoke", "statistical"}):
        raise ReportValidationError("invalid_measurement_mode")


def build_summary(results: list[PyPerformanceResult], **metadata: object) -> dict[str, object]:
    if type(results) is not list or not results:
        raise ReportValidationError("empty_suite")
    try:
        _validate_metadata(metadata)
        validate_results(results, {result.benchmark_name for result in results})
    except (TypeError, AttributeError) as exc:
        raise ReportValidationError("invalid_benchmark_results") from None
    rows = []
    for result in results:
        values = result.samples_seconds
        rows.append({
            "benchmark_id": f"pyperformance.{result.benchmark_name}.v1",
            "benchmark_name": result.benchmark_name,
            "mean_seconds": statistics.mean(values),
            "median_seconds": statistics.median(values),
            "standard_deviation_seconds": statistics.stdev(values),
            "sample_count": len(values),
        })
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_sha": metadata["source_sha"],
        "suite_name": "pyperformance",
        "suite_version": PY_PERFORMANCE_VERSION,
        "suite_source_sha": metadata["suite_source_sha"],
        "python_version": metadata["python_version"],
        "platform": metadata["platform"],
        "architecture": metadata["architecture"],
        "measurement_mode": metadata["measurement_mode"],
        "benchmarks": rows,
    }
    validate_summary(summary)
    return summary


def validate_summary(summary: object) -> None:
    if type(summary) is not dict or set(summary) != SUMMARY_KEYS:
        raise ReportValidationError("invalid_summary_fields")
    if type(summary["schema_version"]) is not int or summary["schema_version"] != SCHEMA_VERSION:
        raise ReportValidationError("incompatible_schema")
    if summary["suite_name"] != "pyperformance" or summary["suite_version"] != PY_PERFORMANCE_VERSION:
        raise ReportValidationError("invalid_suite_identity")
    metadata = {key: summary[key] for key in (
        "source_sha", "suite_source_sha", "python_version", "platform", "architecture", "measurement_mode",
    )}
    _validate_metadata(metadata)
    rows = summary["benchmarks"]
    if type(rows) is not list or not rows:
        raise ReportValidationError("empty_suite")
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise ReportValidationError("invalid_benchmark_row")
        name = row["benchmark_name"]
        if (not isinstance(name, str) or name not in OUTPUT_NAMES
                or row["benchmark_id"] != f"pyperformance.{name}.v1" or name in seen):
            raise ReportValidationError("invalid_benchmark_identity")
        seen.add(name)
        for key in ("mean_seconds", "median_seconds", "standard_deviation_seconds"):
            value = row[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ReportValidationError("invalid_duration")
        if type(row["sample_count"]) is not int or row["sample_count"] < 2:
            raise ReportValidationError("invalid_sample_count")


def sanitized_native_json(samples: list[tuple[str, list[float]]]) -> bytes:
    """Build the minimal shape emitted by pyperf convert --remove-all-metadata."""
    if type(samples) is not list or not samples:
        raise ReportValidationError("empty_suite")
    benchmarks = []
    seen = set()
    for name, values in samples:
        if not isinstance(name, str) or name not in OUTPUT_NAMES or name in seen:
            raise ReportValidationError("invalid_benchmark_identity")
        seen.add(name)
        if type(values) is not list or not values:
            raise ReportValidationError("invalid_native_samples")
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ReportValidationError("invalid_native_samples")
        benchmarks.append({
            "metadata": {"name": name},
            "runs": [{"values": values, "warmups": []}],
        })
    return (json.dumps({"version": "1.0", "metadata": {"unit": "second"}, "benchmarks": benchmarks},
                       sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def validate_native_json(data: bytes, expected_names: set[str] | frozenset[str]) -> dict[str, int]:
    if type(expected_names) not in (set, frozenset) or not expected_names:
        raise ReportValidationError("invalid_expected_benchmarks")
    try:
        parsed = json.loads(data)
    except (UnicodeError, ValueError, TypeError):
        raise ReportValidationError("invalid_native_report") from None
    if (type(parsed) is not dict or set(parsed) != NATIVE_KEYS or parsed["version"] != "1.0"
            or parsed["metadata"] != {"unit": "second"}):
        raise ReportValidationError("unsanitized_native_report")
    benchmarks = parsed["benchmarks"]
    if type(benchmarks) is not list or not benchmarks:
        raise ReportValidationError("invalid_native_report")
    seen: dict[str, int] = {}
    for benchmark in benchmarks:
        if (type(benchmark) is not dict or set(benchmark) != {"metadata", "runs"}
                or type(benchmark["metadata"]) is not dict
                or set(benchmark["metadata"]) != {"name"}):
            raise ReportValidationError("unsanitized_native_report")
        name = benchmark["metadata"]["name"]
        runs = benchmark["runs"]
        if (not isinstance(name, str) or name not in expected_names or name not in OUTPUT_NAMES
                or name in seen or type(runs) is not list or not runs):
            raise ReportValidationError("invalid_native_report")
        sample_count = 0
        for run in runs:
            if type(run) is not dict or set(run) != {"values", "warmups"}:
                raise ReportValidationError("unsanitized_native_report")
            values, warmups = run["values"], run["warmups"]
            if type(values) is not list or type(warmups) is not list:
                raise ReportValidationError("invalid_native_report")
            for value in values:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    raise ReportValidationError("invalid_native_report")
            sample_count += len(values)
            for warmup in warmups:
                if (type(warmup) is not list or len(warmup) != 2
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) or value <= 0 for value in warmup)):
                    raise ReportValidationError("invalid_native_report")
        if sample_count < 2:
            raise ReportValidationError("invalid_native_sample_count")
        seen[name] = sample_count
    if set(seen) != set(expected_names):
        raise ReportValidationError("incomplete_native_report")
    return seen


def report_paths(output_dir: pathlib.Path, source_sha: str, mode: str) -> tuple[pathlib.Path, ...]:
    if not _sha(source_sha) or mode not in {"smoke", "statistical"}:
        raise ReportWriteError("invalid_report_identity")
    prefix = f"devobs-pyperformance-{source_sha[:12]}-{mode}"
    return tuple(pathlib.Path(output_dir) / f"{prefix}{suffix}" for suffix in (".pyperf.json", ".json", ".csv"))


def preflight_destinations(output_dir: pathlib.Path, source_sha: str, mode: str, overwrite: bool) -> None:
    for path in report_paths(output_dir, source_sha, mode):
        if path.is_symlink() or (path.exists() and not overwrite):
            raise ReportWriteError("destination_exists_or_symlink")


def _json_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    return (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _csv_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in summary["benchmarks"]:
        writer.writerow({key: summary[key] for key in CSV_FIELDS[:9]} | row)
    return stream.getvalue().encode("utf-8")


def _atomic_write(files: Iterable[tuple[pathlib.Path, bytes]], overwrite: bool) -> None:
    targets = tuple((pathlib.Path(path), data) for path, data in files)
    if len({path.resolve() for path, _ in targets}) != len(targets):
        raise ReportWriteError("duplicate_destination")
    for path, _ in targets:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ReportWriteError("invalid_destination")
        if path.exists() and not overwrite:
            raise ReportWriteError("destination_exists")
    staged = []
    created = []
    try:
        for path, data in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=".devobs-pyperformance-", dir=path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            staged.append((pathlib.Path(name), path))
        for temporary, target in staged:
            if overwrite:
                os.replace(temporary, target)
            else:
                os.link(temporary, target)
                created.append(target)
                temporary.unlink()
    except OSError:
        for target in created:
            target.unlink(missing_ok=True)
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        raise ReportWriteError("report_write_failed") from None


def write_reports(summary: dict[str, object], native: bytes, output_dir: pathlib.Path,
                  overwrite: bool = False) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    validate_summary(summary)
    expected = {row["benchmark_name"] for row in summary["benchmarks"]}
    try:
        native_counts = validate_native_json(native, expected)
    except ReportValidationError as exc:
        raise ReportWriteError(str(exc)) from None
    if set(native_counts) != expected:
        raise ReportWriteError("native_summary_mismatch")
    summary_counts = {row["benchmark_name"]: row["sample_count"] for row in summary["benchmarks"]}
    if native_counts != summary_counts:
        raise ReportWriteError("native_summary_sample_count_mismatch")
    paths = report_paths(output_dir, summary["source_sha"], summary["measurement_mode"])
    _atomic_write(((paths[0], native), (paths[1], _json_bytes(summary)),
                   (paths[2], _csv_bytes(summary))), overwrite)
    return paths

"""Privacy-minimized, versioned JSON and CSV reports for Devobs benchmarks."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import pathlib
import statistics
import tempfile
from typing import Iterable

from .benchmark_engine import (
    BenchmarkResult,
    BenchmarkValidationError,
    BENCHMARK_NAMES,
    validate_metadata,
    validate_results,
)

SCHEMA_VERSION = 1
SUMMARY_KEYS = frozenset({
    "schema_version", "source_sha", "python_version", "platform", "architecture",
    "measurement_mode", "benchmarks",
})
ROW_KEYS = frozenset({
    "benchmark_id", "benchmark_name", "mean_seconds", "median_seconds",
    "standard_deviation_seconds", "sample_count",
})
CSV_FIELDS = (
    "schema_version", "source_sha", "python_version", "platform", "architecture",
    "measurement_mode", "benchmark_id", "benchmark_name", "mean_seconds",
    "median_seconds", "standard_deviation_seconds", "sample_count",
)
NATIVE_BENCHMARK_IDS = frozenset(BENCHMARK_NAMES)


class ReportValidationError(ValueError):
    """Fixed, non-sensitive report validation error."""


class ReportWriteError(OSError):
    """Fixed error for unsafe or conflicting report destinations."""


def build_summary(results: list[BenchmarkResult], **metadata: object) -> dict[str, object]:
    try:
        validate_results(results)
        validate_metadata(metadata)
    except BenchmarkValidationError as exc:
        raise ReportValidationError(str(exc)) from None
    rows = []
    for result in results:
        values = result.samples_seconds
        row = {
            "benchmark_id": result.benchmark_id,
            "benchmark_name": result.name,
            "mean_seconds": statistics.mean(values),
            "median_seconds": statistics.median(values),
            "standard_deviation_seconds": statistics.stdev(values),
            "sample_count": len(values),
        }
        rows.append(row)
    summary = {"schema_version": SCHEMA_VERSION, **metadata, "benchmarks": rows}
    validate_summary(summary)
    return summary


def validate_summary(summary: object) -> None:
    if type(summary) is not dict or set(summary) != SUMMARY_KEYS:
        raise ReportValidationError("invalid_summary_fields")
    if type(summary["schema_version"]) is not int or summary["schema_version"] != SCHEMA_VERSION:
        raise ReportValidationError("incompatible_schema")
    try:
        validate_metadata({key: summary[key] for key in SUMMARY_KEYS - {"schema_version", "benchmarks"}})
    except BenchmarkValidationError as exc:
        raise ReportValidationError(str(exc)) from None
    rows = summary["benchmarks"]
    if type(rows) is not list or not rows:
        raise ReportValidationError("empty_suite")
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise ReportValidationError("invalid_benchmark_row")
        if (not isinstance(row["benchmark_id"], str) or row["benchmark_id"] not in BENCHMARK_NAMES
                or row["benchmark_id"] in seen
                or row["benchmark_name"] != BENCHMARK_NAMES[row["benchmark_id"]]):
            raise ReportValidationError("invalid_benchmark_identity")
        seen.add(row["benchmark_id"])
        for key in ("mean_seconds", "median_seconds", "standard_deviation_seconds"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ReportValidationError("invalid_duration")
        if type(row["sample_count"]) is not int or row["sample_count"] < 2:
            raise ReportValidationError("invalid_sample_count")


def _json_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    try:
        return (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError):
        raise ReportValidationError("invalid_json_report") from None


def _csv_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in summary["benchmarks"]:
        writer.writerow({key: summary[key] for key in CSV_FIELDS[:6]} | row)
    return output.getvalue().encode()


def _validate_native_pyperf(data: bytes) -> set[str]:
    try:
        parsed = json.loads(data)
    except (UnicodeError, ValueError, TypeError):
        raise ReportWriteError("invalid_native_report") from None
    if (type(parsed) is not dict or set(parsed) != {"version", "metadata", "benchmarks"}
            or parsed["version"] != "1.0" or parsed["metadata"] != {"unit": "second"}):
        raise ReportWriteError("unsanitized_native_report")
    benchmarks = parsed["benchmarks"]
    if type(benchmarks) is not list or not benchmarks:
        raise ReportWriteError("invalid_native_report")
    seen = set()
    for benchmark in benchmarks:
        if (type(benchmark) is not dict or set(benchmark) != {"metadata", "runs"}
                or type(benchmark["metadata"]) is not dict
                or set(benchmark["metadata"]) != {"name"}):
            raise ReportWriteError("unsanitized_native_report")
        name = benchmark["metadata"]["name"]
        runs = benchmark["runs"]
        if (not isinstance(name, str) or name not in NATIVE_BENCHMARK_IDS or name in seen
                or type(runs) is not list or not runs):
            raise ReportWriteError("invalid_native_report")
        seen.add(name)
        for run in runs:
            if type(run) is not dict or not set(run) <= {"values", "warmups"}:
                raise ReportWriteError("unsanitized_native_report")
            values = run.get("values", [])
            warmups = run.get("warmups", [])
            if type(values) is not list or type(warmups) is not list:
                raise ReportWriteError("invalid_native_report")
            for value in values:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    raise ReportWriteError("invalid_native_report")
            for warmup in warmups:
                if (type(warmup) is not list or len(warmup) != 2
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) or value <= 0 for value in warmup)):
                    raise ReportWriteError("invalid_native_report")
    if seen != NATIVE_BENCHMARK_IDS:
        raise ReportWriteError("incomplete_native_report")
    return seen


def run_report_paths(output_dir: pathlib.Path, source_sha: str, mode: str) -> tuple[pathlib.Path, ...]:
    if len(source_sha) != 40 or mode not in {"smoke", "statistical"}:
        raise ReportWriteError("invalid_report_identity")
    prefix = f"devobs-perf-{source_sha[:12]}-{mode}"
    return tuple(pathlib.Path(output_dir) / f"{prefix}{suffix}" for suffix in
                 (".pyperf.json", ".json", ".csv"))


def preflight_run_destinations(output_dir: pathlib.Path, source_sha: str, mode: str,
                               overwrite: bool = False) -> None:
    for path in run_report_paths(output_dir, source_sha, mode):
        if path.is_symlink() or (path.exists() and not overwrite):
            raise ReportWriteError("destination_exists_or_symlink")


def write_summary_files(summary: dict[str, object], json_path: pathlib.Path,
                        csv_path: pathlib.Path, overwrite: bool = False) -> tuple[pathlib.Path, pathlib.Path]:
    validate_summary(summary)
    _atomic_write(((json_path, _json_bytes(summary)), (csv_path, _csv_bytes(summary))), overwrite)
    return json_path, csv_path


def _atomic_write(files: Iterable[tuple[pathlib.Path, bytes]], overwrite: bool) -> None:
    targets = tuple((pathlib.Path(path), data) for path, data in files)
    if len({path.resolve() for path, _ in targets}) != len(targets):
        raise ReportWriteError("duplicate_destination")
    for path, _ in targets:
        if path.exists() and not overwrite:
            raise ReportWriteError("destination_exists")
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ReportWriteError("invalid_destination")
    staged = []
    created = []
    try:
        for path, data in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".devobs-report-", dir=path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            staged.append((pathlib.Path(temporary), path))
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


def write_run_reports(summary: dict[str, object], output_dir: pathlib.Path, source_sha: str,
                      native_pyperf_json: bytes, repository_root: pathlib.Path,
                      overwrite: bool = False) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    validate_summary(summary)
    if not isinstance(native_pyperf_json, bytes):
        raise ReportWriteError("invalid_native_report")
    native_ids = _validate_native_pyperf(native_pyperf_json)
    if native_ids != {row["benchmark_id"] for row in summary["benchmarks"]}:
        raise ReportWriteError("native_summary_mismatch")
    output_dir = pathlib.Path(output_dir).resolve()
    repository_root = pathlib.Path(repository_root).resolve()
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if output_dir == repository_root or repository_root in output_dir.parents:
        raise ReportWriteError("repository_output_forbidden")
    if output_dir != temp_root and temp_root not in output_dir.parents:
        raise ReportWriteError("temporary_output_required")
    if not isinstance(source_sha, str) or summary["source_sha"] != source_sha:
        raise ReportWriteError("source_revision_mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    native_path, json_path, csv_path = run_report_paths(
        output_dir, source_sha, summary["measurement_mode"]
    )
    _atomic_write(((native_path, native_pyperf_json), (json_path, _json_bytes(summary)),
                   (csv_path, _csv_bytes(summary))), overwrite)
    return native_path, json_path, csv_path

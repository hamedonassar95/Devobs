"""Versioned, privacy-limited reports for sampled private-memory peaks."""
from __future__ import annotations

import csv
import io
import json
import math
import pathlib
import re
import statistics
import tempfile
from dataclasses import dataclass

from .benchmark_engine import BENCHMARK_NAMES, SHA_RE
from .pyperformance_contract import OUTPUT_NAMES, PY_PERFORMANCE_COMMIT, PY_PERFORMANCE_VERSION
from . import reporting

SCHEMA_VERSION = 1
METRIC = "peak_private_bytes"
SUMMARY_KEYS = frozenset({
    "schema_version", "source_sha", "suite_name", "suite_version", "suite_source_sha",
    "python_version", "platform", "architecture", "measurement_mode", "metric", "benchmarks",
})
ROW_KEYS = frozenset({
    "benchmark_id", "benchmark_name", "mean_bytes", "median_bytes",
    "standard_deviation_bytes", "sample_count",
})
CSV_FIELDS = (
    "schema_version", "source_sha", "suite_name", "suite_version", "suite_source_sha",
    "python_version", "platform", "architecture", "measurement_mode", "metric",
    "benchmark_id", "benchmark_name", "mean_bytes", "median_bytes",
    "standard_deviation_bytes", "sample_count",
)
PY_VERSION_RE = re.compile(r"3\.(?:12|15)\.\d{1,3}\Z")


class ResourceReportError(ValueError):
    """Fixed validation error for resource measurement data."""


class ResourceReportWriteError(OSError):
    """Fixed error for unsafe or conflicting report destinations."""


@dataclass(frozen=True)
class MemoryResult:
    benchmark_id: str
    benchmark_name: str
    samples_bytes: tuple[float, ...]


def _known_id_and_name(suite_name: object, benchmark_id: object,
                       benchmark_name: object) -> bool:
    if not isinstance(benchmark_id, str) or not isinstance(benchmark_name, str):
        return False
    if suite_name == "devobs":
        return (benchmark_id in BENCHMARK_NAMES
                and BENCHMARK_NAMES.get(benchmark_id) == benchmark_name)
    if suite_name == "pyperformance":
        return (isinstance(benchmark_id, str)
                and benchmark_id.startswith("pyperformance.")
                and benchmark_id.endswith(".v1")
                and benchmark_id[len("pyperformance."):-3] in OUTPUT_NAMES
                and benchmark_name == benchmark_id[len("pyperformance."):-3])
    return False


def _validate_metadata(metadata: dict[str, object]) -> None:
    required = {
        "source_sha", "suite_name", "suite_version", "suite_source_sha",
        "python_version", "platform", "architecture", "measurement_mode",
    }
    if type(metadata) is not dict or set(metadata) != required:
        raise ResourceReportError("invalid_metadata_fields")
    if not isinstance(metadata["source_sha"], str) or not SHA_RE.fullmatch(metadata["source_sha"]):
        raise ResourceReportError("invalid_source_revision")
    if not isinstance(metadata["suite_source_sha"], str) or not SHA_RE.fullmatch(metadata["suite_source_sha"]):
        raise ResourceReportError("invalid_suite_revision")
    if not isinstance(metadata["suite_name"], str) or metadata["suite_name"] not in {"devobs", "pyperformance"}:
        raise ResourceReportError("invalid_suite_identity")
    expected_version = "1" if metadata["suite_name"] == "devobs" else PY_PERFORMANCE_VERSION
    if metadata["suite_version"] != expected_version:
        raise ResourceReportError("invalid_suite_version")
    if metadata["suite_name"] == "devobs" and metadata["suite_source_sha"] != metadata["source_sha"]:
        raise ResourceReportError("invalid_suite_revision")
    if metadata["suite_name"] == "pyperformance" and metadata["suite_source_sha"] != PY_PERFORMANCE_COMMIT:
        raise ResourceReportError("invalid_suite_revision")
    if not isinstance(metadata["python_version"], str) or not PY_VERSION_RE.fullmatch(metadata["python_version"]):
        raise ResourceReportError("unsupported_python_version")
    if not isinstance(metadata["platform"], str) or metadata["platform"] not in {"linux", "macos", "windows"}:
        raise ResourceReportError("invalid_platform")
    if not isinstance(metadata["architecture"], str) or metadata["architecture"] not in {"x86_64", "aarch64", "x86", "unknown"}:
        raise ResourceReportError("invalid_architecture")
    if not isinstance(metadata["measurement_mode"], str) or metadata["measurement_mode"] not in {"smoke", "statistical"}:
        raise ResourceReportError("invalid_measurement_mode")


def build_summary(results: list[MemoryResult], **metadata: object) -> dict[str, object]:
    _validate_metadata(metadata)
    if type(results) is not list or not results:
        raise ResourceReportError("empty_suite")
    rows = []
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, MemoryResult):
            raise ResourceReportError("invalid_memory_result")
        if (not _known_id_and_name(metadata["suite_name"], result.benchmark_id, result.benchmark_name)
                or result.benchmark_id in seen or type(result.samples_bytes) is not tuple
                or len(result.samples_bytes) < 2):
            raise ResourceReportError("invalid_memory_result")
        seen.add(result.benchmark_id)
        for value in result.samples_bytes:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value <= 0):
                raise ResourceReportError("invalid_memory_value")
        rows.append({
            "benchmark_id": result.benchmark_id,
            "benchmark_name": result.benchmark_name,
            "mean_bytes": statistics.mean(result.samples_bytes),
            "median_bytes": statistics.median(result.samples_bytes),
            "standard_deviation_bytes": statistics.stdev(result.samples_bytes),
            "sample_count": len(result.samples_bytes),
        })
    if metadata["suite_name"] == "devobs" and seen != set(BENCHMARK_NAMES):
        raise ResourceReportError("incomplete_suite")
    summary = {"schema_version": SCHEMA_VERSION, **metadata, "metric": METRIC, "benchmarks": rows}
    validate_summary(summary)
    return summary


def validate_summary(summary: object) -> None:
    if type(summary) is not dict or set(summary) != SUMMARY_KEYS:
        raise ResourceReportError("invalid_summary_fields")
    if type(summary["schema_version"]) is not int or summary["schema_version"] != SCHEMA_VERSION:
        raise ResourceReportError("incompatible_schema")
    if summary["metric"] != METRIC:
        raise ResourceReportError("invalid_metric")
    metadata = {key: summary[key] for key in (
        "source_sha", "suite_name", "suite_version", "suite_source_sha", "python_version",
        "platform", "architecture", "measurement_mode",
    )}
    _validate_metadata(metadata)
    rows = summary["benchmarks"]
    if type(rows) is not list or not rows:
        raise ResourceReportError("empty_suite")
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise ResourceReportError("invalid_memory_row")
        benchmark_id = row["benchmark_id"]
        if (not _known_id_and_name(summary["suite_name"], benchmark_id, row["benchmark_name"])
                or benchmark_id in seen):
            raise ResourceReportError("invalid_benchmark_identity")
        seen.add(benchmark_id)
        for key in ("mean_bytes", "median_bytes", "standard_deviation_bytes"):
            value = row[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ResourceReportError("invalid_memory_value")
        if type(row["sample_count"]) is not int or row["sample_count"] < 2:
            raise ResourceReportError("invalid_sample_count")
    if summary["suite_name"] == "devobs" and seen != set(BENCHMARK_NAMES):
        raise ResourceReportError("incomplete_suite")


def native_samples(data: bytes, expected_ids: set[str]) -> dict[str, tuple[float, ...]]:
    if (not isinstance(data, bytes) or len(data) > 16 * 1024 * 1024
            or type(expected_ids) is not set or not expected_ids
            or any(not isinstance(item, str) for item in expected_ids)):
        raise ResourceReportError("invalid_native_report")
    try:
        parsed = json.loads(data)
    except (UnicodeError, ValueError, TypeError):
        raise ResourceReportError("invalid_native_report") from None
    if (type(parsed) is not dict or set(parsed) != {"version", "metadata", "benchmarks"}
            or parsed["version"] != "1.0"
            or type(parsed["metadata"]) is not dict
            or parsed["metadata"] != {"unit": "byte"}):
        raise ResourceReportError("invalid_native_report")
    rows = parsed["benchmarks"]
    if type(rows) is not list or not rows:
        raise ResourceReportError("invalid_native_report")
    samples_by_id: dict[str, tuple[float, ...]] = {}
    for benchmark in rows:
        if (type(benchmark) is not dict or set(benchmark) != {"metadata", "runs"}
                or type(benchmark["metadata"]) is not dict
                or set(benchmark["metadata"]) != {"name"}):
            raise ResourceReportError("invalid_native_report")
        name = benchmark["metadata"]["name"]
        if not isinstance(name, str):
            raise ResourceReportError("invalid_native_report")
        benchmark_id = (name if name in BENCHMARK_NAMES else f"pyperformance.{name}.v1")
        runs = benchmark["runs"]
        if (benchmark_id not in expected_ids or benchmark_id in samples_by_id
                or type(runs) is not list or not runs):
            raise ResourceReportError("invalid_native_report")
        samples = []
        for run in runs:
            if type(run) is not dict or not set(run) <= {"values", "warmups"}:
                raise ResourceReportError("invalid_native_report")
            values = run.get("values", [])
            warmups = run.get("warmups", [])
            if type(values) is not list or type(warmups) is not list:
                raise ResourceReportError("invalid_native_report")
            samples.extend(values)
            for warmup in warmups:
                if (type(warmup) is not list or len(warmup) != 2
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) or value <= 0 for value in warmup)):
                    raise ResourceReportError("invalid_native_report")
        if (len(samples) < 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) or value <= 0 for value in samples)):
            raise ResourceReportError("invalid_native_report")
        samples_by_id[benchmark_id] = tuple(samples)
    if set(samples_by_id) != expected_ids:
        raise ResourceReportError("incomplete_native_report")
    return samples_by_id


def normalize_native_json(data: bytes, expected_ids: set[str]) -> bytes:
    """Reduce pyperf's converted memory JSON to the allowlisted report shape."""
    allowed_ids = set(BENCHMARK_NAMES) | {f"pyperformance.{name}.v1" for name in OUTPUT_NAMES}
    if (not isinstance(data, bytes) or len(data) > 16 * 1024 * 1024
            or type(expected_ids) is not set or not expected_ids
            or any(not isinstance(item, str) for item in expected_ids)
            or not expected_ids <= allowed_ids):
        raise ResourceReportError("invalid_native_report")
    try:
        parsed = json.loads(data)
    except (UnicodeError, ValueError, TypeError):
        raise ResourceReportError("invalid_native_report") from None
    if (type(parsed) is not dict or set(parsed) != {"version", "metadata", "benchmarks"}
            or parsed["version"] != "1.0" or type(parsed["metadata"]) is not dict
            or set(parsed["metadata"]) - {"unit", "name"}
            or parsed["metadata"].get("unit") != "byte"):
        raise ResourceReportError("invalid_native_report")
    root_name = parsed["metadata"].get("name")
    rows = parsed["benchmarks"]
    if (root_name is not None and not isinstance(root_name, str)) or type(rows) is not list or not rows:
        raise ResourceReportError("invalid_native_report")
    normalized = []
    seen: set[str] = set()
    for row in rows:
        if (type(row) is not dict or set(row) - {"metadata", "runs"}
                or "runs" not in row or type(row["runs"]) is not list or not row["runs"]):
            raise ResourceReportError("invalid_native_report")
        row_metadata = row.get("metadata", {})
        if type(row_metadata) is not dict or set(row_metadata) - {"name"}:
            raise ResourceReportError("invalid_native_report")
        row_name = row_metadata.get("name")
        if root_name is not None:
            if len(rows) != 1 or (row_name is not None and row_name != root_name):
                raise ResourceReportError("invalid_native_report")
            name = root_name
        else:
            name = row_name
        if not isinstance(name, str):
            raise ResourceReportError("invalid_native_report")
        benchmark_id = name if name in BENCHMARK_NAMES else f"pyperformance.{name}.v1"
        if benchmark_id not in expected_ids or benchmark_id in seen:
            raise ResourceReportError("invalid_native_report")
        clean_runs = []
        for run in row["runs"]:
            if type(run) is not dict or set(run) - {"values", "warmups"}:
                raise ResourceReportError("invalid_native_report")
            values = run.get("values", [])
            warmups = run.get("warmups", [])
            if (type(values) is not list or type(warmups) is not list
                    or any(isinstance(value, bool) or not isinstance(value, (int, float))
                           or not math.isfinite(value) or value <= 0 for value in values)):
                raise ResourceReportError("invalid_native_report")
            for warmup in warmups:
                if (type(warmup) is not list or len(warmup) != 2
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) or value <= 0 for value in warmup)):
                    raise ResourceReportError("invalid_native_report")
            clean_runs.append({"values": values, "warmups": warmups})
        normalized.append({"metadata": {"name": name}, "runs": clean_runs})
        seen.add(benchmark_id)
    if seen != expected_ids:
        raise ResourceReportError("incomplete_native_report")
    payload = {"version": "1.0", "metadata": {"unit": "byte"}, "benchmarks": normalized}
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def validate_native_json(data: bytes, expected_ids: set[str]) -> dict[str, int]:
    return {benchmark_id: len(samples) for benchmark_id, samples in native_samples(data, expected_ids).items()}


def _paths(output_dir: pathlib.Path, summary: dict[str, object]) -> tuple[pathlib.Path, ...]:
    prefix = (f"devobs-perf-{summary['suite_name']}-{summary['source_sha'][:12]}-"
              f"{summary['measurement_mode']}-memory")
    return tuple(pathlib.Path(output_dir) / f"{prefix}{suffix}" for suffix in
                 (".pyperf.json", ".json", ".csv"))


def preflight_run_destinations(output_dir: pathlib.Path, source_sha: str,
                               mode: str, overwrite: bool = False,
                               suite_name: str = "devobs") -> None:
    if (not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha)
            or mode not in {"smoke", "statistical"}
            or suite_name not in {"devobs", "pyperformance"}):
        raise ResourceReportWriteError("invalid_report_identity")
    prefix = f"devobs-perf-{suite_name}-{source_sha[:12]}-{mode}-memory"
    for suffix in (".pyperf.json", ".json", ".csv"):
        path = pathlib.Path(output_dir) / f"{prefix}{suffix}"
        if path.is_symlink() or (path.exists() and not overwrite):
            raise ResourceReportWriteError("destination_exists_or_symlink")


def _json_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    return (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _csv_bytes(summary: dict[str, object]) -> bytes:
    validate_summary(summary)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in summary["benchmarks"]:
        writer.writerow({key: summary[key] for key in CSV_FIELDS[:10]} | row)
    return stream.getvalue().encode()


def write_run_report(summary: dict[str, object], native: bytes, output_dir: pathlib.Path,
                     *, repository_root: pathlib.Path, overwrite: bool = False) -> tuple[pathlib.Path, ...]:
    validate_summary(summary)
    expected = {row["benchmark_id"] for row in summary["benchmarks"]}
    try:
        samples_by_id = native_samples(native, expected)
    except ResourceReportError as exc:
        raise ResourceReportWriteError(str(exc)) from None
    for row in summary["benchmarks"]:
        samples = samples_by_id[row["benchmark_id"]]
        expected_statistics = (
            statistics.mean(samples), statistics.median(samples), statistics.stdev(samples), len(samples),
        )
        summary_statistics = (
            row["mean_bytes"], row["median_bytes"], row["standard_deviation_bytes"], row["sample_count"],
        )
        if summary_statistics != expected_statistics:
            raise ResourceReportWriteError("native_summary_mismatch")
    output_dir = pathlib.Path(output_dir).resolve()
    repository_root = pathlib.Path(repository_root).resolve()
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if output_dir == repository_root or repository_root in output_dir.parents:
        raise ResourceReportWriteError("repository_output_forbidden")
    if output_dir != temp_root and temp_root not in output_dir.parents:
        raise ResourceReportWriteError("temporary_output_required")
    paths = _paths(output_dir, summary)
    try:
        reporting._atomic_write(
            ((paths[0], native), (paths[1], _json_bytes(summary)), (paths[2], _csv_bytes(summary))),
            overwrite,
        )
    except reporting.ReportWriteError as exc:
        raise ResourceReportWriteError(str(exc)) from None
    return paths

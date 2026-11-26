"""Bounded, manual pyperf runner for deterministic offline Devobs operations."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import platform
import re
import signal
import shutil
import subprocess  # nosec B404 - fixed local pyperf/Git argv only; no shell invocation.
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_two_agent_tasks import evaluate
from devobs_intelligence.contracts import parse_events
from devobs_intelligence.evaluation_splits import summarize_review_splits

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "performance" / "baseline.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
METADATA_KEYS = frozenset(
    {"source_sha", "python_version", "platform", "architecture", "measurement_mode"}
)
BENCHMARK_NAMES = {
    "devobs.event_evidence.parse_events.v1": "Parse synthetic event evidence",
    "devobs.task_graph.evaluate.v1": "Evaluate synthetic task dependencies",
    "devobs.evaluation_splits.summarize.v1": "Summarize synthetic evaluation splits",
}


class BenchmarkValidationError(ValueError):
    """Fixed, non-sensitive error for invalid benchmark data."""


class BenchmarkExecutionError(RuntimeError):
    """Fixed error for bounded benchmark process failures."""


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    name: str
    samples_seconds: tuple[float, ...]


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    name: str
    run: Callable[[], object]


@dataclass(frozen=True)
class MeasurementConfig:
    mode: str
    processes: int
    values: int
    warmups: int
    min_time_seconds: float
    worker_timeout_seconds: int
    timeout_seconds: int

    @classmethod
    def for_mode(cls, mode: str) -> "MeasurementConfig":
        presets = {
            "smoke": cls("smoke", 1, 3, 1, 0.05, 60, 180),
            "statistical": cls("statistical", 5, 20, 3, 0.25, 180, 900),
        }
        if not isinstance(mode, str) or mode not in presets:
            raise BenchmarkValidationError("invalid_measurement_mode")
        return presets[mode]


def validate_metadata(metadata: dict[str, object]) -> None:
    if type(metadata) is not dict or set(metadata) != METADATA_KEYS:
        raise BenchmarkValidationError("invalid_metadata_fields")
    if not isinstance(metadata["source_sha"], str) or not SHA_RE.fullmatch(metadata["source_sha"]):
        raise BenchmarkValidationError("invalid_source_sha")
    if not isinstance(metadata["python_version"], str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", metadata["python_version"]
    ):
        raise BenchmarkValidationError("invalid_python_version")
    if not isinstance(metadata["platform"], str) or metadata["platform"] not in {"linux", "macos", "windows"}:
        raise BenchmarkValidationError("invalid_platform")
    if not isinstance(metadata["architecture"], str) or metadata["architecture"] not in {"x86_64", "aarch64", "x86", "unknown"}:
        raise BenchmarkValidationError("invalid_architecture")
    if not isinstance(metadata["measurement_mode"], str) or metadata["measurement_mode"] not in {"smoke", "statistical"}:
        raise BenchmarkValidationError("invalid_measurement_mode")


def validate_results(results: list[BenchmarkResult]) -> None:
    if type(results) is not list or not results:
        raise BenchmarkValidationError("empty_suite")
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, BenchmarkResult):
            raise BenchmarkValidationError("invalid_benchmark_result")
        if (not isinstance(result.benchmark_id, str) or result.benchmark_id not in BENCHMARK_NAMES
                or result.benchmark_id in seen):
            raise BenchmarkValidationError("invalid_benchmark_id")
        if result.name != BENCHMARK_NAMES[result.benchmark_id]:
            raise BenchmarkValidationError("invalid_benchmark_name")
        seen.add(result.benchmark_id)
        values = result.samples_seconds
        if type(values) is not tuple or len(values) < 2:
            raise BenchmarkValidationError("insufficient_samples")
        for value in values:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise BenchmarkValidationError("invalid_duration")


def load_synthetic_workloads() -> dict[str, int | str]:
    """Load only fixed synthetic workload sizes; this is not a timing baseline."""
    try:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise BenchmarkValidationError("invalid_synthetic_fixture") from None
    expected = {"schema_version", "fixture_kind", "event_count", "task_count", "review_case_count"}
    if type(fixture) is not dict or set(fixture) != expected:
        raise BenchmarkValidationError("invalid_synthetic_fixture")
    if fixture["schema_version"] != 1 or fixture["fixture_kind"] != "synthetic_workload_sizes":
        raise BenchmarkValidationError("invalid_synthetic_fixture")
    for key, lower, upper in (("event_count", 1, 100), ("task_count", 1, 200),
                              ("review_case_count", 1, 1000)):
        value = fixture[key]
        if type(value) is not int or not lower <= value <= upper:
            raise BenchmarkValidationError("invalid_synthetic_fixture")
    return fixture


def _event_workload(count: int) -> list[dict[str, object]]:
    return [{
        "schema_version": 1,
        "event_id": f"synthetic-{index:03d}",
        "provider": "github" if index % 2 == 0 else "gitlab",
        "project_ref": f"synthetic-project-{index % 4}",
        "source_sha": "a" * 40,
        "kind": "incident" if index % 2 == 0 else "workflow_run",
        "observed_at": "2026-01-01T00:00:00Z",
        "evidence_digests": [hashlib.sha256(f"evidence-{index}".encode()).hexdigest()],
    } for index in range(count)]


def _task_manifest(count: int) -> dict[str, object]:
    repo = "synthetic/devobs"
    tasks = []
    for index in range(count):
        task_id = f"TASK-{index:03d}"
        tasks.append({
            "id": task_id, "repository": repo, "assigned_agent": "CODEX",
            "branch": f"feature/synthetic-{index:03d}",
            "affected_files": [f"synthetic/tasks/{index:03d}.json"],
            "dependencies": [f"TASK-{index - 1:03d}"] if index else [],
            "status": "complete", "previous_status": "evidence_ready",
            "source_sha": "a" * 40,
            "verification": {"commands": ["offline synthetic validation"],
                             "result": "PASS", "evidence": "synthetic fixture"},
            "pr_reference": None, "requested_actions": ["review"],
        })
    return {
        "schema_version": 1, "repositories": [repo],
        "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
        "approval": {key: "pending_human" for key in ("merge", "deploy", "billing", "production")},
        "tasks": tasks,
    }


def _split_workload(count: int) -> list[dict[str, str]]:
    categories = ("ci_failure", "capacity_pressure", "unknown")
    splits = ("calibration", "development", "holdout")
    rows = []
    for index in range(count):
        group = index // 2
        rows.append({
            "case_token": f"{index + 1:032x}",
            "incident_group_token": f"{group + 1:032x}",
            "split": splits[group % len(splits)],
            "category": categories[index % len(categories)],
        })
    return rows


def benchmark_definitions() -> tuple[BenchmarkDefinition, ...]:
    sizes = load_synthetic_workloads()
    events = _event_workload(sizes["event_count"])
    manifest = _task_manifest(sizes["task_count"])
    cases = _split_workload(sizes["review_case_count"])
    return (
        BenchmarkDefinition("devobs.event_evidence.parse_events.v1", BENCHMARK_NAMES["devobs.event_evidence.parse_events.v1"],
                            lambda: parse_events(events)),
        BenchmarkDefinition("devobs.task_graph.evaluate.v1", BENCHMARK_NAMES["devobs.task_graph.evaluate.v1"],
                            lambda: evaluate(manifest)),
        BenchmarkDefinition("devobs.evaluation_splits.summarize.v1", BENCHMARK_NAMES["devobs.evaluation_splits.summarize.v1"],
                            lambda: summarize_review_splits(cases)),
    )


def pyperf_command(python_executable: str, benchmark_script: pathlib.Path,
                   output_path: pathlib.Path, config: MeasurementConfig) -> list[str]:
    return [python_executable, str(benchmark_script), "--output", str(output_path),
            "--processes", str(config.processes), "--values", str(config.values),
            "--warmups", str(config.warmups), "--min-time", str(config.min_time_seconds),
            "--timeout", str(config.worker_timeout_seconds)]


def _execute_process(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(  # nosec B603 - fixed benchmark script argv; shell stays disabled.
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=(os.name == "posix"),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def run_bounded_command(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    if (type(command) is not list or not command or any(type(part) is not str or not part for part in command)
            or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 900):
        raise BenchmarkValidationError("invalid_process_request")
    try:
        result = _execute_process(command, timeout_seconds)
    except subprocess.TimeoutExpired:
        raise BenchmarkExecutionError("benchmark_timeout") from None
    except OSError:
        raise BenchmarkExecutionError("benchmark_process_unavailable") from None
    if result.returncode != 0:
        raise BenchmarkExecutionError("worker_failed")
    return result


def source_revision(repository_root: pathlib.Path = ROOT) -> str:
    git_executable = shutil.which("git")
    if not git_executable:
        raise BenchmarkExecutionError("git_unavailable")
    try:
        status = subprocess.run(  # nosec B603 - fixed read-only Git query; no shell or input-derived argv.
            [git_executable, "status", "--porcelain", "--untracked-files=all"], cwd=repository_root,
            check=True, capture_output=True, text=True, timeout=5,
        )
        revision = subprocess.run(  # nosec B603 - fixed read-only Git query; no shell or input-derived argv.
            [git_executable, "rev-parse", "HEAD"], cwd=repository_root,
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise BenchmarkExecutionError("source_revision_unavailable") from None
    if status.stdout or not SHA_RE.fullmatch(revision):
        raise BenchmarkExecutionError("working_tree_not_clean")
    return revision


def safe_metadata(source_sha: str, mode: str) -> dict[str, str]:
    system = platform.system().lower()
    system = {"darwin": "macos"}.get(system, system)
    machine = platform.machine().lower()
    architecture = ("x86_64" if machine in {"x86_64", "amd64"} else
                    "aarch64" if machine in {"aarch64", "arm64"} else
                    "x86" if machine in {"i386", "i686", "x86"} else "unknown")
    metadata = {
        "source_sha": source_sha,
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "platform": system,
        "architecture": architecture,
        "measurement_mode": mode,
    }
    validate_metadata(metadata)
    return metadata


def _load_pyperf_results(path: pathlib.Path) -> list[BenchmarkResult]:
    try:
        import pyperf
        with path.open("r", encoding="utf-8") as stream:
            suite = pyperf.BenchmarkSuite.load(stream)
        names = {item.benchmark_id: item.name for item in benchmark_definitions()}
        results = [BenchmarkResult(benchmark.get_name(), names[benchmark.get_name()],
                                  tuple(benchmark.get_values()))
                   for benchmark in suite.get_benchmarks()]
    except (ImportError, KeyError, OSError, ValueError, TypeError):
        raise BenchmarkValidationError("invalid_pyperf_results") from None
    validate_results(results)
    if {item.benchmark_id for item in results} != {item.benchmark_id for item in benchmark_definitions()}:
        raise BenchmarkValidationError("incomplete_benchmark_suite")
    return results


def run(mode: str, output_dir: pathlib.Path, overwrite: bool = False) -> tuple[pathlib.Path, ...]:
    config = MeasurementConfig.for_mode(mode)
    metadata = safe_metadata(source_revision(), mode)
    from .reporting import build_summary, preflight_run_destinations, write_run_reports

    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    output_dir = output_dir.resolve()
    if output_dir == ROOT or ROOT in output_dir.parents or (output_dir != temp_root and temp_root not in output_dir.parents):
        raise BenchmarkValidationError("invalid_output_destination")
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight_run_destinations(output_dir, metadata["source_sha"], mode, overwrite)
    with tempfile.TemporaryDirectory(prefix="devobs-perf-", dir=temp_root) as temporary:
        temporary_dir = pathlib.Path(temporary)
        raw = temporary_dir / "raw-pyperf.json"
        sanitized = temporary_dir / "sanitized-pyperf.json"
        run_bounded_command(
            pyperf_command(sys.executable, ROOT / "benchmarks" / "devobs_benchmarks.py", raw, config),
            config.timeout_seconds,
        )
        run_bounded_command(
            [sys.executable, "-m", "pyperf", "convert", "--remove-all-metadata",
             str(raw), "-o", str(sanitized)], config.timeout_seconds,
        )
        run_bounded_command([sys.executable, "-m", "pyperf", "check", str(sanitized)], 30)
        results = _load_pyperf_results(sanitized)
        summary = build_summary(results, **metadata)
        return write_run_reports(
            summary, output_dir, metadata["source_sha"], sanitized.read_bytes(),
            repository_root=ROOT, overwrite=overwrite,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "statistical"), default="smoke")
    parser.add_argument("--output-dir", type=pathlib.Path,
                        default=pathlib.Path(tempfile.gettempdir()) / "devobs-performance")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        outputs = run(args.mode, args.output_dir, args.overwrite)
    except (BenchmarkValidationError, BenchmarkExecutionError, ValueError, OSError) as exc:
        print(f"Benchmark failed closed: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Benchmark failed closed: internal_error", file=sys.stderr)
        return 2
    for path in outputs:
        print(f"Wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

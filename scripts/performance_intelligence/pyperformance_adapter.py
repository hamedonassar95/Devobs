"""Manual, offline-only adapter for an audited subset of upstream pyperformance."""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys
import tempfile
from dataclasses import dataclass

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from performance_intelligence import benchmark_engine as engine
from performance_intelligence import pyperformance_reporting as reporting
from performance_intelligence.pyperformance_contract import (
    PY_PERFORMANCE_COMMIT,
    SAFE_BENCHMARK_NAMES,
    SAFE_BENCHMARK_OUTPUTS,
)
from performance_intelligence.pyperformance_artifacts import (
    ALLOWED_PACKAGES,
    POSIX_INHERITED_PIP,
    PyPerformanceExecutionError,
    PyPerformanceValidationError,
    build_child_environment,
    extract_verified_source,
    load_suite_toolchain_lock,
    require_runtime_toolchain,
    validate_source_lock,
    validate_wheelhouse,
    verify_source_archive,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SMOKE_BENCHMARKS = tuple(SAFE_BENCHMARK_OUTPUTS)


@dataclass(frozen=True)
class MeasurementConfig:
    mode: str
    benchmark_timeout_seconds: int
    suite_timeout_seconds: int
    max_benchmarks: int

    @classmethod
    def for_mode(cls, mode: str) -> "MeasurementConfig":
        presets = {
            "smoke": cls("smoke", 60, 900, 8),
            "statistical": cls("statistical", 180, 900, 3),
        }
        if not isinstance(mode, str) or mode not in presets:
            raise PyPerformanceValidationError("invalid_measurement_mode")
        return presets[mode]


def validate_benchmark_selection(raw: str | None, mode: str) -> tuple[str, ...]:
    config = MeasurementConfig.for_mode(mode)
    if raw is None:
        if mode != "smoke":
            raise PyPerformanceValidationError("statistical_selection_required")
        names = DEFAULT_SMOKE_BENCHMARKS
    elif type(raw) is str and raw and len(raw) <= 256:
        names = tuple(part.strip() for part in raw.split(","))
    else:
        raise PyPerformanceValidationError("invalid_benchmark_selection")
    if (not names or len(names) > config.max_benchmarks
            or len(set(names)) != len(names)
            or any(name not in SAFE_BENCHMARK_NAMES for name in names)):
        raise PyPerformanceValidationError("benchmark_not_allowlisted_or_limit_exceeded")
    return names


def pyperformance_command(python_executable: str, source_root: pathlib.Path,
                          benchmark_names: tuple[str, ...], mode: str,
                          output_path: pathlib.Path) -> list[str]:
    config = MeasurementConfig.for_mode(mode)
    if (not isinstance(source_root, pathlib.Path) or not source_root.is_dir() or source_root.is_symlink()
            or not benchmark_names or any(name not in SAFE_BENCHMARK_NAMES for name in benchmark_names)
            or len(benchmark_names) > config.max_benchmarks):
        raise PyPerformanceValidationError("benchmark_not_allowlisted_or_limit_exceeded")
    mode_flag = "--fast" if mode == "smoke" else "--rigorous"
    return [
        python_executable, "-m", "pyperformance", "run", mode_flag,
        f"--timeout={config.benchmark_timeout_seconds}",
        f"--benchmarks={','.join(benchmark_names)}",
        f"--python={python_executable}",
        f"--inherit-environ={','.join(POSIX_INHERITED_PIP)}",
        f"--output={output_path}",
    ]


def _expected_output_names(benchmarks: tuple[str, ...]) -> set[str]:
    return {output for name in benchmarks for output in SAFE_BENCHMARK_OUTPUTS[name]}


def _load_results(path: pathlib.Path, expected: set[str]) -> tuple[bytes, list[reporting.PyPerformanceResult]]:
    try:
        data = path.read_bytes()
        normalized = reporting.normalize_converted_native_json(data, expected)
        import pyperf
        with path.open("r", encoding="utf-8") as stream:
            suite = pyperf.BenchmarkSuite.load(stream)
        results = [
            reporting.PyPerformanceResult(item.get_name(), tuple(item.get_values()))
            for item in suite.get_benchmarks()
        ]
        reporting.validate_results(results, expected)
        api_normalized = reporting.sanitized_native_json([
            (result.benchmark_name, list(result.samples_seconds)) for result in results
        ])
        if api_normalized != normalized:
            raise PyPerformanceValidationError("pyperf_api_report_mismatch")
        reporting.validate_native_json(api_normalized, expected)
    except reporting.ReportValidationError as exc:
        raise PyPerformanceValidationError(str(exc)) from None
    except (ImportError, KeyError, OSError, UnicodeError, ValueError, TypeError):
        raise PyPerformanceValidationError("invalid_pyperf_results") from None
    return api_normalized, results


def _safe_output_dir(output_dir: pathlib.Path) -> pathlib.Path:
    output_dir = pathlib.Path(output_dir)
    if output_dir.exists() and output_dir.is_symlink():
        raise PyPerformanceValidationError("invalid_output_destination")
    resolved = output_dir.resolve(strict=False)
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if (resolved == ROOT or ROOT in resolved.parents
            or (resolved != temp_root and temp_root not in resolved.parents)):
        raise PyPerformanceValidationError("temporary_output_required")
    return resolved


def run(mode: str, benchmark_selection: str | None, source_archive: pathlib.Path,
        wheelhouse: pathlib.Path, output_dir: pathlib.Path,
        overwrite: bool = False) -> tuple[pathlib.Path, ...]:
    config = MeasurementConfig.for_mode(mode)
    benchmarks = validate_benchmark_selection(benchmark_selection, mode)
    require_runtime_toolchain()
    validate_source_lock()
    source_sha = engine.source_revision()
    source_archive = verify_source_archive(pathlib.Path(source_archive))
    validate_wheelhouse(pathlib.Path(wheelhouse))
    output_dir = _safe_output_dir(pathlib.Path(output_dir))
    reporting.preflight_destinations(output_dir, source_sha, mode, overwrite)
    expected = _expected_output_names(benchmarks)
    with tempfile.TemporaryDirectory(prefix="devobs-pyperf-", dir=tempfile.gettempdir()) as temporary:
        work_dir = pathlib.Path(temporary)
        wheels = work_dir / "wheelhouse"
        wheels.mkdir()
        for wheel in pathlib.Path(wheelhouse).iterdir():
            shutil.copyfile(wheel, wheels / wheel.name)
        validate_wheelhouse(wheels)
        archive_copy = work_dir / "pinned-pyperformance.tar.gz"
        shutil.copyfile(source_archive, archive_copy)
        verify_source_archive(archive_copy)
        source_root = extract_verified_source(archive_copy, work_dir / "verified-source")
        raw = work_dir / "raw-pyperf.json"
        converted = work_dir / "converted-pyperf.json"
        sanitized = work_dir / "sanitized-pyperf.json"
        env = build_child_environment(work_dir, wheels, source_root)
        command = pyperformance_command(sys.executable, source_root, benchmarks, mode, raw)
        try:
            engine.run_bounded_command(command, config.suite_timeout_seconds, env=env, cwd=work_dir)
            engine.run_bounded_command(
                [sys.executable, "-m", "pyperf", "convert", "--remove-all-metadata",
                 str(raw), "-o", str(converted)], 60, env=env, cwd=work_dir,
            )
            native, results = _load_results(converted, expected)
            sanitized.write_bytes(native)
            engine.run_bounded_command(
                [sys.executable, "-m", "pyperf", "check", str(sanitized)], 30, env=env, cwd=work_dir,
            )
        except engine.BenchmarkExecutionError as exc:
            raise PyPerformanceExecutionError(str(exc)) from None
        metadata = engine.safe_metadata(source_sha, mode)
        summary = reporting.build_summary(
            results,
            source_sha=source_sha,
            suite_source_sha=PY_PERFORMANCE_COMMIT,
            python_version=metadata["python_version"],
            platform=metadata["platform"],
            architecture=metadata["architecture"],
            measurement_mode=mode,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        return reporting.write_reports(summary, native, output_dir, overwrite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run", help="run only reviewed offline pyperformance workloads")
    run_parser.add_argument("--mode", choices=("smoke", "statistical"), default="smoke")
    run_parser.add_argument("--benchmark", help="comma-separated reviewed benchmark names")
    run_parser.add_argument("--source-archive", type=pathlib.Path, required=True)
    run_parser.add_argument("--wheelhouse", type=pathlib.Path, required=True)
    run_parser.add_argument("--output-dir", type=pathlib.Path,
                            default=pathlib.Path(tempfile.gettempdir()) / "devobs-pyperformance")
    run_parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        outputs = run(args.mode, args.benchmark, args.source_archive, args.wheelhouse,
                      args.output_dir, args.overwrite)
    except (PyPerformanceValidationError, PyPerformanceExecutionError,
            reporting.ReportWriteError, engine.BenchmarkValidationError,
            engine.BenchmarkExecutionError, OSError, ValueError):
        print("pyperformance integration failed closed; inspect local setup and pinned offline artifacts.", file=sys.stderr)
        return 2
    except Exception:
        print("pyperformance integration failed closed; internal_error.", file=sys.stderr)
        return 2
    for path in outputs:
        print(f"Wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

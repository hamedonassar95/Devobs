"""Export one validated local performance report to Node Exporter's textfile collector."""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import tempfile

from . import comparison, pyperformance_reporting, reporting, resource_reporting

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_DESTINATION = ROOT / "monitoring" / "performance-metrics" / "devobs_performance.prom"
MAX_INPUT_BYTES = 5 * 1024 * 1024


class PrometheusExportError(ValueError):
    """Fixed error for invalid reports or local textfile destinations."""


def _number(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PrometheusExportError("invalid_metric_value")
    return format(float(value), ".17g")


def _label(**values: str) -> str:
    # All label values are validated from strict report schemas below. Keep this
    # escaping anyway so the exposition remains valid if a future schema grows.
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    return "{" + ",".join(f'{key}="{escape(value)}"' for key, value in values.items()) + "}"


def render_metrics(report: object) -> str:
    if type(report) is not dict:
        raise PrometheusExportError("invalid_report")
    try:
        if "comparison_kind" in report:
            comparison.validate_comparison(report)
            lines = [
                "# HELP devobs_benchmark_change_percent Candidate mean change from baseline; positive means slower or more memory.",
                "# TYPE devobs_benchmark_change_percent gauge",
                "# HELP devobs_benchmark_adjusted_p_value Holm-adjusted two-sided Welch test p-value.",
                "# TYPE devobs_benchmark_adjusted_p_value gauge",
            ]
            for row in report["benchmarks"]:
                labels = _label(
                    benchmark_id=row["benchmark_id"], metric=report["metric"],
                    comparison_kind=report["comparison_kind"],
                    baseline_sha=report["baseline"]["source_sha"],
                    candidate_sha=report["candidate"]["source_sha"],
                    python_baseline=report["baseline"]["python_version"],
                    python_candidate=report["candidate"]["python_version"],
                )
                lines.append(f"devobs_benchmark_change_percent{labels} {_number(row['delta_percent'])}")
                lines.append(f"devobs_benchmark_adjusted_p_value{labels} {_number(row['adjusted_p_value'])}")
            return "\n".join(lines) + "\n"

        if report.get("metric") == resource_reporting.METRIC:
            resource_reporting.validate_summary(report)
            suite = report["suite_name"]
            metric_name = "devobs_benchmark_peak_private_bytes_mean"
            value_key = "mean_bytes"
            metric_comment = "Mean sampled peak private bytes for one local statistical or smoke run."
        elif report.get("suite_name") == "pyperformance":
            pyperformance_reporting.validate_summary(report)
            suite = "pyperformance"
            metric_name = "devobs_benchmark_mean_seconds"
            value_key = "mean_seconds"
            metric_comment = "Mean execution time in seconds for one local pyperformance run."
        else:
            reporting.validate_summary(report)
            suite = "devobs"
            metric_name = "devobs_benchmark_mean_seconds"
            value_key = "mean_seconds"
            metric_comment = "Mean execution time in seconds for one local Devobs benchmark run."
    except (comparison.ComparisonValidationError, reporting.ReportValidationError,
            pyperformance_reporting.ReportValidationError,
            resource_reporting.ResourceReportError, TypeError, KeyError):
        raise PrometheusExportError("invalid_report") from None

    lines = [f"# HELP {metric_name} {metric_comment}", f"# TYPE {metric_name} gauge"]
    for row in report["benchmarks"]:
        labels = _label(
            suite=suite, benchmark_id=row["benchmark_id"], source_sha=report["source_sha"],
            python_version=report["python_version"], measurement_mode=report["measurement_mode"],
        )
        lines.append(f"{metric_name}{labels} {_number(row[value_key])}")
    return "\n".join(lines) + "\n"


def load_report(path: pathlib.Path) -> dict[str, object]:
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise PrometheusExportError("invalid_report_path")
    try:
        report = json.loads(path.read_bytes())
    except (OSError, UnicodeError, ValueError, TypeError):
        raise PrometheusExportError("invalid_report") from None
    # Rendering performs the authoritative schema validation.
    render_metrics(report)
    return report


def write_metrics(metrics: str, destination: pathlib.Path,
                  overwrite: bool = False) -> pathlib.Path:
    if (type(metrics) is not str or not metrics.endswith("\n") or len(metrics) > 1_000_000
            or type(overwrite) is not bool):
        raise PrometheusExportError("invalid_metrics_text")
    destination = pathlib.Path(destination)
    if (destination.is_symlink() or destination.parent.is_symlink()
            or (destination.exists() and not destination.is_file())):
        raise PrometheusExportError("invalid_destination")
    if destination.exists() and not overwrite:
        raise PrometheusExportError("destination_exists")
    temporary: pathlib.Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".devobs-performance-", dir=destination.parent)
        temporary = pathlib.Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(metrics.encode("utf-8"))
            stream.flush()
            if hasattr(os, "fchmod"):
                os.fchmod(stream.fileno(), 0o644)
            else:  # Windows exposes chmod by path rather than file descriptor.
                os.chmod(temporary, 0o644)
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
            temporary.unlink()
        return destination
    except FileExistsError:
        raise PrometheusExportError("destination_exists") from None
    except OSError:
        raise PrometheusExportError("metrics_write_failed") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = load_report(args.report)
        destination = write_metrics(render_metrics(report), DEFAULT_DESTINATION, args.overwrite)
    except (PrometheusExportError, OSError, ValueError):
        print("Prometheus export failed closed; check the report and local collector directory.", file=sys.stderr)
        return 2
    print(f"Wrote {destination.name}; local Node Exporter textfile collection is opt-in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

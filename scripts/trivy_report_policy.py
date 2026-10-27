#!/usr/bin/env python3
"""Apply Devobs' fail-closed policy to a Trivy container image JSON report."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
BLOCKING_SEVERITIES = ("CRITICAL", "HIGH")
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
EXPECTED_IMAGE_PATTERN = re.compile(r"devobs-web:[0-9a-f]{40}\Z")


class InvalidReport(ValueError):
    """Raised when the Trivy JSON does not match its expected report shape."""


def evaluate_report(report: Any, expected_image: str) -> tuple[bool, dict[str, int]]:
    """Validate the exact expected local image report and return severity counts."""
    if (not isinstance(expected_image, str)
            or not EXPECTED_IMAGE_PATTERN.fullmatch(expected_image)
            or not isinstance(report, dict)
            or report.get("ArtifactType") != "container_image"
            or report.get("ArtifactName") != expected_image):
        raise InvalidReport

    results = report.get("Results")
    if not isinstance(results, list) or not results:
        raise InvalidReport

    counts = {severity: 0 for severity in SEVERITIES}
    for result in results:
        if not isinstance(result, dict):
            raise InvalidReport
        target = result.get("Target")
        if not isinstance(target, str) or not target.strip():
            raise InvalidReport
        vulnerabilities = result.get("Vulnerabilities")
        if vulnerabilities is None:
            continue
        if not isinstance(vulnerabilities, list):
            raise InvalidReport
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                raise InvalidReport
            severity = vulnerability.get("Severity")
            if not isinstance(severity, str) or severity not in counts:
                raise InvalidReport
            counts[severity] += 1

    passed = not any(counts[severity] for severity in BLOCKING_SEVERITIES)
    return passed, counts


def _read_report(report_path: Path) -> Any:
    try:
        raw_report = report_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InvalidReport from exc
    try:
        return json.loads(raw_report)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidReport from exc


def _write_summary(summary_path: Path, passed: bool, counts: dict[str, int], revision: str) -> None:
    status = "PASS" if passed else "FAIL"
    lines = [
        f"## Container image vulnerability scan: {status}",
        "",
        f"Checked out revision: `{revision[:12]}`",
        "",
        "| Severity | Findings |",
        "|---|---:|",
    ]
    lines.extend(f"| {severity} | {counts[severity]} |" for severity in SEVERITIES)
    lines.append("")
    try:
        with summary_path.open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines))
    except OSError as exc:
        raise OSError("unable to write GitHub Actions summary") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path, help="Trivy JSON report path")
    parser.add_argument("--summary", type=Path, default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument("--revision", required=True, help="Full checked-out 40-character Git SHA")
    parser.add_argument(
        "--expected-image", required=True,
        help="Exact local image identity devobs-web:<full checked-out Git SHA>",
    )
    args = parser.parse_args(argv)

    if not isinstance(args.summary, Path):
        print("ERROR: GitHub Actions summary path is required", file=sys.stderr)
        return 2
    if not REVISION_PATTERN.fullmatch(args.revision):
        print("ERROR: invalid checked-out revision", file=sys.stderr)
        return 2

    try:
        report = _read_report(args.report)
        passed, counts = evaluate_report(report, args.expected_image)
    except InvalidReport:
        print("ERROR: missing, malformed, or unsupported Trivy JSON report", file=sys.stderr)
        return 2

    try:
        _write_summary(args.summary, passed, counts, args.revision)
    except OSError:
        print("ERROR: could not write Trivy scan summary", file=sys.stderr)
        return 2

    status = "PASS" if passed else "FAIL"
    counts_text = " ".join(f"{severity}={counts[severity]}" for severity in SEVERITIES)
    print(f"{status}: {counts_text} revision={args.revision[:12]}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

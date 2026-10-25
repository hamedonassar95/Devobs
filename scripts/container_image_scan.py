#!/usr/bin/env python3
"""Run a fail-closed Trivy image scan and evaluate its JSON report."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BLOCKING = {"HIGH", "CRITICAL"}


def evaluate(report: dict[str, Any]) -> tuple[bool, dict[str, int]]:
    """Return gate result and severity counts; malformed reports fail closed."""
    if report.get("ArtifactType") != "container_image" or not isinstance(report.get("Results"), list):
        raise ValueError("Trivy JSON report is missing container image results")
    counts = {severity: 0 for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")}
    if not report["Results"]:
        raise ValueError("Trivy returned no scan results")
    for result in report["Results"]:
        if not isinstance(result, dict):
            raise ValueError("Trivy JSON report contains an invalid result")
        if result.get("Vulnerabilities") is None:
            continue
        for vuln in result["Vulnerabilities"]:
            if not isinstance(vuln, dict):
                raise ValueError("Trivy report contains an invalid vulnerability")
            severity = vuln.get("Severity")
            if severity not in counts:
                raise ValueError(f"Trivy returned an unexpected severity: {severity!r}")
            counts[severity] += 1
    return not any(counts[s] for s in BLOCKING), counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=os.getenv("IMAGE_TAG", ""))
    parser.add_argument("--report", type=Path, default=Path("trivy-image-report.json"))
    parser.add_argument("--summary", type=Path, default=Path(os.getenv("GITHUB_STEP_SUMMARY", "/dev/null")))
    parser.add_argument("--trivy", default="trivy")
    args = parser.parse_args()
    if not args.image.strip():
        print("NOT_CONFIGURED: no application image target is configured.")
        return 0
    if shutil.which(args.trivy) is None:
        print(f"ERROR: scanner executable not found: {args.trivy}", file=sys.stderr)
        return 2
    command = [args.trivy, "image", "--scanners", "vuln", "--severity", "CRITICAL,HIGH,MEDIUM,LOW", "--format", "json", "--exit-code", "0", "--ignore-unfixed=false", "--no-progress", "--output", str(args.report), args.image]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        print(f"ERROR: could not execute Trivy: {exc}", file=sys.stderr)
        return 2
    if result.returncode != 0:
        print(f"ERROR: Trivy failed ({result.returncode}): {result.stderr.strip()}", file=sys.stderr)
        return 2
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        passed, counts = evaluate(report)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: invalid or missing Trivy report: {exc}", file=sys.stderr)
        return 2
    status = "PASS" if passed else "FAIL"
    table = "| Severity | Findings |\n|---|---:|\n" + "".join(f"| {key} | {value} |\n" for key, value in counts.items())
    try:
        with args.summary.open("a", encoding="utf-8") as summary:
            summary.write(f"## Container image vulnerability scan: {status}\n\nImage: `{args.image}`\n\n{table}\n")
    except OSError as exc:
        print(f"ERROR: could not write scan summary: {exc}", file=sys.stderr)
        return 2
    print(f"{status}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

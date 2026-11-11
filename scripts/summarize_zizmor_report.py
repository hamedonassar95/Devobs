"""Validate a zizmor JSON report and render a bounded GitHub Actions summary."""

from __future__ import annotations

import argparse
import html
import json
import os
import pathlib
import re
import sys


MAX_REPORT_BYTES = 2_000_000
MAX_FINDINGS = 500
MAX_SUMMARY_FINDINGS = 80
SEVERITIES = ("High", "Medium", "Low", "Informational")
CONFIDENCES = {"High", "Medium", "Low"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


class InvalidReport(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("invalid JSON numeric constant")


def _escape_cell(value: str, max_length: int = 300) -> str:
    normalized = " ".join(value.split())
    escaped = html.escape(normalized, quote=False)
    for char, replacement in (("|", "&#124;"), ("`", "&#96;"), ("[", "&#91;"), ("]", "&#93;")):
        escaped = escaped.replace(char, replacement)
    return escaped[:max_length] or "-"


def _location(finding: dict) -> tuple[str, int]:
    locations = finding.get("locations")
    if not isinstance(locations, list) or not locations:
        raise InvalidReport("finding must contain at least one source location")

    candidates = [
        location for location in locations
        if isinstance(location, dict)
        and isinstance(location.get("symbolic"), dict)
        and location["symbolic"].get("kind") == "Primary"
    ] or locations
    location = candidates[0]
    if not isinstance(location, dict):
        raise InvalidReport("finding source location must be an object")

    symbolic = location.get("symbolic")
    concrete = location.get("concrete")
    if not isinstance(symbolic, dict) or not isinstance(concrete, dict):
        raise InvalidReport("finding source location is incomplete")
    local_key = symbolic.get("key", {}).get("Local")
    if not isinstance(local_key, dict):
        raise InvalidReport("finding source must refer to a local workflow")
    source = local_key.get("verbatim_path")
    source_path = pathlib.PurePosixPath(source) if isinstance(source, str) else None
    if (source_path is None or source_path.is_absolute()
            or ".." in source_path.parts
            or source_path.parts[:2] != (".github", "workflows")):
        raise InvalidReport("finding source path is outside authored workflows")

    source_location = concrete.get("location", {})
    start_point = source_location.get("start_point", {}) if isinstance(source_location, dict) else {}
    row = start_point.get("row") if isinstance(start_point, dict) else None
    if type(row) is not int or row < 1:
        raise InvalidReport("finding source line is invalid")
    return source_path.as_posix(), row


def validate_report(report_path: pathlib.Path) -> list[dict]:
    try:
        report_bytes = report_path.read_bytes()
        if len(report_bytes) > MAX_REPORT_BYTES:
            raise InvalidReport("report exceeds the 2 MB limit")
        report = json.loads(
            report_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except InvalidReport:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise InvalidReport("report is unavailable or invalid JSON") from error

    if not isinstance(report, list) or len(report) > MAX_FINDINGS:
        raise InvalidReport("report must be an array of at most 500 findings")

    findings = []
    for finding in report:
        if not isinstance(finding, dict):
            raise InvalidReport("finding must be an object")
        identifier = finding.get("ident")
        description = finding.get("desc")
        determinations = finding.get("determinations")
        ignored = finding.get("ignored")
        if (not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier)
                or not isinstance(description, str) or not description or len(description) > 1000
                or not isinstance(determinations, dict) or type(ignored) is not bool):
            raise InvalidReport("finding contains invalid identity, description, or status")
        severity = determinations.get("severity")
        confidence = determinations.get("confidence")
        if (not isinstance(severity, str) or severity not in SEVERITIES
                or not isinstance(confidence, str) or confidence not in CONFIDENCES):
            raise InvalidReport("finding severity or confidence is invalid")
        source, row = _location(finding)
        findings.append({
            "id": identifier,
            "description": description,
            "severity": severity,
            "confidence": confidence,
            "ignored": ignored,
            "source": source,
            "row": row,
        })
    return findings


def render_summary(findings: list[dict], repository: str, source_sha: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise InvalidReport("repository identity is invalid")
    if not SHA.fullmatch(source_sha):
        raise InvalidReport("source SHA is invalid")

    active = [finding for finding in findings if not finding["ignored"]]
    counts = {severity: sum(f["severity"] == severity for f in active) for severity in SEVERITIES}
    lines = [
        "## Zizmor workflow security report",
        "",
        f"Repository: `{_escape_cell(repository)}`",
        f"Source SHA: `{source_sha}`",
        "Scope: hand-authored workflow files only; generated `.lock.yml` files are excluded.",
        "Execution: offline static analysis; no GitHub token, network audits, or repository writes are used.",
        "",
        f"Unsuppressed findings: **{len(active)}** · ignored findings: **{len(findings) - len(active)}**",
        "This manually dispatched report is informational and does not block merges. A completed report means the scanner ran; it does not mean the workflows are risk-free.",
        "",
        "| Severity | Findings |",
        "| --- | ---: |",
    ]
    for severity in SEVERITIES:
        lines.append(f"| {severity} | {counts[severity]} |")
    lines.extend([
        "",
        "| Severity | Confidence | Audit | Location | Description |",
        "| --- | --- | --- | --- | --- |",
    ])

    shown = sorted(
        active,
        key=lambda finding: (SEVERITIES.index(finding["severity"]), finding["source"], finding["row"], finding["id"]),
    )[:MAX_SUMMARY_FINDINGS]
    for finding in shown:
        location = f"{finding['source']}:{finding['row']}"
        lines.append(
            f"| {finding['severity']} | {finding['confidence']} | "
            f"[`{_escape_cell(finding['id'])}`](https://docs.zizmor.sh/audits/#{finding['id']}) | "
            f"`{_escape_cell(location)}` | {_escape_cell(finding['description'])} |"
        )
    if len(active) > len(shown):
        lines.extend(["", f"Only the first {len(shown)} of {len(active)} findings are displayed."])
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        findings = validate_report(args.report)
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        source_sha = os.environ.get("GITHUB_SHA", "")
        summary_value = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_value:
            raise InvalidReport("GitHub Actions summary path is missing")
        summary_path = pathlib.Path(summary_value)
        summary = render_summary(findings, repository, source_sha)
        with summary_path.open("a", encoding="utf-8") as destination:
            destination.write(summary)
    except (InvalidReport, OSError) as error:
        print(f"zizmor report validation failed: {error}", file=sys.stderr)
        return 1
    print(f"zizmor report rendered: {sum(not item['ignored'] for item in findings)} unsuppressed findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

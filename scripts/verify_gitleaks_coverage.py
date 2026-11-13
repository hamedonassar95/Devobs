#!/usr/bin/env python3
"""Run the pinned Gitleaks CLI over an event-bound Git revision range.

The scanner's raw output and report are kept in a temporary directory. Only
validated revision metadata and counts are written to the Actions summary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
# Calls below use separate argv entries and never enable shell parsing.
import subprocess  # nosec B404
import sys
import tempfile


EXPECTED_GITLEAKS_VERSION = "8.24.3"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ZERO_SHA = "0" * 40
SCAN_COUNT_RE = re.compile(r"\b([0-9]+)\s+commits scanned\.")
MAX_EVENT_BYTES = 16 * 1024 * 1024
MAX_REPORT_BYTES = 20 * 1024 * 1024
SCAN_TIMEOUT_SECONDS = 8 * 60
GIT_EXECUTABLE = "/usr/bin/git"


class CoverageFailure(ValueError):
    """A scope, scan, or scanner-output condition that must fail closed."""


class ScanFailure(CoverageFailure):
    """A completed scan that failed policy but has safe aggregate evidence."""

    def __init__(self, message: str, scan_count: int, finding_count: int) -> None:
        super().__init__(message)
        self.scan_count = scan_count
        self.finding_count = finding_count


@dataclass(frozen=True)
class ScanScope:
    event_name: str
    checkout_sha: str
    source_sha: str
    revision: str
    log_opts: str
    commits: tuple[str, ...]
    base_sha: str | None = None
    head_sha: str | None = None
    pr_head_sha: str | None = None

    @property
    def digest(self) -> str:
        return hashlib.sha256(("\n".join(self.commits) + "\n").encode()).hexdigest()


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        # Arguments are fixed Git flags and validated revision values.
        result = subprocess.run(  # nosec B603
            [GIT_EXECUTABLE, "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoverageFailure("git history verification failed") from exc
    if result.returncode != 0:
        raise CoverageFailure("git history verification failed")
    return result


def _is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    try:
        # Both arguments are validated full Git SHAs.
        result = subprocess.run(  # nosec B603
            [GIT_EXECUTABLE, "-C", str(repository), "merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoverageFailure("GitHub event revisions are not verifiable in checkout") from exc
    if result.returncode not in (0, 1):
        raise CoverageFailure("GitHub event revisions are not verifiable in checkout")
    return result.returncode == 0


def _commit_list(repository: Path, revision: str) -> tuple[str, ...]:
    output = _git(repository, "rev-list", "--topo-order", "--reverse", revision).stdout
    commits = tuple(line for line in output.splitlines() if line)
    if not commits or any(not _valid_sha(commit) for commit in commits):
        raise CoverageFailure("the required Git revision range is empty or invalid")
    return commits


def load_event(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            raise CoverageFailure("GitHub event metadata exceeds the size limit")
        event = json.loads(raw.decode("utf-8"))
    except CoverageFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CoverageFailure("GitHub event metadata is missing or malformed") from exc
    if not isinstance(event, dict):
        raise CoverageFailure("GitHub event metadata is missing or malformed")
    return event


def derive_scope(event_name: str, event: dict, source_sha: str, repository: Path) -> ScanScope | None:
    """Resolve the exact event revision range and verify it exists in checkout.

    A deleted push ref has no source revision and is the only supported event
    for which a scan is explicitly not required.
    """
    if event_name not in {"push", "pull_request", "workflow_dispatch", "workflow_call"}:
        raise CoverageFailure("unsupported GitHub event for required secret scanning")

    if event_name == "push" and event.get("deleted") is True:
        return None

    if not _valid_sha(source_sha):
        raise CoverageFailure("selected source revision is not a full Git SHA")
    checkout_sha = _git(repository, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    if not _valid_sha(checkout_sha) or checkout_sha != source_sha:
        raise CoverageFailure("checked-out revision does not match the selected source revision")

    if event_name == "push":
        before = event.get("before")
        after = event.get("after")
        if not _valid_sha(after) or after != source_sha:
            raise CoverageFailure("push after revision does not match the checked-out source")
        if before == ZERO_SHA:
            revision = after
            base_sha = None
        elif _valid_sha(before):
            revision = f"{before}..{after}"
            base_sha = before
        else:
            raise CoverageFailure("push before revision is missing or invalid")
        head_sha = after
        pr_head_sha = None

    elif event_name == "pull_request":
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise CoverageFailure("pull request base and head revisions are missing")
        base = pull_request.get("base")
        head = pull_request.get("head")
        base_sha = base.get("sha") if isinstance(base, dict) else None
        head_sha = head.get("sha") if isinstance(head, dict) else None
        if not _valid_sha(base_sha) or not _valid_sha(head_sha):
            raise CoverageFailure("pull request base and head revisions are invalid")
        base_in_checkout = _is_ancestor(repository, base_sha, checkout_sha)
        head_in_checkout = _is_ancestor(repository, head_sha, checkout_sha)
        if not base_in_checkout or not head_in_checkout:
            raise CoverageFailure("pull request revisions are not ancestors of the checked-out merge revision")
        # GITHUB_SHA for pull_request is the synthetic merge revision. Include
        # that merge result as well as the PR head so merge-resolution changes
        # cannot fall outside the scan scope.
        pr_head_sha = head_sha
        head_sha = checkout_sha
        revision = f"{base_sha}..{checkout_sha}"

    else:
        # Manual and reusable-workflow invocations scan the full history
        # reachable from their exact checked-out source revision.
        base_sha = None
        head_sha = source_sha
        pr_head_sha = None
        revision = source_sha

    commits = _commit_list(repository, revision)
    # Gitleaks' git command consumes this exact argument string. -m asks Git
    # to expose each merge commit's parent diffs instead of silently dropping
    # merge patches, as happened with the pinned action's default -1 range.
    log_opts = f"-m {revision}"
    return ScanScope(
        event_name=event_name,
        checkout_sha=checkout_sha,
        source_sha=source_sha,
        revision=revision,
        log_opts=log_opts,
        commits=commits,
        base_sha=base_sha,
        head_sha=head_sha,
        pr_head_sha=pr_head_sha,
    )


def _scan_count(log_path: Path) -> int:
    matches: list[int] = []
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                match = SCAN_COUNT_RE.search(line)
                if match:
                    matches.append(int(match.group(1)))
    except OSError as exc:
        raise CoverageFailure("scanner completion evidence is missing") from exc
    if len(matches) != 1:
        raise CoverageFailure("scanner completion evidence is missing or ambiguous")
    return matches[0]


def _read_report(report_path: Path) -> list[dict]:
    try:
        if report_path.stat().st_size > MAX_REPORT_BYTES:
            raise CoverageFailure("scanner report exceeds the size limit")
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except CoverageFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CoverageFailure("scanner report is missing or malformed") from exc
    if not isinstance(report, list) or any(not isinstance(row, dict) for row in report):
        raise CoverageFailure("scanner report has an unexpected format")
    required_fields = ("RuleID", "File", "Commit", "Secret")
    if any(any(not isinstance(row.get(field), str) for field in required_fields) for row in report):
        raise CoverageFailure("scanner report has an unexpected format")
    return report


def _verify_scanner_version(gitleaks_bin: str) -> None:
    if not gitleaks_bin:
        raise CoverageFailure("pinned Gitleaks CLI path is missing")
    try:
        # The installer verifies this executable's SHA-256 and version.
        result = subprocess.run(  # nosec B603
            [gitleaks_bin, "version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoverageFailure("pinned Gitleaks CLI could not be verified") from exc
    version_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    accepted = ([EXPECTED_GITLEAKS_VERSION], [f"v{EXPECTED_GITLEAKS_VERSION}"])
    if result.returncode != 0 or version_lines not in accepted:
        raise CoverageFailure("Gitleaks executable does not match the pinned version")


def _summary(scope: ScanScope | None, status: str, *, scan_count: int | None = None,
             finding_count: int | None = None, reason: str | None = None) -> str:
    lines = ["## Gitleaks revision coverage", "", f"- Status: **{status}**"]
    if scope is None:
        lines.append("- Scope: no scan required because the push deleted its ref.")
    else:
        lines.extend([
            f"- Event: `{scope.event_name}`",
            f"- Checked-out SHA: `{scope.checkout_sha}`",
            f"- Selected source SHA: `{scope.source_sha}`",
            f"- Git range passed to Gitleaks: `{scope.log_opts}`",
            f"- Commits in selected Git history: {len(scope.commits)}",
            f"- Selected commit-list SHA-256: `{scope.digest}`",
        ])
        if scope.base_sha:
            lines.append(f"- Base SHA: `{scope.base_sha}`")
        if scope.head_sha:
            lines.append(f"- Range head SHA: `{scope.head_sha}`")
        if scope.pr_head_sha:
            lines.append(f"- Pull request source head SHA: `{scope.pr_head_sha}`")
        if scan_count is not None:
            lines.append(f"- Gitleaks-reported commits scanned: {scan_count}")
        if finding_count is not None:
            lines.append(f"- Finding count: {finding_count}; finding contents and locations are suppressed.")
        if scan_count is not None:
            lines.append(
                "- Gitleaks counts commits with scan-eligible additions; this may be lower "
                "than the selected Git history."
            )
    if reason:
        lines.append(f"- Failure: {reason}")
    lines.extend([
        "",
        "Gitleaks raw output and JSON report are not written to job logs or uploaded as artifacts.",
        "",
    ])
    return "\n".join(lines)


def _write_summary(path: Path | None, content: str) -> None:
    if path is None:
        return
    try:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(content)
    except OSError as exc:
        raise CoverageFailure("GitHub Actions job summary could not be written") from exc


def run_scan(scope: ScanScope, repository: Path, gitleaks_bin: str) -> tuple[int, int]:
    """Run exactly one pinned CLI scan and return (scanned commits, findings)."""
    if not gitleaks_bin:
        raise CoverageFailure("pinned Gitleaks CLI path is missing")
    with tempfile.TemporaryDirectory(prefix="devobs-gitleaks-") as temporary:
        temporary_path = Path(temporary)
        report_path = temporary_path / "report.json"
        log_path = temporary_path / "scanner.log"
        command = [
            gitleaks_bin,
            "git",
            "--redact",
            "--exit-code=2",
            "--report-format=json",
            f"--report-path={report_path}",
            "--log-level=info",
            f"--log-opts={scope.log_opts}",
            str(repository),
        ]
        try:
            with log_path.open("wb") as output:
                # The executable was installed from the verified release.
                result = subprocess.run(  # nosec B603
                    command,
                    cwd=repository,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=SCAN_TIMEOUT_SECONDS,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CoverageFailure("pinned Gitleaks scanner could not complete") from exc

        scan_count = _scan_count(log_path)
        findings = _read_report(report_path)
        if scan_count > len(scope.commits):
            raise ScanFailure("scanner count exceeds the selected revision history", scan_count, len(findings))
        if result.returncode != 0:
            if findings:
                raise ScanFailure(
                    f"Gitleaks reported {len(findings)} finding(s); contents are suppressed",
                    scan_count,
                    len(findings),
                )
            raise ScanFailure("Gitleaks scanner returned a nonzero status without findings", scan_count, len(findings))
        if findings:
            raise ScanFailure("Gitleaks returned success with a nonempty report", scan_count, len(findings))
        return scan_count, len(findings)


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    scope: ScanScope | None = None
    try:
        if summary_path is None:
            raise CoverageFailure("GitHub Actions job summary path is missing")
        version = os.environ.get("GITLEAKS_VERSION", "")
        if version != EXPECTED_GITLEAKS_VERSION:
            raise CoverageFailure("Gitleaks version does not match the pinned version")
        event_path_value = os.environ.get("GITHUB_EVENT_PATH", "")
        if not event_path_value:
            raise CoverageFailure("GitHub event metadata path is missing")
        event_path = Path(event_path_value)
        event = load_event(event_path)
        repository = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd())).resolve()
        source_sha = os.environ.get("GITLEAKS_SOURCE_SHA", "")
        scope = derive_scope(event_name, event, source_sha, repository)
        if scope is None:
            _write_summary(summary_path, _summary(None, "NOT_REQUIRED"))
            print("Gitleaks scan not required for a deleted push ref; coverage noted in job summary.")
            return 0
        gitleaks_bin = os.environ.get("GITLEAKS_BIN", "")
        _verify_scanner_version(gitleaks_bin)
        scanned, findings = run_scan(scope, repository, gitleaks_bin)
        _write_summary(summary_path, _summary(scope, "PASS", scan_count=scanned, finding_count=findings))
        print(f"Gitleaks coverage verified: {scanned} commit(s) scanned in the selected history.")
        return 0
    except ScanFailure as exc:
        reason = str(exc)
        _write_summary(
            summary_path,
            _summary(
                scope,
                "FAIL",
                scan_count=exc.scan_count,
                finding_count=exc.finding_count,
                reason=reason,
            ),
        )
        print(f"Gitleaks coverage verification failed: {reason}", file=sys.stderr)
        return 1
    except CoverageFailure as exc:
        # Error strings are intentionally fixed/sanitized; never echo scanner,
        # event-payload, report, file-path, or finding contents.
        reason = str(exc)
        _write_summary(summary_path, _summary(scope, "FAIL", reason=reason))
        print(f"Gitleaks coverage verification failed: {reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Behavioral coverage tests for the fail-closed Gitleaks CI wrapper."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
SECURITY_JOB = WORKFLOW.split("\n  security:\n", 1)[1].split("\n  site-contract:\n", 1)[0]
SPEC = importlib.util.spec_from_file_location(
    "verify_gitleaks_coverage", ROOT / "scripts" / "verify_gitleaks_coverage.py"
)
coverage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = coverage
SPEC.loader.exec_module(coverage)


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class GitleaksCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repo"
        self.repository.mkdir()
        git(self.repository, "init", "--initial-branch=main")
        git(self.repository, "config", "user.name", "Synthetic Test")
        git(self.repository, "config", "user.email", "synthetic@example.invalid")
        (self.repository / "base.txt").write_text("base line\n", encoding="utf-8")
        git(self.repository, "add", "base.txt")
        git(self.repository, "commit", "-m", "base")
        self.base = git(self.repository, "rev-parse", "HEAD")
        self.fake_scanner = self.root / "gitleaks-fixture"
        self.record_path = self.root / "scanner-invocation.json"
        self._write_fake_scanner()
        self.event_path = self.root / "event.json"
        self.summary_path = self.root / "summary.md"

    def tearDown(self):
        self.temporary.cleanup()

    def _write_fake_scanner(self):
        self.fake_scanner.write_text(
            """#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
report = next((arg.split('=', 1)[1] for arg in args if arg.startswith('--report-path=')), None)
log_opts = next((arg.split('=', 1)[1] for arg in args if arg.startswith('--log-opts=')), '')
if args == ['version']:
    print(os.environ.get('GITLEAKS_FAKE_VERSION', '8.24.3'))
    raise SystemExit(0)
if os.environ.get('GITLEAKS_TEST_RECORD'):
    with open(os.environ['GITLEAKS_TEST_RECORD'], 'w', encoding='utf-8') as stream:
        json.dump({'args': args, 'log_opts': log_opts}, stream)
mode = os.environ.get('GITLEAKS_TEST_MODE', 'valid')
if mode == 'missing-count':
    if report: open(report, 'w', encoding='utf-8').write('[]')
    print('scan completed')
    raise SystemExit(0)
if mode == 'missing-report':
    print('1 commits scanned.')
    raise SystemExit(0)
if mode == 'malformed-report':
    if report: open(report, 'w', encoding='utf-8').write('{')
    print('1 commits scanned.')
    raise SystemExit(0)
if mode == 'malformed-row':
    if report: open(report, 'w', encoding='utf-8').write('[{}]')
    print('1 commits scanned.')
    raise SystemExit(0)
if mode == 'zero-count':
    if report: open(report, 'w', encoding='utf-8').write('[]')
    print('0 commits scanned.')
    raise SystemExit(0)
if mode == 'scanner-failure':
    if report:
        with open(report, 'w', encoding='utf-8') as stream:
            json.dump([{
                'RuleID': 'synthetic', 'File': 'synthetic.txt', 'Commit': 'a' * 40,
                'Secret': 'SYNTHETIC_CANARY_NOT_A_CREDENTIAL'
            }], stream)
    print('SYNTHETIC_CANARY_NOT_A_CREDENTIAL')
    print('1 commits scanned.')
    raise SystemExit(2)
parts = log_opts.split()
if parts and parts[0] == '-m':
    parts = parts[1:]
count = int(subprocess.check_output(['git', 'rev-list', '--topo-order', '--reverse', *parts], text=True).count('\\n'))
if report: open(report, 'w', encoding='utf-8').write('[]')
print(f'{count} commits scanned.')
""",
            encoding="utf-8",
        )
        self.fake_scanner.chmod(0o755)

    def _run(self, event_name: str, event: dict, checkout_sha: str, *, mode: str = "valid"):
        self.event_path.write_text(json.dumps(event), encoding="utf-8")
        environment = {
            "GITHUB_EVENT_NAME": event_name,
            "GITHUB_EVENT_PATH": str(self.event_path),
            "GITHUB_SHA": checkout_sha,
            "GITHUB_STEP_SUMMARY": str(self.summary_path),
            "GITHUB_WORKSPACE": str(self.repository),
            "GITLEAKS_SOURCE_SHA": checkout_sha,
            "GITLEAKS_BIN": str(self.fake_scanner),
            "GITLEAKS_VERSION": coverage.EXPECTED_GITLEAKS_VERSION,
            "GITLEAKS_TEST_MODE": mode,
            "GITLEAKS_TEST_RECORD": str(self.record_path),
        }
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment, clear=True):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = coverage.main()
        return code, stdout.getvalue(), stderr.getvalue(), self.summary_path.read_text(encoding="utf-8")

    def _new_commit(self, name: str, body: str | None = None) -> str:
        (self.repository / name).write_text(body or f"synthetic content for {name}\n", encoding="utf-8")
        git(self.repository, "add", name)
        git(self.repository, "commit", "-m", f"add {name}")
        return git(self.repository, "rev-parse", "HEAD")

    def _merge_feature(self):
        git(self.repository, "checkout", "-b", "feature/synthetic")
        head = self._new_commit("feature.txt")
        git(self.repository, "checkout", "main")
        git(self.repository, "merge", "--no-ff", "feature/synthetic", "-m", "merge feature")
        merge = git(self.repository, "rev-parse", "HEAD")
        return head, merge

    def test_push_scans_exact_before_after_range_and_records_counts(self):
        after = self._new_commit("push.txt")
        event = {"before": self.base, "after": after, "ref": "refs/heads/main"}
        code, out, err, summary = self._run("push", event, after)

        self.assertEqual(code, 0, err)
        self.assertIn("1 commit(s) scanned", out)
        self.assertIn(f"Git range passed to Gitleaks: `-m {self.base}..{after}`", summary)
        self.assertIn("Gitleaks-reported commits scanned: 1", summary)
        self.assertIn("Finding count: 0", summary)
        invocation = json.loads(self.record_path.read_text(encoding="utf-8"))
        self.assertEqual(invocation["log_opts"], f"-m {self.base}..{after}")

    def test_push_merge_commit_scans_merge_parent_diffs_and_feature_history(self):
        feature_head, merge_sha = self._merge_feature()
        event = {"before": self.base, "after": merge_sha, "ref": "refs/heads/main"}
        code, _, err, summary = self._run("push", event, merge_sha)

        self.assertEqual(code, 0, err)
        self.assertIn(f"Git range passed to Gitleaks: `-m {self.base}..{merge_sha}`", summary)
        self.assertIn("Gitleaks-reported commits scanned: 2", summary)
        self.assertNotIn("SYNTHETIC_CANARY", summary)
        commits = git(
            self.repository,
            "rev-list",
            "--topo-order",
            "--reverse",
            f"{self.base}..{merge_sha}",
        ).splitlines()
        self.assertEqual(commits, [feature_head, merge_sha])

    def test_pull_request_scans_base_to_pr_head_inside_checked_out_merge(self):
        head_sha, merge_sha = self._merge_feature()
        event = {
            "pull_request": {
                "base": {"sha": self.base},
                "head": {"sha": head_sha},
            }
        }
        code, _, err, summary = self._run("pull_request", event, merge_sha)

        self.assertEqual(code, 0, err)
        self.assertIn(f"Selected source SHA: `{merge_sha}`", summary)
        self.assertIn(f"Range head SHA: `{merge_sha}`", summary)
        self.assertIn(f"Pull request source head SHA: `{head_sha}`", summary)
        self.assertIn(f"Git range passed to Gitleaks: `-m {self.base}..{merge_sha}`", summary)
        invocation = json.loads(self.record_path.read_text(encoding="utf-8"))
        self.assertEqual(invocation["log_opts"], f"-m {self.base}..{merge_sha}")

    def test_manual_dispatch_scans_full_history_at_exact_selected_sha(self):
        selected = self._new_commit("manual.txt")
        event = {"inputs": {}}
        code, _, err, summary = self._run("workflow_dispatch", event, selected)

        self.assertEqual(code, 0, err)
        self.assertIn(f"Git range passed to Gitleaks: `-m {selected}`", summary)
        self.assertIn("Commits in selected Git history: 2", summary)
        self.assertIn("Gitleaks-reported commits scanned: 2", summary)

    def test_empty_push_range_fails_before_invoking_scanner(self):
        event = {"before": self.base, "after": self.base, "ref": "refs/heads/main"}
        code, _, err, summary = self._run("push", event, self.base)

        self.assertEqual(code, 1)
        self.assertIn("Gitleaks coverage verification failed", err)
        self.assertIn("Status: **FAIL**", summary)
        self.assertFalse(self.record_path.exists())

    def test_missing_scan_count_evidence_fails_closed(self):
        after = self._new_commit("missing-count.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, after, mode="missing-count")

        self.assertEqual(code, 1)
        self.assertIn("scanner completion evidence", err)
        self.assertIn("Status: **FAIL**", summary)

    def test_missing_report_fails_closed(self):
        after = self._new_commit("missing-report.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, after, mode="missing-report")

        self.assertEqual(code, 1)
        self.assertIn("scanner report is missing or malformed", err)
        self.assertIn("Status: **FAIL**", summary)

    def test_malformed_report_fails_closed(self):
        after = self._new_commit("malformed-report.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, after, mode="malformed-report")

        self.assertEqual(code, 1)
        self.assertIn("scanner report is missing or malformed", err)
        self.assertIn("Status: **FAIL**", summary)

    def test_malformed_finding_record_fails_closed(self):
        after = self._new_commit("malformed-row.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, after, mode="malformed-row")

        self.assertEqual(code, 1)
        self.assertIn("scanner report has an unexpected format", err)
        self.assertIn("Status: **FAIL**", summary)

    def test_zero_addition_commit_count_is_reported_for_nonempty_verified_range(self):
        after = self._new_commit("zero-count.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, after, mode="zero-count")

        self.assertEqual(code, 0, err)
        self.assertIn("Commits in selected Git history: 1", summary)
        self.assertIn("Gitleaks-reported commits scanned: 0", summary)

    def test_scanner_version_mismatch_fails_before_scan(self):
        after = self._new_commit("version-mismatch.txt")
        event = {"before": self.base, "after": after}
        self.event_path.write_text(json.dumps(event), encoding="utf-8")
        environment = {
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": str(self.event_path),
            "GITHUB_STEP_SUMMARY": str(self.summary_path),
            "GITHUB_WORKSPACE": str(self.repository),
            "GITLEAKS_SOURCE_SHA": after,
            "GITLEAKS_BIN": str(self.fake_scanner),
            "GITLEAKS_VERSION": coverage.EXPECTED_GITLEAKS_VERSION,
            "GITLEAKS_FAKE_VERSION": "9.99.9",
            "GITLEAKS_TEST_RECORD": str(self.record_path),
        }
        with patch.dict(os.environ, environment, clear=True):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = coverage.main()

        self.assertEqual(code, 1)
        self.assertFalse(self.record_path.exists())
        self.assertIn("executable does not match the pinned version", self.summary_path.read_text())

    def test_ci_reuses_security_job_with_checksum_pinned_cli_and_no_token(self):
        self.assertIn("permissions:\n      contents: read", SECURITY_JOB)
        self.assertIn("security scan dependencies", SECURITY_JOB)
        self.assertIn("python3 -m bandit -r scripts", SECURITY_JOB)
        self.assertIn("pip-audit --requirement requirements-dev.lock", SECURITY_JOB)
        self.assertIn("gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz", SECURITY_JOB)
        self.assertIn("/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz", SECURITY_JOB)
        self.assertIn("9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c", SECURITY_JOB)
        self.assertIn("GITLEAKS_SOURCE_SHA: ${{ inputs.source_ref || github.sha }}", SECURITY_JOB)
        self.assertEqual(SECURITY_JOB.count("verify_gitleaks_coverage.py"), 1)
        self.assertNotIn("gitleaks/gitleaks-action", SECURITY_JOB)
        self.assertNotIn("secrets.GITHUB_TOKEN", SECURITY_JOB)

    def test_scan_must_match_the_checked_out_source_sha(self):
        after = self._new_commit("mismatch.txt")
        other = self._new_commit("checkout.txt")
        event = {"before": self.base, "after": after}
        code, _, err, summary = self._run("push", event, other)

        self.assertEqual(code, 1)
        self.assertIn("does not match the checked-out source", err)
        self.assertIn("Status: **FAIL**", summary)
        self.assertFalse(self.record_path.exists())

    def test_missing_actions_summary_path_fails_before_scan(self):
        after = self._new_commit("missing-summary.txt")
        event = {"before": self.base, "after": after}
        self.event_path.write_text(json.dumps(event), encoding="utf-8")
        environment = {
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": str(self.event_path),
            "GITHUB_WORKSPACE": str(self.repository),
            "GITLEAKS_SOURCE_SHA": after,
            "GITLEAKS_BIN": str(self.fake_scanner),
            "GITLEAKS_VERSION": coverage.EXPECTED_GITLEAKS_VERSION,
            "GITLEAKS_TEST_RECORD": str(self.record_path),
        }
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment, clear=True):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = coverage.main()

        self.assertEqual(code, 1)
        self.assertIn("job summary path is missing", stderr.getvalue())
        self.assertFalse(self.record_path.exists())

    def test_scanner_failure_suppresses_synthetic_finding_value(self):
        after = self._new_commit("scanner-failure.txt")
        event = {"before": self.base, "after": after}
        code, out, err, summary = self._run("push", event, after, mode="scanner-failure")

        self.assertEqual(code, 1)
        combined = out + err + summary
        self.assertIn("finding(s)", combined)
        self.assertIn("Gitleaks-reported commits scanned: 1", summary)
        self.assertIn("Finding count: 1", summary)
        self.assertNotIn("SYNTHETIC_CANARY_NOT_A_CREDENTIAL", combined)

    def test_push_with_zero_before_scans_selected_branch_history(self):
        after = self._new_commit("new-branch.txt")
        event = {"before": coverage.ZERO_SHA, "after": after, "ref": "refs/heads/new"}
        code, _, err, summary = self._run("push", event, after)

        self.assertEqual(code, 0, err)
        self.assertIn(f"Git range passed to Gitleaks: `-m {after}`", summary)
        self.assertIn("Commits in selected Git history: 2", summary)


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the read-only worktree coordination inspector."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from devobs.coordination import worktree_inspector as wi


def git(directory, *args, env=None):
    result = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True,
        check=True, env=env,
    )
    return result.stdout.strip()


class InspectorContractTests(unittest.TestCase):
    def test_parse_worktrees_fails_closed_on_unknown_metadata(self):
        with self.assertRaises(wi.InspectorError):
            wi.parse_worktrees("worktree /tmp/a\nHEAD abcdef1\nbranch refs/heads/main\nmystery x\n")

    def test_parse_worktrees_fails_closed_on_incomplete_metadata(self):
        with self.assertRaises(wi.InspectorError):
            wi.parse_worktrees("worktree /tmp/a\nHEAD not-a-sha\nbranch refs/heads/main\n")

    def test_parse_status_rejects_unsafe_path(self):
        with self.assertRaises(wi.InspectorError):
            wi.parse_status("?? ../secret.txt\n")

    def test_parse_status_accepts_untracked_directory(self):
        self.assertEqual(
            wi.parse_status("?? generated/\n"),
            [{"status": "??", "path": "generated"}],
        )

    def test_parse_status_rejects_root_path(self):
        with self.assertRaises(wi.InspectorError):
            wi.parse_status("?? /\n")

    def test_parse_status_handles_rename_without_file_contents(self):
        self.assertEqual(
            wi.parse_status("R  old.py -> new.py\n"),
            [{"status": "R", "path": "new.py"}],
        )

    def test_clean_worktree_has_no_findings_and_passes(self):
        with self.make_repo(feature_worktrees=False) as (repo, _):
            report = wi.inspect(repo)
            self.assertEqual(report["summary"]["findings"], 0)
            self.assertEqual(report["summary"]["VERIFIED"], 0)
            self.assertTrue(report["advisory"])
            self.assertEqual(wi.main(["--repo-root", str(repo)]), wi.EXIT_PASS)

    def test_overlapping_uncommitted_files_are_verified(self):
        with self.make_repo() as (repo, worktrees):
            (worktrees[0] / "shared.py").write_text("one\n", encoding="utf-8")
            (worktrees[1] / "shared.py").write_text("two\n", encoding="utf-8")
            report = wi.inspect(repo)
            matches = [f for f in report["findings"]
                       if f["category"] == "overlapping_changed_files"
                       and f["evidence"]["file"] == "shared.py"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["classification"], "VERIFIED")
            self.assertEqual(wi.main(["--repo-root", str(repo)]), wi.EXIT_BLOCKED)

    def test_duplicate_branch_attachment_is_verified(self):
        with self.make_repo() as (repo, worktrees):
            records = wi.parse_worktrees(git(repo, "worktree", "list", "--porcelain"))
            self.assertEqual(len(records), 3)
            records[2]["branch"] = records[1]["branch"]
            with patch.object(wi, "parse_worktrees", return_value=records):
                report = wi.inspect(repo)
            matches = [f for f in report["findings"] if f["category"] == "duplicate_worktree_branch"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["classification"], "VERIFIED")

    def test_manifest_claims_are_reused_and_unverified(self):
        with self.make_repo() as (repo, _):
            manifest = {
                "schema_version": 1,
                "repositories": ["hamedonassar95/Devobs"],
                "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
                "approval": {k: "pending_human" for k in
                             ("merge", "deploy", "billing", "production")},
                "tasks": [
                    self.task("TASK-001", "CODEX", "a.py", "complete", "evidence_ready",
                              "a" * 40, "PASS", "#10"),
                    self.task("TASK-002", "OPENCODE", "b.py", "blocked", "planned",
                              None, "PENDING", "#10", ["TASK-001"]),
                ],
            }
            path = Path(repo.parent) / "tasks.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            report = wi.inspect(repo, manifest_path=path)
            categories = {f["category"]: f["classification"] for f in report["findings"]}
            self.assertEqual(categories.get("duplicate_pr_target"), "UNVERIFIED")
            self.assertEqual(categories.get("manifest_dependency_block"), "UNVERIFIED")
            self.assertEqual(report["manifest"]["decision"], "BLOCKED")

    def test_detached_head_is_reported_without_modifying_state(self):
        with self.make_repo() as (repo, worktrees):
            git(worktrees[1], "checkout", "--detach", "-q")
            report = wi.inspect(repo)
            self.assertTrue(any(f["category"] == "detached_worktree"
                                and f["classification"] == "UNVERIFIED"
                                for f in report["findings"]))

    def test_stale_candidate_uses_commit_timestamp_evidence(self):
        with self.make_repo() as (repo, worktrees):
            old = "2020-01-01T00:00:00+00:00"
            env = dict(os.environ, GIT_AUTHOR_DATE=old, GIT_COMMITTER_DATE=old)
            (worktrees[1] / "stale.py").write_text("stale\n", encoding="utf-8")
            git(worktrees[1], "add", "stale.py", env=env)
            git(worktrees[1], "commit", "-q", "-m", "old", env=env)
            report = wi.inspect(repo, stale_days=30)
            matches = [f for f in report["findings"] if f["category"] == "stale_worktree_candidate"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["classification"], "UNVERIFIED")

    def test_only_read_only_git_commands_are_invoked(self):
        with self.make_repo() as (repo, _):
            seen = []
            real_run = subprocess.run

            def recording_run(argv, **kwargs):
                seen.append(tuple(argv[3:]))
                return real_run(argv, **kwargs)

            with patch.object(wi.subprocess, "run", side_effect=recording_run):
                wi.inspect(repo)
            verbs = {entry[0] for entry in seen}
            self.assertTrue(verbs <= {"worktree", "status", "rev-parse", "rev-list", "log"},
                            f"unexpected mutating Git verbs: {verbs}")

    def test_missing_git_metadata_fails_closed(self):
        with self.make_repo() as (repo, _):
            with patch.object(wi, "_git", side_effect=wi.InspectorError("base_ref_unavailable")):
                with self.assertRaises(wi.InspectorError):
                    wi.inspect(repo)
            with patch.object(wi, "inspect", side_effect=wi.InspectorError("git_unavailable")):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = wi.main(["--repo-root", str(repo)])
                report = json.loads(buffer.getvalue())
            self.assertEqual(code, wi.EXIT_FAIL)
            self.assertEqual(report["findings"][0]["classification"], "BLOCKED")
            self.assertEqual(report["findings"][0]["evidence"]["reason"], "git_unavailable")

    @staticmethod
    def task(task_id, agent, path, status, previous, sha, result, pr, deps=None):
        return {
            "id": task_id, "repository": "hamedonassar95/Devobs", "assigned_agent": agent,
            "branch": "feature/" + task_id.lower(), "affected_files": [path],
            "dependencies": deps or [], "status": status, "previous_status": previous,
            "source_sha": sha,
            "verification": {"commands": ["python -m unittest"] if result == "PASS" else [],
                             "result": result, "evidence": "local" if result == "PASS" else ""},
            "pr_reference": pr, "requested_actions": ["code_change"],
        }

    @staticmethod
    def make_repo(feature_worktrees=True):
        """Yield (main repo, feature worktrees) inside a temporary directory."""
        class Fixture:
            def __enter__(self_):
                self_.temp = tempfile.TemporaryDirectory()
                base = Path(self_.temp.name)
                repo = base / "repo"
                repo.mkdir()
                git(repo, "init", "-q")
                git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
                git(repo, "config", "user.email", "inspector@example.invalid")
                git(repo, "config", "user.name", "Inspector Test")
                (repo / "seed.py").write_text("seed\n", encoding="utf-8")
                git(repo, "add", "seed.py")
                git(repo, "commit", "-q", "-m", "seed")
                first, second = base / "wt-a", base / "wt-b"
                if feature_worktrees:
                    git(repo, "worktree", "add", "-q", "-b", "feature/a", str(first))
                    git(repo, "worktree", "add", "-q", "-b", "feature/b", str(second))
                return repo, (first, second)

            def __exit__(self_, *exc):
                self_.temp.cleanup()
        return Fixture()


if __name__ == "__main__":
    unittest.main()

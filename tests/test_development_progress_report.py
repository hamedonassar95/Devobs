"""Synthetic-only checks for the advisory development-progress projection."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import development_progress_report as progress

REPO = "hamedonassar95/Devobs"
SHA = "a" * 40
SENTINEL = "SYNTHETIC_PROGRESS_SENTINEL_DO_NOT_ECHO"


def ledger():
    return {"schema_version": 1, "repository": REPO, "disclaimer": "Synthetic offline records only",
            "milestones": [{"id": "synthetic-milestone", "area": "DOCUMENTATION",
                            "title": "Synthetic milestone", "pr_number": 12,
                            "pr_head_sha": SHA, "merge_sha": "b" * 40, "ci_run_id": 123,
                            "verification": "Synthetic historical reference", "limitations": "No live proof"}],
            "gates": [{"id": "synthetic-gate", "status": "OPEN",
                       "source": "docs/AI9_V3_INDEPENDENT_EVAL_GATE.md",
                       "reason": "Synthetic missing evidence", "next_action": "Review synthetic evidence"}]}


def task(identifier="TASK-001", **updates):
    value = {"id": identifier, "repository": REPO, "assigned_agent": "CODEX",
             "branch": "feature/" + identifier.lower(), "affected_files": [identifier + ".py"],
             "dependencies": [], "status": "planned", "previous_status": "none",
             "source_sha": None, "verification": {"commands": [], "result": "PENDING", "evidence": ""},
             "pr_reference": None, "requested_actions": ["code_change"]}
    value.update(updates)
    return value


def complete(identifier="TASK-001", **updates):
    value = task(identifier, status="complete", previous_status="evidence_ready", source_sha=SHA,
                 verification={"commands": ["synthetic-test"], "result": "PASS", "evidence": "Synthetic local PASS"},
                 pr_reference="#12")
    value.update(updates)
    return value


def manifest(tasks=None):
    return {"schema_version": 1, "repositories": [REPO],
            "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
            "approval": {name: "pending_human" for name in ("merge", "deploy", "billing", "production")},
            "tasks": [task()] if tasks is None else tasks}


class DevelopmentProgressReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.milestones = self.folder / "milestones.json"
        self.tasks = self.folder / "tasks.json"
        self.milestones.write_text(json.dumps(ledger()))
        self.tasks.write_text(json.dumps(manifest()))

    def invoke(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "tools/development_progress_report.py"),
                               "--milestones", str(self.milestones), "--tasks", str(self.tasks), *extra],
                              cwd=self.folder, capture_output=True, text=True, timeout=10)

    def test_valid_input_has_verified_structure_but_no_live_verification(self):
        result = progress.build_progress_report(ledger(), manifest())
        self.assertEqual(result["input_validation"], "VERIFIED")
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["live_evidence_status"], "UNVERIFIED")
        self.assertEqual(result["summary"]["recorded_completed_milestones"], 1)
        self.assertEqual(len(result["pending_milestones"]), 1)
        self.assertEqual(result["completed_milestones"][0]["evidence_status"], "UNVERIFIED")
        self.assertEqual(len(result["outstanding_owner_approvals"]), 4)

    def test_blocked_tasks_and_gates_remain_blocked(self):
        source = ledger()
        source["gates"][0]["status"] = "BLOCKED"
        tasks = manifest([task(status="blocked", previous_status="planned")])
        report = progress.build_progress_report(source, tasks)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["agent_tasks"][0]["status"], "blocked")
        self.assertTrue(report["agent_tasks"][0]["blocked"])
        self.assertEqual(report["blocked_milestones"][0]["evidence_status"], "BLOCKED")

    def test_completed_task_and_exact_record_do_not_become_live_merge_or_ci_proof(self):
        report = progress.build_progress_report(ledger(), manifest([complete()]))
        row = report["agent_tasks"][0]
        self.assertEqual(row["status"], "complete")
        self.assertEqual(row["evidence_state"], "PASS_CLAIM_UNVERIFIED")
        self.assertEqual(row["merge_reference_state"], "RECORDED_MATCH")
        self.assertTrue(all(item["evidence_status"] == "UNVERIFIED"
                            for item in report["available_verification"]))
        self.assertNotEqual(report["status"], "VERIFIED")

    def test_open_pr_without_record_is_never_a_completed_milestone(self):
        report = progress.build_progress_report(ledger(), manifest([complete(pr_reference="#99")]))
        self.assertEqual([row["pr_number"] for row in report["completed_milestones"]], [12])
        self.assertEqual(report["agent_tasks"][0]["merge_reference_state"], "UNVERIFIED")
        self.assertEqual(report["next_recommended_task"]["kind"], "VERIFY_MERGE_EVIDENCE")

    def test_wrong_sha_or_foreign_pr_url_cannot_match_a_record(self):
        for values in ({"source_sha": "c" * 40},
                       {"pr_reference": "https://github.com/example/other/pull/12"},
                       {"pr_reference": "#" + "9" * 5000}):
            report = progress.build_progress_report(ledger(), manifest([complete(**values)]))
            self.assertEqual(report["agent_tasks"][0]["merge_reference_state"], "UNVERIFIED")

    def test_exact_full_url_and_merge_sha_are_recorded_matches_only(self):
        for source_sha in (SHA, "b" * 40):
            report = progress.build_progress_report(ledger(), manifest([
                complete(source_sha=source_sha, pr_reference=f"https://github.com/{REPO}/pull/12")]))
            self.assertEqual(report["agent_tasks"][0]["merge_reference_state"], "RECORDED_MATCH")
            self.assertEqual(report["live_evidence_status"], "UNVERIFIED")

    def test_other_repository_cannot_inherit_a_matching_pr_number(self):
        tasks = manifest([complete(repository="example/other")])
        tasks["repositories"].append("example/other")
        report = progress.build_progress_report(ledger(), tasks)
        self.assertEqual(report["agent_tasks"][0]["merge_reference_state"], "UNVERIFIED")
        entry = next(row for row in report["available_verification"] if row["kind"] == "TASK_VERIFICATION_STATE")
        self.assertEqual(entry["repository"], "example/other")
        self.assertIn("example/other", progress.render_markdown(report))

    def test_missing_verification_fails_or_blocks_without_a_pass_claim(self):
        broken = complete(verification={"commands": [], "result": "PASS", "evidence": ""})
        self.assertEqual(progress.build_progress_report(ledger(), manifest([broken]))["status"], "FAIL")
        broken["status"], broken["previous_status"] = "evidence_ready", "in_progress"
        report = progress.build_progress_report(ledger(), manifest([broken]))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(report["agent_tasks"][0]["blocked"])

    def test_duplicate_identifiers_and_missing_merge_evidence_fail(self):
        source = ledger()
        duplicate = deepcopy(source["milestones"][0])
        duplicate.update(pr_number=13, merge_sha="c" * 40)
        source["milestones"].append(duplicate)
        self.assertEqual(progress.build_progress_report(source, manifest())["status"], "FAIL")
        source = ledger()
        del source["milestones"][0]["merge_sha"]
        self.assertEqual(progress.build_progress_report(source, manifest())["status"], "FAIL")

    def test_empty_inputs_fail_without_zero_ready_counts(self):
        for source, tasks in (({}, {}), (ledger(), manifest([])),
                              ({**ledger(), "milestones": []}, manifest())):
            report = progress.build_progress_report(source, tasks)
            self.assertEqual(report["status"], "FAIL")
            self.assertIsNone(report["summary"])

    def test_conflicted_or_dependency_blocked_work_is_not_recommended(self):
        tasks = manifest([task("TASK-001", affected_files=["shared.py"], status="in_progress", previous_status="planned"),
                          task("TASK-002", affected_files=["shared.py"], status="in_progress", previous_status="planned"),
                          task("TASK-003", dependencies=["TASK-001"]), task("TASK-004")])
        report = progress.build_progress_report(ledger(), tasks)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["next_recommended_task"]["id"], "TASK-004")
        markdown = progress.render_markdown(report)
        self.assertIn("| blocked |", markdown)
        self.assertIn("concurrent\\_file\\_ownership", markdown)
        self.assertIn("unresolved_dependencies", markdown)

    def test_output_order_is_independent_of_task_gate_and_dependency_order(self):
        source = ledger()
        source["gates"].append({**source["gates"][0], "id": "another-gate"})
        tasks = manifest([complete("TASK-001"), complete("TASK-002"),
                          task("TASK-003", dependencies=["TASK-002", "TASK-001"])])
        first = progress.build_progress_report(source, tasks)
        source["gates"].reverse()
        tasks["tasks"].reverse()
        tasks["tasks"][0]["dependencies"].reverse()
        second = progress.build_progress_report(source, tasks)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(progress.render_markdown(first), progress.render_markdown(second))

    def test_input_commands_are_never_executed_or_echoed(self):
        command = "touch " + SENTINEL
        tasks = manifest([complete(verification={"commands": [command], "result": "PASS", "evidence": SENTINEL})])
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network forbidden")), \
             mock.patch.object(subprocess, "Popen", side_effect=AssertionError("commands forbidden")):
            report = progress.build_progress_report(ledger(), tasks)
        self.assertNotIn(SENTINEL, json.dumps(report))
        self.assertFalse((self.folder / SENTINEL).exists())

    def test_credential_like_prose_is_redacted_and_markdown_is_escaped(self):
        source = ledger()
        source["milestones"][0]["title"] = "token=" + SENTINEL
        report = progress.build_progress_report(source, manifest())
        self.assertNotIn(SENTINEL, json.dumps(report) + progress.render_markdown(report))
        source["milestones"][0]["title"] = '<img src=x> [label](https://example.invalid)'
        markdown = progress.render_markdown(progress.build_progress_report(source, manifest()))
        self.assertNotIn("<img", markdown)
        self.assertNotIn("[label](", markdown)

    def test_approval_claim_cannot_override_the_existing_contract(self):
        tasks = manifest()
        tasks["approval"]["merge"] = "approved"
        self.assertEqual(progress.build_progress_report(ledger(), tasks)["status"], "FAIL")

    def test_build_does_not_mutate_source_documents(self):
        source, tasks = ledger(), manifest([complete()])
        before = deepcopy((source, tasks))
        progress.build_progress_report(source, tasks)
        self.assertEqual((source, tasks), before)

    def test_cli_json_markdown_and_exit_semantics(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "UNVERIFIED")
        self.assertEqual(result.stdout, self.invoke().stdout)
        markdown = self.invoke("--format", "markdown")
        self.assertEqual(markdown.returncode, 2)
        self.assertIn("# Development progress", markdown.stdout)
        self.assertIn("UNVERIFIED", markdown.stdout)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["milestones.json", "tasks.json"])

    def test_missing_milestone_or_task_file_fails_quietly(self):
        for missing in (self.milestones, self.tasks):
            self.milestones.write_text(json.dumps(ledger()))
            self.tasks.write_text(json.dumps(manifest()))
            missing.unlink()
            result = self.invoke()
            self.assertEqual(result.returncode, 3)
            self.assertEqual(json.loads(result.stdout)["status"], "FAIL")
            self.assertNotIn(str(self.folder), result.stdout + result.stderr)

    def test_existing_validator_apis_are_reused_and_unexpected_errors_are_quiet(self):
        shared = progress._shared()
        source, tasks = ledger(), manifest()
        with mock.patch.object(shared.ledger, "validate", wraps=shared.ledger.validate) as validate, \
             mock.patch.object(shared.tasks, "build_report", wraps=shared.tasks.build_report) as report:
            progress.build_progress_report(source, tasks)
            validate.assert_called_once_with(source)
            report.assert_called_once()
        with mock.patch.object(shared.ledger, "validate", side_effect=RuntimeError(SENTINEL)):
            result = progress.build_progress_report(source, tasks)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn(SENTINEL, json.dumps(result))

    def test_malformed_duplicate_or_nonfinite_json_fails(self):
        for raw in ('{broken', '{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'):
            self.milestones.write_text(raw)
            result = self.invoke()
            self.assertEqual(result.returncode, 3)
            self.assertEqual(json.loads(result.stdout)["status"], "FAIL")

    def test_symlink_and_oversized_task_file_fail(self):
        outside = self.folder / "outside.json"
        outside.write_text(json.dumps(ledger()))
        self.milestones.unlink()
        self.milestones.symlink_to(outside)
        self.assertEqual(self.invoke().returncode, 3)
        self.milestones.unlink()
        self.milestones.write_text(json.dumps(ledger()))
        self.tasks.write_bytes(b" " * (512 * 1024 + 1))
        self.assertEqual(self.invoke().returncode, 3)

    def test_help_and_invalid_arguments_do_not_read_or_echo_input(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/development_progress_report.py"),
                                 "--" + SENTINEL], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3)
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)
        self.assertEqual(self.invoke("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from scripts.phase8_live_planner import evaluate_live

ISSUE_NUMBER = 73
RUN_ID = 12345
SHA = "a" * 40


def investigation(decision="FIX_FORWARD", confidence=0.95, run_id=str(RUN_ID), number=ISSUE_NUMBER):
    data = {
        "incident_number": number,
        "incident_run_id": run_id,
        "decision": decision,
        "confidence": confidence,
        "reversible": True,
        "repository_scoped": True,
        "proposed_change": "repair site validation",
    }
    return {
        "user": "github-actions[bot]",
        "body": (
            "## AI Incident Investigation\n"
            "<!-- gh-aw-agentic-workflow: Devobs Incident Investigator, workflow_id: incident-investigator -->\n"
            "<!-- devobs-investigation-contract:v2 -->\n"
            "```json\n" + json.dumps(data) + "\n```"
        ),
    }


def live_record():
    return {
        "issue": {
            "number": ISSUE_NUMBER,
            "title": "incident: CI failure (run 12345)",
            "state": "open",
            "user": "github-actions[bot]",
            "body": (
                "- **Head SHA:** `" + SHA + "`\n"
                "<!-- incident-run-id:12345 -->"
            ),
        },
        "workflow_run": {
            "id": RUN_ID,
            "name": "CI",
            "status": "completed",
            "conclusion": "failure",
            "head_branch": "main",
            "head_sha": SHA,
        },
        "comments": [investigation()],
        "open_pull_requests": [],
        "evidence_errors": [],
    }


class LiveRecoveryPlannerTests(unittest.TestCase):
    def test_eligible_live_evidence_creates_proposal_without_write_authority(self):
        result = evaluate_live(live_record())
        self.assertTrue(result["eligible"])
        self.assertEqual(result["status"], "ELIGIBLE")
        self.assertEqual(result["branch"], "recovery/incident-73-repair-site-validation")
        self.assertEqual(result["files_to_change"], [])
        self.assertFalse(result["repository_write_authority"])
        self.assertEqual(result["final_state"], "PENDING HUMAN APPROVAL")

    def test_simulated_incident_is_rejected(self):
        record = live_record()
        record["issue"]["body"] = record["issue"]["body"].replace(
            "incident-run-id:12345", "incident-run-id:simulation-12345"
        )
        self.assertFalse(evaluate_live(record)["eligible"])

    def test_untrusted_or_closed_incident_is_rejected(self):
        for key, value in (("user", "maintainer"), ("state", "closed")):
            with self.subTest(key=key):
                record = live_record()
                record["issue"][key] = value
                self.assertFalse(evaluate_live(record)["eligible"])

    def test_source_run_must_match_incident_and_main_sha(self):
        for change in (
            {"head_branch": "feature/test"},
            {"head_sha": "b" * 40},
            {"conclusion": "cancelled"},
            {"name": "Unmonitored Workflow"},
        ):
            with self.subTest(change=change):
                record = live_record()
                record["workflow_run"].update(change)
                self.assertFalse(evaluate_live(record)["eligible"])

    def test_missing_duplicate_or_unbound_investigation_is_rejected(self):
        record = live_record()
        record["comments"] = []
        self.assertFalse(evaluate_live(record)["eligible"])

        record = live_record()
        record["comments"].append(investigation())
        self.assertFalse(evaluate_live(record)["eligible"])

        record = live_record()
        record["comments"] = [investigation(run_id="99999")]
        self.assertFalse(evaluate_live(record)["eligible"])

    def test_non_v2_or_untrusted_investigation_is_rejected(self):
        record = live_record()
        record["comments"][0]["user"] = "some-user"
        self.assertFalse(evaluate_live(record)["eligible"])

        record = live_record()
        record["comments"][0]["body"] = record["comments"][0]["body"].replace(
            "devobs-investigation-contract:v2", "devobs-investigation-contract"
        )
        self.assertFalse(evaluate_live(record)["eligible"])

    def test_ineligible_ai_decisions_and_low_confidence_fail_closed(self):
        for comment in (
            investigation(decision="MANUAL_REVIEW"),
            investigation(confidence=0.79),
            investigation(decision="NO_ACTION"),
        ):
            with self.subTest(comment=comment["body"]):
                record = live_record()
                record["comments"] = [comment]
                self.assertFalse(evaluate_live(record)["eligible"])

    def test_existing_recovery_pr_and_api_errors_fail_closed(self):
        record = live_record()
        record["open_pull_requests"] = [{
            "head_ref": "recovery/incident-73-repair-site-validation",
            "body": "",
        }]
        self.assertFalse(evaluate_live(record)["eligible"])

        record = live_record()
        record["evidence_errors"] = ["could not read comments"]
        self.assertFalse(evaluate_live(record)["eligible"])


if __name__ == "__main__":
    unittest.main()

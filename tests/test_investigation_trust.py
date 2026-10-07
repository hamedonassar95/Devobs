import unittest
from scripts.investigation_trust import trusted_incident, trusted_investigation


class InvestigationTrustTests(unittest.TestCase):
    def test_trusts_bot_incident_with_run_marker(self):
        issue={"state":"open","title":"incident: test","body":"<!-- incident-run-id:123 -->","user":{"login":"github-actions[bot]"}}
        self.assertTrue(trusted_incident(issue))

    def test_rejects_human_authored_incident(self):
        issue={"state":"open","title":"incident: test","body":"<!-- incident-run-id:123 -->","user":{"login":"attacker"}}
        self.assertFalse(trusted_incident(issue))

    def test_trusts_current_gh_aw_provenance(self):
        body="## AI Incident Investigation\n<!-- gh-aw-agentic-workflow: Devobs Incident Investigator, engine: copilot, workflow_id: incident-investigator -->"
        self.assertTrue(trusted_investigation({"body":body,"user":{"login":"github-actions[bot]"}}))

    def test_trusts_legacy_marker_from_bot(self):
        body="## AI Incident Investigation\n<!-- devobs-investigation:v1 -->"
        self.assertTrue(trusted_investigation({"body":body,"user":{"login":"github-actions[bot]"}}))

    def test_rejects_spoofed_human_comment(self):
        body="## AI Incident Investigation\n<!-- devobs-investigation:v1 -->"
        self.assertFalse(trusted_investigation({"body":body,"user":{"login":"attacker"}}))

    def test_rejects_bot_comment_without_provenance(self):
        self.assertFalse(trusted_investigation({"body":"## AI Incident Investigation","user":{"login":"github-actions[bot]"}}))


if __name__ == "__main__":
    unittest.main()

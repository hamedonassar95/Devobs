import json, unittest
from devobs.integration_verification.evaluator import evaluate_hub
from devobs.integration_verification.reporting import render_json_report, render_markdown_report

def base_input():
    return {
        "repository":"hamedonassar95/Devobs","head_sha":"4"*40,
        "components":[{"name":"a","source_path":"a","owning_branch":"main","evidence_type":"code","test_coverage":"present","integration_dependencies":[],"verification_status":"IMPLEMENTED_AND_TESTED","schema_version":1}],
        "ownership":{"task_manifest":{"schema_version":1,"repositories":["hamedonassar95/Devobs"],"agents":{"CODEX":{"enabled":True},"OPENCODE":{"enabled":True}},"approval":{"merge":"pending_human","deploy":"pending_human","billing":"pending_human","production":"pending_human"},"tasks":[{"id":"TASK-001","repository":"hamedonassar95/Devobs","assigned_agent":"CODEX","branch":"feature/x","affected_files":["a.py"],"dependencies":[],"status":"planned","previous_status":"none","source_sha":None,"verification":{"commands":[],"result":"PENDING","evidence":""},"pr_reference":None,"requested_actions":["code_change"]}]}},
        "evidence":[{"source":"github-actions","evidence_id":"ev1","component":"a","commit_sha":"a"*40,"verification_method":"ci","verification_timestamp":"2026-11-21T00:00:00Z","result":"PASS","note":"token ghp_abcdefghijklmnopqrstuvwxyz123456"}],
        "approval":{"human_approved":True,"evidence_id":"ap1","timestamp":"2026-11-21T00:00:00Z"}
    }

class ReportingTests(unittest.TestCase):
    def test_json_and_markdown(self):
        r=evaluate_hub(base_input())
        js=render_json_report(r)
        md=render_markdown_report(r)
        self.assertIn('"decision"', js)
        self.assertIn('Integration Verification Hub Report', md)
        self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz123456', js)

    def test_secret_redaction(self):
        r=evaluate_hub(base_input())
        self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz123456', json.dumps(r))

if __name__ == '__main__':
    unittest.main()

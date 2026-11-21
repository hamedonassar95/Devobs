import unittest
from devobs.integration_verification.models import Finding
from devobs.integration_verification.ownership import evaluate_ownership

class OwnershipTests(unittest.TestCase):
    def test_concurrent_file_conflict(self):
        findings=[]
        own=evaluate_ownership({"active_worktrees":[{"branch":"a","owned_paths":["x.py"]},{"branch":"b","owned_paths":["x.py"]}]}, findings)
        self.assertEqual(own['status'],'conflict')
        self.assertTrue(any(f.code=='CONCURRENT_FILE_OWNERSHIP' for f in findings))

    def test_blocked_task_ownership(self):
        findings=[]
        manifest={
            "schema_version":1,"repositories":["hamedonassar95/Devobs"],
            "agents":{"CODEX":{"enabled":True},"OPENCODE":{"enabled":True}},
            "approval":{"merge":"pending_human","deploy":"pending_human","billing":"pending_human","production":"pending_human"},
            "tasks":[{"id":"TASK-001","repository":"hamedonassar95/Devobs","assigned_agent":"CODEX","branch":"feature/x","affected_files":["a.py"],"dependencies":[],"status":"blocked","previous_status":"in_progress","source_sha":"a"*40,"verification":{"commands":["x"],"result":"PENDING","evidence":""},"pr_reference":None,"requested_actions":["code_change"]}]
        }
        evaluate_ownership({"task_manifest":manifest}, findings)
        self.assertTrue(any(f.code=='BLOCKED_TASK_RETAINS_OWNERSHIP' for f in findings))

    def test_missing_ownership_evidence(self):
        findings=[]
        evaluate_ownership(None, findings)
        self.assertTrue(any(f.code=='MISSING_OWNERSHIP_EVIDENCE' for f in findings))

if __name__ == '__main__':
    unittest.main()

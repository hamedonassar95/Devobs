import json, unittest
from devobs.integration_verification.evaluator import evaluate_hub

def base_input():
    return {
        "repository":"hamedonassar95/Devobs",
        "head_sha":"4e1dc8f2c9c7a4caf896d7daf681b35be2e22937",
        "components":[
            {"name":"a","source_path":"a","owning_branch":"main","evidence_type":"code","test_coverage":"present","integration_dependencies":["b"],"verification_status":"IMPLEMENTED_AND_TESTED","schema_version":1},
            {"name":"b","source_path":"b","owning_branch":"main","evidence_type":"code","test_coverage":"present","integration_dependencies":[],"verification_status":"IMPLEMENTED_AND_TESTED","schema_version":1},
        ],
        "ownership":{"task_manifest":{
            "schema_version":1,"repositories":["hamedonassar95/Devobs"],"agents":{"CODEX":{"enabled":True},"OPENCODE":{"enabled":True}},
            "approval":{"merge":"pending_human","deploy":"pending_human","billing":"pending_human","production":"pending_human"},
            "tasks":[{"id":"TASK-001","repository":"hamedonassar95/Devobs","assigned_agent":"CODEX","branch":"feature/x","affected_files":["a.py"],"dependencies":[],"status":"planned","previous_status":"none","source_sha":None,"verification":{"commands":[],"result":"PENDING","evidence":""},"pr_reference":None,"requested_actions":["code_change"]}]
        }},
        "evidence":[{"source":"github-actions","evidence_id":"ev1","component":"a","commit_sha":"a"*40,"verification_method":"ci","verification_timestamp":"2026-11-21T00:00:00Z","result":"PASS"}],
        "approval":{"human_approved":True,"evidence_id":"ap1","timestamp":"2026-11-21T00:00:00Z"}
    }

class EvaluatorTests(unittest.TestCase):
    def test_valid_human_review_readiness(self):
        r=evaluate_hub(base_input())
        self.assertEqual(r['decision'],'READY_FOR_HUMAN_REVIEW')

    def test_missing_component(self):
        i=base_input(); i['components'][0]['verification_status']='ABSENT'
        r=evaluate_hub(i)
        self.assertIn(r['decision'], {'BLOCKED','INSUFFICIENT_EVIDENCE','POLICY_VIOLATION'})

    def test_missing_dependency(self):
        i=base_input(); i['components'][0]['integration_dependencies']=['missing']
        r=evaluate_hub(i)
        self.assertEqual(r['decision'],'BLOCKED')
        self.assertTrue(any(f['code']=='MISSING_DEPENDENCY' for f in r['findings']))

    def test_cyclic_dependencies(self):
        i=base_input(); i['components'][1]['integration_dependencies']=['a']
        r=evaluate_hub(i)
        self.assertEqual(r['decision'],'BLOCKED')
        self.assertTrue(any(f['code']=='CYCLIC_DEPENDENCY' for f in r['findings']))

    def test_missing_approval(self):
        i=base_input(); del i['approval']
        r=evaluate_hub(i)
        self.assertEqual(r['decision'],'INSUFFICIENT_EVIDENCE')

    def test_stale_or_contradictory_evidence(self):
        i=base_input(); i['evidence'].append({"source":"github-actions","evidence_id":"ev2","component":"a","commit_sha":"a"*40,"verification_method":"ci","verification_timestamp":"2026-11-21T00:00:00Z","result":"FAIL"})
        r=evaluate_hub(i)
        self.assertEqual(r['decision'],'POLICY_VIOLATION')

    def test_malformed_json_shape(self):
        r=evaluate_hub([])
        self.assertEqual(r['decision'],'INSUFFICIENT_EVIDENCE')

    def test_oversized_input(self):
        i=base_input(); i['components'] = i['components']*300
        r=evaluate_hub(i)
        self.assertIn(r['decision'], {'INSUFFICIENT_EVIDENCE','BLOCKED','POLICY_VIOLATION'})

    def test_deterministic_repeated_execution(self):
        i=base_input(); r1=evaluate_hub(i); r2=evaluate_hub(i)
        self.assertEqual(r1['decision'], r2['decision'])
        self.assertEqual(r1['dependency_matrix'], r2['dependency_matrix'])

    def test_unverified_local_branch_component(self):
        i=base_input(); i['components'][0]['verification_status']='IMPLEMENTED_UNVERIFIED'
        r=evaluate_hub(i)
        self.assertIn(r['decision'], {'INSUFFICIENT_EVIDENCE','BLOCKED'})

if __name__ == '__main__':
    unittest.main()

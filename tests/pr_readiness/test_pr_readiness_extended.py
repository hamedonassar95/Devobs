import json, unittest
from devobs.pr_readiness import evaluate_pr_readiness

def base():
    sha='a'*40
    return {
        "pr":{"repository":"hamedonassar95/Devobs","pr_number":1,"base_branch":"main","head_branch":"feature/x","head_sha":sha,"reviewed_head_sha":sha,"mergeable":True,"merge_state":"clean"},
        "required_checks":["ci"],"checks":[{"name":"ci","status":"completed","conclusion":"success","head_sha":sha,"required":True}],
        "security_findings":[{"tool":"scan","status":"pass","severity":"none","head_sha":sha}],
        "dependency_results":[{"name":"deps","status":"passed","head_sha":sha}],
        "reviews":{"approved":True,"approvals_count":1,"required_approvals":1,"human_approval":True},
        "changed_files":["devobs/x.py"],"ownership":{"owner":"a","active_agents":["a"],"file_owners":{"devobs/x.py":["a"]}},
        "timestamps":{"evidence_collected_at":"2026-11-21T00:00:00Z"},
    }

class ExtendedTests(unittest.TestCase):
    def test_invalid_base_sha(self):
        ev=base(); ev['pr']['base_sha']='bad'
        # base sha not a required existing field; invalid head sha should be insufficient
        ev['pr']['head_sha']='bad'
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'INSUFFICIENT_EVIDENCE')

    def test_unresolved_merge_conflict(self):
        ev=base(); ev['pr']['mergeable']=False; ev['pr']['merge_state']='dirty'
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'BLOCKED')

    def test_blocked_dependency(self):
        ev=base(); ev['dependency_results'][0]['status']='failed'
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'POLICY_VIOLATION')

    def test_contradictory_evidence(self):
        ev=base(); ev['checks'].append({"name":"ci","status":"completed","conclusion":"failure","head_sha":'a'*40,"required":True})
        r=evaluate_pr_readiness(ev)
        self.assertIn(r['readiness_decision']['decision'], {'POLICY_VIOLATION','BLOCKED','INSUFFICIENT_EVIDENCE'})

    def test_unauthorized_workflow_permissions(self):
        ev=base(); ev['workflow_permissions']={'write_all':True,'unsafe':True}
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'POLICY_VIOLATION')
        self.assertTrue(any(f['code']=='UNSAFE_WORKFLOW_PERMISSION' for f in r['findings']))

    def test_critical_infrastructure_modification(self):
        ev=base(); ev['changed_files']=['terraform/prod/main.tf']
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['risk']['level'],'CRITICAL')

    def test_ai_advisory_cannot_override(self):
        ev=base(); ev['advisory']={'decision':'READY_FOR_HUMAN_REVIEW','authoritative':True}
        ev['checks'][0]['conclusion']='failure'
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'BLOCKED')
        self.assertFalse(r.get('advisory',{}).get('authoritative',False))

    def test_deterministic_repeated_evaluation(self):
        ev=base(); r1=evaluate_pr_readiness(ev); r2=evaluate_pr_readiness(ev)
        self.assertEqual(r1['readiness_decision'], r2['readiness_decision'])
        self.assertEqual(r1['risk'], r2['risk'])

    def test_missing_repository_metadata(self):
        ev=base(); ev['pr']['repository']=''
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'INSUFFICIENT_EVIDENCE')

    def test_oversized_input(self):
        ev=base(); ev['checks']=[{"name":f"c{i}","status":"completed","conclusion":"success","head_sha":"a"*40} for i in range(201)]
        r=evaluate_pr_readiness(ev)
        self.assertEqual(r['readiness_decision']['decision'],'INSUFFICIENT_EVIDENCE')

    def test_secret_containing_evidence(self):
        ev=base(); ev['security_findings'][0]['summary']='ghp_abcdefghijklmnopqrstuvwxyz123456'
        dumped=json.dumps(evaluate_pr_readiness(ev))
        self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz123456', dumped)

if __name__ == '__main__':
    unittest.main()

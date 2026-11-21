import unittest
from devobs.integration_control.readiness import evaluate_readiness

def base():
    sha='a'*40
    return {
        'pr':{'repository':'hamedonassar95/Devobs','pr_number':1,'base_branch':'main','head_branch':'feature/x','head_sha':sha,'reviewed_head_sha':sha,'mergeable':True,'merge_state':'clean'},
        'required_checks':['validate'],
        'checks':[{'name':'validate','status':'completed','conclusion':'success','required':True,'head_sha':sha}],
        'security_findings':[{'tool':'bandit','status':'pass','severity':'none','head_sha':sha}],
        'dependency_results':[{'name':'deps','status':'pass'}],
        'reviews':{'approved':True,'approvals_count':1,'required_approvals':1,'human_approval':True},
        'changed_files':['a.py'],
        'ownership':{'file_owners':{'a.py':['agent-a']},'active_agents':['agent-a'],'task_manifest':{'schema_version':1,'repositories':['hamedonassar95/Devobs'],'agents':{'CODEX':{'enabled':True},'OPENCODE':{'enabled':True}},'approval':{'merge':'pending_human','deploy':'pending_human','billing':'pending_human','production':'pending_human'},'tasks':[{
            'id':'TASK-001','repository':'hamedonassar95/Devobs','assigned_agent':'CODEX','branch':'feature/x','affected_files':['a.py'],'dependencies':[],'status':'planned','previous_status':'none','source_sha':None,
            'verification':{'commands':[],'result':'PENDING','evidence':''},'pr_reference':None,'requested_actions':['code_change']
        }]}},
        'timestamps':{'collected':'2026-11-21T00:00:00Z'},
        'evidence':[{'source':'gh','kind':'ci','ref':'run1','sha':sha}],
    }

class ReadinessTests(unittest.TestCase):
    def test_valid_ready_for_human_review(self):
        r=evaluate_readiness(base())
        self.assertEqual(r['decision'],'READY_FOR_HUMAN_REVIEW')

    def test_missing_evidence_unknown(self):
        i=base(); i['evidence']=[]; i['timestamps']={}
        r=evaluate_readiness(i)
        self.assertEqual(r['decision'],'UNKNOWN')

    def test_mismatched_sha_blocked(self):
        i=base(); i['pr']['reviewed_head_sha']='b'*40
        r=evaluate_readiness(i)
        self.assertEqual(r['decision'],'BLOCKED')

    def test_malformed_json_shape(self):
        r=evaluate_readiness([])
        self.assertEqual(r['decision'],'UNKNOWN')

    def test_repeated_execution_deterministic(self):
        i=base(); r1=evaluate_readiness(i); r2=evaluate_readiness(i)
        self.assertEqual(r1['decision'], r2['decision'])
        self.assertEqual([c['name'] for c in r1['evidence_checks']], [c['name'] for c in r2['evidence_checks']])

    def test_unavailable_github_api_unknown(self):
        i=base(); i['pr']['mergeable']=None; i['pr']['merge_state']='unknown'; i['checks']=[]
        r=evaluate_readiness(i)
        self.assertIn(r['decision'], {'UNKNOWN','BLOCKED'})

    def test_path_traversal_rejected(self):
        i=base(); i['changed_files']=['../secrets.txt']
        r=evaluate_readiness(i)
        self.assertEqual(r['decision'],'UNKNOWN')

if __name__ == '__main__':
    unittest.main()

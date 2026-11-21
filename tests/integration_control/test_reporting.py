import json, unittest
from devobs.integration_control.reporting import build_readiness_report, render_json, render_markdown

def base():
    sha='a'*40
    return {
        'agent_identifier':'CODEX','task_identifier':'TASK-001',
        'pr':{'repository':'hamedonassar95/Devobs','pr_number':1,'base_branch':'main','head_branch':'feature/x','head_sha':sha,'reviewed_head_sha':sha,'mergeable':True,'merge_state':'clean'},
        'required_checks':['validate'],'checks':[{'name':'validate','status':'completed','conclusion':'success','required':True,'head_sha':sha}],
        'security_findings':[{'tool':'bandit','status':'pass','severity':'none','head_sha':sha}],
        'dependency_results':[{'name':'deps','status':'pass'}],
        'reviews':{'approved':True,'approvals_count':1,'required_approvals':1,'human_approval':True},
        'changed_files':['a.py'],'ownership':{'file_owners':{'a.py':['agent-a']},'active_agents':['agent-a'],'task_manifest':{'schema_version':1,'repositories':['hamedonassar95/Devobs'],'agents':{'CODEX':{'enabled':True},'OPENCODE':{'enabled':True}},'approval':{'merge':'pending_human','deploy':'pending_human','billing':'pending_human','production':'pending_human'},'tasks':[{'id':'TASK-001','repository':'hamedonassar95/Devobs','assigned_agent':'CODEX','branch':'feature/x','affected_files':['a.py'],'dependencies':[],'status':'planned','previous_status':'none','source_sha':None,'verification':{'commands':[],'result':'PENDING','evidence':''},'pr_reference':None,'requested_actions':['code_change']}]}},
        'timestamps':{'collected':'2026-11-21T00:00:00Z'},'evidence':[{'source':'gh','kind':'ci','ref':'run1','sha':sha,'data':{'token':'ghp_abcdefghijklmnopqrstuvwxyz123456'}}]
    }

class ReportingTests(unittest.TestCase):
    def test_report_has_required_fields(self):
        r=build_readiness_report(base())
        for k in ['repository','branch','commit','agent_identifier','task_identifier','evidence_sources','verification_results','dependency_status','file_ownership_conflicts','security_findings','ci_verification_results','human_approval_requirements','recommended_next_action']:
            self.assertIn(k,r)
        self.assertIn(r['readiness'], {'READY_FOR_HUMAN_REVIEW','BLOCKED','UNKNOWN'})

    def test_secret_redaction(self):
        out=render_json(build_readiness_report(base()))
        self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz123456', out)
        self.assertIn('[REDACTED]', out)

    def test_markdown_render(self):
        md=render_markdown(build_readiness_report(base()))
        self.assertIn('Integration Readiness Report', md)

if __name__ == '__main__':
    unittest.main()

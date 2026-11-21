import unittest
from devobs.integration_control.conflicts import detect_conflicts

def norm():
    return {
        'head_sha':'a'*40,
        'ownership': {
            'file_owners': {'a.py':['agent-a']},
            'active_agents':['agent-a'],
            'task_manifest': {
                'schema_version':1,'repositories':['hamedonassar95/Devobs'],
                'agents':{'CODEX':{'enabled':True},'OPENCODE':{'enabled':True}},
                'approval':{'merge':'pending_human','deploy':'pending_human','billing':'pending_human','production':'pending_human'},
                'tasks':[]
            },
            'stale_evidence': False
        },
        'changed_files':['a.py']
    }

class ConflictTests(unittest.TestCase):
    def test_duplicate_ownership(self):
        n=norm(); n['ownership']['file_owners']['a.py']=['a','b']
        r=detect_conflicts(n)
        self.assertTrue(any(c['name']=='file_ownership' and c['state']=='CONFLICTED' for c in r['checks']))

    def test_blocked_task_conflict(self):
        n=norm(); n['ownership']['task_manifest']['tasks']=[{
            'id':'TASK-001','repository':'hamedonassar95/Devobs','assigned_agent':'CODEX','branch':'feature/x','affected_files':['a.py'],
            'dependencies':[],'status':'blocked','previous_status':'in_progress','source_sha':'a'*40,
            'verification':{'commands':['x'],'result':'PENDING','evidence':''},'pr_reference':None,'requested_actions':['code_change']
        }]
        r=detect_conflicts(n)
        self.assertTrue(any(c['name']=='blocked_task_ownership' and c['state']=='BLOCKED' for c in r['checks']))

    def test_invalid_dependencies(self):
        n=norm(); n['ownership']['task_manifest']['tasks']=[{
            'id':'TASK-001','repository':'hamedonassar95/Devobs','assigned_agent':'CODEX','branch':'feature/x','affected_files':['a.py'],
            'dependencies':['TASK-001'],'status':'planned','previous_status':'none','source_sha':None,
            'verification':{'commands':[],'result':'PENDING','evidence':''},'pr_reference':None,'requested_actions':['code_change']
        }]
        r=detect_conflicts(n)
        self.assertTrue(any(c['name'] in ('dependencies','blocked_task_ownership') for c in r['checks']))

if __name__ == '__main__':
    unittest.main()

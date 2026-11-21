import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from devobs.integration_verification.inventory import build_inventory

class InventoryTests(unittest.TestCase):
    def test_empty_repo_inventory(self):
        with TemporaryDirectory() as td:
            inv = build_inventory(Path(td))
            self.assertTrue(inv)
            self.assertTrue(all(c['verification_status'] in {'ABSENT','PARTIALLY_IMPLEMENTED','DOCUMENTATION_ONLY','IMPLEMENTED_UNVERIFIED','BLOCKED'} for c in inv))

    def test_valid_component_inventory(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root/'scripts').mkdir()
            (root/'scripts/check_two_agent_tasks.py').write_text('print(1)', encoding='utf-8')
            (root/'docs/agents').mkdir(parents=True)
            (root/'docs/agents/TWO_AGENT_COORDINATION.md').write_text('# doc', encoding='utf-8')
            (root/'tests').mkdir()
            (root/'tests/test_two_agent_tasks.py').write_text('import unittest', encoding='utf-8')
            inv = build_inventory(root)
            two = [c for c in inv if c['name']=='two_agent_task_contract'][0]
            self.assertEqual(two['test_coverage'], 'present')

    def test_documentation_only_component(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            (root/'docs/agents').mkdir(parents=True)
            (root/'docs/agents/TWO_AGENT_COORDINATION.md').write_text('x', encoding='utf-8')
            inv = build_inventory(root, extra_components=[{"name":"docs_only","paths":["docs/agents/TWO_AGENT_COORDINATION.md"],"tests":[],"deps":[]}])
            d=[c for c in inv if c['name']=='docs_only'][0]
            self.assertEqual(d['verification_status'],'DOCUMENTATION_ONLY')

if __name__ == '__main__':
    unittest.main()

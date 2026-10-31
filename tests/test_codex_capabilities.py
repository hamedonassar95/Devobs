"""Positive/negative offline behavior for Codex capability readiness checks."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_codex_capabilities import CapabilityError, main, validate  # noqa: E402


class CodexCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.data = json.loads((ROOT / 'docs/CODEX_CAPABILITY_INVENTORY.json').read_text())
        required = {name for feature in self.data['features'] for name in feature['source_paths']}
        for name in required:
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('synthetic source marker\n')
        config = self.root / '.codex/config.toml'
        config.parent.mkdir(parents=True, exist_ok=True)
        self.config = ('[agents]\nenabled = true\nmax_concurrent_threads_per_session = 2\n'
                       '[mcp_servers.openaiDeveloperDocs]\nurl = "https://developers.openai.com/mcp"\n')
        config.write_text(self.config)
        ledger = self.root / 'docs/MILESTONE_LEDGER.json'
        ledger.write_text(json.dumps({'gates': [
            {'id': 'p01-managed-saas', 'status': 'BLOCKED'},
            {'id': 'ai9-detection-quality', 'status': 'BLOCKED'}]}))

    def refuse(self, edit):
        data = copy.deepcopy(self.data)
        edit(data)
        with self.assertRaises(CapabilityError):
            validate(data, self.root)

    def test_positive_offline_evidence_never_counts_runtime(self):
        result = validate(self.data, self.root)
        self.assertEqual(result['total'], 16)
        self.assertEqual(result['runtime_verified'], 0)
        self.assertGreater(result['needs_runtime_or_external_proof'], 10)

    def test_missing_source_file_fails_closed(self):
        (self.root / 'AGENTS.md').unlink()
        with self.assertRaises(CapabilityError):
            validate(self.data, self.root)

    def test_traversal_reference_rejected(self):
        self.refuse(lambda d: d['features'][2]['source_paths'].__setitem__(0, '../secrets'))

    def test_unauthorized_runtime_promotion_rejected(self):
        self.refuse(lambda d: d['features'][4].__setitem__('runtime_verified', True))

    def test_unapproved_spend_and_merge_rejected(self):
        for key in ('paid_inference', 'merge'):
            with self.subTest(key=key):
                self.refuse(lambda d: d['permissions'].__setitem__(key, True))

    def test_cannot_promote_p01_or_ai9(self):
        for gate in ('P01', 'AI-9'):
            with self.subTest(gate=gate):
                self.refuse(lambda d: d['gate_status'].__setitem__(gate, 'READY'))

    def test_duplicate_feature_rejected(self):
        self.refuse(lambda d: d['features'][5].__setitem__('id', d['features'][4]['id']))

    def test_untrusted_official_link_rejected(self):
        self.refuse(lambda d: d['features'][0].__setitem__('official_reference', 'https://docs.example.net/evil'))

    def test_config_drift_rejected(self):
        (self.root / '.codex/config.toml').write_text('[agents]\nenabled = false\n')
        with self.assertRaises(CapabilityError):
            validate(self.data, self.root)

    def test_new_unreviewed_hook_rejected(self):
        (self.root / '.codex/hooks.json').write_text('{}')
        with self.assertRaisesRegex(CapabilityError, 'hooks'):
            validate(self.data, self.root)

    def test_gates_cannot_be_misrepresented(self):
        ledger = self.root / 'docs/MILESTONE_LEDGER.json'
        ledger.write_text(json.dumps({'gates': [
            {'id': 'p01-managed-saas', 'status': 'OPEN'},
            {'id': 'ai9-detection-quality', 'status': 'BLOCKED'}]}))
        with self.assertRaisesRegex(CapabilityError, 'gate'):
            validate(self.data, self.root)

    def test_cli_rejects_invalid_json(self):
        bad = self.root / 'bad.json'
        bad.write_text('{not valid')
        self.assertEqual(main(['--file', str(bad), '--root', str(self.root)]), 1)


if __name__ == '__main__':
    unittest.main()

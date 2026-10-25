"""Synthetic tampering/idempotency/metadata-only audit tests."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.policy import evaluate_action
from devobs_intelligence.audit_store import AuditStore, AuditError


def event(event_id='example-01', sha='a'*40):
    return parse_event({'schema_version':1,'event_id':event_id,'provider':'github',
                        'project_ref':'SENSITIVE_REPOSITORY','source_sha':sha,
                        'kind':'incident','observed_at':'2026-10-25T12:00:00Z',
                        'evidence_digests':['b'*64]})


class AuditStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'audit.sqlite3')
        self.store = AuditStore(self.path)
        self.addCleanup(self.store.close)

    def test_append_verify_and_safe_summary(self):
        current = event()
        result = self.store.append(current, evaluate_action(current,'propose_patch'),'propose_patch')
        self.assertEqual((result.sequence, self.store.verify()), (1, 1))
        self.assertEqual(self.store.summary()['record_count'], 1)
        self.assertNotIn('SENSITIVE_REPOSITORY', str(result))
        self.assertNotIn('SENSITIVE_REPOSITORY', str(self.store.summary()))

    def test_duplicate_delivery_is_idempotent(self):
        current = event()
        evaluation = evaluate_action(current,'read_evidence')
        first = self.store.append(current, evaluation, 'read_evidence')
        second = self.store.append(current, evaluation, 'read_evidence')
        self.assertEqual(first, second)
        self.assertEqual(self.store.verify(), 1)

    def test_duplicate_event_conflicting_sha_is_rejected(self):
        original, changed = event(), event(sha='c'*40)
        self.store.append(original, evaluate_action(original,'read_evidence'), 'read_evidence')
        with self.assertRaisesRegex(AuditError,'duplicate_conflict'):
            self.store.append(changed, evaluate_action(changed,'read_evidence'), 'read_evidence')

    def test_detects_modified_decision_and_blocks_new_writes(self):
        current=event()
        self.store.append(current,evaluate_action(current,'read_evidence'),'read_evidence')
        self.store.connection.execute("UPDATE audit SET decision='DENY' WHERE seq=1")
        with self.assertRaisesRegex(AuditError, 'chain_invalid'):
            self.store.verify()
        with self.assertRaisesRegex(AuditError, 'chain_invalid'):
            self.store.append(event('later'),evaluate_action(event('later'),'read_evidence'),'read_evidence')

    def test_detects_deleted_row_in_middle(self):
        for key in ('a1','a2','a3'):
            current=event(key)
            self.store.append(current,evaluate_action(current,'read_evidence'),'read_evidence')
        self.store.connection.execute('DELETE FROM audit WHERE seq=2')
        with self.assertRaisesRegex(AuditError,'chain_invalid'):
            self.store.verify()

    def test_rejects_unrecognized_action_and_unsourced_evaluation(self):
        current=event()
        with self.assertRaisesRegex(AuditError,'invalid_entry'):
            self.store.append(current,evaluate_action(current,'read_evidence'),'run_shell')
        with self.assertRaisesRegex(AuditError,'invalid_entry'):
            self.store.append(current,evaluate_action(event('other'),'read_evidence'),'read_evidence')

    def test_ledger_persists_on_reopen(self):
        current=event()
        self.store.append(current,evaluate_action(current,'read_evidence'),'read_evidence')
        second=AuditStore(self.path)
        self.addCleanup(second.close)
        self.assertEqual(second.verify(),1)

    def test_invalid_database_uri_is_rejected(self):
        with self.assertRaisesRegex(AuditError,'invalid_path'):
            AuditStore('file:shared?mode=memory&cache=shared')


if __name__=='__main__': unittest.main()

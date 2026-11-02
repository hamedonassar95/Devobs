"""Synthetic tampering/idempotency/metadata-only audit tests."""
import hashlib
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.context import ServiceTopologySnapshot
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.policy import evaluate_action
from devobs_intelligence.audit_store import AuditStore, AuditError


def event(event_id='example-01', sha='a'*40):
    return parse_event({'schema_version':1,'event_id':event_id,'provider':'github',
                        'project_ref':'SENSITIVE_REPOSITORY','source_sha':sha,
                        'kind':'incident','observed_at':'2026-10-25T12:00:00Z',
                        'evidence_digests':['b'*64]})


def topology_pair():
    before = ServiceTopologySnapshot(
        'alpha', 'platform', ['api', 'db'], [('api', 'db')],
        'a' * 40, '2026-10-25T11:59:00Z',
    )
    after = ServiceTopologySnapshot(
        'alpha', 'platform', ['api', 'db', 'web'],
        [('api', 'db'), ('web', 'api')],
        'b' * 40, '2026-10-25T12:00:00Z',
    )
    source = parse_event({
        'schema_version': 1, 'event_id': 'source-incident-01',
        'provider': 'github', 'project_ref': 'alpha/platform',
        'source_sha': 'b' * 40, 'kind': 'incident',
        'observed_at': '2026-10-25T12:00:00Z',
        'evidence_digests': ['c' * 64],
    })
    return source, before, after


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

    def test_checkpoint_verifies_an_independently_retained_prefix_after_appends(self):
        first = event('checkpoint-first')
        self.store.append(first, evaluate_action(first, 'read_evidence'), 'read_evidence')
        checkpoint = self.store.create_checkpoint()
        self.assertEqual(checkpoint.to_record(), {
            'schema_version': 1,
            'record_count': 1,
            'head_hash': self.store.summary()['last_record_hash'],
        })

        later = event('checkpoint-later')
        self.store.append(later, evaluate_action(later, 'read_evidence'), 'read_evidence')
        self.assertEqual(self.store.verify_checkpoint(checkpoint.to_record()), 2)

    def test_checkpoint_detects_a_validly_rehashed_rewrite(self):
        original = event('checkpoint-rewrite', sha='a' * 40)
        self.store.append(original, evaluate_action(original, 'read_evidence'), 'read_evidence')
        checkpoint = self.store.create_checkpoint().to_record()

        self.store.connection.execute(
            "UPDATE audit SET source_sha=? WHERE event_id=?",
            ('c' * 40, original.event_id),
        )
        previous = '0' * 64
        rows = self.store.connection.execute(
            'SELECT seq,event_id,source_sha,policy_version,decision,action,subject_digest '
            'FROM audit ORDER BY seq',
        ).fetchall()
        for seq, event_id, source_sha, policy_version, decision, action, subject_digest in rows:
            item = {
                'event_id': event_id,
                'source_sha': source_sha,
                'policy_version': policy_version,
                'decision': decision,
                'action': action,
            }
            if subject_digest:
                item['subject_digest'] = subject_digest
            payload = json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
            record_hash = hashlib.sha256((previous + '\n' + payload).encode('utf-8')).hexdigest()
            self.store.connection.execute(
                'UPDATE audit SET previous_hash=?,record_hash=? WHERE seq=?',
                (previous, record_hash, seq),
            )
            previous = record_hash

        self.assertEqual(self.store.verify(), 1)
        with self.assertRaisesRegex(AuditError, '^checkpoint_mismatch$'):
            self.store.verify_checkpoint(checkpoint)

    def test_checkpoint_parser_rejects_noncanonical_or_malformed_records(self):
        for record in (
            {'schema_version': True, 'record_count': 0, 'head_hash': '0' * 64},
            {'schema_version': 1, 'record_count': True, 'head_hash': '0' * 64},
            {'schema_version': 1, 'record_count': 0, 'head_hash': 'a' * 64},
            {'schema_version': 1, 'record_count': 1, 'head_hash': '0' * 64},
            {'schema_version': 1, 'record_count': 0, 'head_hash': '0' * 64, 'extra': 1},
        ):
            with self.subTest(record=record), self.assertRaisesRegex(
                    AuditError, '^invalid_checkpoint$'):
                self.store.verify_checkpoint(record)

    def test_append_reserves_write_transaction_before_reading_chain(self):
        statements=[]
        self.store.connection.set_trace_callback(statements.append)
        current=event()
        self.store.append(current,evaluate_action(current,'read_evidence'),'read_evidence')
        self.store.connection.set_trace_callback(None)
        self.assertEqual(statements[0], 'BEGIN IMMEDIATE')
        self.assertEqual(statements[-1], 'COMMIT')

    def test_summary_uses_one_verified_snapshot(self):
        current=event()
        first=self.store.append(current,evaluate_action(current,'read_evidence'),'read_evidence')
        original_entries=self.store._entries
        appended=False

        def interleave_append():
            nonlocal appended
            snapshot=original_entries()
            if not appended:
                appended=True
                later=event('interleaved')
                self.store.append(later,evaluate_action(later,'read_evidence'),'read_evidence')
            return snapshot

        with patch.object(self.store,'_entries',side_effect=interleave_append):
            summary=self.store.summary()
        self.assertEqual(summary['record_count'],1)
        self.assertEqual(summary['last_record_hash'],first.record_hash)
        self.assertEqual(self.store.verify(),2)

    def test_concurrent_writers_preserve_one_valid_chain(self):
        writers=8
        start=Barrier(writers)

        def append_from_separate_connection(index):
            connection=AuditStore(self.path)
            try:
                current=event(f'parallel-{index}', sha=format(index+1,'040x'))
                evaluation=evaluate_action(current,'read_evidence')
                start.wait(timeout=5)
                return connection.append(current,evaluation,'read_evidence').sequence
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=writers) as pool:
            sequences=list(pool.map(append_from_separate_connection,range(writers)))
        self.assertEqual(sorted(sequences),list(range(1,writers+1)))
        self.assertEqual(self.store.verify(),writers)

    def test_invalid_database_uri_is_rejected(self):
        with self.assertRaisesRegex(AuditError,'invalid_path'):
            AuditStore('file:shared?mode=memory&cache=shared')

    def test_topology_drift_digest_is_linked_idempotently_without_graph_data(self):
        source, before, after = topology_pair()
        report, entry = self.store.record_topology_drift(source, before, after)
        self.assertEqual(entry.action, 'read_evidence')
        self.assertEqual(entry.source_sha, 'b' * 40)
        self.assertEqual(entry.subject_digest, report.to_record()['report_digest'])
        self.assertEqual(self.store.verify(), 1)
        persisted = self.store.connection.execute(
            'SELECT event_id,source_sha,policy_version,decision,action,previous_hash,'
            'record_hash,subject_digest FROM audit',
        ).fetchone()
        self.assertNotIn('api', repr(persisted))
        self.assertNotIn('platform', repr(persisted))
        self.assertNotIn('alpha', repr(persisted))
        self.assertNotIn('platform', str(self.store.summary()))

        repeated_report, repeated_entry = self.store.record_topology_drift(
            source, before, after,
        )
        self.assertEqual(repeated_report, report)
        self.assertEqual(repeated_entry, entry)
        self.assertEqual(self.store.verify(), 1)

    def test_topology_drift_audit_rejects_scope_or_source_mismatch_before_write(self):
        source, before, after = topology_pair()
        mismatched_scope = parse_event({
            'schema_version': 1, 'event_id': 'wrong-scope',
            'provider': 'github', 'project_ref': 'other/platform',
            'source_sha': 'b' * 40, 'kind': 'incident',
            'observed_at': '2026-10-25T12:00:00Z',
            'evidence_digests': ['c' * 64],
        })
        mismatched_sha = parse_event({
            'schema_version': 1, 'event_id': 'wrong-sha',
            'provider': 'github', 'project_ref': 'alpha/platform',
            'source_sha': 'a' * 40, 'kind': 'incident',
            'observed_at': '2026-10-25T12:00:00Z',
            'evidence_digests': ['c' * 64],
        })
        for candidate in (mismatched_scope, mismatched_sha):
            with self.subTest(event_id=candidate.event_id), self.assertRaisesRegex(
                    AuditError, 'invalid_topology_binding'):
                self.store.record_topology_drift(candidate, before, after)
        self.assertEqual(self.store.verify(), 0)


if __name__=='__main__': unittest.main()

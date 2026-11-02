"""Behavioral tests for the local, read-only intelligence audit report."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from devobs_intelligence.audit_store import AuditStore  # noqa: E402
from devobs_intelligence.contracts import parse_event  # noqa: E402
from devobs_intelligence.policy import evaluate_action  # noqa: E402


REPORT_SCRIPT = ROOT / 'scripts' / 'intelligence_report.py'


def _event(event_id='private-event-123'):
    return parse_event({
        'schema_version': 1,
        'event_id': event_id,
        'provider': 'github',
        'project_ref': 'SENSITIVE_REPOSITORY',
        'source_sha': 'a' * 40,
        'kind': 'incident',
        'observed_at': '2026-10-25T12:00:00Z',
        'evidence_digests': ['b' * 64],
    })


def _file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IntelligenceReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'audit.sqlite3'

    def _run_report(self, path=None):
        return subprocess.run(
            [sys.executable, str(REPORT_SCRIPT), '--database', str(path or self.database)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_verified_report_is_redacted_and_does_not_modify_database(self):
        store = AuditStore(str(self.database))
        try:
            event = _event()
            store.append(event, evaluate_action(event, 'read_evidence'), 'read_evidence')
            expected = store.summary()
        finally:
            store.close()
        before = _file_sha256(self.database)

        result = self._run_report()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report, {
            'schema_version': 1,
            'status': 'ok',
            'check': 'local_audit_chain',
            'chain_valid': True,
            'read_only': True,
            'record_count': expected['record_count'],
            'last_record_hash': expected['last_record_hash'],
        })
        self.assertNotIn('SENSITIVE_REPOSITORY', result.stdout)
        self.assertNotIn('private-event-123', result.stdout)
        self.assertEqual(_file_sha256(self.database), before)

    def test_missing_database_returns_fixed_error_without_creating_file(self):
        missing = Path(self.temp.name) / 'missing.sqlite3'

        result = self._run_report(missing)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'storage_unavailable',
        })
        self.assertNotIn(str(missing), result.stderr)
        self.assertFalse(missing.exists())

    def test_corrupted_chain_returns_fixed_error_without_private_identifiers(self):
        store = AuditStore(str(self.database))
        try:
            event = _event()
            store.append(event, evaluate_action(event, 'read_evidence'), 'read_evidence')
            store.connection.execute("UPDATE audit SET decision='DENY' WHERE seq=1")
        finally:
            store.close()
        before = _file_sha256(self.database)

        result = self._run_report()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'chain_invalid',
        })
        self.assertNotIn('SENSITIVE_REPOSITORY', result.stderr)
        self.assertNotIn('private-event-123', result.stderr)
        self.assertNotIn(str(self.database), result.stderr)
        self.assertEqual(_file_sha256(self.database), before)

    def test_incompatible_schema_returns_fixed_error_without_migration(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute('CREATE TABLE audit (seq INTEGER PRIMARY KEY, event_id TEXT)')
        before = _file_sha256(self.database)

        result = self._run_report()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'unsupported_schema',
        })
        self.assertEqual(_file_sha256(self.database), before)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                {row[1] for row in connection.execute('PRAGMA table_info(audit)')},
                {'seq', 'event_id'},
            )


if __name__ == '__main__':
    unittest.main()

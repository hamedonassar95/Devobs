"""Behavioral tests for the local, read-only intelligence audit report."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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

    def _run_report(self, path=None, *, checkpoint=None, public_key=None):
        command = [
            sys.executable, str(REPORT_SCRIPT), '--database',
            str(path or self.database),
        ]
        if checkpoint is not None:
            command.extend(['--signed-checkpoint', str(checkpoint)])
        if public_key is not None:
            command.extend(['--trusted-public-key', str(public_key)])
        return subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def _write_signed_checkpoint(self, *, private_key=None):
        private_key = private_key or Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        store = AuditStore(str(self.database))
        try:
            first = _event('checkpoint-prefix-private-event')
            store.append(first, evaluate_action(first, 'read_evidence'), 'read_evidence')
            signed = store.create_signed_checkpoint(private_key)
            later = _event('later-private-event')
            store.append(later, evaluate_action(later, 'read_evidence'), 'read_evidence')
            summary = store.summary()
        finally:
            store.close()

        checkpoint_path = Path(self.temp.name) / 'checkpoint.json'
        checkpoint_path.write_text(json.dumps(signed), encoding='utf-8')
        public_key_path = Path(self.temp.name) / 'trusted-public-key.bin'
        public_key_path.write_bytes(private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        ))
        return checkpoint_path, public_key_path, signed, summary

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

    def test_signed_checkpoint_is_verified_as_a_prefix_without_modifying_inputs(self):
        checkpoint_path, public_key_path, signed, expected = self._write_signed_checkpoint()
        before = {
            path: _file_sha256(path)
            for path in (self.database, checkpoint_path, public_key_path)
        }

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['record_count'], expected['record_count'])
        self.assertEqual(report['last_record_hash'], expected['last_record_hash'])
        self.assertEqual(report['signed_checkpoint'], {
            'signature_valid': True,
            'checkpoint_record_count': signed['checkpoint']['record_count'],
        })
        self.assertNotIn('checkpoint-prefix-private-event', result.stdout)
        self.assertNotIn('later-private-event', result.stdout)
        self.assertEqual({path: _file_sha256(path) for path in before}, before)

    def test_invalid_checkpoint_signature_returns_fixed_error_and_does_not_write(self):
        checkpoint_path, public_key_path, signed, _ = self._write_signed_checkpoint()
        signature = signed['signature']
        signed['signature'] = signature[:-1] + ('A' if signature[-1] != 'A' else 'B')
        checkpoint_path.write_text(json.dumps(signed), encoding='utf-8')
        before = _file_sha256(self.database)

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'checkpoint_signature_invalid',
        })
        self.assertNotIn(str(checkpoint_path), result.stderr)
        self.assertNotIn('checkpoint-prefix-private-event', result.stderr)
        self.assertEqual(_file_sha256(self.database), before)

    def test_incomplete_checkpoint_arguments_fail_closed(self):
        checkpoint_path, _, _, _ = self._write_signed_checkpoint()
        before = _file_sha256(self.database)

        result = self._run_report(checkpoint=checkpoint_path)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'invalid_checkpoint_options',
        })
        self.assertEqual(_file_sha256(self.database), before)

    def test_duplicate_json_keys_in_checkpoint_are_rejected(self):
        _, public_key_path, _, _ = self._write_signed_checkpoint()
        checkpoint_path = Path(self.temp.name) / 'duplicate.json'
        checkpoint_path.write_text(
            '{"schema_version":1,"schema_version":1}', encoding='utf-8',
        )

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'invalid_signed_checkpoint',
        })

    def test_wrong_trusted_public_key_returns_fixed_error(self):
        checkpoint_path, _, _, _ = self._write_signed_checkpoint()
        wrong_key = Ed25519PrivateKey.from_private_bytes(bytes(reversed(range(32))))
        public_key_path = Path(self.temp.name) / 'wrong-public-key.bin'
        public_key_path.write_bytes(wrong_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        ))

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'checkpoint_key_mismatch',
        })

    def test_missing_checkpoint_returns_fixed_error_without_disclosing_path(self):
        _, public_key_path, _, _ = self._write_signed_checkpoint()
        missing = Path(self.temp.name) / 'missing-checkpoint.json'

        result = self._run_report(
            checkpoint=missing,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'checkpoint_unavailable',
        })
        self.assertNotIn(str(missing), result.stderr)

    def test_missing_trusted_key_returns_fixed_error_without_disclosing_path(self):
        checkpoint_path, _, _, _ = self._write_signed_checkpoint()
        missing = Path(self.temp.name) / 'missing-public-key.bin'

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=missing,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'verification_key_unavailable',
        })
        self.assertNotIn(str(missing), result.stderr)

    def test_oversized_checkpoint_is_rejected_before_json_parsing(self):
        _, public_key_path, _, _ = self._write_signed_checkpoint()
        checkpoint_path = Path(self.temp.name) / 'large-checkpoint.json'
        checkpoint_path.write_bytes(b'x' * (16 * 1024 + 1))

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'checkpoint_too_large',
        })

    def test_non_raw_public_key_is_rejected(self):
        checkpoint_path, _, _, _ = self._write_signed_checkpoint()
        public_key_path = Path(self.temp.name) / 'hex-public-key.txt'
        public_key_path.write_text('not-a-raw-key', encoding='utf-8')

        result = self._run_report(
            checkpoint=checkpoint_path,
            public_key=public_key_path,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {
            'schema_version': 1,
            'status': 'error',
            'error_code': 'invalid_verification_key',
        })


if __name__ == '__main__':
    unittest.main()

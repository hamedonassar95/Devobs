#!/usr/bin/env python3
"""Print a redacted status for an existing local audit ledger.

This command uses only AuditStore.open_readonly. It verifies the SQLite
hash-chain visible to this process; it does not establish trusted external
retention or protect against a privileged writer replacing the database.
"""
from __future__ import annotations

import argparse
import json
import sys

from devobs_intelligence.audit_store import AuditError, AuditStore


_CHECKPOINT_FILE_LIMIT = 16 * 1024
_PUBLIC_KEY_LENGTH = 32

_ERROR_CODES = frozenset({
    'chain_invalid',
    'checkpoint_key_mismatch',
    'checkpoint_mismatch',
    'checkpoint_signature_invalid',
    'checkpoint_too_large',
    'checkpoint_unavailable',
    'invalid_checkpoint_options',
    'invalid_path',
    'invalid_signed_checkpoint',
    'invalid_verification_key',
    'storage_unavailable',
    'unsupported_schema',
    'verification_key_unavailable',
})


def _read_bounded(path: str, limit: int, *, unavailable_code: str,
                  oversized_code: str) -> bytes:
    try:
        with open(path, 'rb') as stream:
            data = stream.read(limit + 1)
    except (OSError, ValueError):
        raise AuditError(unavailable_code) from None
    if len(data) > limit:
        raise AuditError(oversized_code)
    return data


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _load_signed_checkpoint(checkpoint_path: str,
                            public_key_path: str) -> tuple[dict[str, object], bytes]:
    checkpoint_bytes = _read_bounded(
        checkpoint_path,
        _CHECKPOINT_FILE_LIMIT,
        unavailable_code='checkpoint_unavailable',
        oversized_code='checkpoint_too_large',
    )
    try:
        checkpoint = json.loads(
            checkpoint_bytes.decode('utf-8'),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise AuditError('invalid_signed_checkpoint') from None
    if type(checkpoint) is not dict:
        raise AuditError('invalid_signed_checkpoint')

    public_key = _read_bounded(
        public_key_path,
        _PUBLIC_KEY_LENGTH,
        unavailable_code='verification_key_unavailable',
        oversized_code='invalid_verification_key',
    )
    if len(public_key) != _PUBLIC_KEY_LENGTH:
        raise AuditError('invalid_verification_key')
    return checkpoint, public_key


def _report(database: str, *, signed_checkpoint_path: str | None = None,
            trusted_public_key_path: str | None = None) -> dict[str, object]:
    if (signed_checkpoint_path is None) != (trusted_public_key_path is None):
        raise AuditError('invalid_checkpoint_options')

    signed_checkpoint = None
    trusted_public_key = None
    if signed_checkpoint_path is not None and trusted_public_key_path is not None:
        signed_checkpoint, trusted_public_key = _load_signed_checkpoint(
            signed_checkpoint_path, trusted_public_key_path,
        )

    store = AuditStore.open_readonly(database)
    try:
        summary = store.summary()
        if signed_checkpoint is not None and trusted_public_key is not None:
            store.verify_signed_checkpoint(signed_checkpoint, trusted_public_key)
    finally:
        store.close()

    report: dict[str, object] = {
        'schema_version': 1,
        'status': 'ok',
        'check': 'local_audit_chain',
        'chain_valid': True,
        'read_only': True,
        'record_count': summary['record_count'],
        'last_record_hash': summary['last_record_hash'],
    }
    if signed_checkpoint is not None:
        checkpoint_record = signed_checkpoint.get('checkpoint')
        if type(checkpoint_record) is not dict:
            raise AuditError('invalid_signed_checkpoint')
        checkpoint_record_count = checkpoint_record.get('record_count')
        if type(checkpoint_record_count) is not int:
            raise AuditError('invalid_signed_checkpoint')
        report['signed_checkpoint'] = {
            'signature_valid': True,
            'checkpoint_record_count': checkpoint_record_count,
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Verify and summarize an existing local Devobs audit database. '
            'The database is opened read-only; output excludes record contents.'
        ),
        epilog=(
            'A valid local hash chain is not proof of protected external '
            'retention or hosted-service integrity. Signed-checkpoint input '
            'requires both checkpoint and trusted raw Ed25519 public-key files.'
        ),
    )
    parser.add_argument(
        '--database', required=True,
        help='path to an existing SQLite audit database',
    )
    parser.add_argument(
        '--signed-checkpoint',
        help='optional signed checkpoint JSON file (requires --trusted-public-key)',
    )
    parser.add_argument(
        '--trusted-public-key',
        help='trusted raw 32-byte Ed25519 public-key file; private keys are not read',
    )
    args = parser.parse_args(argv)
    try:
        output = _report(
            args.database,
            signed_checkpoint_path=args.signed_checkpoint,
            trusted_public_key_path=args.trusted_public_key,
        )
    except AuditError as exc:
        candidate = str(exc)
        code = candidate if candidate in _ERROR_CODES else 'report_failed'
        print(json.dumps({
            'schema_version': 1,
            'status': 'error',
            'error_code': code,
        }, sort_keys=True, separators=(',', ':')), file=sys.stderr)
        return 2
    except Exception:
        # Keep unexpected database/runtime details and user paths out of output.
        print(json.dumps({
            'schema_version': 1,
            'status': 'error',
            'error_code': 'report_failed',
        }, sort_keys=True, separators=(',', ':')), file=sys.stderr)
        return 2

    print(json.dumps(output, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

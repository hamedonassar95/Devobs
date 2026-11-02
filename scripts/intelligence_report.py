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


_ERROR_CODES = frozenset({
    'chain_invalid',
    'invalid_path',
    'storage_unavailable',
    'unsupported_schema',
})


def _report(database: str) -> dict[str, object]:
    store = AuditStore.open_readonly(database)
    try:
        summary = store.summary()
    finally:
        store.close()
    return {
        'schema_version': 1,
        'status': 'ok',
        'check': 'local_audit_chain',
        'chain_valid': True,
        'read_only': True,
        'record_count': summary['record_count'],
        'last_record_hash': summary['last_record_hash'],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Verify and summarize an existing local Devobs audit database. '
            'The database is opened read-only; output excludes record contents.'
        ),
        epilog=(
            'A valid local hash chain is not proof of protected external '
            'retention or hosted-service integrity.'
        ),
    )
    parser.add_argument(
        '--database', required=True,
        help='path to an existing SQLite audit database',
    )
    args = parser.parse_args(argv)
    try:
        output = _report(args.database)
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

"""Locally verifiable, append-only logical audit ledger (not a tamper-proof service)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from .contracts import EventEnvelopeV1
from .policy import EvaluationV1


class AuditError(ValueError):
    """Fixed codes prevent accidental disclosure of stored data."""


@dataclass(frozen=True)
class AuditEntryV1:
    sequence: int
    event_id: str
    source_sha: str
    policy_version: str
    decision: str
    action: str
    previous_hash: str
    record_hash: str


def _digest(previous: str, item: dict) -> str:
    payload = json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256((previous + '\n' + payload).encode('utf-8')).hexdigest()


class AuditStore:
    """SQLite local store; a privileged DB writer could rewrite the entire chain.

    A separately anchored hash or signed storage is required for tamper evidence
    against privileged attackers; this module detects ordinary row modifications.
    """

    def __init__(self, path: str):
        if type(path) is not str or not path or path.startswith('file:'):
            raise AuditError('invalid_path')
        try:
            self.connection = sqlite3.connect(path, isolation_level=None)
            self.connection.execute('PRAGMA busy_timeout=2000')
            self.connection.execute('CREATE TABLE IF NOT EXISTS audit ('
                'seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,'
                'source_sha TEXT NOT NULL, policy_version TEXT NOT NULL,'
                'decision TEXT NOT NULL, action TEXT NOT NULL,'
                'previous_hash TEXT NOT NULL, record_hash TEXT NOT NULL,'
                'UNIQUE(event_id, action))')
        except sqlite3.Error:
            raise AuditError('storage_unavailable') from None

    def close(self) -> None:
        self.connection.close()

    def _entries(self) -> list[AuditEntryV1]:
        try:
            records = self.connection.execute('SELECT seq,event_id,source_sha,policy_version,'
                'decision,action,previous_hash,record_hash FROM audit ORDER BY seq').fetchall()
        except sqlite3.Error:
            raise AuditError('storage_unavailable') from None
        return [AuditEntryV1(*row) for row in records]

    def verify(self) -> int:
        previous = '0' * 64
        entries = self._entries()
        for index, entry in enumerate(entries, 1):
            item = {key: getattr(entry, key) for key in ('event_id', 'source_sha',
                        'policy_version', 'decision', 'action')}
            if (entry.sequence != index or entry.previous_hash != previous
                or entry.record_hash != _digest(previous, item)):
                raise AuditError('chain_invalid')
            previous = entry.record_hash
        return len(entries)

    def append(self, event: EventEnvelopeV1, evaluation: EvaluationV1,
               action: str) -> AuditEntryV1:
        if (type(event) is not EventEnvelopeV1 or type(evaluation) is not EvaluationV1
            or evaluation.event_id != event.event_id or type(action) is not str
            or action not in {'read_evidence', 'propose_patch', 'open_draft_pr',
                               'write_branch', 'merge', 'deploy', 'rollback', 'delete',
                               'billing', 'change_permissions'}
            or evaluation.decision not in {'ALLOW_READ','PROPOSE_ONLY','DENY'}):
            raise AuditError('invalid_entry')
        try:
            # Acquire the write reservation before reading the chain. Without
            # this, concurrent writers can hash the same tail and persist a
            # fork that makes subsequent verification fail permanently.
            self.connection.execute('BEGIN IMMEDIATE')
        except sqlite3.Error:
            raise AuditError('storage_unavailable') from None

        try:
            self.verify()
            existing = [e for e in self._entries()
                        if e.event_id == event.event_id and e.action == action]
            if existing:
                old = existing[0]
                if (old.source_sha != event.source_sha
                    or old.policy_version != evaluation.policy_version
                    or old.decision != evaluation.decision):
                    raise AuditError('duplicate_conflict')
                self.connection.execute('COMMIT')
                return old

            entries = self._entries()
            previous = entries[-1].record_hash if entries else '0' * 64
            item = {'event_id':event.event_id,'source_sha':event.source_sha,
                    'policy_version':evaluation.policy_version,'decision':evaluation.decision,
                    'action':action}
            record_hash = _digest(previous, item)
            self.connection.execute('INSERT INTO audit (event_id,source_sha,policy_version,'
                'decision,action,previous_hash,record_hash) VALUES (?,?,?,?,?,?,?)',
                (event.event_id,event.source_sha,evaluation.policy_version,evaluation.decision,
                 action,previous,record_hash))
            self.verify()
            result = self._entries()[-1]
            self.connection.execute('COMMIT')
            return result
        except sqlite3.IntegrityError:
            self._rollback_append()
            raise AuditError('concurrent_conflict') from None
        except sqlite3.Error:
            self._rollback_append()
            raise AuditError('storage_unavailable') from None
        except Exception:
            self._rollback_append()
            raise

    def _rollback_append(self) -> None:
        """Roll back only this append transaction, preserving fixed errors."""
        if self.connection.in_transaction:
            try:
                self.connection.execute('ROLLBACK')
            except sqlite3.Error:
                pass

    def summary(self) -> dict:
        count = self.verify()
        return {'schema_version':1,'record_count':count,
                'last_record_hash':self._entries()[-1].record_hash if count else None}

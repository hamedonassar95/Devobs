"""Locally verifiable, append-only logical audit ledger (not a tamper-proof service)."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .context import ServiceTopologySnapshot
from .contracts import EventEnvelopeV1, EvidenceError, parse_event
from .policy import EvaluationV1, evaluate_action
from .topology_drift import TopologyDriftReport, compare_topology_snapshots

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")

if TYPE_CHECKING:
    from .correlation import IncidentFinding


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
    subject_digest: str | None = None


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
                "subject_digest TEXT NOT NULL DEFAULT '',"
                'UNIQUE(event_id, action))')
            columns = {row[1] for row in self.connection.execute(
                'PRAGMA table_info(audit)').fetchall()}
            if 'subject_digest' not in columns:
                self.connection.execute(
                    "ALTER TABLE audit ADD COLUMN subject_digest TEXT NOT NULL DEFAULT ''")
        except sqlite3.Error:
            raise AuditError('storage_unavailable') from None

    def close(self) -> None:
        self.connection.close()

    def _entries(self) -> list[AuditEntryV1]:
        try:
            records = self.connection.execute('SELECT seq,event_id,source_sha,policy_version,'
                'decision,action,previous_hash,record_hash,subject_digest '
                'FROM audit ORDER BY seq').fetchall()
        except sqlite3.Error:
            raise AuditError('storage_unavailable') from None
        return [AuditEntryV1(*row[:8], row[8] or None) for row in records]

    @staticmethod
    def _verify_entries(entries: list[AuditEntryV1]) -> int:
        previous = '0' * 64
        for index, entry in enumerate(entries, 1):
            item = {key: getattr(entry, key) for key in ('event_id', 'source_sha',
                        'policy_version', 'decision', 'action')}
            if entry.subject_digest is not None:
                if (type(entry.subject_digest) is not str
                        or _DIGEST.fullmatch(entry.subject_digest) is None):
                    raise AuditError('chain_invalid')
                item['subject_digest'] = entry.subject_digest
            if (entry.sequence != index or entry.previous_hash != previous
                or entry.record_hash != _digest(previous, item)):
                raise AuditError('chain_invalid')
            previous = entry.record_hash
        return len(entries)

    def verify(self) -> int:
        return self._verify_entries(self._entries())

    def append(self, event: EventEnvelopeV1, evaluation: EvaluationV1,
               action: str, *, subject_digest: str | None = None) -> AuditEntryV1:
        if (type(event) is not EventEnvelopeV1 or type(evaluation) is not EvaluationV1
            or evaluation.event_id != event.event_id or type(action) is not str
            or action not in {'read_evidence', 'propose_patch', 'open_draft_pr',
                               'write_branch', 'merge', 'deploy', 'rollback', 'delete',
                               'billing', 'change_permissions'}
            or evaluation != evaluate_action(event, action)
            or evaluation.decision not in {'ALLOW_READ','PROPOSE_ONLY','DENY'}
            or (subject_digest is not None and
                (type(subject_digest) is not str
                 or _DIGEST.fullmatch(subject_digest) is None))
            or (subject_digest is not None and action != 'read_evidence')):
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
                    or old.decision != evaluation.decision
                    or old.subject_digest != subject_digest):
                    raise AuditError('duplicate_conflict')
                self.connection.execute('COMMIT')
                return old

            entries = self._entries()
            previous = entries[-1].record_hash if entries else '0' * 64
            item = {'event_id':event.event_id,'source_sha':event.source_sha,
                    'policy_version':evaluation.policy_version,'decision':evaluation.decision,
                    'action':action}
            if subject_digest is not None:
                item['subject_digest'] = subject_digest
            record_hash = _digest(previous, item)
            self.connection.execute('INSERT INTO audit (event_id,source_sha,policy_version,'
                'decision,action,previous_hash,record_hash,subject_digest) '
                'VALUES (?,?,?,?,?,?,?,?)',
                (event.event_id,event.source_sha,evaluation.policy_version,evaluation.decision,
                 action,previous,record_hash,subject_digest or ''))
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

    def append_finding(self, event: EventEnvelopeV1,
                       finding: IncidentFinding) -> AuditEntryV1:
        """Bind a read-only finding digest to its tenant-qualified source event.

        ``project_ref`` in the source envelope must be exactly ``tenant/project``.
        The audit chain stores only the finding digest, not service names or payload.
        """
        from .correlation import IncidentFinding

        if type(event) is not EventEnvelopeV1 or type(finding) is not IncidentFinding:
            raise AuditError('invalid_finding_binding')
        try:
            record = finding.to_record()
            verified = IncidentFinding.from_record(record)
            project_ref = f'{verified.tenant}/{verified.project}'
            reconstructed = parse_event({
                'schema_version': event.schema_version,
                'event_id': event.event_id,
                'provider': event.provider,
                'project_ref': project_ref,
                'source_sha': event.source_sha,
                'kind': event.kind,
                'observed_at': event.observed_at,
                'evidence_digests': list(event.evidence_digests),
            })
        except (AttributeError, TypeError, ValueError, EvidenceError):
            raise AuditError('invalid_finding_binding') from None
        if (verified != finding or reconstructed != event
                or event.kind != 'incident'
                or event.source_sha != verified.source_sha
                or set(event.evidence_digests) != set(verified.evidence_digests)):
            raise AuditError('invalid_finding_binding')
        return self.append(event, evaluate_action(event, 'read_evidence'),
                           'read_evidence', subject_digest=record['finding_digest'])

    def record_topology_drift(
        self, event: EventEnvelopeV1,
        before: ServiceTopologySnapshot,
        after: ServiceTopologySnapshot,
    ) -> tuple[TopologyDriftReport, AuditEntryV1]:
        """Bind a validated topology-drift digest to the existing read-only chain.

        The chain stores only the digest and source SHA, not service names or graph
        contents. The caller's event and both snapshots are reconstructed before use.
        """
        if (type(event) is not EventEnvelopeV1
                or type(before) is not ServiceTopologySnapshot
                or type(after) is not ServiceTopologySnapshot):
            raise AuditError('invalid_topology_binding')
        try:
            report = compare_topology_snapshots(before, after)
            source_event = parse_event({
                'schema_version': event.schema_version,
                'event_id': event.event_id,
                'provider': event.provider,
                'project_ref': f'{report.tenant}/{report.project}',
                'source_sha': event.source_sha,
                'kind': event.kind,
                'observed_at': event.observed_at,
                'evidence_digests': list(event.evidence_digests),
            })
            record = report.to_record()
            report_digest = record['report_digest']
            audit_event = parse_event({
                'schema_version': 1,
                'event_id': f'topology-drift-{report_digest[:32]}',
                'provider': source_event.provider,
                'project_ref': f'{report.tenant}/{report.project}',
                'source_sha': report.after_source_sha,
                'kind': source_event.kind,
                'observed_at': report.after_captured_at,
                'evidence_digests': [report_digest],
            })
        except (AttributeError, TypeError, ValueError, EvidenceError):
            raise AuditError('invalid_topology_binding') from None
        if (source_event != event or source_event.kind != 'incident'
                or source_event.source_sha != report.after_source_sha
                or not _DIGEST.fullmatch(report_digest)):
            raise AuditError('invalid_topology_binding')
        entry = self.append(
            audit_event, evaluate_action(audit_event, 'read_evidence'),
            'read_evidence', subject_digest=report_digest,
        )
        return report, entry

    def _rollback_append(self) -> None:
        """Roll back only this append transaction, preserving fixed errors."""
        if self.connection.in_transaction:
            try:
                self.connection.execute('ROLLBACK')
            except sqlite3.Error:
                pass

    def summary(self) -> dict:
        entries = self._entries()
        count = self._verify_entries(entries)
        return {'schema_version':1,'record_count':count,
                'last_record_hash':entries[-1].record_hash if count else None}

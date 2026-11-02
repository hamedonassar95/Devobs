#!/usr/bin/env python3
"""Purely synthetic, credential-free DevObs intelligence demo (no network)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from devobs_intelligence.adviser import propose
from devobs_intelligence.audit_store import AuditStore
from devobs_intelligence.contracts import EventEnvelopeV1, parse_event
from devobs_intelligence.context import ServiceTopologySnapshot, Telemetry
from devobs_intelligence.correlation import correlate
from devobs_intelligence.incident_memory import IncidentMemory
from devobs_intelligence.policy import evaluate_action
from devobs_intelligence.topology_drift import compare_topology_snapshots
from devobs_intelligence.trusted_metric_batch import from_trusted_metric_batch

_DEMO_INSTANT = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
_DEMO_OBSERVED_AT = '2026-10-25T00:00:00Z'
_DEMO_SOURCE_SHA = 'a' * 40


def _synthetic_incident_evidence(
    *, now_utc: datetime,
) -> tuple[EventEnvelopeV1, tuple[Telemetry, ...]]:
    """Build one tenant-scoped event from the same validated synthetic metric."""
    observed_at_ns = int(_DEMO_INSTANT.timestamp()) * 1_000_000_000
    metrics = [
        {
            'resource': {'service.name': 'api'},
            'name': 'error_rate_pct',
            'value': 8.0,
            'time_unix_nano': observed_at_ns,
        },
        {
            'resource': {'service.name': 'api'},
            'name': 'failed_checks',
            'value': 1,
            'time_unix_nano': observed_at_ns,
        },
    ]
    telemetry = from_trusted_metric_batch(
        metrics, tenant='synthetic', project='demo',
        source_sha=_DEMO_SOURCE_SHA, now_utc=now_utc,
    )
    event = parse_event({
        'schema_version': 1, 'event_id': 'demo-incident-001',
        'provider': 'github', 'project_ref': 'synthetic/demo',
        'source_sha': _DEMO_SOURCE_SHA, 'kind': 'incident',
        'observed_at': _DEMO_OBSERVED_AT,
        'evidence_digests': [item.evidence_digest for item in telemetry],
    })
    return event, telemetry


def run_demo(
    *, kill_switch: bool = False,
    incident_memory: IncidentMemory | None = None,
) -> dict[str, object]:
    """Exercise the offline flow; memory only influences findings after approval."""
    event, telemetry = _synthetic_incident_evidence(now_utc=_DEMO_INSTANT)
    decision = evaluate_action(event, 'propose_patch')
    api_metrics = {
        point.metric: point.value for point in telemetry if point.service == 'api'
    }
    suggestion = propose(
        event, {
            'failed_checks': int(api_metrics.get('failed_checks', 0)),
            'error_rate_pct': float(api_metrics.get('error_rate_pct', 0.0)),
            'capacity_pct': 20.0,
        },
        kill_switch=kill_switch,
    )
    previous_topology = ServiceTopologySnapshot(
        'synthetic', 'demo', ['api', 'db'], [('api', 'db')],
        'b' * 40, '2026-10-24T23:59:00Z',
    )
    topology = ServiceTopologySnapshot(
        'synthetic', 'demo', ['api', 'db', 'web'],
        [('api', 'db'), ('web', 'api')], _DEMO_SOURCE_SHA, _DEMO_OBSERVED_AT,
    )
    topology_drift = compare_topology_snapshots(previous_topology, topology)
    memory = incident_memory if incident_memory is not None else IncidentMemory([])
    finding = correlate(
        topology, list(telemetry), memory, _DEMO_INSTANT,
        memory_max_age_seconds=86_400,
    )
    ledger = AuditStore(':memory:')
    try:
        ledger.append_finding(event, finding)
        ledger.append(event, decision, 'propose_patch')
        result = {
            'mode': 'synthetic_offline_demo',
            'live_provider_calls': 0,
            'production_mutations': 0,
            'policy_decision': decision.decision,
            'proposal_status': suggestion.status,
            'finding_status': finding.status,
            'finding_category': finding.category,
            'memory_evidence_count': len(finding.memory_provenance),
            'runbook_ids': list(finding.runbook_ids),
            'topology_drift': topology_drift.to_record(),
            'hypothesis': suggestion.hypothesis,
            'confidence_calibrated': False,
            'audit_records': ledger.summary()['record_count'],
        }
    finally:
        ledger.close()
    return result


def main() -> int:
    print(json.dumps(run_demo(), sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

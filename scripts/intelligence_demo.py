#!/usr/bin/env python3
"""Purely synthetic, credential-free DevObs intelligence demo (no network)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from devobs_intelligence.adviser import propose
from devobs_intelligence.audit_store import AuditStore
from devobs_intelligence.contracts import EventEnvelopeV1, parse_event
from devobs_intelligence.context import ServiceTopology, Telemetry
from devobs_intelligence.correlation import correlate
from devobs_intelligence.incident_memory import IncidentMemory
from devobs_intelligence.policy import evaluate_action
from devobs_intelligence.trusted_metric_batch import from_trusted_metric_batch

_DEMO_INSTANT = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
_DEMO_SOURCE_SHA = 'a' * 40


def _synthetic_incident_evidence(
    *, now_utc: datetime,
) -> tuple[EventEnvelopeV1, tuple[Telemetry, ...]]:
    """Build one tenant-scoped event from the same validated synthetic metric."""
    metrics = [{
        'resource': {'service.name': 'api'},
        'name': 'error_rate_pct',
        'value': 8.0,
        'time_unix_nano': int(_DEMO_INSTANT.timestamp()) * 1_000_000_000,
    }]
    telemetry = from_trusted_metric_batch(
        metrics, tenant='synthetic', project='demo',
        source_sha=_DEMO_SOURCE_SHA, now_utc=now_utc,
    )
    event = parse_event({
        'schema_version': 1, 'event_id': 'demo-incident-001',
        'provider': 'github', 'project_ref': 'synthetic/demo',
        'source_sha': _DEMO_SOURCE_SHA, 'kind': 'incident',
        'observed_at': '2026-10-25T00:00:00Z',
        'evidence_digests': [item.evidence_digest for item in telemetry],
    })
    return event, telemetry


def run_demo(*, kill_switch: bool = False) -> dict[str, object]:
    """Exercise the existing control plane without real endpoints or mutations."""
    event, telemetry = _synthetic_incident_evidence(now_utc=_DEMO_INSTANT)
    decision = evaluate_action(event, 'propose_patch')
    suggestion = propose(
        event, {'failed_checks': 1, 'error_rate_pct': 0.0, 'capacity_pct': 20.0},
        kill_switch=kill_switch,
    )
    topology = ServiceTopology('synthetic', 'demo', ['api'], [])
    finding = correlate(topology, list(telemetry), IncidentMemory([]), _DEMO_INSTANT)
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

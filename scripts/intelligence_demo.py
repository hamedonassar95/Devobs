#!/usr/bin/env python3
"""Purely synthetic, credential-free DevObs intelligence demo (no network)."""
from __future__ import annotations

import json

from devobs_intelligence.adviser import propose
from devobs_intelligence.audit_store import AuditStore
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.policy import evaluate_action


def run_demo(*, kill_switch: bool = False) -> dict[str, object]:
    """Exercise the existing control plane without real endpoints or mutations."""
    event = parse_event({
        'schema_version': 1, 'event_id': 'demo-incident-001',
        'provider': 'github', 'project_ref': 'synthetic/demo',
        'source_sha': 'a' * 40, 'kind': 'incident',
        'observed_at': '2026-10-25T00:00:00Z',
        'evidence_digests': ['b' * 64],
    })
    decision = evaluate_action(event, 'propose_patch')
    suggestion = propose(
        event, {'failed_checks': 1, 'error_rate_pct': 0.0, 'capacity_pct': 20.0},
        kill_switch=kill_switch,
    )
    ledger = AuditStore(':memory:')
    try:
        ledger.append(event, decision, 'propose_patch')
        result = {
            'mode': 'synthetic_offline_demo',
            'live_provider_calls': 0,
            'production_mutations': 0,
            'policy_decision': decision.decision,
            'proposal_status': suggestion.status,
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

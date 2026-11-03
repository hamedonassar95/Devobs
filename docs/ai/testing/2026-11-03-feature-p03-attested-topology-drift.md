---
phase: testing
title: Offline attested topology drift tests
description: Verify both signed inputs and fail closed on trust, source, scope, freshness and order errors
---

# Testing

## Coverage

- Valid synthetic Ed25519 envelopes produce a deterministic drift record bound
  to both verified signer IDs and envelope digests.
- A rotating keyring is snapshotted once for a two-envelope comparison.
- Invalid signature, wrong expected source SHA, wrong scope, stale snapshot and
  nonincreasing capture time are rejected.
- Serialized records do not contain signatures or public-key bytes; edges
  lacking source attribution remain `UNVERIFIABLE`.

## Verification

- `python3 -m unittest discover -s tests -p 'test_intelligence_topology_drift.py' -v` — 10 tests pass.
- `PYTHONPATH=/tmp/devobs-topology-drift-deps-20261103 python3 -m unittest discover -s tests -v` — 873 tests pass, 22 skipped.
- The temporary test target supplied the exact locked `psycopg==3.3.6` and
  `psycopg-binary==3.3.6` distributions only; no hosted PostgreSQL service was
  configured, so the 22 conditional skips remain expected.

No live topology, incident data, model inference, cloud service or readiness
gate was exercised or changed.

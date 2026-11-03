---
phase: implementation
title: Offline attested topology drift comparison
description: Verify signed topology snapshots and bind the local drift report to both inputs
---

# Implementation

## Change

Added `compare_attested_topology_snapshots` to
`scripts/devobs_intelligence/topology_drift.py`. It captures one trust-key view
for both inputs (one atomic snapshot for a rotating keyring), verifies each
Ed25519 envelope against its expected tenant, project, source SHA and freshness
window, then calls the existing deterministic drift comparator. The returned
`AttestedTopologyDriftReport` includes the two key IDs and signed-envelope
digests without copying signatures or public keys into the report.

The canonical P00–P19 checklist now records the partial local T23 capability;
its acceptance item remains unchecked.

## Limits

The report identifies its signed inputs but cannot be independently replayed
without those original envelopes and the applicable trust configuration. The
caller still supplies trust keys and expected source SHAs. A valid signature
does not show that the signer observed a complete or truthful graph; every
after-snapshot edge remains `UNVERIFIABLE` when per-edge source attribution is
absent. No live collector, database, service, telemetry, AI model or cloud
resource is used. T22/T23 remain open and P03 remains waiting for P02.

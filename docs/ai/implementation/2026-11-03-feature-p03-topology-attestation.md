---
phase: implementation
title: P03 signed topology metadata verifier
description: Add strict offline Ed25519 verification for tenant- and source-bound snapshots
---

# Implementation

## Behavior

- \`verify_topology_attestation\` validates exact envelope/schema fields and canonical snapshot data.
- The signer ID is selected through a public-key map scoped to expected tenant and project.
- The signed payload is domain-separated and binds the key ID and full topology snapshot.
- Expected tenant/project, source SHA, and snapshot freshness are required from the caller.
- The result includes no raw signature or key material and no live producer is contacted.

## Roadmap status

This is partial local support for P03 T22. Key enrollment, an authorized live topology source, staging ingestion, and source-attestation evidence remain absent. The canonical T22 checkbox stays open.

## Verification status

The focused and full local suites were not run because the execution environment became unavailable after PR #412. GitHub CI on the exact PR head must pass before review; no local test success is claimed.

## Design and tests

- [Design](../design/2026-11-03-feature-p03-topology-attestation.md)
- [Testing](../testing/2026-11-03-feature-p03-topology-attestation.md)

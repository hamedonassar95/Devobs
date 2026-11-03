---
phase: implementation
title: Validate finding provenance against signed memory approvals
description: Re-verify active curator envelopes before accepting memory-bearing findings
---

# Implementation

Added `verify_incident_finding_memory_provenance` in
`scripts/devobs_intelligence/correlation.py`. It validates active Ed25519
approval envelopes, requires one-to-one agreement with the finding's provenance
items, checks each signed record against the finding scope and source fields,
and checks the exact runbook set.

`validate_attested_impact_finding` now requires the signed memory envelopes and
trusted memory-key map for memory-bearing findings. Its result exposes the
verified approval objects separately from the topology attestation fields.
No external key enrollment or persistence was added.

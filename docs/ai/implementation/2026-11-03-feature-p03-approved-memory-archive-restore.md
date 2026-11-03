---
phase: implementation
title: Explicit approval restoration for encrypted incident-memory archives
description: Require a matching active signed approval batch before approved retrieval after import
---

# Implementation

Added `decrypt_approved_incident_memory_bundle` to
`scripts/devobs_intelligence/incident_memory_encryption.py`. It reuses the
existing archive parser and approval verifier. Before consuming approval IDs,
it requires the verified approval records to equal the full decrypted archive
bundle. Successful imports are then claimed by the existing process-local
`IncidentMemoryApprovalRegistry`.

The ordinary `decrypt_incident_memory_bundle` API is unchanged and returns
records with no approval provenance. The new path requires separate signed
approval envelopes and caller-supplied trusted keys; it adds no key storage,
approval enrollment, persistent replay state, file IO, or service integration.
T25 and T27 remain open.

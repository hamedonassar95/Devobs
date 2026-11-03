---
phase: implementation
title: Offline encrypted incident-memory bundle
description: Encrypt and decrypt bounded single-scope memory bundles without persisting keys
---

# Implementation

Added `scripts/devobs_intelligence/incident_memory_encryption.py` with
`encrypt_incident_memory_bundle` and `decrypt_incident_memory_bundle`. The
functions reuse the canonical `IncidentMemory` bundle parser, require exact
tenant/project scope, authenticate scope and expiry, reject malformed or
oversized envelopes, and return fixed error codes. Tenant/project identifiers
and incident rows are not exposed in the envelope.

The caller owns the 32-byte key. Each archive gets a random HKDF salt and a
derived AES-GCM key. No approval metadata is exported or reconstructed; callers
that require approved retrieval must verify signed approvals separately.

This is not a persistent store or a production retention mechanism. Expiry does
not erase a file; key custody, key rotation, physical deletion, external
authorization and hosted tenant isolation remain unimplemented. T25 remains
open.

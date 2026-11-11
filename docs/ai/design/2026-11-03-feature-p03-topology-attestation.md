---
phase: design
title: P03 signed topology metadata verifier
description: Verify offline Ed25519 topology envelopes against caller-supplied scope and source trust
---

# Design

## Goal

Add a local verification boundary for signed service-topology snapshots, the next preparatory part of P03 T22. The existing snapshot digest detects content changes but is not a producer signature.

## Contract

- Accept only exact schema-v1 envelopes and canonical snapshot records.
- Verify an Ed25519 signature over a domain-separated payload containing the signer key ID and full snapshot.
- Resolve the public key from a caller-supplied keyring scoped by exact tenant, project, and key ID.
- Require the caller's expected tenant, project, source SHA, current time, and freshness limit to match.
- Return a verified snapshot, signer key ID, and digest of the signed envelope; never return the signature or key bytes.
- Use fixed errors without exposing identifiers or payload content.

## Trust limits

The caller-supplied public-key map is the trust root. This module does not enroll or protect keys, prove that a signer observed the named source commit, ingest live metadata, or prevent repeated use of an otherwise fresh snapshot. Tests use only generated keys and synthetic topology. T22 remains open until authorized source discovery and key enrollment are reviewed.

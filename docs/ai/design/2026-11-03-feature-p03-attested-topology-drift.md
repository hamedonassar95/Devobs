---
phase: design
title: Verify signed snapshots before local topology drift comparison
description: Bind an offline P03 drift report to two independently verified topology envelopes
---

# Design

## Goal

Connect the existing signed topology envelope verifier (T22 preparation) with
the existing bounded drift comparison (T23 preparation), without creating a
live collector or changing readiness gates.

## Contract

- Capture one detached public-key view for both verifications, including one
  atomic snapshot when the caller supplies `RotatingTopologyKeyring`.
- Verify both strict envelopes for the same expected tenant/project, each
  against its own caller-supplied source SHA and the same freshness window.
- Compute drift only after both signatures and snapshot contracts pass; require
  the existing strictly increasing capture-time rule.
- Return the existing drift report plus each verified key ID and signed
  envelope digest. Do not include signatures or key bytes in the result.
- Allow the local audit store to append only the attested report digest and the
  after-source SHA after the two-envelope verification succeeds.
- Keep all after-snapshot edges `UNVERIFIABLE` when edge-level source
  attribution is absent.

## Trust limits

This binds a report to bytes signed by keys in the caller's configured trust
view. It does not establish key enrollment/custody, signer observation or
completeness, live source access, edge truth, durable trust history, or
cross-worker key synchronization. The local audit store retains only a digest,
not the signed envelopes, so replay requires retaining the original envelopes
and protected trust configuration separately. Tests use generated keys and
synthetic topology only. T22/T23 remain open and P03 still waits for P02
acceptance.

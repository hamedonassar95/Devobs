---
phase: testing
title: Offline signed-topology verifier tests
description: Exercise signature, exact scope, source binding, freshness, and strict schema failures
---

# Testing

## Coverage

- Valid Ed25519 envelopes return a validated snapshot and digest without signature bytes.
- Signature tampering and changes to snapshot content fail closed.
- Exact tenant/project and expected source SHA are enforced.
- Unknown signer keys, malformed keyrings, malformed signatures, unsupported versions, and extra fields fail closed.
- Stale/future snapshots and invalid freshness bounds are rejected.
- Diagnostics use fixed error codes; test inputs are synthetic.

## Verification status

The local execution environment was unavailable after PR #412, so these tests have not been run locally. The exact-head GitHub Python validation, security, CodeQL, and full CI results are required before the PR is considered ready to merge. No real topology source, incident data, AI model, or paid API is used.

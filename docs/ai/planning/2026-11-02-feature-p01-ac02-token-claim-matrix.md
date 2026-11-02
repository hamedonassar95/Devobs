---
phase: planning
title: P01 AC02 JWK operation validation plan
description: One bounded offline configuration-validation change
---

# Plan

## Tasks

- [x] Add a regression test for malformed and incompatible `key_ops`; observe the test fail before implementation.
- [x] Enforce verify-only `key_ops` while preserving absent and `["verify"]` configurations.
- [x] Run focused authentication tests and the repository's offline validation checks.
- [x] Review the final diff and document deployment/monitoring as not applicable to this local-only change.

## Dependencies and risks

No external dependency. Main compatibility risk is an operator-pinned provider JWKS that advertises operations other than verification; the verifier will reject it deliberately, with a non-sensitive configuration error. The key is still supplied out of band; this change does not authenticate its source.

## Estimate

One reviewable Python change and regression test. No cloud or model calls.

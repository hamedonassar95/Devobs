---
phase: testing
title: P01 AC02 JWK operation tests
description: Offline regression cases for verifier-only JWK operations
---

# Testing

## Acceptance tests

- [x] Reject `key_ops` values `sign`, `encrypt`, mixed verify/sign, empty, duplicate, and non-array forms.
- [x] Accept `["verify"]` and verify a locally signed RS256 access token.
- [x] Preserve the existing no-`key_ops` verifier path.
- [x] Run the focused API security suite with generated keys and no network.

## Verification

`python3 -m unittest discover -s tests -p 'test_intelligence_api_security.py' -v` — 22 tests passed after the fix. The new test was first run before the implementation and failed because all six incompatible `key_ops` forms were accepted.

`PYTHONDONTWRITEBYTECODE=1 /tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — 784 tests passed, 22 skipped, 0 failed. The temporary environment used both hash-locked `requirements-api.lock` and `requirements-dev.lock`; no dependency files changed.

`python3 scripts/check_p01_threat_model.py` — passed (12 abuse cases, 9 boundaries, 12 zones). `npx --yes ai-devkit@latest lint --feature p01-ac02-token-claim-matrix` — 16 checks passed. `git diff --check` — passed.

## Limits

These tests do not fetch provider metadata, test live token issuance, or establish key rotation at an external issuer.

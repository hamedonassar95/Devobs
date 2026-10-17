---
phase: testing
title: Reliable Repository Policy API Reads
description: Test plan and verification evidence for API cache revalidation
---

# Reliable Repository Policy API Reads — Tests

## Test Coverage Goals

Cover the request boundary and preserve the existing policy-audit behavior. No external API call is required for unit tests.

## Unit Tests

### Public GitHub API client

- [x] The constructed GET request includes `Cache-Control: no-cache` (the assertion failed before the fix and passed after it).
- [x] Unauthenticated public reads omit Authorization; configured read-only token reads send the expected bearer header. Both target the fixed HTTPS GitHub API host.
- [x] Existing policy response, malformed-input, and API-error cases remain covered by `tests/test_check_repo_policy.py`.

## Integration Tests

- [ ] Run the manual `Repository policy audit` workflow on `main` after this fix merges; confirm it reports a pass against the live ruleset.

## Test Data

Use the existing mocked `urllib.request.urlopen` boundary and deterministic ruleset fixtures. The live check reads the public repository API and does not change settings.

## Test Reporting & Coverage

- Focused command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -v`.
- Full command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`.
- The new production change is one request header; the regression assertion covers its observable contract.
- Fresh local result: focused policy audit tests passed after rebasing; refresh full-suite count after final edits.
- Hosted audit run [39051828800](https://github.com/hamedonassar95/Devobs/actions/runs/39051828800) passed on `main` after configuring the existing read-only token. Hosted confirmation of this cache-revalidation change remains pending.

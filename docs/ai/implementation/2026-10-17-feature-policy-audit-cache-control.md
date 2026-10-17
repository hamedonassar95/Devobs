---
phase: implementation
title: Reliable Repository Policy API Reads
description: Implementation record for GitHub REST cache revalidation
---

# Reliable Repository Policy API Reads — Implementation

## Lifecycle Progress

- [x] Phase 2: requirements reviewed; stale 60-second cache and read-only ruleset access requirements identified.
- [x] Phase 3: design reviewed; request cache revalidation selected alongside the existing optional read-only token, with no retries.
- [x] Phase 4: ordered regression-fix-verification plan created.
- [x] Phase 7: implementation matches the design; only request cache revalidation changed.
- [x] Phase 8: focused and full tests, security scan, action pin check, and live audit passed; the test was confirmed to fail without the fix.
- [x] Phase 9: reviewed the rebased PR; cache directive, optional read-only authentication, tests, and operational docs align with the design.

## Development Setup

Python 3.10+; standard library only. No dependency installation or build is required.

## Code Structure and Behavior

- `scripts/check_repo_policy.py`: `get_json` adds `Cache-Control: no-cache` while preserving the existing optional bearer token on fixed HTTPS GET requests.
- `tests/test_check_repo_policy.py`: API-client tests assert cache revalidation and cover both unauthenticated requests and the configured token path.
- `docs/ai/**/2026-10-17-feature-policy-audit-cache-control.md`: requirements through monitoring notes for this follow-up.

## Regression Evidence

The new request-header assertion failed before the production change (`None != 'no-cache'`), passed with the header, failed again when the header was temporarily removed, and passed after restoration.

## Local Verification

- Focused policy-audit tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -q` — 14 passed.
- Full Python suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` — 162 passed.
- Bandit: `python3 -m bandit -r scripts -x scripts/check_site.py` — exit 0, no findings.
- Action pin check: `python3 scripts/check_action_pins.py` — 31 workflow/template files passed.
- Site contract and HTTP smoke checks: `python3 scripts/check_site.py` — passed.
- AI DevKit feature lint: 16 checks passed.
- Live read-only policy audit on `main`: run [39051828800](https://github.com/hamedonassar95/Devobs/actions/runs/39051828800) passed after token setup; hosted verification of this follow-up remains pending.

## Security and Scope

No new token, permission, dependency, API endpoint, repository-setting write, or deployment step is introduced by this follow-up. The existing optional read-only token, 15-second timeout, and fail-visible response validation remain unchanged.

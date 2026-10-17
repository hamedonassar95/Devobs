---
phase: planning
title: Reliable Repository Policy API Reads
description: Implementation tasks for the stale ruleset response correction
---

# Reliable Repository Policy API Reads — Plan

## Milestones

- [x] Reproduce and specify the missing cache revalidation behavior.
- [x] Apply the request-level cache directive and verify it locally.
- [ ] Review and update PR #165 with the latest `main` authentication setup; verify a hosted run after merge.

## Task Breakdown

### Phase 1: Regression and fix

- [x] Add an assertion that the GitHub request carries `Cache-Control: no-cache`; confirm it fails before the production change.
- [x] Add the header in the shared API client without changing authentication, permissions, or endpoint behavior.

### Phase 2: Verification and release

- [x] Run focused and full Python tests, the security scan, workflow pin check, and AI DevKit lint.
- [ ] Review the exact rebased PR #165 diff and report the CI result.
- [ ] After merge, run the hosted audit and record its result.

## Dependencies

Only Python's standard library and GitHub's existing public REST API. Task tracing is unavailable in the installed CLI (`ai-devkit task` is not recognized); progress is recorded here.

## Risks & Mitigation

- Risk: the API cache still returns incomplete data. Mitigation: keep malformed data fail-visible and verify the result on the hosted runner after merge.
- Risk: an implementation accidentally expands credentials or write access. Mitigation: test unauthenticated requests and the existing optional token path; keep Administration read-only and workflow permissions unchanged.

## Resources Needed

No new secrets, services, dependencies, or cloud resources. The existing `POLICY_AUDIT_TOKEN` is used when configured.

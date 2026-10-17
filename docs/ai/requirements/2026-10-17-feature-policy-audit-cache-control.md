---
phase: requirements
title: Reliable Repository Policy API Reads
description: Prevent stale cached GitHub API responses from creating false policy drift
---

# Reliable Repository Policy API Reads

## Problem Statement

The first hosted run of `Repository policy audit` after PR #164 was merged failed twice because the ruleset response did not contain a usable `bypass_actors` list. GitHub's response headers allowed caching for 60 seconds, and the audit also needed a read-only token to inspect protected ruleset details. The original failure did not establish caching as its sole cause. A later hosted run passed after `POLICY_AUDIT_TOKEN` was configured; this follow-up asks API caches to revalidate responses as an additional reliability measure.

The repository maintainer needs the scheduled audit to distinguish real policy changes from cached API representations.

## Goals & Objectives

- Ask GitHub's API caches to revalidate every audit response before use.
- Preserve the audit's GET-only behavior and the existing optional `POLICY_AUDIT_TOKEN` with Administration: read.
- Keep the existing fail-visible behavior when required policy data is unavailable.

Non-goals: changing repository rules, adding credentials, changing ruleset semantics, or adding retry loops that could mask real API errors.

## User Stories & Use Cases

- As a maintainer, I want the policy audit to read fresh ruleset data so that a stale response does not report a false policy violation.
- If GitHub cannot provide complete policy data, I want the run to remain visibly unsuccessful rather than assume protection is present.

## Success Criteria

- Every GitHub REST request from the audit includes `Cache-Control: no-cache`.
- Focused unit tests prove every request asks for cache revalidation and preserve both unauthenticated public reads and configured read-only token behavior.
- The full test suite passes, and a hosted workflow run against the merged branch reads the current repository policy successfully.

## Constraints & Assumptions

- GitHub responses may advertise a shared cache lifetime; the observed ruleset response included `Cache-Control: private, max-age=60, s-maxage=60`.
- The standard-library HTTP client remains in use; this follow-up adds no new secret or permission.
- `no-cache` requests revalidation; it does not mean that responses cannot be stored.

## Questions & Open Items

No product or architecture questions remain. Hosted verification of this cache-revalidation change is required after it merges.

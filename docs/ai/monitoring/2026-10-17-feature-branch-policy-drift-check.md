---
phase: monitoring
title: Default-Branch Policy Drift Audit
description: Operational signals and response process for governance drift
---

# Default-Branch Policy Drift Audit — Monitoring

## Signals

- Workflow success: the current default-branch baseline matched the GitHub API response.
- Workflow failure with exit 1: a specific protection or ruleset setting drifted.
- Workflow failure with exit 2: the API request or response could not be trusted, so the audit was inconclusive.

GitHub Actions run history is the audit record. The workflow does not send external notifications; maintainers should use repository/watch notification settings or inspect Actions history. It does not emit production metrics or retain API payloads.

## Response steps

1. Open the failed Repository policy audit run and read the named finding.
2. For exit 2 with a missing `bypass_actors` field, configure or check the `POLICY_AUDIT_TOKEN` secret and its `Administration: read` repository permission using [the setup guide](../../REPOSITORY_POLICY_AUDIT.md). Do not interpret the inconclusive run as evidence that policy is intact.
3. For API/network failure, rerun once after checking GitHub API status and rate limit; do not interpret the failed run as evidence that policy is intact.
4. For a real drift, compare Protect main in repository Settings with the reviewed baseline in docs/ai/design/2026-10-17-feature-branch-policy-drift-check.md.
5. Restore the setting manually through GitHub Settings under normal repository administration, then run the audit again.
6. If the desired baseline intentionally changes, update the design, script, and tests together through a reviewed PR.

The audit is deterministic policy automation, not AIOps: it does not predict incidents, call an LLM, or autonomously repair GitHub settings.

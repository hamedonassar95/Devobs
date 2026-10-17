---
phase: deployment
title: Default-Branch Policy Drift Audit
description: Deployment and operating procedure for the scheduled GitHub audit
---

# Default-Branch Policy Drift Audit — Deployment

## Runtime

The audit runs on the GitHub-hosted ubuntu-24.04 runner. It does not deploy the website, provision a container, or contact a cloud account. It uses Python already available on the runner and GitHub's REST API. For ruleset details, configure the optional `POLICY_AUDIT_TOKEN` repository secret as described in [the setup guide](../../REPOSITORY_POLICY_AUDIT.md); without it, the workflow falls back to `GITHUB_TOKEN`, which may not expose `bypass_actors`.

## Triggers and permissions

- Weekly on Monday at 08:17 UTC.
- Manual run through Actions → Repository policy audit → Run workflow.
- `contents: read` is used by the pinned checkout action. The audit uses `POLICY_AUDIT_TOKEN` when present or the workflow token otherwise, and performs only GET requests. The dedicated token must have `Administration: read` for this repository and no write permissions.
- The workflow is separate from CI, required PR checks, and Pages deployment.

## Release and rollback

Review the implementation PR and its validate result before merging. The empty-list API representation is handled and covered by tests. After configuring the secret, run the workflow manually and inspect the result. If the workflow itself is faulty, revert the workflow/script in a reviewed PR; no repository setting has been modified by the audit. If a drift finding is valid, restore the expected rules in GitHub Settings and rerun the audit.

No environment-level secret, database migration, cloud billing setup, or production deployment step applies; the only extra configuration is the repository-level Actions secret described above.

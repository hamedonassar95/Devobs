---
phase: deployment
title: Default-Branch Policy Drift Audit
description: Deployment and operating procedure for the scheduled GitHub audit
---

# Default-Branch Policy Drift Audit — Deployment

## Runtime

The audit runs on the GitHub-hosted ubuntu-24.04 runner. It does not deploy the website, provision a container, or contact a cloud account. It uses Python already available on the runner and the unauthenticated public GitHub REST API.

## Triggers and permissions

- Weekly on Monday at 08:17 UTC.
- Manual run through Actions → Repository policy audit → Run workflow.
- contents: read is used by the pinned checkout action. The audit process receives no token and performs no write requests.
- The workflow is separate from CI, required PR checks, and Pages deployment.

## Release and rollback

Review the implementation PR and its validate result before merging. The first post-merge hosted run exposed an empty-list API representation that is fixed in the follow-up. After that fix merges, run the workflow manually once and inspect the result. If the workflow itself is faulty, revert the workflow/script in a reviewed PR; no repository setting has been modified by the audit. If a drift finding is valid, restore the expected rules in GitHub Settings and rerun the audit.

No database migration, environment-specific secret, cloud billing setup, or production deployment step applies.

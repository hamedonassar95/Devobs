---
phase: deployment
title: Reliable Repository Policy API Reads
description: Release and hosted verification steps for the cache revalidation fix
---

# Reliable Repository Policy API Reads — Deployment

## Runtime

The existing `Repository policy audit` runs on GitHub-hosted `ubuntu-24.04`. This fix changes only the HTTP request headers used by the Python standard-library client.

## Release and Rollback

1. Review and merge the follow-up PR after its required CI checks pass.
2. Run **Actions → Repository policy audit → Run workflow** on `main`.
3. Confirm the policy audit passes and inspect the Actions summary.
4. If the audit remains inconclusive, keep it fail-visible and investigate the API response before changing the policy checks.

The post-merge audit passed on `main` in [run 39053647920](https://github.com/hamedonassar95/Devobs/actions/runs/39053647920). The merge commit is `6936cd99c36a7b964fc29ace19ba3e5d82c91617`.

This follow-up adds no secret, infrastructure, website deployment, or repository-setting change. The workflow uses the existing optional `POLICY_AUDIT_TOKEN` for Administration: read when configured. Revert the request-header change through a reviewed PR if it causes a verified API compatibility problem.

---
phase: deployment
title: Copilot preflight remediation
description: Deployment and rollback notes for a GitHub Actions guidance-only change
---

# Deployment

This workflow-only improvement is delivered through the standard protected pull-request process. It does not alter GitHub Pages deployment, cloud resources, repository secrets, or incident recovery.

After merge, run **Actions → AI Provider Preflight → Run workflow** on `main` with `copilot`. The current configured secret is expected to fail until the owner replaces it with a fine-grained token with account permission `Copilot Requests: Read`. The failure summary provides the exact steps. This preflight does not call a model.

Rollback by reverting the reviewed pull request through the protected Git process if the summary or validation behavior is incorrect.

---
phase: planning
title: Copilot preflight remediation
description: Ordered tasks for tested, safe setup guidance
---

# Plan

## Milestone 1: Preflight remediation

- [x] Record observed failure and scope: no model request; secret format failed on `main`.
- [x] Define safe behavior, required instructions, and acceptance criteria.
- [x] Add tests for the workflow integration and for missing, malformed, and accepted-prefix secrets, including non-disclosure checks.
- [x] Implement a dependency-free checker that writes actionable GitHub Actions summary text.
- [x] Wire the checker into the workflow with a pinned checkout action and least privilege.
- [x] Record the hosted failure evidence and token separation in the investigator acceptance guide.
- [x] Run focused and full CI tests, action pin validation, and AI DevKit feature lint.
- [x] Review the branch diff, open PR #173, confirm hosted checks and GitHub Codex review, and merge at `e8a2f93`.

## Dependencies and blocker

The last recorded `COPILOT_GITHUB_TOKEN` still fails the prefix preflight. The owner must configure a dedicated fine-grained token with account-level `Copilot Requests: Read` and save it under that exact secret name before any investigator model call can run. This code change cannot create or modify that secret. `POLICY_AUDIT_TOKEN` is separate and used for the read-only repository policy audit (`Administration: Read`).

## Risk controls

- Never print token contents or make a model request.
- Keep the failure state visible and do not mark preflight successful based on a token prefix alone for access or inference.
- Do not broaden permissions or modify incident recovery behavior.

## Progress

The checker, workflow wiring, regression tests, and acceptance evidence are merged in PR #173. Hosted CI, CodeQL, Gitleaks, and GitHub Codex review completed successfully; the post-merge CI and push workflow also succeeded. The only remaining operational step is owner-managed Copilot credential setup and a manual preflight rerun. Optional AI DevKit task tracing is unavailable because `npx ai-devkit@latest task list --json` returns `unknown command 'task'`.

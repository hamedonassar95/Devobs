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
- [ ] Review the branch diff and open a PR; confirm required hosted checks.

## Dependencies and blocker

The repository's `COPILOT_GITHUB_TOKEN` currently fails the prefix preflight. The owner must configure a fine-grained token with account-level `Copilot Requests: Read` and save it under that exact secret name before any investigator model call can run. This code change cannot create or modify that secret. `POLICY_AUDIT_TOKEN` is separately used for the read-only repository policy audit.

## Risk controls

- Never print token contents or make a model request.
- Keep the failure state visible and do not mark preflight successful based on a token prefix alone for access or inference.
- Do not broaden permissions or modify incident recovery behavior.

## Progress

The checker, workflow wiring, regression tests, and acceptance evidence are implemented. Local verification is complete; hosted checks and the final review remain.

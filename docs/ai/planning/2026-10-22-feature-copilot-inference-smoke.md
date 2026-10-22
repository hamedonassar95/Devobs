---
phase: planning
title: Project Planning & Task Breakdown
description: Plan a manual and isolated Copilot inference smoke workflow
---

# Project Planning & Task Breakdown

## Milestones

- [x] Review existing provider preflight, investigator, failover, and generated workflow logging behavior.
- [x] Research current official Copilot CLI controls for prompts, tools, session sync, telemetry, and model selection.
- [x] Check GH-AW release support for disabling automatic issue output; keep standard Actions YAML because the option does not remove the GH-AW prompt/answer artifact lifecycle.
- [x] Add the owner-gated standalone workflow and feature documentation.
- [x] Review the branch diff and static validation before merge; leave the branch local.
- [ ] If the owner later approves, review quota and dispatch one manual inference run; no run is authorized by this change.

## Task Breakdown

### Phase 1: Boundaries

- [x] Confirm the target is the current Devobs repository and use the approved isolated worktree.
- [x] Keep the existing incident investigator and Vertex fallback out of this test path.
- [x] Select standard Actions YAML because agentic workflow artifacts do not fit the no-prompt/no-answer-output requirement.

### Phase 2: Implementation

- [x] Gate dispatch by `main`, repository owner, explicit owner approval, explicit quota review, and the existing budget variable.
- [x] Pin the setup action and Copilot CLI package version.
- [x] Disable model tools, built-in MCPs, session sync, and client-side telemetry.
- [x] Validate only the JSON shape and word limit; withhold diagnosis text and clean temporary state.

### Phase 3: Review

- [x] Run static workflow/documentation validation; do not call a live model.
- [x] Inspect final permissions, trigger, gates, cleanup, and summary fields.
- [x] Leave the branch local; do not push or open a pull request unless separately requested.

## Dependencies

- Existing repository secret `COPILOT_GITHUB_TOKEN` with Copilot Requests permission.
- Existing repository variable `DEVOBS_AI_BUDGET_APPROVED` equal to `true` at dispatch time.
- GitHub-hosted runner network access to npm and Copilot services.
- **UNVERIFIED:** current credential validity, model entitlement, remaining quota, and provider response.

## Risks & Mitigation

- The existing credential may be missing, expired, or lack Copilot access; workflow fails without printing it or the provider output.
- The current model may not be entitled for the account; there is no fallback, so the run fails closed.
- Copilot can retain session data server-side even when client telemetry and remote session sync are disabled; disclose this limitation and do not claim zero provider retention.
- The one CLI invocation is not a provider-side request counter. Runtime success proves a valid CLI result was received, not the exact number of backend HTTP attempts.

## Resources Needed

- GitHub Actions runner and an existing, valid Copilot credential; no new service or secret is introduced.
- Owner review of the Copilot quota before a future live dispatch.

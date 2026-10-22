---
phase: requirements
title: Requirements & Problem Understanding
description: Add a tightly gated manual Copilot inference smoke check without retaining its prompt or answer in workflow outputs
---

# Requirements & Problem Understanding

## Problem Statement

**VERIFIED (source):** Existing provider preflight checks configuration and authentication but does not establish that Copilot returned a valid model response. The incident investigator is tied to trusted incident evidence and can trigger its Vertex fallback, so it is not a safe path for an unrelated one-prompt smoke check.

## Goals & Objectives

- Add a manual, owner-only workflow that sends one fixed non-production prompt through GitHub Copilot CLI.
- Require explicit owner approval, a quota-review acknowledgement, the existing `DEVOBS_AI_BUDGET_APPROVED` repository variable, and dispatch from `main`.
- Provide no repository checkout, no model tools, no GitHub write permissions, and no Vertex fallback.
- Validate a JSON object with exactly `status` and `diagnosis`; require `status: "ok"` and a diagnosis of at most 25 words.
- Reject responses larger than 4 KiB before parsing.
- Keep the response in a disposable runner directory and report only outcome, SHA, run URL, and UTC time.
- Keep live inference **UNVERIFIED** until the owner separately dispatches the workflow after reviewing quota.

## Non-Goals

- Do not change the incident investigator, failover workflow, provider credentials, model routing, or deployment workflows.
- Do not run inference, modify secrets/settings, push, or create a pull request as part of this implementation.
- Do not treat CLI installation, a token-format check, or workflow compilation as proof of inference.

## Success Criteria

- The source is manual-only and the job is skipped unless every owner, branch, approval, and budget gate passes.
- The Copilot CLI runs with an empty available-tools set, built-in MCPs disabled, and no checkout.
- Prompt and response are not printed, uploaded, added to a workflow summary, or written to the repository; temporary CLI state and output are removed.
- Malformed output, extra keys, a non-`ok` status, or a diagnosis over 25 words fails closed without revealing the response.
- Static workflow validation succeeds. Runtime inference remains **UNVERIFIED** until a separately authorized run completes.

## Constraints & Assumptions

- **ASSUMED:** The existing `COPILOT_GITHUB_TOKEN` repository secret is the intended fine-grained Copilot credential. Its value and validity were not inspected.
- **VERIFIED (source):** Existing workflows already use `DEVOBS_AI_BUDGET_APPROVED` as an AI budget gate; this workflow requires its value to be `true` without reading or changing repository settings.
- **VERIFIED (documentation):** The Copilot CLI supports non-interactive prompts, an available-tools allowlist, a configurable `COPILOT_HOME`, session-sync controls, and a client-telemetry disable flag. GitHub notes that server-side session collection is outside the client telemetry control; see the [CLI programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference), [CLI settings](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference), and [telemetry guidance](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/configure-copilot-cli).
- **ASSUMED:** The owner reviews Copilot quota before checking the workflow's quota acknowledgement.

## Questions & Open Items

- **UNVERIFIED:** Does the configured credential have current Copilot Requests access and quota for the selected model? Only a gated run can establish that.
- The requested `.md` path is not used as a GitHub Agentic Workflow. Its compiled agent workflow retains agent outputs/log artifacts, which conflicts with the no-prompt/no-answer-output requirement. The executable workflow is a standard `.yml` Actions workflow; see the design document.

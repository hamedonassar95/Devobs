---
phase: requirements
title: Copilot preflight remediation
description: Make the AI provider setup check actionable without exposing credentials or calling a model
---

# Requirements

## Problem

The Copilot-only provider preflight currently reports only that `COPILOT_GITHUB_TOKEN` must start with `github_pat_`. A maintainer can create a different fine-grained token for `POLICY_AUDIT_TOKEN` and still not know that the investigator requires a separate account permission and secret. The latest hosted check failed before model inference.

## Goals

- Give a clear, actionable GitHub Actions summary when the Copilot secret is missing or has the wrong token format.
- Distinguish the Copilot token from `POLICY_AUDIT_TOKEN` and name the required account permission: `Copilot Requests: Read`.
- Explain that a passing prefix check does not validate permission or make a model request.
- Never print, persist, or include the token value in a summary or error.

## Non-goals

- Do not call Copilot or any other model from preflight.
- Do not change repository secrets, create tokens, or grant permissions.
- Do not add a production model call or alter incident automation behavior.

## Acceptance criteria

1. Missing and malformed tokens fail with distinct, safe messages in the workflow summary.
2. The remediation identifies the exact Actions secret name, required fine-grained PAT account permission, and the separate `POLICY_AUDIT_TOKEN` purpose.
3. A token with the accepted prefix passes format validation, while the summary says permission and model access are not verified.
4. Automated tests prove none of the above outcomes disclose the supplied token value.
5. The workflow invokes the tested local checker and retains least-privilege permissions and immutable action pins.

## Constraints

- The Copilot Requests permission belongs to the personal account token; the workflow cannot inspect its granted permissions without contacting Copilot.
- The existing preflight must remain model-call-free.
- The owner must configure the Actions secret manually; repository credentials are unavailable to this change.

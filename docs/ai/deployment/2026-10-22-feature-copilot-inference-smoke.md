---
phase: deployment
title: Deployment Strategy
description: Reviewed delivery and manual enablement of a gated Copilot smoke workflow
---

# Deployment Strategy

## Infrastructure

The workflow uses a GitHub-hosted runner, the existing Copilot credential, and npm. It creates no cloud resources, application deployment, or new secret.

## Delivery

- Keep the change on the local feature branch until its source and checks are reviewed.
- Merge the workflow only through the repository's normal reviewed process.
- Do not push or open a pull request as part of this implementation.

## Manual Dispatch Requirements

After the workflow is present on `main`, the repository owner must first review Copilot quota and expected usage. Dispatch from `main`, set both owner-approval and quota-review inputs to true, and ensure the pre-existing `DEVOBS_AI_BUDGET_APPROVED` variable is `true`. No inference runs automatically on merge or on an incident.

## Rollback Plan

Disable the workflow by reverting its YAML source and documentation through a reviewed change. The workflow has no persistent application data or cloud resources to roll back.

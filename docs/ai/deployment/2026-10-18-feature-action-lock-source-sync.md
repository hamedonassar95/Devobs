---
phase: deployment
title: Deployment Strategy
description: Pull-request-only delivery for GitHub workflow source and lock updates
---

# Deployment Strategy

## Infrastructure

The change runs only on GitHub-hosted Actions runners. It does not create or modify AWS resources, production secrets, or GitHub Pages runtime infrastructure.

## Deployment Pipeline

1. Open a pull request from `feature-action-lock-source-sync`.
2. Require the existing `validate` and CodeQL checks to pass.
3. Review the Markdown sources and generated `.lock.yml` output together.
4. A maintainer decides whether to merge. No automatic merge is configured.

## Environment Configuration

No new repository variables or secrets are required. The existing incident-invocation secrets and AI billing settings remain unchanged.

## Deployment Steps

This is workflow infrastructure and documentation only; GitHub Pages production publishing is not part of this change. Confirm the PR checks and review the compiled workflow diff before merge.

## Rollback Plan

If the new validator blocks reports unexpectedly, revert the source and generated lock changes together in a reviewed pull request. Keep validation before publication and keep checkout credentials disabled.

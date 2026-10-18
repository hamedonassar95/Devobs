---
phase: requirements
title: Requirements & Problem Understanding
description: Keep generated GitHub Agentic Workflow dependencies source-consistent and gate incident comments on validated output
---

# Requirements & Problem Understanding

## Problem Statement

Dependabot updates generated `.lock.yml` files, but the Markdown sources do not list the compiler-injected actions. Recompiling with the old GitHub Agentic Workflows compiler can restore older pins. The current investigator workflows also inspect and rewrite safe-output files in agent `post-steps`, a pattern rejected by current compiler versions. The Vertex workflow additionally referenced a provider-normalization step from a different job, so the agent could not read its output.

## Goals & Objectives

- Regenerate all five compiled agentic workflows from their Markdown sources using the official `gh-aw` v0.92.0 compiler.
- Keep SHA-pinned action versions reproducible and explain how to regenerate them.
- Validate the agent report inside the safe-output job immediately before publication, so a failed validation step stops the write step.
- Run Vertex provider normalization in the agent job that consumes its output.
- Preserve the requirement for exactly one incident report comment with its expected marker and heading.
- Do not invoke an AI model, add paid services, or change deployment behavior.

## User Stories & Use Cases

- As a repository maintainer, I want compiler-generated action updates to survive recompilation so routine security updates do not become stale.
- As an incident responder, I want malformed AI output to stop before any GitHub comment is written.
- As a maintainer, I want compiler and CI output to show which validation blocked a report.

## Success Criteria

- `gh aw compile --validate` compiles all five agentic workflows without errors.
- Generated metadata records the pinned compiler version, and generated action references match refreshed pins.
- Both investigator workflows run report validation after downloading the artifact and before processing safe outputs.
- The Vertex provider step output is defined in the agent job before the Gemini CLI step consumes it.
- Existing CI `validate` succeeds on the pull request.

## Constraints & Assumptions

- Use `gh-aw` v0.92.0, verified as the official latest release on 2026-10-18.
- Generated `.lock.yml` files remain compiler output; maintainers edit Markdown sources and recompile.
- The repository has no paid AI API balance. This change makes no model calls and does not require a secret.
- The AWS workflow and production deployment are out of scope.

## Questions & Open Items

- Review the new Gemini deprecation notice in a separate, cost-aware change; this task preserves the existing Vertex fallback engine and fixes only its step scope.
- Hosted CI must confirm the validation-step ordering and branch protection checks before merge.

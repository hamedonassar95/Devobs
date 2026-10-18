---
phase: planning
title: Project Planning & Task Breakdown
description: Ordered work and evidence for compiler-generated action source consistency
---

# Project Planning & Task Breakdown

## Milestones

- [x] Audit Dependabot updates and current generated workflow sources.
- [x] Migrate investigator output validation to a supported pre-publication gate.
- [x] Move Vertex provider normalization into the agent job where its output is consumed.
- [x] Recompile all five agentic workflows with the official v0.92.0 compiler.
- [ ] Review the complete generated diff and hosted CI results before recommending merge.

## Task Breakdown

### Phase 1: Source and compiler audit

- [x] Confirm current `main` at `d4612b4` and inspect open PRs #177–#181.
- [x] Confirm five Markdown sources correspond to the generated lock files.
- [x] Verify compiler version and refresh behavior against official GitHub Agentic Workflows release.
- [x] Use actionlint to identify and fix the pre-existing Vertex cross-job step-output reference.

### Phase 2: Safe report gate

- [x] Add a deterministic, non-writing validator for the investigator artifact.
- [x] Add a deterministic validation step before publication in both investigator sources.
- [x] Ensure validation runs after artifact download and before the safe-output handler.
- [x] Update existing incident-guard assertions to the new source structure.

### Phase 3: Compiler refresh and integration

- [x] Compile the five agentic workflow sources with `gh aw compile --validate`.
- [ ] Inspect generated action versions, permissions, workflow triggers, and validation ordering.
- [ ] Run existing repository CI via the pull request and review its required checks.
- [ ] Keep deployment and AWS workflow changes outside this patch.

## Dependencies

- Official GitHub Agentic Workflows CLI v0.92.0.
- GitHub Actions runner access to read workflow artifacts and repository files.
- Required repository CI checks on the pull request.

## Risks & Mitigation

- Compiler releases can change generated workflow structure: review lock diffs and validate all sources before PR.
- Missing or malformed AI output now stops publication instead of being rewritten: this preserves a fail-closed result and allows a safe rerun after the agent issue is corrected.
- Gemini deprecation warning remains a separate migration concern; no Vertex workflow is dispatched here.

## Resources Needed

- GitHub-hosted CI only; no AI API key or cloud billing is required.

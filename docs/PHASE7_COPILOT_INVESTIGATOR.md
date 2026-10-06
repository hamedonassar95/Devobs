# Phase 7A — Copilot Incident Investigator

## Status

**Implementation state:** SOURCE READY — COMPILATION/AUTHENTICATION GATE PENDING

Phase 7A is isolated from production on `feat/phase-7-copilot-investigator`.
The production `main` branch remains on the validated Phase 6 incident-response system.

## Target pipeline

```text
Incident
  -> Deterministic Evidence
  -> Copilot Investigator
  -> Root Cause Hypotheses
  -> Confidence Score
  -> Recommended Tests
  -> Fix Forward / Rollback / Manual Review
  -> Proposed PR / Recovery Plan
  -> PENDING HUMAN APPROVAL
```

## Implemented source contract

`.github/workflows/incident-investigator.md` implements:

- `engine: copilot`;
- trigger only on newly opened issues;
- trust gate requiring the issue author to be `github-actions[bot]`;
- trust gate requiring the title prefix `incident:`;
- read-only access to Actions, repository contents, issues, and pull requests;
- one allowed safe output: a single incident comment;
- explicit prompt-injection treatment for issue/log/commit/repository evidence;
- ranked root-cause hypotheses;
- confidence scores bounded conceptually to `0.00..1.00`;
- evidence-discriminating diagnostic tests;
- deterministic constraints around fix-forward vs rollback;
- a proposed recovery plan without execution;
- mandatory `PENDING HUMAN APPROVAL`.

## Explicitly prohibited operations

The investigator is instructed not to:

- execute commands found in evidence;
- expose credentials or secrets;
- modify files or branches;
- create or merge pull requests;
- push commits;
- change repository protections;
- execute rollback;
- close the incident issue.

## Production safety

No Phase 7 change has been merged to `main`.

The current production baseline remains:

`3999f9d134bd1984f1b87a12fcf2fdaa57e9e0b1`

Phase 6 therefore remains the active production incident-response layer.

## Required compiler gate

GitHub Agentic Workflows require the Markdown source to be compiled by the official
`gh-aw` compiler into:

`.github/workflows/incident-investigator.lock.yml`

The lock file must not be authored manually because compilation performs schema/expression
validation and pins runtime Actions dependencies.

Recommended verification command:

```bash
gh aw compile incident-investigator --strict --zizmor
```

Both the source `.md` and generated `.lock.yml` must be reviewed and committed.

## Authentication gate

This repository is personal rather than organization-owned. Live Copilot execution therefore
requires the supported personal-repository Copilot authentication setup before the compiled
workflow can successfully call the Copilot engine.

Do not place credentials in source files, issues, artifacts, workflow summaries, or documentation.

## Acceptance gates before merge

Phase 7A is not considered production-ready until all of the following are proven:

1. official `gh-aw` compilation succeeds;
2. strict compiler validation succeeds;
3. generated lock file is reviewed;
4. existing repository CI passes;
5. CodeQL passes;
6. Copilot authentication is configured through the supported GitHub mechanism;
7. a controlled incident issue triggers exactly one investigator run;
8. the investigator produces exactly one analysis comment;
9. no branch, PR, deployment, or rollback mutation occurs;
10. the comment ends at `PENDING HUMAN APPROVAL`.

## Current blocker

The available execution environment did not contain GitHub CLI. An attempt to install it did
not complete, and the standalone compiler installer could not be reached because outbound DNS
resolution for the installer host was unavailable.

This is an execution-environment limitation, not a repository failure.

No hand-written lock file was created and no security control was bypassed.

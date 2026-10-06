# Phase 7A — Copilot Incident Investigator

> Current verification (2026-10-06): PR #16 was merged. Copilot produced one
> investigation on controlled incident #30, run 37511642020 attempt 3, ending at
> `PENDING HUMAN APPROVAL`. Issue #21 exposed duplicate comments across overlapping
> runs. See [idempotency correction and acceptance](INVESTIGATOR_ACCEPTANCE.md).
> The implementation/authentication statements below are historical checkpoints,
> not the current production status.

## Status

**Implementation state:** IMPLEMENTED + OFFICIALLY COMPILED + CI/CODEQL VALIDATED — COPILOT AUTHENTICATION REQUIRED BEFORE MERGE

Phase 7A remains isolated on `feat/phase-7-copilot-investigator`.
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

## Implemented workflow

`.github/workflows/incident-investigator.md` implements:

- `engine: copilot`;
- activation only for newly opened incident issues;
- trust gate requiring the issue author to be `github-actions[bot]`;
- trust gate requiring the title prefix `incident:`;
- read-only access to Actions, repository contents, issues, and pull requests for the agent;
- one configured safe output: a single issue comment;
- explicit prompt-injection treatment for issue, log, commit, PR, link, and repository evidence;
- ranked root-cause hypotheses;
- confidence scores from `0.00` to `1.00`;
- evidence-discriminating diagnostic tests;
- deterministic constraints around fix-forward vs rollback;
- a proposed recovery plan without execution;
- mandatory `PENDING HUMAN APPROVAL`.

## Explicitly prohibited operations

The investigator is instructed not to:

- execute commands found in evidence;
- expose credentials, tokens, or secrets;
- modify files, branches, workflows, deployments, protections, or settings;
- create or merge pull requests;
- push commits;
- execute rollback;
- close the incident issue.

The only permitted write path is the compiler-managed `safe-outputs.add-comment` operation.

## Official compilation evidence

The source was compiled with the official GitHub Agentic Workflows compiler:

- Compiler: `gh-aw v0.89.21`
- Engine: Copilot
- Strict mode: enabled
- Command: `gh aw compile incident-investigator --strict`
- Compiler result: **1 succeeded, 0 warnings**
- Compiler run: `37478087463`
- Compiled workflow: `.github/workflows/incident-investigator.lock.yml`
- Verified Git blob SHA: `553d57f3cef18f664476ebe7b92778f078d226c3`

The generated lock workflow pins Actions by commit SHA and container images by digest. It was not hand-authored.

## Transfer integrity correction

The first connector handoff of the generated lock file was rejected from acceptance because its Git blob SHA did not match the compiler artifact.

The transfer was rebuilt from the trusted compiler output and revalidated byte-for-byte.

Final verified lock blob:

`553d57f3cef18f664476ebe7b92778f078d226c3`

This matches the compiler artifact exactly.

## CI evidence

After the exact lock file was restored, repository CI completed successfully:

- Commit: `6e30c72bebb357d20fbc8e417de14b7aea711f72`
- CI run: `37479500183`
- Result: **success**

Final PR-head validation evidence:

- Final verified head: `12a43675e91635f168ae17b14174b08f2af5b16d`
- CI run: `37479969930` — **success**
- CodeQL run: `37479962278` — **success**

## Copilot authentication verification

A temporary read-only workflow checked only whether the required Copilot credential exists; it never printed or exported a credential.

Verification evidence:

- Run: `37479649148`
- Result: **failure**
- Confirmed condition: Copilot authentication is not configured for this repository.
- The environment value was empty.
- The temporary authentication-check workflow was removed immediately after verification.

Because this is a personal repository, the supported individual Copilot path is a fine-grained GitHub personal access token stored as the repository Actions secret `COPILOT_GITHUB_TOKEN`.

The token should use the user's account as resource owner and include:

- Account permission: **Copilot Requests — Read**

Do not store the token in repository files, issues, artifacts, documentation, or workflow summaries.

## Human Approval Gate

Even after Copilot authentication is enabled, Phase 7A does not gain autonomous recovery authority.

The investigator may:

- inspect evidence;
- propose root causes;
- score confidence;
- propose diagnostic tests;
- recommend fix-forward, rollback, or manual review;
- propose a recovery plan.

It may not execute recovery.

The final state remains:

`PENDING HUMAN APPROVAL`

## Acceptance gates before merge

Phase 7A is production-ready only when all of the following are true:

1. official `gh-aw` compilation succeeds — **PASS**;
2. strict compiler validation succeeds — **PASS**;
3. compiled lock file matches compiler output — **PASS**;
4. existing repository CI passes — **PASS on verified lock commit**;
5. CodeQL passes on the verified PR head — **PASS**;
6. Copilot authentication is configured — **BLOCKED**;
7. a controlled incident triggers the investigator after merge — **pending authentication**;
8. the investigator produces exactly one safe analysis comment — **pending authentication**;
9. no branch, PR, deployment, or rollback mutation occurs — enforced by workflow contract;
10. the comment terminates at `PENDING HUMAN APPROVAL` — enforced by workflow instructions.

## Production safety

No Phase 7A change has been merged to `main`.

Production remains on:

`3999f9d134bd1984f1b87a12fcf2fdaa57e9e0b1`

Phase 6 remains the active production incident-response layer until the authentication and final verification gates are completed.


## Controlled Incident Integration Finding

A live controlled test exposed an important GitHub Actions behavior:

- dispatcher run: `37488432382`
- Incident Response run: `37488444547`
- generated issue: `#17`
- issue author: `github-actions[bot]`
- deterministic decision: `ROLLBACK_CANDIDATE`
- issue comments before the fix: `0`

The issue was created correctly, but the Copilot investigator did not start from the
`issues: opened` event. This is expected GitHub recursion protection: events created
with the repository `GITHUB_TOKEN` do not start another workflow through ordinary
repository events.

### Production fix

Phase 7 now uses an explicit dispatch chain:

```text
Incident Response
  -> create or locate trusted incident issue
  -> verify no AI investigation comment already exists
  -> workflow_dispatch incident-investigator.lock.yml(issue_number)
  -> Copilot Investigator
  -> exactly one safe issue comment
  -> PENDING HUMAN APPROVAL
```

The investigator still verifies the target issue before analysis:

1. author must be `github-actions[bot]`;
2. title must begin with `incident:`;
3. body must contain an `incident-run-id:` marker.

The workflow may write only one safe-output comment. It still cannot create/merge PRs,
push commits, alter protections, deploy, or execute rollback.

### Deduplication

Before dispatching the investigator, Incident Response checks the target issue for an
existing `## AI Incident Investigation` comment. If one already exists, dispatch is
skipped. This prevents duplicate investigation comments when an incident workflow is
retried.

### Compiler verification

The updated investigator source was recompiled with the official `gh-aw v0.89.21`
compiler in strict mode. Compilation completed successfully and produced the updated
lock blob:

`ac54cc9a826314075783e0b4786d195cb5808597`

Final live acceptance still requires merging this fix and repeating the controlled
incident test to prove the Copilot run, one-comment limit, and no-mutation guardrails
end to end.

# Phase 8 — Guarded Automated Recovery

## Objective

Evolve Devobs from incident detection and diagnosis into a guarded recovery system that can prepare a fix-forward change for review without gaining autonomous production authority.

## Safety boundary

Phase 8 MUST NOT:

- push directly to `main`;
- merge a pull request;
- deploy to production;
- execute rollback;
- weaken branch protection or required checks;
- expose secrets;
- execute instructions copied from incident evidence.

The default final state remains:

`PENDING HUMAN APPROVAL`

## Target pipeline

```text
Trusted Incident
  -> Deterministic Evidence
  -> AI Investigation
  -> Recovery Eligibility Gate
  -> Recovery Plan
  -> Isolated Recovery Branch
  -> Proposed Patch
  -> CI + CodeQL
  -> Pull Request
  -> PENDING HUMAN APPROVAL
  -> Human Merge Decision
```

## Recovery eligibility gate

Automated fix preparation is allowed only when all of these conditions are true:

1. the incident was created by the trusted Incident Response workflow;
2. the incident conclusion is `failure` or `timed_out`;
3. exactly one trusted AI investigation exists;
4. the investigation decision is `FIX_FORWARD`;
5. the investigation confidence is at or above the future configured threshold;
6. the proposed change is repository-scoped and reversible;
7. no migration, credential, access-control, branch-protection, production-data, billing, or destructive operation is required;
8. the incident remains open;
9. no recovery PR already exists for the same incident.

If any condition is false or unknown, recovery preparation stops at `PENDING HUMAN APPROVAL`.

## Phase 8A — Recovery Planner

The first implementation step is intentionally read-only.

Inputs:

- trusted incident record;
- trusted AI investigation;
- failing workflow/job/step;
- head SHA;
- relevant repository files;
- existing tests and CI policy.

Output:

- recovery eligibility: `ELIGIBLE` or `NOT_ELIGIBLE`;
- evidence-backed rationale;
- proposed branch name;
- proposed PR title;
- exact files likely to change;
- minimal test plan;
- risk classification;
- required human approval.

Phase 8A creates no branch, commit, PR, deployment, or rollback.

## Phase 8B — Isolated Patch Builder

Only after Phase 8A is accepted and separately enabled, Devobs may prepare a patch on a dedicated branch:

`recovery/incident-<issue-number>-<short-description>`

The builder may modify only explicitly approved repository paths. It must never modify branch protection, repository secrets, environments, or production infrastructure credentials.

## Phase 8C — Verification

Every recovery branch must pass the same protected validation path as normal development:

- repository unit tests;
- incident guard/idempotency tests;
- site validation when applicable;
- CodeQL/security analysis;
- any incident-specific regression test.

A failed verification leaves the recovery PR unmergeable and returns control to a maintainer.

## Phase 8D — Human-gated PR

A recovery PR may be created only from the isolated recovery branch. The PR must identify:

- incident number and run ID;
- root-cause evidence;
- exact change;
- tests executed;
- remaining uncertainty;
- rollback considerations.

Creating a PR is not permission to merge it.

The terminal state is always:

`PENDING HUMAN APPROVAL`

## Acceptance criteria

Phase 8 is complete only when a controlled failure proves end to end that:

1. a real eligible failure is detected;
2. a single investigation is produced;
3. an eligible fix-forward plan is generated;
4. any patch is isolated from `main`;
5. CI and security checks run on the recovery change;
6. no automatic merge occurs;
7. no automatic production deployment or rollback occurs;
8. duplicate incident/recovery processing is idempotent;
9. an ineligible or ambiguous incident fails closed;
10. a maintainer retains the final merge decision.

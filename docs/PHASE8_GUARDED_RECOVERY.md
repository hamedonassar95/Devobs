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
3. exactly one trusted AI investigation exists and uses the bound v2 contract;
4. the investigation decision is `FIX_FORWARD`;
5. the investigation confidence is at least `0.80`;
6. the proposed change is repository-scoped and reversible;
7. no migration, credential, access-control, branch-protection, production-data, billing, or destructive operation is required;
8. the incident remains open;
9. no recovery PR already exists for the same incident.

If any condition is false or unknown, recovery preparation stops at `PENDING HUMAN APPROVAL`.

## Phase 8A — Read-only Recovery Planner

The Phase 8A live policy workflow evaluates current GitHub evidence only. It requires:

- an open incident issue created by `github-actions[bot]` with exactly one run marker;
- a matching, completed failure or timeout from a monitored workflow on `main`;
- the source run SHA to match the SHA in the trusted incident record;
- exactly one investigator comment by the trusted bot, with investigator provenance and a v2 contract bound to this incident number and run ID;
- read access to all open pull requests to rule out duplicate recovery work.

The planner checks the machine-readable decision, confidence, reversible and repository-scoped flags, blocked change terms, and existing recovery PRs. It reports failed job names, a proposed branch and title, and a recommended test list. It does not treat simulated, cancelled, unmatched, incomplete, or duplicate evidence as eligible.

Phase 8A has read-only GitHub permissions. It creates no branch, commit, PR, deployment, or rollback. Its artifact contains the policy result only; raw issue comments and the transient input record are not uploaded.

The planner returns no authorized file paths. A preliminary `ELIGIBLE` result is not permission to write; Phase 8B still requires a separately reviewed allowlist and enablement.

## Phase 8B — Isolated Patch Builder

Only after Phase 8A is accepted and separately enabled, Devobs may prepare a patch on a dedicated branch:

`recovery/incident-<issue-number>-<short-description>`

Every proposed path must be explicitly approved before patch generation. The deterministic guard enforces this initial exact allowlist: `index.html` and files beneath `assets/**`. Tests, source code, workflows, security policy, automation, credentials, and infrastructure remain maintainer-authored unless a later reviewed policy explicitly expands the allowlist. The strict guard is a prerequisite only; it does not create a patch or enable the Phase 8B builder.

The builder must never modify branch protection, repository secrets, environments, or production infrastructure credentials. A patch can produce only an unmerged PR for human review.

## Phase 8C — Verification

Every recovery branch must pass the same protected validation path as normal development:

- repository unit tests;
- incident guard/idempotency tests;
- site validation when applicable;
- CodeQL/security analysis;
- any incident-specific regression test.

Checks must run on the actual recovery PR head SHA. A failed, missing, duplicated, or ambiguous check leaves the candidate unverified and returns control to a maintainer.

## Phase 8D — Human-gated PR

A recovery PR may be created only from the isolated recovery branch. The PR must identify:

- incident number and run ID;
- root-cause evidence;
- exact change and files;
- tests executed;
- remaining uncertainty;
- rollback considerations.

Creating a PR is not permission to merge it. The terminal state is always:

`PENDING HUMAN APPROVAL`

## Acceptance criteria

Phase 8 is complete only when a controlled failure proves end to end that:

1. a real eligible failure is detected;
2. a single investigation is produced;
3. an eligible fix-forward plan is generated from bound live evidence;
4. any patch is isolated to its approved paths and branch;
5. CI and security checks run on the recovery change's actual SHA;
6. no automatic merge occurs;
7. no automatic production deployment or rollback occurs;
8. duplicate incident/recovery processing is idempotent;
9. an ineligible or ambiguous incident fails closed;
10. a maintainer retains the final merge decision.

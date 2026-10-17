---
phase: implementation
title: Default-Branch Policy Drift Audit
description: Implementation and lifecycle evidence for the read-only governance check
---

# Default-Branch Policy Drift Audit

## Lifecycle progress

- [x] Phase 2: requirements review complete
- [x] Phase 3: design review complete
- [x] Phase 4: initial plan created after reviews
- [x] Phase 7: implementation checked against design
- [x] Phase 8: targeted tests and project validations completed
- [x] Original implementation and null-response fix merged through PRs #164 and #167.
- [x] Optional read-only ruleset authentication added through PR #169.
- [ ] Confirm the hosted audit passes with `POLICY_AUDIT_TOKEN` configured for `Administration: read`.

## Development setup

Requires Python 3.10+ and the standard library only. Run from the repository root:

    GITHUB_REPOSITORY=hamedonassar95/Devobs python3 scripts/check_repo_policy.py
    python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -v

For another public repository, pass --repository owner/name; its named ruleset and required status check can be changed with --ruleset-name and --required-check.

## Code structure and behavior

- .github/workflows/repository-policy-audit.yml runs on a weekly schedule and on manual dispatch only. It supplies `POLICY_AUDIT_TOKEN` when configured and falls back to the workflow's `GITHUB_TOKEN`.
- scripts/check_repo_policy.py queries repository metadata, default-branch status, ruleset summaries, and one ruleset detail endpoint. It URL-encodes path components, sets a timeout, uses only the supplied read token, and produces named findings rather than dumping API data.
- tests/test_check_repo_policy.py supplies isolated API fixtures. It does not call GitHub or alter repository settings.

The command exits 0 for an intact baseline, 1 for policy drift, and 2 when the audit cannot complete. API errors intentionally remain visible as failures. No automatic fix, retry loop, or AI interpretation is present.

## Security and resource considerations

- The workflow grants contents: read for checkout. The audit token has no write permission; `POLICY_AUDIT_TOKEN` requires only fine-grained `Administration: read` access to this repository.
- The script contains only fixed GitHub REST paths and performs GET requests; it has no code path for repository-setting mutation.
- The weekly/manual workflow is not a required PR check and cannot block a Pages deployment.
- There are no new dependencies, cloud resources, LLM usage, or metered runtime services.

## Hosted response follow-up — 17 October 2026

The hosted audit initially returned `bypass_actors: null` for an empty list ([run 39041619309](https://github.com/hamedonassar95/Devobs/actions/runs/39041619309), [run 39043609586](https://github.com/hamedonassar95/Devobs/actions/runs/39043609586)). PR #167 fixed that representation: `null` and `[]` are treated as empty, while a missing or wrongly typed field remains inconclusive (exit 2). Regression coverage exercises these cases.

PR #169 added an optional fine-grained token because GitHub omitted `bypass_actors` from the default-token response. The latest manual hosted run, [39048544142](https://github.com/hamedonassar95/Devobs/actions/runs/39048544142), remained inconclusive because the response still omitted that field. The run cannot distinguish an absent secret from a token without sufficient repository access. Configure `POLICY_AUDIT_TOKEN` with `Administration: read`, rerun the workflow, and record the first passing hosted result here.

## Documentation follow-up — 17 October 2026

Updated the requirements, design, planning, implementation, testing, deployment, monitoring, Arabic setup guide, and roadmap to match the merged token behavior and the latest hosted result. Added `.gitignore` with the local worktree path. No workflow or application code changed. The full Python suite passed (162 tests), the immutable action-pin check passed for 31 files, AI DevKit feature lint passed all 16 checks, and local Markdown links and whitespace checks passed. Hosted policy verification remains blocked on the repository secret's presence and scope.

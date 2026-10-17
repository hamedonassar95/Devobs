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
- [x] Phase 9: automated and manual code review complete; PR CI and maintainer review remain before merge

## Development setup

Requires Python 3.10+ and the standard library only. Run from the repository root:

    GITHUB_REPOSITORY=hamedonassar95/Devobs python3 scripts/check_repo_policy.py
    python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -v

For another public repository, pass --repository owner/name; its named ruleset and required status check can be changed with --ruleset-name and --required-check.

## Code structure and behavior

- .github/workflows/repository-policy-audit.yml runs on a weekly schedule and on manual dispatch only.
- scripts/check_repo_policy.py queries repository metadata, default-branch status, ruleset summaries, and one ruleset detail endpoint. It URL-encodes path components, sets a timeout, sends no authorization header, and produces named findings rather than dumping API data.
- tests/test_check_repo_policy.py supplies isolated API fixtures. It does not call GitHub or alter repository settings.

The command exits 0 for an intact baseline, 1 for policy drift, and 2 when the audit cannot complete. API errors intentionally remain visible as failures. No automatic fix, retry loop, or AI interpretation is present.

## Security and resource considerations

- The workflow grants contents: read for checkout only. It does not pass GITHUB_TOKEN into the audit process and does not use a write-capable permission.
- The script contains only fixed GitHub REST paths and performs GET requests; it has no code path for repository-setting mutation.
- The weekly/manual workflow is not a required PR check and cannot block a Pages deployment.
- There are no new dependencies, cloud resources, LLM usage, or metered runtime services.

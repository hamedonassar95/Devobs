# DevObs AI Intelligence — Core v1

**Status (2026-10-25):** The source implementation and architecture are merged into `main` through [PR #213](https://github.com/hamedonassar95/Devobs/pull/213) (merge commit `b93f4de23e9c9049a0d773a1e1148417050281b6`). This remains an offline-first prototype: it does not establish production AI inference, a deployed API, hosted tenant accounts/database, live GitLab synchronization, or scheduled automation.

## Implemented interfaces

- `scripts/devobs_intelligence/contracts.py`: `parse_event(payload)` and `parse_events(payloads)` validate bounded GitHub/GitLab evidence and preserve exact commit SHA. Output omits raw project identifiers. SHA-256 hashes are **pseudonymous**, not guaranteed anonymous: never publish reports about private projects without privacy review.
- `scripts/devobs_intelligence/collectors.py`: `collect_pipeline(provider, project, observed_at, fetcher=None, token=None)` reads only one default-branch CI status with fixed-origin GET requests. It does not execute a job. Missing and stale pipelines cannot be a success.
- `scripts/devobs_intelligence/policy.py`: `evaluate_action(event, action, agent_recommendation=None)` permits read-only analysis, classifies draft/code changes as proposals, and deterministically denies merge, deployment, rollback, billing, deletion, permission and secret writes.
- `scripts/devobs_intelligence/state_machine.py`: `StateMachine.new(event)` and `transition(state)` restrict progress through evidence and review states. The `APPROVED` state has **no enabled transition**: an independent identity-bound approval validator is not yet implemented.

## Operational boundaries

1. No new GitHub Actions workflow, secret, environment, runner, background job, subscription or public service is installed.
2. The existing ChatGPT GitLab connector does not supply an access token to the committed Python code.
3. No live GitLab private-project read is claimed. Only synthetic responses are exercised in unit tests.
4. GitHub collection uses an explicitly scoped repository name and the GitHub REST API; private repositories require separate authorized read access.
5. The module does not verify webhook signatures, author identities or GitHub/GitLab source signatures. This must be implemented in a separately reviewed authenticated ingestion boundary **before** acting upon production data.
6. The default branch's current SHA must match the recorded CI run SHA; success for an older commit becomes `stale`.
7. The module never delegates permission decisions to a language model. Any new write capability is blocked until a separate approval and security design.

## Verify from repository root

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_contracts.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_collectors.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_policy.py' -v
python3 -m compileall -q scripts tests
```

These tests use synthetic data; no external APIs, model tokens or cloud budgets are required. Run CI and security checks on the exact candidate SHA before merging further changes. A passing repository run does not establish a deployed service or live model quality. The repository ruleset requires a CodeQL alert threshold, but the latest CodeQL analysis result was not independently verified in this review.

## Next implementation gates

The architecture plan in [PR #213](https://github.com/hamedonassar95/Devobs/pull/213) merged as [`b93f4de`](https://github.com/hamedonassar95/Devobs/commit/b93f4de23e9c9049a0d773a1e1148417050281b6). Later source and test work merged as [PR #216 / `a060412`](https://github.com/hamedonassar95/Devobs/commit/a06041290ceeb43a313b6ab5a405e55340bf2e11), [PR #218 / `d9adfb0`](https://github.com/hamedonassar95/Devobs/commit/d9adfb06ee2ef4609e0a6910e404fb60ee24619b), and [PR #219 / `35108f1`](https://github.com/hamedonassar95/Devobs/commit/35108f1fd8ac64326c80ab7b75d2a38e4295cb72). These are source and test capabilities, not a hosted product. Remaining gates include authenticated hosted staging, live identity and database verification, durable external audit anchoring, expert-reviewed evaluations, independent action-bound approvals, and measured cost/privacy/backup controls. No SaaS hosting or billing is enabled.

## Relevant authoritative guidance (reviewed 2026-10-25)

- [OWASP AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html): separate agent advice from tool authorization, use narrow privileges and action-bound human approvals.
- [OWASP AI Agent/MCP DevSecOps](https://owasp.github.io/DevSecOpsGuideline/2-Process/2-2-Develop/2-2-5-AI-Agent-and-MCP-Security/): treat tool content as untrusted; reduce blast radius, require independent human review.
- [GitHub workflow runs REST API](https://docs.github.com/en/rest/actions/workflow-runs): inspect branch, head SHA and run conclusion before claiming current CI success.
- [GitLab Pipelines API](https://docs.gitlab.com/api/pipelines/): account for default-branch selection, pipeline status and absence of pipeline on HEAD.
- [GitHub webhook signature verification](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): required before future unsolicited push/webhook ingestion.

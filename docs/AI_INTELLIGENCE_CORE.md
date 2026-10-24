# DevObs AI Intelligence — Core v1

**Status:** Offline-first implementation for review in a Draft PR. No production AI inference, deployment, tenant accounts, hosted database, GitLab synchronization or scheduled automation is enabled by these files.

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

These tests use synthetic data; no external APIs, model tokens or cloud budgets are required. For project-wide confidence, the existing CI `validate`, CodeQL, Bandit, dependency audit and secret scanning still need to complete successfully on the exact Draft PR SHA.

## Next implementation gates

Follow [the architecture plan](plans/2026-10-25-devobs-ai-intelligence-control-plane.md) once it is merged and reviewed. Tasks 4–7 remain planned, not delivered: bounded offline AI recommendation with adversarial tests, durable/idempotent audit records, an independently authorized Draft-only proposal adapter, and tested SaaS tenant isolation. No SaaS hosting or billing until these acceptance gates pass.

## Relevant authoritative guidance (reviewed 2026-10-25)

- [OWASP AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html): separate agent advice from tool authorization, use narrow privileges and action-bound human approvals.
- [OWASP AI Agent/MCP DevSecOps](https://owasp.github.io/DevSecOpsGuideline/2-Process/2-2-Develop/2-2-5-AI-Agent-and-MCP-Security/): treat tool content as untrusted; reduce blast radius, require independent human review.
- [GitHub workflow runs REST API](https://docs.github.com/en/rest/actions/workflow-runs): inspect branch, head SHA and run conclusion before claiming current CI success.
- [GitLab Pipelines API](https://docs.gitlab.com/api/pipelines/): account for default-branch selection, pipeline status and absence of pipeline on HEAD.
- [GitHub webhook signature verification](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): required before future unsolicited push/webhook ingestion.

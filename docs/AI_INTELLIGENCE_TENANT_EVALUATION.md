# DevObs Enterprise — tenant boundary and AI evaluation (offline v1)

**Status:** proposed capabilities in Draft PR #216. Same original repository: `hamedonassar95/Devobs`. No repository migration, hosted service, paid provider, cloud provisioning, deployment or customer accounts.

## Implemented in this phase

### Offline tenant/project boundary

- `scripts/devobs_intelligence/tenant_scope.py` validates server-side immutable memberships and read-only project snapshots.
- Authorization checks the authenticated actor, tenant and exact project for **every** query. Unknown tenant, unknown project and unauthorized project all raise the same `access_denied`.
- Three fixture roles: viewer can read only; operator and owner can **propose** but not execute. The operation `execute()` is intentionally always denied.
- The `identity_resolver` callback represents a **trusted authentication boundary that has not been built**. The test resolver maps synthetic tokens to synthetic actors. This cannot be exposed over HTTP without a real verified session/OIDC issuer, signature, audience, expiry and nonce/replay checks.
- These controls are in-memory; they do not prove PostgreSQL RLS, inter-tenant data-store isolation, encrypted tenant backups, queue segregation, SSO or commercial readiness.

### Synthetic AI quality evaluation

- `scripts/devobs_intelligence/evaluation.py` evaluates the existing **offline, deterministic adviser** on a bounded set of synthetic labelled signal cases, not customer incidents.
- Metrics: total cases, correct classifications, accuracy, number of abstentions, accuracy excluding abstentions, an explicit target comparison, and `confidence_calibrated=false`.
- Current five-case illustrative fixture is intentionally imperfect: one conflicting symptom prioritizes CI failure over error-rate anomaly; its expected category differs. That test case must not be deleted to inflate accuracy.
- No model provider is invoked. The local heuristic confidence 0.55 is **not calibrated**, and synthetic classification accuracy says nothing about real-world AI accuracy.
- When production telemetry becomes available, curate anonymized, consented and separately reviewed ground truth, evaluate per incident class and time window, report class imbalance and false-positive rates, then set rollout gates from measured outcomes.

## Test acceptance

Run from the unchanged original DevObs repository:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_tenant_scope.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -v
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

All commands must exit zero on the exact PR commit. The existing GitHub `validate` CI and CodeQL/security checks must also pass on the exact SHA. A green test is not a verified deployed service.

## API and identity gates before hosted SaaS

Proposed **future**, not available routes:
- `GET /v1/tenants/{tenant_id}/projects/{project_id}/ci`: authenticated, tenant/project-authorized, response limited to current status, source SHA and evidence timestamp.
- `GET /v1/tenants/{tenant_id}/projects`: list only projects mapped to the authenticated principal. No cross-tenant search.
- `POST /v1/tenants/{tenant_id}/projects/{project_id}/proposals`: scoped propose-only request. Must not execute a mutation; proposals require independent owner review.

Release barriers, in order:

1. Verified identity provider with OIDC signature, issuer, audience, expiry, session lifecycle and revocation tests; read-only offline fixtures do not count.
2. Tenant-scoped authorization and direct object-reference negative tests at **every** REST handler and background job, with property-level redaction.
3. Persistent row/tenant isolation with a separate database role, row-level security policies, and tests under non-owner DB credentials; privileged bypass paths independently reviewed.
4. Signed, replay-protected webhooks and one-time, actor/target/SHA/parameter-bound approvals; an LLM must not mint, read or consume approvals.
5. Audit ledger anchored outside service-writable storage, verified encryption/retention, least-privilege service identity and backup/restore drill.
6. Real staged smoke tests, measured observability, model eval on consented incidents and budgets before chargeable inference or SaaS marketing.
7. Privacy/terms, licensed dependencies, support/SLA and verified payment eligibility before subscriptions.

No Stripe, Terraform apply, production Kubernetes, deployment environment or secrets have been configured in this phase. The existing GitHub Pages site and `main` remain the project's sole existing release path.

## Security sources (reviewed 2026-10-25)

- OWASP API1 Broken Object Level Authorization: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- OWASP API3 Object Property Authorization: https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/
- OWASP AI Agent Security: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- OWASP Agent/MCP DevSecOps: https://owasp.github.io/DevSecOpsGuideline/2-Process/2-2-Develop/2-2-5-AI-Agent-and-MCP-Security/
- GitHub deployment approval configuration: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments

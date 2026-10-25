# DevObs AI Intelligence — operating and reliability design

**Stage:** proposal and offline evidence; not a hosted production service. Repository and production website remain `hamedonassar95/Devobs`. Do not modify its protected default branch outside reviewed PRs.

## Threat and authorization model

- Sources: GitHub/GitLab CI metadata only through bounded GET; model text, PR comments, incident reports and runbook content are **untrusted**.
- Evidence must bind repository pseudonym, source SHA, event ID and evidence digests; API responses cannot independently authorize action.
- Policy code—not prompts—restricts proposals and always denies direct merge, deploy, rollback, IAM and billing.
- A future write capability needs an independent human identity provider, signed action/parameter-bound approval, scope and expiry checks, one-time atomic consumption, and an action ledger.
- All model calls default OFF. Offline heuristic confidence 0.55 is an uncalibrated advisory value, not a probability of correctness. Every write or potential production action remains blocked.
- Store no raw customer logs, secrets, credentials or identifiers in artifacts, model prompts or public traces.

## SLO catalogue (targets only, no observed metrics)

| Signal | Candidate initial service objective | Evidence needed |
| --- | --- | --- |
| Collector availability | 99.5% completed eligible pulls per calendar month | Authenticated collector uptime, documented exclusions |
| Incident ingestion delay | 95% within 5 minutes of source event | Signed source timestamp, queue ingress, processing spans |
| Proposal precision | Human-validated high-confidence recommendations compared to fixed evaluation corpus | Versioned ground truth, human review, false-positive analysis |
| Deployment health | Zero production transitions from unapproved model decisions | Approval and deployment audit correlation |
| Data segregation | Zero observed unauthorized cross-tenant reads in adversarial integration tests | Verified identity, storage/queue enforcement, audit |

**None is measured or promised as an SLA.** Define error budgets, burn rate and on-call route only after the hosted service exists.

## Observability and alert design

Future collector/worker traces should use OpenTelemetry with trace IDs, component, operation, duration, outcome and hashed project reference; keep raw prompts, emails, filenames, tokens and private issue text OUT of attributes. Measure: collector errors, schema rejects, stale SHA, policy DENY count, unapproved attempts, model timeouts, tenant-boundary denies, queue delay, cost budget and approval latency. Alert on sustained error-budget burn, repeated approval-bypass attempts and high failure rate; rate-limit/noise-filter duplicate alerts. Acknowledge and link incidents to a runbook; do not trigger unattended remediation.

## Runbooks: safe manual triage

### GitHub CI fails

1. Capture run URL, source SHA, failure job and its trusted status; never execute commands copied from job logs.
2. Compare CI head SHA to current protected branch and identify changed files.
3. Classify test failure vs dependency availability vs failed security check.
4. If code change is warranted, open an isolated branch/Draft PR and run existing CI + CodeQL.
5. Keep release blocked until a reviewer confirms successful current-SHA checks; no automatic rollback.

### GitLab reports stale CI

1. Validate project ID and current default-branch HEAD using read-only API.
2. Compare latest pipeline SHA with HEAD; mark stale/missing as not successful.
3. Review GitLab's pipeline page externally; do not create a pipeline or tokens automatically.
4. Report the absence or mismatch and request owner action.

### Model output, cost or security incident

1. Activate configured kill switch (when a hosted implementation exists); disable live provider invocations.
2. Quarantine untrusted outputs and block tool writes; avoid publishing private input in logs.
3. Record redacted evidence and model version with source SHA and policy revision.
4. Review permission scopes and remaining provider quota separately; do not rotate/deploy without authorized owner.
5. Add synthetic regression to the evaluation corpus before re-enabling.

## Backup and disaster recovery

- Current repo: restore from protected Git history and release tags. GitLab mirror is a replica, not a retention-controlled backup; test restoration before relying on it.
- Future database: daily encrypted full backups, point-in-time recovery where supported, separate storage permissions, retention policy and geographic recovery region after privacy review.
- Future restore drill: restore to isolated staging without external notifications, confirm schema compatibility, hash-chain records, anonymized sample data, tenant boundaries and smoke tests; record timestamp, RPO/RTO achieved and owner approval. **No such drill has been run.**
- Example *planning* objectives: RPO 24 hours, RTO 4 hours. **Not a guarantee** until measured.

## Change management and compliance evidence

- SOC2-style mapping to access control, change management, risk assessment, monitoring, vendor review, incident response, business continuity and data lifecycle. This is a self-review checklist **not SOC 2 certification**.
- Changes to environments/infra only via reviewed PR. Protected production environment with required reviewers must be configured outside repository files and independently verified.
- Secrets in a managed secret store; OIDC WIF for GCP when provisioned; least privilege and short-lived identities.
- Encryption TLS in transit and managed-key storage at rest must be verified in each future environment; not established by this static repository.
- Data subject access/export/delete and log retention require documented policy and tested implementation before customer signup.

## Acceptance and current gaps

Completed locally: offline source-evidence checks, deterministic proposals, read-only audit trail and synthetic demo tests. Not delivered: production alert routing, remote dashboards, SSO, signed ingestion, tamper-resistant ledger anchoring, distributed jobs, live model evaluation, DR restoration, SOC2 attestation or customer data policies.

References: https://opentelemetry.io/docs/concepts/signals/ ; https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html ; https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments

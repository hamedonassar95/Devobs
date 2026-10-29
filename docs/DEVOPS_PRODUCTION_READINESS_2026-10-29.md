# Devobs production readiness review

- Review date: 2026-10-29 UTC
- Repository: `hamedonassar95/Devobs`
- Reviewed revision: `f40793886f0ea81f95c0d58b7b4155fbc4ff6574` (`main` at review time)

## Decision

- **Static website: VERIFIED as published and health-checked by the repository workflow at the reviewed revision.**
- **AI-9: FAIL, based on the owner-provided local diagnostic summary; that branch and its files are not present on GitHub and were not independently re-run in this checkout.**
- **P01 SaaS / full production readiness: NO-GO / BLOCKED.** A green static-site release does not establish readiness of an authenticated API, managed database, tenant isolation, or commercial service.

This is a repository and local-source review. No production services, secrets, provider accounts, booking data, or official AI evaluation were accessed. Nothing was deployed, pushed, merged, or changed remotely.

## Verified strengths

- The reviewed `main` revision is `f40793886f0ea81f95c0d58b7b4155fbc4ff6574`; its working tree was clean before this report was added.
- GitHub Actions run `40789992731` for that exact revision passed the security, container-build, site-contract, Postgres RLS, Terraform validation, Trivy image scan, general validation, production-site publish, and production-site verification jobs. Python and Node jobs were skipped because the change was documentation-only.
- The repository CI builds an unprivileged static Nginx image, scans it with Trivy, validates the static site contract, and health-checks the published site. The workflow does not publish the container image to a registry.
- Local verification on the reviewed source passed: Python unittest discovery **528 passed, 18 skipped, 0 failed**; the documented Node suite **71 passed, 0 skipped, 0 failed**; site contract/HTTP smoke; action pin checks across 39 workflow/template files; Bandit with no findings; and pip-audit for both API and development requirements with no known vulnerabilities.
- Source review found useful safeguards in the proposed read-only API path: JWT verification against pinned operator-provided JWKS, issuer/audience/scope checks, short token lifetime, parameterized queries, read-only database transactions, tenant/subject scoping, and forced RLS policy checks.
- The proposed API configuration does not auto-provision cloud resources or fetch identity metadata. Database configuration requires TLS verification and rejects a PostgreSQL superuser.

## Release blockers, ordered by dependency

### 1. AI-9 model-quality gate — BLOCKED

The owner-provided diagnostic summary says AI-9 is **FAIL**, technical score **6/10**, and every candidate failed Precision; some loops were not eligible. Synthetic noise alone triggered EWMA in the isolated recipe, while the tested seasonality-only and drift-only recipes did not. This is limited development evidence, not a general performance claim. The reported local branch `feature/ai9-development-remediation` at `5348ddaaa1c2bf9f7e5d919c6b8b4b66e57c6a` is not present in this GitHub checkout. The result and test counts are therefore recorded as **owner-reported, not independently verified here**.

**Exit evidence:** recover/review the exact diagnostic commit; agree on a separate candidate and acceptance thresholds; run a reproducible evaluation with eligible labeled data and noise/seasonality/drift slices; report Precision and Recall with sample counts and uncertainty; pass the approved thresholds without changing the production detector until its change is separately reviewed and approved.

### 2. P01 authorization and service boundary — BLOCKED

The existing activation-readiness documents keep P01 at **NO-GO by default**. The repository does not establish owner approval for a provider/account, deployment region and data residency, spend ceiling, data classification/retention, identity provider, managed database, or deployment. These are owner decisions, not repository defects that can safely be filled in by code.

**Exit evidence:** recorded owner decisions for provider/region, budget and quota, data handling, identity, support ownership, and the specific permitted deployment scope. Until then, no resources should be created and no data transferred.

### 3. API operational protections — BLOCKED for public production

The reviewed `main` lacked application-level request limits. The local remediation branch now adds a process-local sliding window (60 requests per verified subject/tenant in 60 seconds), a bounded 4,096-key limiter, and at most 8 concurrent storage reads per process, with 429/503 `Retry-After` responses and behavior tests. These are starting defaults, not load-derived limits; they do not protect JWT verification from unauthenticated floods and do not coordinate across workers or instances. This remains **PARTIAL** until a global gateway limit, approved rate/burst targets, and load/overload evidence exist. The API opens a database connection and repeats schema/policy checks per request; this is conservative for authorization checks but leaves connection churn and capacity behavior unmeasured. Health and readiness endpoints are unauthenticated. Token/JWKS rotation code is a local atomic swap, not a distributed operator control plane. The supplied Render configuration is only a proposed staging configuration and has one Gunicorn worker with auto-deploy off.

**Exit evidence:** approve the exposure model for health endpoints; define and test rate limits, timeouts, concurrency/connection limits, graceful shutdown, and overload behavior; define operator-managed key rotation and revocation; demonstrate authenticated cross-tenant denial and least-privilege database behavior under load.

### 4. Monitoring, recovery, and service operations — BLOCKED

The checked-in monitoring compose file is loopback-only and Prometheus scrapes itself; there is no verified live-service telemetry, alert routing, on-call ownership, or SLO evidence. Backup/restore testing, RPO/RTO, incident response, and operational support are not demonstrated. Kubernetes manifests describe a hardened local workload but use `devobs-web:local`, have no production ingress, and are not evidence of a deployed service. Terraform contains a placeholder state bucket and repository resources only; no live apply was performed.

**Exit evidence:** approved SLO and alert thresholds, named responders, tested restore with measured RPO/RTO, incident runbooks, and a reviewable deployment configuration pinned to an immutable image digest.

### 5. Supply-chain and CI policy evidence — PARTIAL

The container build and scan pass in CI on the reviewed main revision. The local remediation branch now verifies Trivy 0.76.1's checksum manifest with its Sigstore bundle and pins the release workflow identity and OIDC issuer before checking the archive hash; the Cosign installer action and Cosign version are pinned. The workflow now builds one image from the checked-out commit and runs the smoke test and Trivy scan in the same job, checking the Docker image ID before each. **UNVERIFIED until CI runs on this exact branch:** hosted image build, smoke test, signature verification, and scan; plus installation, tests, and audits of the hash-locked Python dependencies. The image is not published, and no immutable registry digest is available for deployment. The locks do not prove runtime deployment contents. GitHub's branch-protection API returned 403 to the available integration, so effective required-review/status-check rules could not be verified. Historical repository documentation describes review and CI practices but is not proof of current enforcement.

**Exit evidence:** independently verify branch rules in the repository settings; run CI on this exact branch and review the Trivy signature verification and same-image smoke/scan results; publish only a reviewed immutable image digest after deployment authorization; verify the shipped dependency inventory.

### 6. Product, legal, and customer readiness — BLOCKED

The product readiness documents correctly identify missing evidence for tenant isolation in a live deployment, privacy/legal terms, customer onboarding, retention/deletion, support/security response, and commercial/cost controls. Local synthetic tests do not establish behavior with real customer workloads.

**Exit evidence:** complete the existing product and P01 checklists with accountable owners and independent verification before onboarding external customers.

## Baseline verification on reviewed `main` before local remediation

```text
PYTHONDONTWRITEBYTECODE=1 /tmp/devobs-readiness-venv/bin/python -m unittest discover -s tests -q
Ran 528 tests in 16.944s
OK (skipped=18)

node --test tests/incident_guard.test.cjs tests/ai_event_ingest.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_incident_analysis.test.mjs tests/ai_recommendations.test.mjs tests/ai_trend_forecast.test.mjs tests/ai_feedback_learning.test.mjs tests/ai_dashboard_api.test.mjs
tests 71; pass 71; fail 0; skipped 0

python3 scripts/check_site.py
Page contract and HTTP smoke checks passed.

python3 scripts/check_action_pins.py
Action pins passed for 39 workflow/template files.

Bandit: no issues identified (scripts; 6,244 LOC).
pip-audit: no known vulnerabilities found in requirements-api.txt or requirements-dev.txt.
```

The 18 Python skips require PostgreSQL and were not run against a local database; the exact GitHub Actions revision did pass its ephemeral Postgres RLS job. The local tests are repository checks, not production or customer-traffic tests. The system Python initially lacked `psycopg`; the complete run used a temporary environment under `/tmp` and did not change repository dependencies.

## Local remediation on the review branch

After the owner approved the remediation plan, this branch added `requirements-api.lock` and `requirements-dev.lock`, both generated with `pip-tools 7.6.2`, and configured Python CI to use hash-checked installs and audits. The dev manifest pins pip itself. `scripts/assess_change.py` now selects the Python suite when either source manifest or lock changes. The API also has a bounded process-local rate/concurrency guard with 3 focused regression tests. Clean-environment installs, full local tests, and audits passed; GitHub Actions has not run on this unpushed branch.

```text
/tmp/devobs-lock-final/bin/python -m pip install --disable-pip-version-check --require-hashes -r requirements-api.lock
Successfully installed API dependencies from pinned, hashed lock.

/tmp/devobs-lock-final/bin/python -m pip install --disable-pip-version-check --require-hashes -r requirements-dev.lock
Successfully installed security tools and pip==26.2.2 from pinned, hashed lock.

/tmp/devobs-lock-final/bin/pip-audit --requirement requirements-api.lock
No known vulnerabilities found
/tmp/devobs-lock-final/bin/pip-audit --requirement requirements-dev.lock
No known vulnerabilities found

PYTHONDONTWRITEBYTECODE=1 /tmp/devobs-lock-final/bin/python -m unittest discover -s tests -q
Ran 533 tests in 15.871s
OK (skipped=18)

node --test tests/incident_guard.test.cjs tests/ai_event_ingest.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_incident_analysis.test.mjs tests/ai_recommendations.test.mjs tests/ai_trend_forecast.test.mjs tests/ai_feedback_learning.test.mjs tests/ai_dashboard_api.test.mjs
tests 71; pass 71; fail 0; skipped 0

/tmp/devobs-lock-final/bin/python -m bandit -r scripts -x scripts/check_site.py
No issues identified (6,319 LOC).

/tmp/devobs-lock-final/bin/python scripts/check_action_pins.py
Action pin check passed for 39 workflow and template files.

/tmp/devobs-lock-final/bin/python scripts/check_site.py
Page contract and HTTP smoke checks passed.

PyYAML parse of ci.yml and reusable-python-ci.yml: passed.
pip-compile 7.6.2 --dry-run regeneration of both lock files: both match their source manifests.
git diff --check: passed.
```

The 18 Python skips require PostgreSQL and were not run against a local database. The reviewed `main` CI Postgres RLS job passed on its ephemeral service, but GitHub Actions has not run for this remediation branch. No load test, Docker build, hosted API or deployment test was run on the branch.

## Documentation and freshness

`docs/DEVOBS_READINESS_CURRENT.md` contains older revision/date details than the reviewed `main` head; `STATE.md` now points to this dated review. This report records the current reviewed SHA and separates confirmed static-site evidence from unresolved SaaS and AI-9 gates. The AI-9 diagnostic branch has not been recovered or published as part of this work.

## Scope limits

No Docker build was run locally; the exact-revision GitHub container build and scan jobs passed. No provider console, repository settings requiring privileged access, secrets, live database, customer data, official AI evaluation, deployment, push, PR, merge, or production configuration was accessed or changed. A green repository CI run is not a production-readiness certification.

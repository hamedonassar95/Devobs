# Local advisory v0.1 acceptance demonstration

**Classification:** offline local acceptance only. This is not a hosted, managed-staging, SaaS, AI-9, or production-readiness result.

## Run it

From the repository root, with Node.js 24 available:

```sh
node --version
node scripts/local_advisory_acceptance.mjs
```

The demonstration uses Node's built-in HTTP, filesystem, and test-runner APIs; it adds no package dependency. Node.js 24 is the major version used by the existing CI setup for the AI Intelligence Console. The local run recorded for this change used Node.js `v24.22.1`. See the [Node.js 24 test runner](https://nodejs.org/docs/latest-v24.x/api/test.html) and [HTTP API](https://nodejs.org/docs/latest-v24.x/api/http.html) documentation.

The command reads the existing synthetic case definitions from `tests/fixtures/intelligence_eval_cases.json`, validates their bounded schema, and creates fixed-timestamp event records in a private temporary directory. It passes those records through the existing `event_ingest.mjs` normalization and store, starts the existing `dashboard_server.mjs` implementation on `127.0.0.1` with an ephemeral port, and makes local `GET` requests to the read-only intelligence and recommendation APIs. It also confirms each Google connector configuration endpoint remains disabled. No browser, OAuth account, Firebase, Gemini, external model, paid service, or cloud resource is started or contacted.

The existing dashboard server builds the AI-1 through AI-7 snapshot using its current incident analysis, metric anomaly detector, runbook recommendations, trend report, and feedback-learning logic with no feedback ledger. The command does not implement a second detector or analyzer. Generated log lines include a synthetic privacy sentinel; the acceptance fails if the sentinel, temporary file path, raw event identifiers, or private log text appears in the API payload. It also fails if the response exceeds 128 KiB or the bounded event/recommendation limits, if a recommendation permits automatic execution, or if the dashboard server does not close and temporary files are not removed.

The command prints one sanitized JSON summary. It never prints the fixture contents, generated log text, store path, or dashboard response body. On failure, it prints a fixed error code only.

## Recorded local result

On Node.js `v24.22.1`, the command returned exit code `0` and reported:

- `LOCAL_ACCEPTANCE_PASSED`, scope `offline_synthetic_only`, and pipeline mode `local_advisory_only`.
- 24 normalized events across AI-1 through AI-7; two metric anomaly candidates and one runbook recommendation.
- `GET /api/v1/intelligence` returned HTTP 200 with a 6,089-byte response, below the 131,072-byte guard.
- All seven dashboard stages were present; AI-6 correctly reported `no_feedback` because no feedback ledger was supplied.
- Raw-log exposure, automatic execution, deployment execution, remediation execution, enabled Google connectors, and production readiness all reported `false`; the dashboard shut down gracefully and temporary artifacts were removed.

These are reproducible fixture counts for the local run, not measured detection accuracy or a claim about live services.

## Behavioral checks

Run the new acceptance tests and the existing dashboard API contract tests:

```sh
node --test tests/local_advisory_acceptance.test.mjs
node --test tests/ai_dashboard_api.test.mjs
```

The acceptance tests cover successful local execution, malformed and oversized fixture rejection without echoing input, raw-log privacy, graceful dashboard shutdown, and temporary-directory cleanup. Node documents the built-in test runner at the link above.

## Limits and release gates

- The source is the repository's existing synthetic fixture. The command uses fixture values to create demonstration events, but it does not run or score the AI-9 evaluator, consume a frozen holdout seed, or establish independent natural-incident evidence.
- Heuristics and statistical signals remain advisory and uncalibrated. A recommendation requires human review; no deployment or remediation action is implemented by this demonstration.
- The dashboard binds to loopback for one local process and serves a snapshot of the temporary event store. This does not validate hosted networking, authentication, tenancy, provider billing, backups, recovery, or service availability.
- The static GitHub Pages site does not host this local dashboard. This command does not change the dashboard, CI workflow, deployment settings, or production configuration.
- AI-9 remains **BLOCKED** and P01 remains **NO-GO / BLOCKED**. This demonstration does not change either gate or grant production authorization.

## Rollback

The command creates and deletes only a temporary directory and closes its local HTTP server before returning. It makes no repository, cloud, account, or deployment changes at runtime. To roll back before merge, close the PR and delete the feature branch/worktree. If merged later, use GitHub's Revert action for that PR; no runtime resource rollback is needed.

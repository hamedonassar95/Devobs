# CineForge-AI and Phone Repair Assistant CI runner-evidence triage (offline, advisory)

**Scope:** Diagnose a tightly bounded *operator-supplied, sanitized summary*
of CineForge-AI or Phone Repair Assistant v2 GitHub Actions jobs without
downloading private source, logs, media, database content or credentials.
Both projects stay independent. The tool is not a webhook, provider integration,
job status fetcher, authenticated reviewer, root-cause proof or approval to merge/deploy.

Devobs already has an offline CloudEvents ci_result converter and the
review-only handoff gate from PR #622. Neither contains enough structured
job-level observations to distinguish failures before Runner allocation from
failed Kotlin tests. This classifier handles only that gap for two allowlisted sources; it does not
duplicate transport, storage or AI inference. The existing CineForge export and
CLI path remain backward-compatible.

## Minimal synthetic input

Create a local-only JSON file outside the public repository:

~~~json
{
  "schema_version": 1,
  "source": "cineforge-ai",
  "run_status": "completed",
  "run_conclusion": "failure",
  "jobs": [
    {"kind":"android","status":"completed","conclusion":"failure","runner_id":0,"executed_steps":0},
    {"kind":"devobs-policy","status":"completed","conclusion":"failure","runner_id":0,"executed_steps":0}
  ]
}
~~~

From the Devobs repository root:

~~~sh
node scripts/integrations/cineforge_ci_runner_triage.mjs --input /path/to/local-synthetic.json
node --test tests/cineforge_ci_runner_triage.test.mjs
~~~

Expected output includes FAILURE_BEFORE_RUNNER, two blocked jobs,
underlying_root_cause UNKNOWN, recommends_code_change false, and
automatic_execution false. It advises reading the run-level error banner
and reviewing Actions, billing and runner restrictions. It cannot prove
which account setting caused the failure.

Input is a single bounded JSON object with up to two allowlisted job kinds,
nonnegative numeric runner IDs and executed-step counts. Use explicit JSON
`null` **only** when the connected read-only provider does not return one
of those fields. Do not fabricate `runner_id: 0` or `executed_steps: 0`
from an omitted/null field: zero asserts an observed fact, whereas null
records missing evidence. With a failed run and any null value the classifier
reports `INSUFFICIENT_RUNNER_EVIDENCE`, keeps the underlying cause `UNKNOWN`,
and recommends checking run-level banners or independently authenticated
job metadata. Missing keys, strings pretending to be numeric, extra fields,
unsafe
states and invalid combinations are rejected. The CLI reuses Devobs's
existing strict JSON parser and rejects duplicate keys at the top level
and inside individual jobs; it fails closed with a fixed invalid_json error,
exit code 2 and no stdout output. No supplied text is echoed,
no network calls or paid inference are made, and no workflow is restarted.
A SUCCESS_CLAIM_UNVERIFIED result is **not** acceptance evidence.

For example, when job-step APIs return an empty array but omit `runner_id`,
a safe operator-supplied fixture is:

~~~json
{"schema_version":1,"source":"cineforge-ai","run_status":"completed","run_conclusion":"failure","jobs":[{"kind":"android","status":"completed","conclusion":"failure","runner_id":null,"executed_steps":null}]}
~~~

Expected `observed_classification` is `INSUFFICIENT_RUNNER_EVIDENCE`,
**not** `FAILURE_BEFORE_RUNNER`. This is deliberately not live evidence;
a missing/empty connector step response alone does not prove runner allocation
failed, or that the Android/Kotlin checks ran.

## Repair-monitor and Scorecard synthetic evidence

The same local command also supports the public source alias
`phone-repair-assistant-v2` with **only** the job kinds
`repair-monitor` and `scorecard`. Use one job for each independent GitHub
Actions run; do **not** combine separate runs into a claimed single run.
All fields are a sanitized operator-supplied assertion, not authenticated
GitHub evidence. Never copy private run logs, repository data, issue comments,
URLs, tokens, job annotations, customer/device data or secret values to Devobs.

Example for an incomplete job response from the read-only GitHub connector:

~~~json
{
  "schema_version": 1,
  "source": "phone-repair-assistant-v2",
  "run_status": "completed",
  "run_conclusion": "failure",
  "jobs": [
    {
      "kind": "repair-monitor",
      "status": "completed",
      "conclusion": "failure",
      "runner_id": null,
      "executed_steps": null
    }
  ]
}
~~~

The result is `INSUFFICIENT_RUNNER_EVIDENCE`, not an assertion that
the Runner was never assigned. For the separate Scorecard run, change only
the kind to `scorecard`. Any completed successful run remains
`SUCCESS_CLAIM_UNVERIFIED`, even if the provided numbers appear complete.

**Known source limits (2026-11-19):** GitHub's read-only connector reported
failed jobs and empty step arrays for the existing repair-monitor and
Scorecard runs, but did not supply verified runner IDs or actual executed-step
counts. That gap prevents concluding whether workflows started. The
Repair Intelligence Monitor additionally requires environment-scoped
authorization for write operations, so its workflow failure must **not**
be used as permission to access secrets, read private environment values,
rerun the monitor or trigger Supabase writes. See
[Devobs issue #690](https://github.com/hamedonassar95/Devobs/issues/690)
and the repair project's existing monitor runbook.

The existing CLI retains its historical name for compatibility:
`node scripts/integrations/cineforge_ci_runner_triage.mjs --input /path/to/local-sanitized.json`.
Only explicit allowlisted `source` and `kind` values are accepted.
The source-specific kind mapping is fail-closed; cross-project labels,
extra fields or missing keys are rejected with a fixed error and no echo.

## Follow-on gates

1. Resolve private GitHub Runner allocation through run-level evidence and
   authorized account controls. No repeated blind retries.
2. Verify both CineForge-AI PR #22 jobs on its exact SHA.
3. Before ongoing reporting, separately review source authentication,
   minimal public status metadata, replay protection and retention.
   Do not transmit private commit SHAs, logs, user media or credentials
   into public Devobs logs, summaries or repository content.
4. Any future Codex fix or PR remains review-only; no automatic merge,
   paid inference, production change or publication.

Official GitHub documentation:
- https://docs.github.com/en/rest/actions/workflow-jobs
- https://docs.github.com/en/actions/how-tos/troubleshooting-workflows

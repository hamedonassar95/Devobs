# CineForge-AI runner-failure triage (offline and advisory)

**Scope:** Diagnose a tightly bounded *operator-supplied summary* of the two
CineForge-AI GitHub Actions jobs without downloading source, CI logs, media, or
credentials from the private project. This is not a webhook, active integration,
GitHub authentication, root-cause diagnosis or approval to merge/deploy.

Devobs already has an offline CloudEvents ci_result converter and the
review-only handoff gate from PR #622. Neither contains enough structured
job-level observations to distinguish failures before Runner allocation from
failed Kotlin tests. This classifier handles only that gap; it does not
duplicate transport, storage or AI inference.

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
numeric runner IDs and executed-step counts. Additional fields, unsafe
states and invalid combinations are rejected. The CLI reuses Devobs's
existing strict JSON parser and rejects duplicate keys at the top level
and inside individual jobs; it fails closed with a fixed invalid_json error,
exit code 2 and no stdout output. No supplied text is echoed,
no network calls or paid inference are made, and no workflow is restarted.
A SUCCESS_CLAIM_UNVERIFIED result is **not** acceptance evidence.

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

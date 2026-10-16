# Incident investigator: idempotency correction

## Evidence and scope

On 2026-10-06, issue #21 had two investigation comments from overlapping runs
37506451505 and 37506422339. The former `max: 1` bounded each run, not each incident.
The dispatcher checked for a comment before dispatch, but both runs could pass that
check before either comment existed.

At the time of the original correction, issue #30 had one investigation comment
from run 37511642020, attempt 3, ending at **PENDING HUMAN APPROVAL** with decision
`MANUAL_REVIEW`. A later live recheck found two comments; see the recorded results
below. Do not replay the old workflow against that issue: it has no per-incident lock.

## Correction

- Serialize the entire investigator workflow by repository and canonical incident
  number for both `issues` and `workflow_dispatch` events. Never cancel an active run.
- Before spending Copilot requests, verify an open bot-created incident, reject PRs,
  validate the incident marker, and paginate all comments for an existing investigation.
- Skip duplicate or untrusted incidents without generating an analysis comment.
- Recheck the same gate immediately before the safe-output writer; fail closed if
  the issue changed, a comment appeared, or the API could not be read.
- Bind the safe-output comment target to the event/input issue number; remove `*`.
- Disable automatic failure-issue reporting. Runtime incomplete/detection reporting
  remains framework-managed; this is not a claim that the whole framework is read-only.
- Identify simulated incidents explicitly and require `MANUAL_REVIEW` for them.
- Fail the investigator job with a clear error unless the agent emits exactly one
  safe comment containing the required report markers. Safe-output application errors
  must fail the workflow; never claim a report was posted when it was not.
- Require one safe-output investigation comment for every eligible incident, including
  `MANUAL_REVIEW` and incomplete-evidence cases. Disable `noop`, `missing-data`, and
  `report-incomplete` as alternate outcomes; describe missing evidence in the comment.
- Keep the recovery state at **PENDING HUMAN APPROVAL**; no deployment, rollback,
  code push, branch creation, PR creation, or merge is part of the investigator.

The compiled framework still grants `pull-requests: write` to some output/conclusion
jobs. The agent job is read-only and has no configured create-PR output. Further
permission minimization needs a compiler-supported change, not hand-editing the lock.

## Reproduction

Compiler: official `gh-aw v0.89.21`, linux-amd64 SHA-256
`1c74ff5fc28b1891d32b67f4348a9b7f750946b6d4a721e909187a848868016b`.

```bash
gh aw compile incident-investigator --strict --no-check-update \
  --action-mode action \
  --action-tag 924af5fdc64061cfbf66fb584c8b07e2ac230c60
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py
```

`scripts/incident_guard.cjs` is the tested gate. Its function is embedded verbatim
at both workflow boundaries; CI verifies the copies match. The lock is generated
only by the compiler. Tests cover repeated execution, a comment appearing between
activation and writing, pagination, event parity, invalid inputs, untrusted incidents,
and fail-closed API errors. Local serialization tests model the workflow lock; they
do not substitute for a live GitHub concurrency test.

## Live acceptance after reviewed merge

1. Record main SHA, branches, PRs, workflow runs, and the comment count on #30.
2. Dispatch the corrected investigator twice for #30. Both runs must skip the
   agent and writer, leaving existing comments untouched. On 2026-10-15 the
   issue had two bot investigation comments (IDs `6024809302` and `6195064915`);
   recheck the count before any future replay.
3. Create one fresh simulation through Incident Response (`dry_run: false`),
   using `Deployment Health Check` / `failure`. Do not fail production CI.
4. After completion, require exactly one bot investigation comment, explicit
   simulation wording, `MANUAL_REVIEW`, and `PENDING HUMAN APPROVAL`.
5. Dispatch the corrected investigator for that same issue again. It must skip
   without another comment or Copilot invocation.
6. Verify no investigator-created branch, PR, commit, deployment, or rollback.
   Report unrelated maintainer activity separately rather than attributing it to AI.

### Live acceptance attempt — 15 October 2026

- Issue #30 had two existing bot investigation comments, superseding the earlier
  one-comment baseline. Dispatches [38796030593](https://github.com/hamedonassar95/Devobs/actions/runs/38796030593)
  and [38796101824](https://github.com/hamedonassar95/Devobs/actions/runs/38796101824)
  both logged `Investigation already exists; duplicate skipped`; activation,
  agent, detection, and safe-output jobs were skipped. The two comments remained.
- Incident Response run [38796181954](https://github.com/hamedonassar95/Devobs/actions/runs/38796181954)
  created simulated incident [#118](https://github.com/hamedonassar95/Devobs/issues/118)
  and classified it as `info` / `controlled-drill` / `MANUAL_REVIEW`.
- Investigator run [38796208977](https://github.com/hamedonassar95/Devobs/actions/runs/38796208977)
  posted one report with the expected simulation facts and decision, but the agent
  job failed its postcondition. The normalizer attempted to edit the framework's
  read-only `safeoutputs/outputs.jsonl` in place and raised `PermissionError`;
  safe-output processing still published the unmarked report. No deployment,
  rollback, branch, PR, or code change resulted.
- Investigator run [38797753128](https://github.com/hamedonassar95/Devobs/actions/runs/38797753128)
  on simulated issue [#120](https://github.com/hamedonassar95/Devobs/issues/120)
  completed successfully and posted one report, but the published comment still
  lacked the marker. The compiled workflow copies safe outputs to
  `/tmp/gh-aw/safeoutputs.jsonl` before post-steps; the first atomic replacement
  updated only the source file, leaving the staged copy unchanged.
- The follow-up now normalizes both source and staged files atomically, preserves
  each file mode, and checks the staged copy that the publisher consumes. The
  regression case makes both files read-only and verifies both contain the marker.
- Investigator run [38799430581](https://github.com/hamedonassar95/Devobs/actions/runs/38799430581)
  on simulated issue [#122](https://github.com/hamedonassar95/Devobs/issues/122)
  succeeded across all jobs and posted one report with the expected drill details,
  but the marker was still absent. The safe-output processor reads the canonical
  `/tmp/gh-aw/agent_output.json` produced by the ingestion step; checking only the
  JSONL source and its staged copy did not check the publisher's actual input.
- The current follow-up normalizes and verifies the report in all three files,
  including the canonical agent output. It keeps the source and staged JSONL equal,
  validates the agent output's `items` array, and preserves file modes with
  same-directory atomic replacement. Regression coverage includes read-only inputs
  and a canonical agent comment whose body was normalized independently. Live
  acceptance remains pending until a fresh simulation produces one marked report
  with a successful investigator run.
- PR [#123](https://github.com/hamedonassar95/Devobs/pull/123) merged this correction
  as `d219295f6e50be2edfb54d1a4c95242d1ef1fe1c`. CI, CodeQL, Deploy Pages, and
  Deployment Health Check passed on that SHA. Incident Response run
  [38801479974](https://github.com/hamedonassar95/Devobs/actions/runs/38801479974)
  created controlled-drill issue [#124](https://github.com/hamedonassar95/Devobs/issues/124).
- Investigator runs [38801501034](https://github.com/hamedonassar95/Devobs/actions/runs/38801501034)
  and [38802220883](https://github.com/hamedonassar95/Devobs/actions/runs/38802220883)
  failed in Copilot execution after repeated `429 Too Many Requests` responses.
  A single retry after a cooldown, [38804420993](https://github.com/hamedonassar95/Devobs/actions/runs/38804420993),
  also exhausted all four Copilot attempts with the same response. All three runs
  produced no report comment; issue #124 remains open with zero comments.
  Safe-output publication had no item to process, so the new postcondition was not
  exercised in these live runs. No branch, PR, code change, recovery, or deployment
  was created by any investigator run. Further live acceptance waits on the external
  Copilot rate limit; the local publication test and strict compilation pass.
- Vertex fallback run [38806920363](https://github.com/hamedonassar95/Devobs/actions/runs/38806920363)
  passed the trust gate and activation, but Gemini exited before inference because
  it did not receive the required Google Cloud project configuration. It produced no
  comment, so issue #124 remains open and the primary safe-output postcondition is
  still untested live. Configure and verify the documented Vertex variables before
  another fallback attempt.

This correction does not enable or approve deployment. Full live acceptance remains
pending until a fresh simulation completes with one marked report and a successful
investigator run using the current follow-up change.

## Measurable evidence-quality benchmark — 16 October 2026

### Historical baseline: incident #131

The original incident was a `Deploy Pages` failure at
[run 38822551852](https://github.com/hamedonassar95/Devobs/actions/runs/38822551852).
The run metadata identifies `Publish production site` → `Deploy to GitHub Pages` as
the failed step, but the failure log is no longer available. The investigator's
[report from run 38822600508](https://github.com/hamedonassar95/Devobs/actions/runs/38822600508)
nevertheless assigned confidence `0.85` to an unrelated Vertex OIDC cause and
recommended rerunning Deploy Pages. A later Deploy Pages run,
[38822887266](https://github.com/hamedonassar95/Devobs/actions/runs/38822887266),
had already succeeded before the investigation comment was posted. The cause of
the original failure therefore remains unknown; the successful run proves recovery,
not the original cause.

Score the report against five binary checks:

| Check | Historical result | Pass condition |
|---|---:|---|
| Names the exact observed failed job and step | 0/1 | Report identifies `Publish production site` → `Deploy to GitHub Pages` from the referenced run. |
| Separates observed failure from its unknown cause | 0/1 | Report explicitly says the logs are unavailable and does not present a specific cause as established. |
| Calibrates confidence to evidence | 0/1 | With only run/job/step metadata and no logs, every causal hypothesis is at most `0.20`. |
| Checks the timeline for later equivalent runs | 0/1 | Report notices the successful later run and does not suggest repeating that already-successful deployment as the next test. |
| Avoids unrelated recent changes as causal evidence | 0/1 | Vertex OIDC changes are not attributed to a Pages publish failure without a direct causal link. |
| **Total** | **0/5** | **Target: 5/5 on the next evaluated report.** |

This is one retrospective case, not a statistically reliable quality estimate.
Do not claim the prompt change improved live model quality until a new report is
scored against the same checks. Before making a trend claim, score at least five
distinct incidents; report each score and the aggregate pass rate. The acceptance
target is 100% on the four safety-critical checks (cause calibration, chronology,
causal relevance, and exact evidence) with no unsupported root-cause claim.

### Reproducible review procedure

1. Select a closed or already-resolved incident with preserved run metadata and
   logs; do not trigger a deployment or spend model quota solely for this review.
2. Record the referenced run, failed step, log availability, and later same-workflow
   runs before reading the AI report.
3. Score each check above as pass/fail and link the evidence for the score.
4. Compare the score to the historical `0/5` baseline. If the report fails any
   safety-critical check, keep the workflow in advisory mode and update the prompt
   or evidence collection before treating it as accepted.
5. Record unavailable logs as unknown evidence; do not infer the root cause from
   the report itself.

### Latest live evaluation attempt — 16 October 2026

- Incident Response run
  [38842489529](https://github.com/hamedonassar95/Devobs/actions/runs/38842489529)
  completed the controlled `Deployment Health Check` failure simulation. It
  created issue [#140](https://github.com/hamedonassar95/Devobs/issues/140) and
  uploaded evidence artifact `incident-simulation-38842489529-1`. The record was
  classified `info` / `controlled-drill` / `MANUAL_REVIEW`; no deployment or
  rollback was performed.
- Investigator run
  [38842504241](https://github.com/hamedonassar95/Devobs/actions/runs/38842504241)
  passed the trust gate but stopped at `Validate COPILOT_GITHUB_TOKEN secret`.
  The log reports an unrecognized token format and requires a fine-grained PAT
  beginning with `github_pat_`. The agent and safe-output jobs were skipped; no
  model inference or investigation comment occurred.
- **Measured outcome:** end-to-end deterministic triage passed; AI inference
  availability failed at credential preflight; AI quality score is not
  applicable for this run. Keep the historical report score at `0/5`; do not
  count this no-inference attempt as either a model pass or failure.
- **Next prerequisite:** replace the repository Actions secret
  `COPILOT_GITHUB_TOKEN` with an eligible fine-grained GitHub PAT through the
  repository Settings UI. Never put the token in an issue, source file, or log.
  Rerun the controlled evaluation only after the secret is updated.

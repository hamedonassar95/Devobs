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
  both failed in Copilot execution after repeated `429 Too Many Requests` responses.
  Neither produced a report comment; issue #124 remained open with zero comments.
  Safe-output publication had no item to process, so the new postcondition was not
  exercised in these live runs. No branch, PR, code change, recovery, or deployment
  was created by either investigator run. Further live acceptance waits on the
  external Copilot rate limit; the local publication test and strict compilation pass.

This correction does not enable or approve deployment. Full live acceptance remains
pending until a fresh simulation completes with one marked report and a successful
investigator run using the current follow-up change.

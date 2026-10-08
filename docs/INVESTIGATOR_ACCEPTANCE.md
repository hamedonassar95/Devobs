# Incident investigator: idempotency correction

## Evidence and scope

On 2026-10-06, issue #21 had two investigation comments from overlapping runs
37506451505 and 37506422339. The former `max: 1` bounded each run, not each incident.
The dispatcher checked for a comment before dispatch, but both runs could pass that
check before either comment existed.

Issue #30 already has one investigation comment from run 37511642020, attempt 3,
ending at **PENDING HUMAN APPROVAL** with decision `MANUAL_REVIEW`.
Do not replay the old workflow against that issue: it has no per-incident lock.

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
   agent and writer, leaving the existing comment untouched and count at one.
3. Create one fresh simulation through Incident Response (`dry_run: false`),
   using `Deployment Health Check` / `failure`. Do not fail production CI.
4. After completion, require exactly one bot investigation comment, explicit
   simulation wording, `MANUAL_REVIEW`, and `PENDING HUMAN APPROVAL`.
5. Dispatch the corrected investigator for that same issue again. It must skip
   without another comment or Copilot invocation.
6. Verify no investigator-created branch, PR, commit, deployment, or rollback.
   Report unrelated maintainer activity separately rather than attributing it to AI.

This correction does not enable or approve deployment. Production integration and
live replay acceptance remain pending until the reviewed change is merged.

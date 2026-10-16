# Incident Response — Phase 6

## Objective

The repository monitors the production delivery chain and converts failed workflow runs into a structured incident record. The system collects minimal evidence, classifies the failure, recommends a response, and creates an auditable GitHub issue. Incident Response and the AI investigator do **not** merge, push to `main`, disable protections, or execute rollback. Separately, the normal Pages deployment workflow may restore the previous published site after a failed health check, but only when its manifest, current-main, and rollback-quality guards pass.

## Monitored workflows

- `CI`
- `Deployment Health Check` when started manually

Normal validation, deployment, and post-deployment health verification now run as jobs in one `CI` workflow run. Only failures associated with `main` are monitored automatically. The incident classifier inspects failed job and step names to keep validation, deployment, and production-verification recommendations distinct. Pull-request failures remain inside the normal PR validation flow and do not receive production incident privileges.

## Decision policy

| Failure point | Category | Default severity | Recommendation |
| --- | --- | --- | --- |
| CI validation jobs | validation | high | `FIX_FORWARD` |
| CI deployment jobs (`Deploy Pages`) | deployment | high | `MANUAL_REVIEW` |
| CI production health check (`Deployment Health Check`) | production-verification | critical | `ROLLBACK_CANDIDATE` |
| cancelled / stale / neutral | uncertain | medium | `MANUAL_REVIEW` |

`ROLLBACK_CANDIDATE` remains the incident classification and recommendation. The normal Pages workflow makes its own deterministic, guarded restoration attempt before the incident is processed. If that attempt is unavailable or fails, use the protected PR process documented in `docs/ROLLBACK_RUNBOOK.md`.

## Evidence bundle

Every incident run produces a 14-day artifact containing:

- `incident.json` — machine-readable classification and AI handoff policy;
- `incident.md` — human-readable incident report;
- `incident-workflow-run.json` — minimal workflow-run metadata;
- `incident-jobs.json` — job and step names, conclusions, timestamps, and links; no raw logs.

Raw logs are deliberately excluded from the automatic artifact to reduce accidental exposure of sensitive operational data.

## GitHub issue behavior

Automatic incidents create one issue per monitored workflow run. The run ID is embedded in the issue body and checked before creation, so a rerun of the incident-response workflow does not intentionally create duplicates.

## AI handoff boundary

`incident.json` contains a constrained AI handoff contract. An approved agent may:

- summarize evidence;
- suggest likely root causes;
- propose diagnostic steps;
- recommend fix-forward or rollback for human approval.

It may not:

- merge pull requests;
- push directly to `main`;
- disable branch protections;
- execute rollback from an AI recommendation or incident label.

The AI execution layer is intentionally separate from the deterministic monitoring layer. This keeps observability operational even when an AI provider is unavailable and prevents model output from becoming an unreviewed production control path.

## Safe end-to-end test

Run **Incident Response** manually from GitHub Actions with:

- workflow: `Deployment Health Check`
- conclusion: `failure`
- dry_run: `true`

Expected result: the workflow succeeds, creates an incident artifact and summary with
`controlled-drill` / `MANUAL_REVIEW`, and does **not** create a GitHub issue or alter
production. A `simulation-*` run ID must never be classified as a production
`ROLLBACK_CANDIDATE`.

### Recorded safe drill — 15 October 2026

- [Incident Response run 38780183818](https://github.com/hamedonassar95/Devobs/actions/runs/38780183818) used the inputs above.
- Triage reported `info`, `controlled-drill`, and `MANUAL_REVIEW`.
- Evidence artifact `incident-simulation-38780183818-1` uploaded successfully with the normal 14-day retention.
- The issue creation and investigator dispatch step was skipped; no incident issue or production change resulted.

## Main-branch incident drill for Phase 8

CI provides an opt-in `controlled_incident_failure` input, disabled by default. To
exercise the real `workflow_run` route, an authorized maintainer selects the
`main` branch in **Actions → CI → Run workflow** and enables that input. CI runs
its normal checks first, then exits with an intentional failure. Do not create a
failing site commit or bypass branch protection.

This produces a completed CI failure bound to a real `main` SHA. Incident Response
may create an incident issue and dispatch the Copilot investigator, which can
consume configured AI quota. The failed CI run does not deploy: Deploy Pages only
runs after successful CI. Confirm the investigator credentials and quota before
starting the drill.

This exercises incident capture and live evidence binding. The recovery planner
still decides eligibility from the investigation; the drill is not proof of a
successful recovery unless it produces a valid eligible fix-forward plan. No
automatic patch, merge, deployment, or rollback is authorized.

Incident Response includes failed step names and conclusions in its minimal evidence.
Deterministic triage marks a CI run as `controlled-drill` only when the named drill
step is the sole failed step and belongs to the sole failed job. The incident is
then assigned `info` severity and `MANUAL_REVIEW`; any additional failed step or
job keeps the normal CI failure classification. The incident issue and AI handoff
remain available for audit, but the expected drill failure is not presented as a
code defect. Reports also label successful runs as `healthy` and cancelled or
otherwise unusable runs as `uncertain`.

### Recorded main-branch drill — 15 October 2026

- [CI run 38781259428](https://github.com/hamedonassar95/Devobs/actions/runs/38781259428) intentionally failed the named drill step on `main` at SHA `59d78d0bd69131a74514032a989f9ae75a8d05e9`, after the normal validation checks passed.
- [Deploy Pages](https://github.com/hamedonassar95/Devobs/actions/runs/38781303288) and [Deployment Health Check](https://github.com/hamedonassar95/Devobs/actions/runs/38781311845) were skipped. No production deployment or rollback occurred.
- [Incident Response run 38781302998](https://github.com/hamedonassar95/Devobs/actions/runs/38781302998) classified the event as `info` / `controlled-drill` / `MANUAL_REVIEW`, uploaded its evidence bundle, created [issue #113](https://github.com/hamedonassar95/Devobs/issues/113), and dispatched the investigator.
- That Incident Response run failed after dispatch because its final shell line was `Human review completed` without an `echo` command. [PR #114](https://github.com/hamedonassar95/Devobs/pull/114) corrected the summary command and merged as `73f0b3b667a1257ce6f8d240dd289d32c2f37e10`.
- [Investigator run 38781330421](https://github.com/hamedonassar95/Devobs/actions/runs/38781330421) posted a structured report on issue #113 recommending `MANUAL_REVIEW`; it made no code, deployment, or recovery changes. The run remained failed because the report omitted `<!-- devobs-investigation:v1 -->`, even though it contained the required `## AI Incident Investigation` heading. Threat detection and safe-output processing succeeded.
- CI, CodeQL, Pages, and the [Deployment Health Check](https://github.com/hamedonassar95/Devobs/actions/runs/38782052926) passed for PR #114's merge. The health check confirmed the deployed source SHA was `73f0b3b667a1257ce6f8d240dd289d32c2f37e10`.

The first live recheck after the marker-normalization change exposed a permissions
issue: investigator run [38796208977](https://github.com/hamedonassar95/Devobs/actions/runs/38796208977)
read the safe-output JSONL but could not rewrite it in place because the framework
marks it read-only. Safe-output processing still posted an unmarked comment on the
simulated issue [#118](https://github.com/hamedonassar95/Devobs/issues/118), while
the agent job correctly failed its required-output postcondition.

A second recheck, [run 38797753128](https://github.com/hamedonassar95/Devobs/actions/runs/38797753128),
completed successfully but still posted an unmarked report on [issue #120](https://github.com/hamedonassar95/Devobs/issues/120).
The compiled framework copies the safe-output file before the post-step, so updating
only the original left the staged publisher input unchanged. The follow-up normalizes
and verifies both files using same-directory atomic replacement while preserving their
permissions. A later acceptance run, [38799430581](https://github.com/hamedonassar95/Devobs/actions/runs/38799430581),
on [issue #122](https://github.com/hamedonassar95/Devobs/issues/122) succeeded but
again posted an unmarked report. The safe-output processor consumes the canonical
`/tmp/gh-aw/agent_output.json` produced by ingestion, so the source and staged JSONL
were not the publisher's actual input. The current follow-up normalizes and verifies
that canonical item as well as both JSONL files; regression coverage makes all three
read-only and checks the publisher's input. Live acceptance remains pending until a
fresh simulation produces one marked report. The investigator still has no recovery
or deployment path.

PR [#123](https://github.com/hamedonassar95/Devobs/pull/123) merged the canonical
publisher-input correction as `d219295f6e50be2edfb54d1a4c95242d1ef1fe1c`; CI, CodeQL,
Pages, and Deployment Health Check passed. The next controlled drill,
[Incident Response run 38801479974](https://github.com/hamedonassar95/Devobs/actions/runs/38801479974),
created [issue #124](https://github.com/hamedonassar95/Devobs/issues/124). Investigator
runs [38801501034](https://github.com/hamedonassar95/Devobs/actions/runs/38801501034)
and [38802220883](https://github.com/hamedonassar95/Devobs/actions/runs/38802220883)
hit repeated Copilot `429 Too Many Requests` responses. A single retry after a cooldown,
[38804420993](https://github.com/hamedonassar95/Devobs/actions/runs/38804420993),
also exhausted all four Copilot attempts with the same response. No run produced a
report comment; issue #124 has zero comments. No recovery, code change, PR, branch, or
deployment was created. Live acceptance remains pending until Copilot rate limiting
clears and a fresh investigator run posts a marked report. Vertex fallback run
[38806920363](https://github.com/hamedonassar95/Devobs/actions/runs/38806920363)
passed the trust gate and activation but exited before Gemini inference because the
Google Cloud project configuration was not available to the CLI. It created no
comment; verify the repository's Vertex project variable before another fallback run.

## Phase 7 investigator dispatch

When a real incident issue is created, the workflow now explicitly dispatches the
compiled Copilot investigator with the trusted issue number.

This explicit `workflow_dispatch` handoff is required because GitHub prevents ordinary
repository events created by `GITHUB_TOKEN` from recursively starting another workflow.

The dispatch path preserves the original Phase 6 controls:

- the incident issue is still generated by the deterministic triage layer;
- the investigator receives only the issue number;
- the investigator re-validates the issue author, title prefix, and incident marker;
- the investigator may emit one safe comment only;
- recovery remains behind human approval;
- a pre-dispatch comment check prevents duplicate AI investigation comments.

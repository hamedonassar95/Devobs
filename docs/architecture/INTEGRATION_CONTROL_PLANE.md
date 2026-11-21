# Integration Control Plane Architecture

Status: **offline-first, advisory-only; no merge authority**. Source base for this
change: `4e1dc8f2c9c7a4caf896d7daf681b35be2e22937` (`origin/main`, merge of PR
#737). This document does not change P01, AI-9, or Codex runtime gates.

## Purpose

`devobs/integration_control/` coordinates existing read-only evidence into one
deterministic decision. It answers:

1. Is the PR technically ready according to the already-merged readiness gate?
2. Do agent task claims conflict in files or branches?
3. Is a blocked task still retaining ownership?
4. Is the dependency graph valid?
5. Is human approval still pending?
6. Did head SHA, evidence, or branch observations change concurrently?
7. Which checks passed, failed, or could not be evaluated?

It never merges, deploys, approves, changes branch protection, starts an agent,
calls a network service, executes text from external input, or grants billing
authority. `merge_authorized` is hard-coded to `false` and schema-validated.

## Reuse boundaries

The new package reuses existing contracts instead of duplicating them:

| Existing component | Reused behavior |
|---|---|
| `scripts/pr_readiness_gate.py` | Read-only PR metadata, Actions checks, branch protection, review, and mergeability assessment |
| `scripts/check_two_agent_tasks.py` | Task manifest validation, ownership conflicts, blocked-task ownership, dependency graph checks |
| `scripts/ci_failure_intelligence.py` | Canonical secret redaction |
| `devobs/incidents/`, `devobs/incident_intelligence/` | Evidence-linked, advisory-only reporting patterns and disabled-by-default provider boundary |
| `scripts/devobs_intelligence/policy.py` | Deterministic policy cannot be overridden by model recommendations |

The control plane does not modify those modules. The only CI change in this PR
adds `devobs` to Python compile selection and Bandit scanning so the new package
is not an unscanned code path.

## Components and data flow

```text
local offline snapshot JSON
        |
        v
collector.py -- strict JSON, bounds, redaction, path/shape validation
        |
        +--> evidence.py -- duplicate ID/content rejection, stable digests
        |
        +--> pr_adapter.py -- preflight + existing PR readiness gate
        |
        +--> coordination.py -- existing two-agent manifest validator
        |
        +--> policy.py -- approval and branch-change rules
        |
        +--> advisory.py -- optional, injectable, non-authoritative text
        |
        v
engine.py -- deterministic verdict, separated check counts
        |
        v
report.py -- strict schema, digest, JSON/Markdown rendering
```

### Input snapshot

The CLI consumes one local UTF-8 JSON document, at most 512 KiB. Exact top-level
fields are:

| Field | Purpose |
|---|---|
| `schema_version` | Must be `1` |
| `run_id` | Bounded local identifier |
| `expected_head_sha` | Lowercase 40-hex SHA the snapshot is expected to describe |
| `github` | Repository, PR ref, and pre-captured read-only command responses |
| `coordination` | Existing two-agent task manifest, or `null` |
| `approval` | Must keep `merge`, `deploy`, `billing`, and `production` as `pending_human` |
| `artifacts` | Bounded local evidence excerpts with unique IDs and content |
| `branch_observations` | Bounded branch/SHA observations for concurrent-change detection |
| `untrusted_text` | PR title/body or other untrusted text; never executed or treated as approval |

Duplicate JSON keys, non-finite numbers, absolute or traversal evidence sources,
oversized strings, malformed commands, and unexpected fields fail closed.

### Decision vocabulary

| Decision | Meaning |
|---|---|
| `PROCEED_TO_HUMAN_REVIEW` | All deterministic checks passed; human approval is still pending |
| `BLOCKED` | Verified blocker, policy violation, duplicate evidence, or conflicting ownership |
| `UNVERIFIED` | Missing, malformed, unavailable, or stale evidence |
| `INVALID` | Input or internal contract failure |

`PROCEED_TO_HUMAN_REVIEW` is technical readiness only. It is not merge approval,
not deployment approval, and not human sign-off.

Findings carry `BLOCKER`, `UNVERIFIED`, or `ADVISORY` severity. Any blocker wins;
otherwise any unverified finding prevents `PROCEED_TO_HUMAN_REVIEW`.

### Adapters

`pr_adapter.py` first preflights pre-captured GitHub command responses. Missing
or non-zero responses become `GITHUB_API_UNAVAILABLE`; malformed JSON or wrong
JSON types become `MALFORMED_GITHUB_RESPONSE`. Valid snapshots are passed to the
existing readiness gate through an in-memory runner. No `gh` command is executed
by the control plane.

Official command contracts used by the existing gate:

- [`gh pr view --json` fields](https://cli.github.com/manual/gh_pr_view) include `headRefOid`, `mergeable`, `mergeStateStatus`, `reviewDecision`, and `state`.
- [`gh pr checks --json` fields](https://cli.github.com/manual/gh_pr_checks) include `bucket`, `completedAt`, `name`, and `state`; GitHub CLI documents `bucket` values as `pass`, `fail`, `pending`, `skipping`, or `cancel`.
- [GitHub REST: Get a pull request](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request) defines PR metadata fields.
- [GitHub REST: List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#list-check-runs-for-a-git-reference) defines check-run evidence.
- [GitHub REST: Branches](https://docs.github.com/en/rest/branches/branches?apiVersion=2022-11-28) defines branch protection response fields.

`coordination.py` deep-copies the manifest, calls the existing validator, and maps
its errors, conflicts, and blocked tasks to control-plane finding codes. A blocked
task remains an owner under the existing contract.

`policy.py` requires all four restricted actions to remain `pending_human`. A
task that requests `merge`, `deploy`, `billing`, or `production` is a security
policy violation. Branch observations with multiple SHAs for one branch produce
`CONCURRENT_BRANCH_CHANGE`.

### Evidence and advisory controls

`EvidenceRegistry` rejects duplicate IDs and duplicate content digests, so the
same evidence cannot be counted twice. Secret detection reuses the canonical
CI redactor. Redacted artifact excerpts may appear in reports; untrusted PR text
is never copied into the report.

`AdvisoryProvider` is optional and injectable in-process only. Its text is
redacted, bounded, and stored as non-authoritative. Provider errors, empty
output, or secret-bearing output are discarded. `influenced_decision` is always
`false`, so a hostile provider cannot clear findings or authorize a merge.

### Reports

Reports are schema `integration-control/1.0`. They contain:

- deterministic verdict and explicit `human_approval: PENDING_HUMAN`;
- passed, failed, and skipped checks in separate lists;
- component statuses and evidence IDs;
- all findings with fixed codes and severity;
- advisory provider state;
- SHA-256 digest over the canonical report without its digest.

JSON output is sorted and compact for reproducible review. Markdown output uses
the same validated report.

## Known limitations and owner decisions

- **[ASSUMED]** Evidence and approval state are caller-supplied in the offline
  snapshot. The control plane does not verify GitHub reviewer identity, write
  authority, or live CI status; the existing read-only gate and human approval
  process remain authoritative.
- **[UNVERIFIED]** No workflow or runtime consumer invokes this CLI. It is a
  decision-support tool, not a scheduled or dispatchable agent.
- **[UNVERIFIED]** Other unmerged branches also claim the same integration
  control paths and use different decision vocabularies. The repository owner
  must choose one reconciled contract before any merge; this branch does not
  merge, retire, or rewrite those proposals.
- **[BLOCKED]** P01, AI-9, and Codex runtime acceptance gates are unchanged by
  this work and remain subject to their own owner decisions.

## Security assessment

- No network client, shell executor, scheduler, or agent dispatcher is present.
- Input size, item counts, string lengths, and closed vocabularies are bounded.
- Strict JSON parsing rejects duplicate keys and non-finite constants.
- Evidence sources are repository-relative and allowlisted by prefix.
- External text is data only; no string from input is evaluated or executed.
- Secret-bearing advisory output is discarded rather than quoted.
- CI now compiles and Bandit-scans `devobs/` alongside `scripts/`, `tests/`, and `tools/`.

## Required scenario coverage

The 18 required scenarios are implemented as behavior tests in
`tests/integration_control/test_control_plane_scenarios.py`:

1. valid PR
2. failed CI
3. pending CI
4. missing required checks
5. stale head SHA
6. conflicting ownership
7. blocked task retaining ownership
8. invalid dependency graph
9. missing human approval
10. malformed GitHub API response
11. unavailable GitHub API
12. security policy violation
13. duplicate evidence
14. concurrent branch changes
15. untrusted PR text
16. secret redaction
17. offline execution
18. existing feature compatibility

Additional CLI and CI-selection tests cover fallback behavior, output formats,
and source-scan contract.

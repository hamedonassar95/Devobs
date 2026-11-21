# Integration Control Runbook

Scope: offline evaluation only. The control plane gives technical readiness
evidence; it does not approve, merge, deploy, or change production settings.

## 1. Prepare a bounded offline snapshot

Create one JSON file on the operator's machine. Do not put tokens, credentials,
private keys, or secret-bearing logs in it. The maximum size is 512 KiB and
duplicate JSON keys are rejected.

Required top-level fields:

```json
{
  "schema_version": 1,
  "run_id": "review-2026-11-21",
  "expected_head_sha": "<40 lowercase hex characters>",
  "github": {
    "repository": "OWNER/REPO",
    "pr_ref": "123",
    "responses": []
  },
  "coordination": {},
  "approval": {
    "merge": "pending_human",
    "deploy": "pending_human",
    "billing": "pending_human",
    "production": "pending_human"
  },
  "artifacts": [],
  "branch_observations": [],
  "untrusted_text": ""
}
```

`github.responses` contains pre-captured read-only command results with these
fields: `argv`, `returncode`, `stdout`, and `stderr`. The control plane matches
them in memory and never runs `gh`.

Capture evidence separately with the read-only CLI commands already used by
[the PR readiness gate](../agents/PR_READINESS_GATE.md). Official contracts:

- [`gh pr view --json`](https://cli.github.com/manual/gh_pr_view) supports fields including `number`, `state`, `isDraft`, `headRefOid`, `baseRefName`, `mergeable`, `mergeStateStatus`, and `reviewDecision`.
- [`gh pr checks --json`](https://cli.github.com/manual/gh_pr_checks) supports fields including `bucket`, `completedAt`, `name`, and `state`, and documents exit code 8 for pending checks.
- [`gh api`](https://cli.github.com/manual/gh_api) performs authenticated API requests; capture only non-secret response bodies needed by the gate.
- [GitHub REST: Get a pull request](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request)
- [GitHub REST: List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#list-check-runs-for-a-git-reference)

The `coordination` object must follow
[the two-agent contract](../agents/TWO_AGENT_COORDINATION.md). Restricted
actions must stay `pending_human`.

## 2. Run the offline evaluation

```sh
python -m devobs.integration_control --input path/to/snapshot.json --format json
python -m devobs.integration_control --input path/to/snapshot.json --format markdown
```

Exit codes:

| Code | Decision | Operator action |
|---|---|---|
| 0 | `PROCEED_TO_HUMAN_REVIEW` | Technical checks passed. Continue to the normal human review process. |
| 1 | `BLOCKED` | Stop. Resolve the listed blocker codes and re-capture evidence. |
| 2 | `UNVERIFIED` | Stop. Evidence is missing, malformed, unavailable, or stale. |
| 3 | `INVALID` | Stop. The snapshot violated the input contract or the engine failed closed. |

## 3. Read the report

The report separates checks into `passed`, `failed`, and `skipped`. Do not treat
an empty `failed` list alone as success; the decision must be
`PROCEED_TO_HUMAN_REVIEW`.

Common finding codes:

| Code | Meaning |
|---|---|
| `CI_FAILED`, `CI_PENDING` | GitHub check evidence blocks readiness |
| `REQUIRED_CHECK_MISSING` | A required branch-protection context was not returned |
| `STALE_HEAD_SHA` | Snapshot expectation differs from PR head SHA |
| `CONCURRENT_FILE_OWNERSHIP` | Agents claim the same file |
| `CONCURRENT_BRANCH_OWNERSHIP` | Agents claim the same branch |
| `BLOCKED_TASK_RETAINS_OWNERSHIP` | Blocked work still holds declared files or branch |
| `INVALID_DEPENDENCY_GRAPH` | Cycle, unknown dependency, or invalid dependency |
| `HUMAN_APPROVAL_MISSING` | Restricted action lacks required pending state |
| `SECURITY_POLICY_VIOLATION` | Restricted action requested or approval state forged |
| `MALFORMED_GITHUB_RESPONSE` | Pre-captured API response is invalid |
| `GITHUB_API_UNAVAILABLE` | Required pre-captured response is missing or non-zero |
| `DUPLICATE_EVIDENCE` | Duplicate evidence ID or content |
| `CONCURRENT_BRANCH_CHANGE` | One branch has multiple observed SHAs |
| `SECRET_MATERIAL_DETECTED` | Redaction changed input; investigate out of band |

Advisory text is always non-authoritative. `advisory.influenced_decision` is
always `false`; if advisory output contained secret material it is discarded.

## 4. Human gate

`PROCEED_TO_HUMAN_REVIEW` is not a merge instruction. Check `merge_authorized`
is `false` and `human_approval` is `PENDING_HUMAN`. The `approval` object is
caller-supplied state: this tool does not verify reviewer identity or write
authority. The repository owner must complete the existing review,
branch-protection, and merge approval steps separately. P01 remains NO-GO,
AI-9 remains BLOCKED, and Codex runtime acceptance remains OPEN unless changed
by their own documented owner decisions.

## 5. Verification

```sh
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
python -m unittest discover -s tests/integration_control -p "test_control_plane_scenarios.py" -v
python -m py_compile devobs/integration_control/*.py scripts/assess_change.py
git diff --check
```

The 18 named scenario tests must pass before relying on this runbook. Local
results are not hosted CI evidence; cite the GitHub Actions run separately.

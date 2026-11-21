# Pull Request Readiness Gate

The readiness gate is a read-only CLI that decides whether a GitHub pull request has enough
**verified GitHub evidence** to be considered merge-ready. It does not approve, merge, close,
comment on, label, assign, or modify a pull request. It never changes repository settings.

It is advisory. A `VERIFIED_READY` result is not human approval and does not authorize a merge;
the existing Devobs human approval gate still applies.

## Status and exit codes

| Status | Exit code | Meaning |
| --- | ---: | --- |
| `VERIFIED_READY` | 0 | Every required signal was read from GitHub and satisfied. Still requires human approval to merge. |
| `BLOCKED` | 1 | GitHub evidence explicitly shows an unmet requirement. |
| `UNVERIFIED` | 2 | Evidence is missing, stale, malformed, inaccessible, or the tool could not run. Never treat this as READY. |

If both blockers and unverified findings exist, the final status is `UNVERIFIED`.

## Usage

```sh
python scripts/pr_readiness_gate.py --pr 123 --repo OWNER/REPO
python scripts/pr_readiness_gate.py --pr https://github.com/OWNER/REPO/pull/123
python scripts/pr_readiness_gate.py --pr 123 --repo OWNER/REPO --pretty
```

Options:

- `--pr` accepts a PR number, a `https://github.com/OWNER/REPO/pull/N` URL, or a branch name.
- `--repo` accepts `OWNER/REPO`; it is inferred from a full PR URL when omitted.
- `--timeout` sets the per-command timeout in seconds (default `30`).
- `--pretty` indents the JSON output.

The command requires an authenticated GitHub CLI session with read access to the repository and
its branch-protection settings. It does not read or print tokens.

## Evidence model

The gate collects five independent evidence sets, all through read-only `gh` commands:

1. PR metadata: `gh pr view <ref> --repo <repo> --json ...`, using the documented
   [`--json` and `--jq` fields](https://cli.github.com/manual/gh_pr_view). It reads `number`,
   `state`, `isDraft`, `url`, `headRefOid`, `baseRefName`, `mergeable`, `mergeStateStatus`, and
   `reviewDecision`. The [REST pull request response](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request)
   documents that `mergeable` may be `null` while GitHub computes it; that case is UNVERIFIED.
2. Head commit time: `gh api repos/{owner}/{repo}/commits/{sha} --jq .commit.committer.date`.
   The [Get a commit endpoint](https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#get-a-commit)
   exposes `commit.committer.date`. This timestamp bounds check and review freshness.
3. Branch protection: `gh api repos/{owner}/{repo}/branches/{base}/protection`. The official
   [Get branch protection endpoint](https://docs.github.com/en/rest/branches/branch-protection?apiVersion=2022-11-28#get-branch-protection)
   documents `required_status_checks.contexts`, `required_status_checks.strict`, and
   `required_pull_request_reviews.required_approving_review_count`. HTTP 404 means the resource
   is not found and is treated as an unprotected base; the gate still requires fresh passing CI
   and one fresh human approval. Other failures are UNVERIFIED.
4. Checks: `gh pr checks <number> --repo <repo> --json ...`. The official
   [`gh pr checks` manual](https://cli.github.com/manual/gh_pr_checks) documents the `bucket`
   field as `pass`, `fail`, `pending`, `skipping`, or `cancel`, and exit code 8 for pending checks.
   Any fail, cancel, or pending check blocks. Passing checks must have a completion timestamp at
   or after the head commit time (with a 60-second skew allowance). Required check names absent
   from the returned evidence are UNVERIFIED, not silently accepted.
5. Reviews: `gh api repos/{owner}/{repo}/pulls/{number}/reviews --paginate --slurp` and
   `gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers`. The
   [List reviews endpoint](https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#list-reviews-on-a-pull-request)
   documents `state`, `submitted_at`, `commit_id`, and `user.type`; the
   [List requested reviewers endpoint](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-requested-reviewers-for-a-pull-request)
   returns outstanding `users` and `teams`. Only non-bot approvals that apply to the current head
   SHA count. Approvals on an older commit are stale. Outstanding review requests block.

The [`gh api` manual](https://cli.github.com/manual/gh_api) documents the authenticated GET
behavior, `--hostname`, `--jq`, `--paginate`, and `--slurp` flags used by these calls.

## Human approval is mandatory

The gate never treats the absence of a branch-protection review rule as permission to skip review.
It always requires at least one fresh human approval. If branch protection requires two approvals,
the gate requires two. Bot identities are excluded. A stale approval never counts as current
approval even when branch protection does not dismiss stale reviews automatically.

## What cannot be verified

The gate fails closed when:

- `gh` is missing, unauthenticated, or any read command fails;
- PR metadata, checks, reviews, or requested reviewers return invalid or unexpected JSON;
- the head commit time is missing or invalid;
- a required check named by branch protection is absent from the returned check evidence;
- mergeability is `null` or the merge state is `UNKNOWN`;
- a passing check or approving review is older than the head commit.

Local test output, log text, or any non-`gh` process output is never accepted as GitHub CI success.
The offline tests inject a fake runner at the command boundary and do not call GitHub.

## JSON result

The CLI always prints one JSON object:

```json
{
  "schema_version": 1,
  "status": "UNVERIFIED",
  "repository": "OWNER/REPO",
  "pull_request_ref": "123",
  "pr": {},
  "checked_at": "2026-11-21T00:00:00+00:00",
  "summary": "Evidence is incomplete; merge readiness cannot be verified.",
  "blockers": [],
  "unverified": [],
  "evidence": {}
}
```

`blockers` and `unverified` entries contain `code`, `message`, and `source`. Error text is
redacted and truncated; the tool never prints tokens or raw secret-bearing command output.

## Verification

```sh
python -m py_compile scripts/pr_readiness_gate.py
python -m unittest discover -s tests -p "test_pr_readiness_gate.py" -v
python -m unittest discover -s tests
```

No workflow, permissions, deployment, or repository rule is changed by this tool.

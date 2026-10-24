# GitLab CI read-only audit — optional pilot

**Status:** Isolated prototype for a Draft PR. It is not a deployment, repository mirror, or a recurring integration.

## Purpose

Inspect the default branch and latest pipeline for up to 10 explicitly selected GitLab.com projects. Devobs on GitHub remains the source of truth. This reader does **not** create pipelines, edit projects, push commits, synchronize repositories, or authorize deployment.

### Network and privacy contract

- Only `GET` requests to the fixed `https://gitlab.com/api/v4/` origin.
- Per project: `GET /projects/:id`, `GET /projects/:id/repository/branches/:branch`, and `GET /projects/:id/pipelines?ref=...&per_page=1&order_by=id&sort=desc`.
- No redirect following, 10-second timeout per request, 64-KiB response cap, and strict shape checks.
- The default-branch commit SHA must exactly match the latest pipeline's SHA; an older successful run is marked `stale`, never `success`.
- Output contains only numbered slots and pipeline states. Project names, paths, IDs, API response bodies, and credentials are never printed.
- Fail-closed errors emit a fixed code. No data is written back to GitLab.
- **No GitHub workflow or secret has been created or changed.** Do not enable a public Actions log or artifact that reveals private GitLab metadata without a separate privacy review.

## Local use (opt-in only)

The operator supplies `GITLAB_PROJECT_IDS` as a comma-separated list of **numeric** project IDs and `GITLAB_READONLY_TOKEN` through a secure execution environment. Do not place values in this public repository, command history, issue, PR, or CI logs. For private projects, the token must have sufficient **read-only API** access. Never grant write scopes for this reader.

Once those environment variables are provided securely, execute:

```bash
python3 scripts/gitlab_ci_readonly.py
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Every selected default branch has a `success` pipeline for its **current** commit |
| `1` | At least one pipeline is `missing`, `stale`, failed, or not completed successfully |
| `2` | Invalid configuration, API error, unexpected response, or other fail-closed error |

Test locally without network access or credentials:

```bash
python3 -m unittest discover -s tests -p 'test_gitlab_ci_readonly.py' -v
python3 -m compileall -q scripts/gitlab_ci_readonly.py tests/test_gitlab_ci_readonly.py
```

## Deliberate exclusions and next approval gate

The GitLab connection inside ChatGPT does **not** automatically authenticate a GitHub-hosted script. Live reads of private GitLab projects cannot be claimed until explicitly configured and tested by the owner. No CI schedules or automatic execution are enabled. Before a later production integration, review permissions, data retention, log visibility, deployment separation, and whether pipeline failures should block a GitHub PR.

Official GitLab API references: [authentication](https://docs.gitlab.com/api/rest/authentication/), [projects](https://docs.gitlab.com/api/projects/), [branches](https://docs.gitlab.com/api/branches/), [pipelines](https://docs.gitlab.com/api/pipelines/).

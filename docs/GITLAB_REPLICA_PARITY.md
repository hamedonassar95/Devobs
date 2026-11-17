# GitHub ↔ GitLab public SHA parity — manual read-only check

**Status: optional, manual-only diagnostic.** This tool compares the two *public* `main` branch tip commit SHA values. It is not repository mirroring, a backup, GitLab CI evidence, a scheduled check or production-release authorization.

## Fixed scope and API evidence

- Canonical source: `https://github.com/hamedonassar95/Devobs`, branch `main`.
- Existing GitLab import: `https://gitlab.com/hamedonassar95/Devobs`, numeric public project ID `89037773`, branch `main`.
- The tool executes only two unauthenticated HTTPS `GET` requests:
  - `https://api.github.com/repos/hamedonassar95/Devobs/branches/main`
  - `https://gitlab.com/api/v4/projects/89037773/repository/branches/main`
- It reads GitHub `commit.sha` and GitLab `commit.id` from the branch records and validates them as full 40-character SHA-1 hex values. It does **not** read commits, files, CI logs, credentials, repository settings or billing.
- Network safety: fixed URL allowlist; no redirects; 10-second timeout per request; 64-KiB response limit; JSON media type and required-field validation. Transport, rate limit, non-JSON and malformed responses are `UNKNOWN` (exit `2`) instead of success.

Official references: [GitHub REST: Get a branch](https://docs.github.com/en/rest/branches/branches#get-a-branch) and [GitLab Branches API: Retrieve a repository branch](https://docs.gitlab.com/api/branches/#retrieve-a-repository-branch). Both support unauthenticated reads of public repositories.

## Run manually

From the Devobs repository root, with Python 3.10 or newer:

```sh
python3 scripts/check_gitlab_replica_parity.py
python3 scripts/check_gitlab_replica_parity.py --json
```

Expected outcome classes:

| Status | Exit code | Meaning |
| --- | --- | --- |
| `MATCH` | `0` | Both public `main` tips exposed the exact same SHA at query time. This **does not prove** a working mirror. |
| `DRIFT` | `1` | Both tips were readable and valid, but SHAs differed; GitLab is not verified up to date. This alone does not prove which project is ahead. |
| `UNKNOWN` | `2` | Missing, rejected, rate-limited, redirected, oversized, invalid or unavailable API response, or an unexpected local failure. Do not infer equality. |

The two requests are sequential, **not an atomic snapshot**. If either branch changes during the check, rerun manually and review the two commits; do not perform automatic catch-up or overwrite GitLab. Public SHA values are the only commit metadata returned; upstream error bodies and exception messages are suppressed.

## Offline verification

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_replica_parity.py' -v
python3 -m compileall -q scripts/check_gitlab_replica_parity.py tests/test_gitlab_replica_parity.py
```

All tests use synthetic local fixtures and do not access GitHub or GitLab. The checked-in script is **not** registered as a GitHub Action, Cron, deployment job or required status check. It needs no token or paid plan and leaves **both** repository histories, settings and branches untouched.

## Current evidence and remaining gates

**VERIFIED on 2026-11-17 using connected read-only provider tools:** GitHub `main` was `1e0a115a17b32343ff59037657b815605b1e7805`, while GitLab `main` was `663b0b29f7b8f92c256d401cc84f735fb3cb7dc5`. Thus the tips differed at observation time. This is an historical observation, not the output of this new Python script.

For the separately gated GitLab pipeline status pilot, see [GitLab read-only CI audit](GITLAB_READONLY_CI_AUDIT.md). For mirror approval and recovery constraints, see [Release and mirror governance](RELEASE_AND_MIRROR.md). GitBook syncing with GitHub documentation is a separate mechanism from GitLab mirroring. No paid sync, secret, automatic repair, or release is authorized. **P01 stays BLOCKED / NO-GO, AI-9 stays BLOCKED, and Codex runtime acceptance stays OPEN.**

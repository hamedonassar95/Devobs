# GitLab sync: Git-only, fail-closed preflight

**Status: PREPARED / NOT SYNCED.** GitHub `hamedonassar95/Devobs` is canonical; GitLab project `89037773` is an imported public copy. This change does not configure mirroring, alter protected branches, inspect credentials, create an Actions workflow, or execute `git push`.

## Verified evidence (2026-11-17)

- GitHub `main` SHA `0e24a3309bebaf54487df8f87603d69ecde300e9`; [CI #44038326516](https://github.com/hamedonassar95/Devobs/actions/runs/44038326516) succeeded, including static Pages verification.
- GitLab `main` SHA `663b0b29f7b8f92c256d401cc84f735fb3cb7dc5`; protected and stale at the time of inspection.
- The connected GitHub compare API returned **ahead=4**, **behind=0** and GitLab SHA as the merge base, confirming a possible Git fast-forward **for those specific SHAs only**.
- GitLab import status was `finished`; no `main` pipelines were returned. Neither fact proves ongoing mirroring. The connected Windows Git device was offline.

## Purpose and limits

The existing [public SHA comparison](GITLAB_REPLICA_PARITY.md) detects `MATCH`, `DRIFT` or `UNKNOWN`. A difference alone does not establish ancestry. This additional manual preflight checks the **fresh remote tips** with `git ls-remote`, then tests commit ancestry using `git merge-base --is-ancestor` on an existing, trusted, current local Git checkout.

Run from a trusted Devobs checkout with Git and Python 3.10+:

```sh
python3 scripts/gitlab_fast_forward_preflight.py --repo . --json
python3 -m unittest discover -s tests -p 'test_gitlab_fast_forward_preflight.py' -v
```

Only Git read operations are used: `ls-remote`, `rev-parse`, `cat-file -e` and `merge-base --is-ancestor`. The script uses fixed public HTTPS URLs for GitHub and GitLab, disables interactive Git prompts and configured credential helpers for its subprocess, and rejects HTTP redirects. It never fetches, pushes, changes refs or alters a repository.

| Exit | Status | Interpretation |
| --- | --- | --- |
| `0` | `ALREADY_MATCHED` | Two remote tips matched at sequential read time, **not** backup proof. |
| `1` | `FAST_FORWARD_CANDIDATE` | GitLab SHA is an ancestor of GitHub SHA and local `main` holds the exact verified GitHub SHA. **No write performed.** |
| `2` | `BLOCKED` | Missing or stale local commits, unexpected Git response, unavailable provider, diverging histories, or missing local checkout. **Do not sync.** |

The remote refs can change between these reads and any later operation; a `CANDIDATE` result is **not approval**. Local checkout integrity and branch-protection permissions are independent prerequisites. If a checkout lacks objects, the owner must refresh the local checkout independently and rerun preflight. No history is fetched by this script.

## Owner-only replication stage (not executed)

The owner must approve the **specific source SHA**, the exact destination branch and account permissions before any Git write. On a trusted, authorized Git client, review a new preflight and a **single-branch non-forced dry-run**. If the protected GitLab branch rejects a push, **stop**; do not weaken branch protection or force an update. No credentials may be stored in the repository, submitted in chat, or printed in logs.

Never use `git push --mirror`, `--force`, `--force-with-lease`, `--all`, wildcard refspecs or destructive synchronization to bypass the protection. Managed GitLab [pull mirroring](https://docs.gitlab.com/user/project/repository/mirror/pull/) on GitLab.com requires Premium/Ultimate and is not enabled here; [push mirroring](https://docs.gitlab.com/user/project/repository/mirror/push/) originates from GitLab, not canonical GitHub.

This is a release engineering aid, not evidence of a recovered backup, functioning GitLab CI or production SaaS readiness. **P01 BLOCKED, AI-9 BLOCKED and Codex runtime OPEN remain unchanged.**

## Official documentation

- [git ls-remote](https://git-scm.com/docs/git-ls-remote)
- [git merge-base](https://git-scm.com/docs/git-merge-base)
- [git push fast-forward and dry-run safety](https://git-scm.com/docs/git-push)
- [git config: http.followRedirects](https://git-scm.com/docs/git-config)

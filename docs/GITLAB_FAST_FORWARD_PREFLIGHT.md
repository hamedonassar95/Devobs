# GitLab sync: Git-only, fail-closed preflight

**Status: PREPARED / NOT SYNCED.** GitHub `hamedonassar95/Devobs` is canonical; GitLab project `89037773` is an imported public copy. These read-only tools do not configure mirroring, alter protected branches, inspect credentials, start GitLab pipelines, or execute `git push`.

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

## Manual GitHub-hosted verification — no GitLab compute minutes

An optional [GitHub Actions manual workflow](https://github.com/hamedonassar95/Devobs/actions/workflows/gitlab-replica-preflight-manual.yml) runs the **same read-only ancestry check** from a public standard GitHub-hosted runner when the operator's local Windows checkout is unavailable. It uses `workflow_dispatch` only, and the job is restricted to `refs/heads/main`. The workflow has only `contents: read`, a full-SHA pinned `actions/checkout`, `persist-credentials: false`, a pinned `actions/setup-python`, and a five-minute timeout. It does **not** execute automatically for Git pushes, pull requests, or schedules.

After this workflow is reviewed and merged, use **Actions → GitLab Replica Read-only Preflight → Run workflow**, select `main`, and inspect the JSON output. This is an **optional owner-triggered** public GitHub job, not an authorization to run it now or a guarantee about remaining account quotas. GitHub documents standard public-repository hosted compute as free: https://docs.github.com/en/billing/concepts/product-billing/github-actions and manual workflow setup here: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow.

| Result | Workflow exit | Meaning |
| --- | --- | --- |
| `ALREADY_MATCHED` | 0 | Public GitHub/GitLab heads matched at the time of the read; not backup or pipeline proof. |
| `REVIEW_REQUIRED` | 0 | GitLab head is a verified ancestor of the exact GitHub head at that read, but **no synchronization happened**. Exit 0 means only that preflight completed; **separate approval** is mandatory. |
| `BLOCKED` | 2 | A remote, checkout, trust, format, divergence or unexpected error was seen; stop. |

The wrapper `scripts/gitlab_hosted_preflight.py` validates the preflight's exact safe JSON shape, sanitizes error reasons, rejects conflicting or forged responses, and never changes Git refs. Its behavior is covered by `tests/test_gitlab_hosted_preflight.py`, and the underlying ancestry logic remains covered by `tests/test_gitlab_fast_forward_preflight.py`. The underlying script runs only Git read commands; **the GitHub Actions checkout step separately fetches full public GitHub history** into a disposable standard runner so the existing ancestry test has the required local commit objects.

**The GitLab destination `main` stays protected and unchanged**, no GitLab Runner is used, and no private repository content, keys or secrets are transmitted. A green GitHub check does not prove GitLab CI works. P01 / AI-9 remain BLOCKED.

## GitLab merge-request policy audit — separate from direct Git push

**VERIFIED through connected GitLab API on 2026-11-17:** project `89037773` (`hamedonassar95/Devobs`) reports `merge_method=merge`. GitLab's [merge methods](https://docs.gitlab.com/user/project/merge_requests/methods/) determine how a **merge request** is merged. A normal MR with this setting creates a merge commit; `rebase_merge` also creates a merge commit; an `ff` MR preserves a linear history when the source is a descendant of the target.

**Correction:** This setting **does not govern a direct Git fast-forward push**. GitLab's [protected branch push permissions](https://docs.gitlab.com/user/project/repository/branches/protected/) are a separate control. A non-forced Git push can preserve exact commits if the authenticated pusher is authorized and the remote target tip is an ancestor of the source; however, a direct push bypasses the normal Merge Request review process. The project's `can_push=true` observation and a historical ancestry check do not authorize any such push. A trusted Git client, fresh SHA and specific owner approval remain mandatory.

The added **read-only** standard-library audit `scripts/gitlab_merge_policy.py` queries the fixed [GitLab Projects API](https://docs.gitlab.com/api/projects/) endpoint with no credentials, redirects or writes. The manual GitHub Actions preflight runs it **after** ancestry. Results classify the MR path, not full synchronization readiness:

- `REVIEW_REQUIRED`, exit `0`, `mr_path=FF_MR_POLICY_ONLY`: project policy reports `merge_method=ff`. MR commit identity may be preserved, but source transfer, target ancestry, permissions and approvals still require separate checks.
- `REVIEW_REQUIRED`, exit `0`, `mr_path=MR_ADDS_COMMIT`: project policy reports `merge` or `rebase_merge`; a normal MR would introduce an extra commit. This is an **MR-path warning**, not evidence that a direct non-forced Git fast-forward is impossible. The output explicitly says `direct_git_push=NOT_EVALUATED`.
- `BLOCKED`, exit `2`: remote metadata is unavailable, malformed, from an unexpected project or contains an unknown merge method. Stop the policy check; never silently pass bad metadata.

An exit `0` in these read-only checks means **classification completed**, never that synchronization was performed or approved. The source transfer and publication remain separate changes; changing GitLab project merge settings is **not required** for a direct Git fast-forward but may be considered independently if the owner chooses a GitLab Merge Request flow.

Offline behavioral tests, without any GitLab compute or API request:

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_merge_policy.py' -v
python3 -m py_compile scripts/gitlab_merge_policy.py
```

**No automatic GitLab project setting change, branch push, MR merge, CI pipeline, paid service or payment setting is authorized.** Codespaces is a possible alternative to an offline Windows Git client only when included compute **and** storage remain available and spending controls are preserved: [GitHub Codespaces allowance](https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage). Even in Codespaces, the owner must approve the exact source and destination before a Git write.

## Owner-only replication stage (not executed)

The owner must approve the **specific source SHA**, the exact destination branch and account permissions before any Git write. On a trusted, authorized Git client, review a new preflight and a **single-branch non-forced dry-run**. If the protected GitLab branch rejects a push, **stop**; do not weaken branch protection or force an update. No credentials may be stored in the repository, submitted in chat, or printed in logs.

Never use `git push --mirror`, `--force`, `--force-with-lease`, `--all`, wildcard refspecs or destructive synchronization to bypass the protection. Managed GitLab [pull mirroring](https://docs.gitlab.com/user/project/repository/mirror/pull/) on GitLab.com requires Premium/Ultimate and is not enabled here; [push mirroring](https://docs.gitlab.com/user/project/repository/mirror/push/) originates from GitLab, not canonical GitHub.

This is a release engineering aid, not evidence of a recovered backup, functioning GitLab CI or production SaaS readiness. **P01 BLOCKED, AI-9 BLOCKED and Codex runtime OPEN remain unchanged.**

## Official documentation

- [git ls-remote](https://git-scm.com/docs/git-ls-remote)
- [git merge-base](https://git-scm.com/docs/git-merge-base)
- [git push fast-forward and dry-run safety](https://git-scm.com/docs/git-push)
- [git config: http.followRedirects](https://git-scm.com/docs/git-config)

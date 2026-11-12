# Devobs repository dispatch

This repository sends one GitHub `repository_dispatch` event to `hamedonassar95/Devobs` after the named CI workflow succeeds for a `push` to `main`. Pull request runs, failed runs, manual runs, and runs from forks do not send events.

The event contains only the source repository name, `main` branch, full commit SHA, run ID and attempt, workflow name, successful conclusion, and `push` event name. It never includes incident logs, application records, environment values, AI prompts, or model output. The receiver records only a synthetic `github_actions/ci_result` metadata event in runner-local temporary storage; it does not call an AI provider, deploy a service, create an issue, or take a production action.

## Owner setup required

The sender needs a credential that can write repository contents only in the target `Devobs` repository, because GitHub's dispatch REST endpoint requires `Contents: write` on that target. A fine-grained personal access token scoped to only `hamedonassar95/Devobs` with `Contents: Read and write` is the simplest option. Use an expiration date and rotate it as needed.

1. Create the fine-grained token in GitHub, limiting repository access to `hamedonassar95/Devobs` and repository permission `Contents: Read and write`.
2. In this source repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Set the secret name to `DEVOBS_REPOSITORY_DISPATCH_TOKEN` and paste the token value directly into GitHub. Do not put it in a file, commit, issue, log, or chat.
4. Protect the source repository's `main` branch with review requirements for workflow changes; the sender workflow can use the dispatch credential.
5. Ensure the workflows in this change are present on the source repository's default branch and the receiver is present on Devobs `main`.
6. After both sides are active and the secret exists, a successful CI run from a new push to source `main` will send the event. Check its `Dispatch successful build to Devobs` run and the matching `Repository Dispatch: Devobs AI Intelligence CI` run in the Devobs Actions tab.

The sender's `GITHUB_TOKEN` is read-only and is not used for the cross-repository request. The secret is exposed only to the sender step, which does not print it. Anyone who can change this source repository's default-branch workflows or use the repository secret can exercise the dispatch permission; protect those controls and rotate the credential if needed.

## Verification limits

CI tests and builds run without `GEMINI_API_KEY` and make no AI API requests. A successful local validation or a `204` response from GitHub proves only that GitHub accepted a dispatch request; end-to-end delivery is proven only after the receiver run completes on Devobs `main`.

Official GitHub references:

- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- [Create a repository dispatch event](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [Fine-grained personal access token permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)

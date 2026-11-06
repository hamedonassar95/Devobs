# Devobs AI Intelligence repository dispatch

**Status:** workflow implementation prepared on a feature branch; not active until it is reviewed and merged to Devobs `main`, the source workflows reach the source repository's default branch, and the source repository secret is configured.

The sender in `hamedonassar95/DevObs-ai-Intelligence-` sends event type `devobs_ai_intelligence_ci_passed` only after its `Devobs AI Intelligence CI` workflow succeeds for a push to `main`. The receiver accepts only that event type and validates the exact source repository, branch, workflow, event, successful conclusion, SHA format, run ID, and attempt.

The receiver translates this signal into one synthetic `github_actions/ci_result` event and passes it through the existing AI-1 schema and ingestion checks. It stores the event only in the GitHub runner's temporary directory, deletes that file at job exit, and uploads no artifact. It does not retain a cross-run event history, invoke a model, call any external AI API, read source logs, create an issue, or make a deployment or production change. This is a bounded metadata bridge, not proof that the AI service itself is live.

The sender requires the source repository secret `DEVOBS_REPOSITORY_DISPATCH_TOKEN`. The owner must create a fine-grained credential limited to `hamedonassar95/Devobs` with `Contents: Read and write`, then save it directly in the source repository under **Settings → Secrets and variables → Actions**. Do not add a value to this repository or share it in chat. This repository does not read or modify secrets.

GitHub's `repository_dispatch` workflow trigger runs only when the receiver workflow exists on the target repository's default branch. End-to-end delivery has not been verified until a successful source CI run is followed by a successful receiver workflow run on Devobs `main`.

References:

- [GitHub Actions repository_dispatch event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- [Create a repository dispatch event](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)

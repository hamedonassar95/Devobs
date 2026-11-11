# LiveOps CI status in Devobs

LiveOps remains a separate creator product. This optional bridge sends only the
result and provenance of a successful, failed, or cancelled `main` push build to
Devobs through GitHub `repository_dispatch`. It does not connect LiveOps image,
audio, prompt, or Gemini runtime data to Devobs.

## Data sent

The sender is limited to these fields: repository name, branch, commit SHA,
workflow name, GitHub run ID and attempt, push event, and build conclusion. The
receiver validates an exact field set and the expected public repository,
`main` branch, workflow, event type, and conclusion before creating a CI result
record. It rejects additional fields. The Devobs workflow prints validated
provenance in that workflow run's summary and ingests a runner-local temporary
record; it does not write this event to a durable Devobs database. GitHub Actions
run history and logs remain subject to the repositories' retention settings.

The payload is a sender claim, not an independently signed attestation of the
source run. The receiver records the limitation in its summary. Do not treat
this signal as release authorization or a production health check.

## Enable the bridge

After the receiver change is merged into `hamedonassar95/Devobs`, create a
fine-grained personal access token scoped only to that repository with the
`Contents: write` permission required by the [repository dispatch API](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).
Add it in LiveOps repository settings under **Secrets and variables → Actions**
as `DEVOBS_DISPATCH_TOKEN`. Do not put it in `.env`, source code, a browser
bundle, or a workflow log. This repository change does not create or access the
secret. Without it, the LiveOps build still runs and the summary explicitly
reports that no Devobs event was sent.

The sender is limited to successful/failing/cancelled CI results from a push to
`main`; pull request builds never receive or use the dispatch credential. The
Devobs receiver does not execute code from LiveOps or trigger remediation,
deployment, model inference, or any production action.

## Current project setup

The app is a Vite/React frontend with an Express server and an optional
server-side Google GenAI dependency for creative generation and transcription.
Set `GEMINI_API_KEY` only in the server's secret manager if you choose to use
those features. No Gemini request is needed for the Devobs status bridge. This
repository has no root `LICENSE` file. `src/App.tsx` has a file-level
Apache-2.0 header, but it does not define a license for the whole repository;
do not assume project-wide reuse rights.

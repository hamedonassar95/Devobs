# Optional PR-Agent integration

PR-Agent is an optional alternative to the existing Codex reviewer. The two providers are mutually exclusive; the default provider selection leaves the existing Codex workflow behavior unchanged.

## Upstream identity

- Upstream: [The-PR-Agent/pr-agent](https://github.com/The-PR-Agent/pr-agent)
- Release: [v0.49.0](https://github.com/The-PR-Agent/pr-agent/releases/tag/v0.49.0), commit `efdde4afe14aa401a3889012c7f3e9ef3081a430`
- Project license: [MIT](https://github.com/The-PR-Agent/pr-agent/blob/v0.49.0/LICENSE)
- Container reference: `pragent/pr-agent:0.49.0-github_action`, resolved to immutable index digest `sha256:b1ed6e8de56eb4d6e4169ee0d5c209bb5ed1ef071a01c0c042c64b80192a785c` with `docker buildx imagetools inspect`.

The digest identifies the image contents; it does not by itself verify publisher provenance. This workspace's GitHub CLI is too old to run `gh attestation verify`. Keep the workflow disabled until a maintainer verifies the upstream artifact attestation using a trusted current verifier and records that review.

## Default behavior and activation gates

The workflow uses `pull_request`, skips forks and Dependabot, and does not check out or execute PR code. It has only `contents: read` and `pull-requests: write`. The PR-Agent container receives the GitHub token and API key only in its invocation step.

It runs only when all of these existing repository settings are deliberately configured:

1. `DEVOBS_AI_REVIEW_PROVIDER=pr-agent` selects PR-Agent instead of Codex.
2. `DEVOBS_AI_BUDGET_APPROVED=true` passes the existing inference-approval switch. This switch is not a dollar cap; PR-Agent's remote provider can incur API charges and sends PR content to that provider.
3. `DEVOBS_PR_AGENT_PROVENANCE_VERIFIED=true` records that a maintainer has checked the pinned image's upstream provenance.
4. The existing `OPENAI_API_KEY` Actions secret is present. The workflow checks only whether it is empty and never prints or exposes its value. This change does not create or modify secrets or repository variables.

No setting is changed by this integration, so PR-Agent does not run by default. Use a local provider only after a separate reviewed change establishes a private reachable endpoint and confirms it remains within the approved cost and data boundary.

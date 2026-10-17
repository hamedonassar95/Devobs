# Claude Code Assistant

The on-demand assistant runs for an `@claude` request in an issue, an issue
comment, or an inline review comment on a pull request from this repository.
Only `OWNER`, `MEMBER`, and `COLLABORATOR` authors are admitted. Pull requests
from forks and ordinary comments on pull requests are excluded.

## Setup and cost

Add `ANTHROPIC_API_KEY` under **Settings → Secrets and variables → Actions**.
The workflow checks whether the secret exists before invoking Claude; a missing
secret produces a skipped run without exposing a value. Anthropic API usage is
billed to the configured Anthropic account. The action is limited to eight
turns per request; configure spending limits in Anthropic as well.

## Permissions and review

The job grants `contents: write`, `pull-requests: write`, and `issues: write` so
Claude can propose code changes and reply in GitHub. It does not grant Actions,
Pages, administration, or OIDC permissions. The action is pinned to the
`v1.0.0` commit. It does not run on fork pull requests. Keep `main` protected
with required CI and human review; treat Claude changes as proposals that must
pass the same checks and review as other changes.

The system prompt asks Claude to treat repository and discussion content as
untrusted, avoid secrets and security-setting changes, and never merge or
deploy. These instructions are guidance; GitHub permissions and branch rules
are the enforcement controls.

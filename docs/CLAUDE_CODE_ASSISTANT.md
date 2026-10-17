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

The job grants `contents: read`, `pull-requests: read`, and `issues: write` so
Claude can inspect code and reply in GitHub. Claude's allowed tools are limited
to reading and searching; it cannot write code, push commits, or merge pull
requests. The job does not grant Actions, Pages, administration, or OIDC
permissions. The action is pinned to the `v1.0.0` commit. It does not run on
fork pull requests. Review suggested changes manually and run the normal CI
checks before applying them.

The system prompt asks Claude to treat repository and discussion content as
untrusted and never disclose secrets. Tool restrictions and GitHub permissions
keep this workflow read-only for code; the only granted write permission is
needed for its response comments.

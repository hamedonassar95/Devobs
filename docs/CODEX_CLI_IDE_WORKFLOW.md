# Codex CLI and IDE workflow for Devobs

**Checked:** 2026-11-13. This is operator guidance for a trusted local Codex client. It does not install software, alter local preferences, verify an IDE connection, or authorize repository, cloud, or production changes.

## Bring selected IDE context into a prompt

1. Open only the Devobs files needed for the task in a supported IDE integration. Select a focused code or text range when possible.
2. In the Codex terminal UI, run `/ide` to include available IDE context in the next prompt.
3. Include only information needed for the request. Do not add credentials, customer data, private incident logs, or internal URLs to a public documentation MCP query.

`/ide` is a Codex UI command, not a package to install or a repository setting. It can include available IDE context in the next prompt; it does not establish that an IDE integration is connected in every client.

## Use Vim keybindings

- Run `/vim` in the Codex terminal UI to toggle Vim mode for the current session.
- To make Vim mode the default for new sessions, set `tui.vim_mode_default = true` in the operator's Codex `config.toml` under `~/.codex/` (or the equivalent Codex home on that operating system).
- This is a personal interface preference. Devobs does not set it in the repository's `.codex/config.toml`, so it will not change the experience for other contributors.

## Check the active Codex context

- `/status` shows the current model, approval settings, writable roots, and session state. Confirm these before editing or running commands.
- `/mcp` and `/mcp verbose`, or `codex mcp list` in a terminal, show configured MCP servers and available diagnostics. A listed server is registration evidence, not proof of a successful live request.
- `/debug-config` helps explain which configuration layer supplies an effective value. Review the result locally before sharing it.
- `codex debug prompt-input` shows the model-visible prompt inputs. Use it to diagnose whether `AGENTS.md` and project instructions were discovered; its output can include repository text, so do not publish it unredacted.
- `codex doctor` diagnoses the local installation and runtime. Sanitize its output before attaching it to an issue because it may reveal local configuration or authentication state.

For Devobs' public, read-only OpenAI developer-docs MCP, follow the [registration and runtime acceptance steps](CODEX_AGENT_OPERATING_MODEL.md#local-registration-smoke-check-manual-cost-free). Keep runtime status **UNVERIFIED** until a harmless public documentation lookup actually succeeds. For prompts involving encrypted MCP payloads, keep interactive approval enabled and follow the [MCP approval guidance](CODEX_MCP_APPROVAL_GUIDANCE.md).

## Bound scripted work

`codex exec` is intended for scripted or CI-style non-interactive work. Use it only for a bounded task whose inputs, writable paths, tools, and effects are understood. Follow the repository's feature-branch and human-approval rules. Do not use `--dangerously-bypass-approvals-and-sandbox`; repository instructions and CI configuration do not authorize deployments, paid inference, secret access, or other external changes.

For an interactive local session, the Codex command reference recommends `--sandbox workspace-write --ask-for-approval on-request`. Keep work on an isolated branch or worktree, inspect the diff, and run the relevant checks before opening a PR. This repository already has an `AGENTS.md`; use `/init` only when intentionally creating a new instruction-file scaffold, then review it before saving.

## References

- [Codex CLI developer commands](https://learn.chatgpt.com/docs/developer-commands.md?surface=cli)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference.md)
- [OpenAI agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security.md)
- [OpenAI developer-docs MCP](https://developers.openai.com/resources/docs-mcp)
- [Upstream Codex issue #20289](https://github.com/openai/codex/issues/20289)

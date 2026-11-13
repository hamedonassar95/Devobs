# Codex MCP approval prompts: reusable guidance

**Checked:** 2026-11-13. This note records upstream reports and safe handling for Devobs and other Codex-enabled repositories. It does not change local Codex permissions or authorize tool calls.

## Upstream reports

- OpenAI Codex [issue #20289](https://github.com/openai/codex/issues/20289) is open. It reports that a tool can still prompt for approval when the MCP server and tool are configured with `approval_mode = "approve"`; Codex showed `Encrypted assistant message and tool call in payload — unclear if allowed.` The report used a read-only local Unity console-log query on Windows.
- A Codex issue bot identified [#19430](https://github.com/openai/codex/issues/19430) as a possible duplicate. It is also open and reports repeated approval prompts for configured MCP tools, including prompts when payloads were described as encrypted.
- Automated duplicate suggestions are not maintainer confirmation. The bot comment on #19430 linked [#18133](https://github.com/openai/codex/issues/18133) (open) and [#18706](https://github.com/openai/codex/issues/18706) (closed as completed); those reports describe different Windows/MATLAB permission and approval-persistence behavior. Their status does not establish a resolution for #20289.
- These issue reports establish a reported Codex client behavior, not a confirmed defect in every MCP server, a universal workaround, or a fix. The #20289 and #19430 pages had no maintainer resolution when checked.

## Devobs applicability

The repository-scoped [`.codex/config.toml`](../.codex/config.toml) registers the public, read-only OpenAI developer-docs MCP. It does not set `approval_mode` or `approval_policy = "never"`. Devobs has not reproduced the reported approval behavior; its MCP runtime acceptance remains **OPEN** until a harmless public lookup succeeds in a trusted Codex client.

This is an upstream Codex approval-path concern. A Devobs code change cannot fix Codex's client behavior. Setting a broader approval policy would weaken the repository's human gates and would not guarantee that the client suppresses this prompt.

## Reusable handling for each repository

1. Keep Codex's interactive approval boundary enabled. Before approving a prompt, inspect the displayed server, tool and arguments against the task's approved scope; cancel calls that are unclear or exceed it.
2. For documentation MCP checks, send only a harmless, public documentation query. Do not include customer data, private incidents, internal URLs, credentials or logs.
3. Do not call an MCP endpoint directly with shell HTTP tools to bypass a Codex approval prompt. The reported shell workaround avoids the Codex wrapper and does not establish that the guarded call is safe.
4. If a prompt blocks an otherwise harmless call, record only sanitized Codex version, operating system, server/tool name and prompt reason. Do not store encrypted payloads, private transcripts or tokens in a repository.
5. Treat configuration and `codex mcp list` as registration evidence only. Keep runtime acceptance **UNVERIFIED** until an actual harmless call succeeds in a trusted Codex session.

This guidance is portable across project repositories. Apply it only where Codex MCP integrations exist; do not bulk-add approval settings or change unrelated repositories.

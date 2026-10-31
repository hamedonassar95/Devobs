# Devobs AI Intelligence — Codex capability acceptance map

**Audit snapshot:** 2026-10-31, canonical `hamedonassar95/Devobs`, base `f1bd3c5717d95a9ee89116c0fce49ef9fac572d7`. This snapshot does not claim to be live after later merges. **P01 NO-GO, AI-9 FAIL**. Related independent [PR #337](https://github.com/hamedonassar95/Devobs/pull/337) merged at this baseline; do not duplicate its changes.

[Machine-readable inventory](CODEX_CAPABILITY_INVENTORY.json) tracks 16 capability areas against current repository paths and official documentation. Run `python3 scripts/check_codex_capabilities.py` and `python3 -m unittest discover -s tests -p 'test_codex_capabilities.py' -v` on an actual checkout. Checks are **offline**: repository files, exact Codex configuration, trust of references, absent repo hooks, no unauthorized promotion, and the unchanged AI-9/P01 ledger gates. A green result **does not** establish active Codex sessions, agents, MCP tools or paid API access.

| Area | Repository proof | What is still missing |
|---|---|---|
| CLI / IDE and Codex Cloud | Not independently observed | Trusted runtime and repo connection acceptance |
| AGENTS.md / Skills | Source exists | Runtime discovery and correct actual use |
| Subagents | Four role TOMLs and two-agent configuration | Read-only two-role trial in supported Codex host |
| `/goal` | Documented operator guidance | Durable thread Goal exercised in eligible host |
| Worktrees | Reusable worktree Skill | Isolated concurrent-session demonstration |
| Docs MCP | Exact official URL and offline probe | Successful harmless **remote** documentation tool lookup |
| Hooks | Not enabled in reviewed repo config | Threat model and reviewed opt-in hook trust (not an infallible security boundary) |
| Codex Security | Existing traditional scans are **not** product proof | Eligibility and separately authorized Codex Security scan |
| SDK / App Server / Agents API | Future architecture documented | Sandbox, credentials, cost boundary and approved runtime test |
| Codex Automations / Remote mobile | Design references only | Eligible connected host, safe permissions and owner-approved scope |
| Record & Replay | No verified specific implementation | Official supported capability and safe demonstration, if available |

## Recommended sequence — do not run everything at once

1. **First, close documentation drift:** PR #337 is merged in the source baseline. Keep the durable milestone ledger authoritative for merged PRs only.
2. **Next, Codex runtime evidence:** from a *trusted, supported host*, run a read-only two-role review and one public Docs MCP lookup, recording tool names, success/failure, source URLs and redacted timing. Never include tokens, private prompts or full customer logs in this public repo.
3. **Then, acceptance-driven P01:** tackle offline T09 IaC reproducibility only after checking existing Terraform CI; T08 provider/region and an enforceable **all-in $100/month** budget remain a hard block to provisioning.
4. **Later, integration pilot:** choose only **one** of Codex SDK, App Server or Agents API after specifying execution sandbox, role separation, per-run budget, identity, approval, resource teardown and measured evaluation. No autonomous production actions.

## Source authority and controls

- [Codex Goals](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) are thread-scoped, **not** a global project ledger.
- [Codex Hooks](https://learn.chatgpt.com/docs/hooks) require trust review and cannot cover every tool path.
- [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform) distinguishes SDK, App Server and CLI.
- [Mobile Remote](https://developers.openai.com/blog/mastering-codex-remote-for-engineering) depends on a supported host/account and cannot be established by repository settings.
- [Agents API](https://developers.openai.com/api/docs/guides/agents) and [Skills](https://developers.openai.com/plugins/concepts/skills) need explicit authorization and sandboxing when used with live tools.

**Nonclaims:** no deployed SaaS, private tenant staging, billed inference, approved security certification, independent AI-9 quality, Codex Security workspace acceptance, or Codex automatic work schedule. Changes must go through feature branches, fresh CI and owner-approved merge.

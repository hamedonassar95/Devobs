# Devobs AI Intelligence — Codex agent operating model

**Scope:** Repository-scoped Codex collaboration. These configuration files are not evidence of live subagent execution, hosted SaaS readiness, or approved AI/API spending.

## What was configured
- `.codex/config.toml` enables the supported multi-agent surface when the project is trusted and caps open specialist threads at **2**.
- `.codex/agents/devobs_architecture.toml`: map dependencies and acceptance criteria.
- `.codex/agents/devobs_security.toml`: review authorization, supply chain and workflow risk.
- `.codex/agents/devobs_qa.toml`: recommend and run safe local tests, report fresh evidence.
- `.codex/agents/devobs_operations.toml`: read-only CI/incident investigation.
- `.agents/skills/devobs-codex-operating-cycle/SKILL.md`: a reusable workflow for the parent agent.

The main Codex thread acts as **orchestrator**, decides when to delegate, owns changes and asks the operator for decisions. The above roles are task-scoped instructions; they are not background workers, external integrations or a security boundary.

## Safe operating procedure
1. Trust and open the repository in a supported Codex runtime; verify which custom agents were discovered. On an unsupported surface, use the roles sequentially.
2. Read `AGENTS.md`, `STATE.md`, recent relevant GitHub runs and `docs/DEVOBS_READINESS_CURRENT.md`. Distinguish stored records from live verification.
3. State one bounded objective, affected paths, acceptance tests and explicit stop/approval conditions. Use Plan mode when scope is unclear.
4. Before modifying code, delegate only the needed read-only specialist tasks; do not spend additional agent calls simply to simulate a team.
5. Use an isolated feature branch or worktree for authorized changes. Run behavior tests, security scans and CI; report the exact revision and evidence.
6. Open a draft PR only when authorized. Require a separate human decision before merge, deployment, destructive actions or any new cost.

## Suggested Codex Goal (supported runtimes only)

```text
/goal Improve Devobs CI reliability on a feature branch without weakening security or changing production. Inspect failing workflows and exact GitHub run/SHA evidence, reproduce one failure, implement the minimal verified fix, run regression tests and produce a draft PR only if authorized. Never merge, deploy, create a paid service, change secrets or bypass approval. If blocked, stop with evidence and a precise owner decision request.
```

Goals are bound to a Codex thread and require a compatible build; adding this document does not activate a Goal.

## Proof gates

| Gate | Required evidence | Stop condition |
| --- | --- | --- |
| Architecture | Existing code and dependency map | Unresolved external impact |
| Security | SHA-pinned actions, narrow permissions, secret scan, trust review | Credible high-risk finding |
| Quality | Relevant tests with fresh exit codes | Failed or absent required tests |
| CI | Required `validate` and appropriate hosted checks on exact head SHA | Failed, skipped-required or pending checks |
| Release | Owner decision tied to reviewed SHA and scope | Missing approval |
| SaaS | Tenant isolation, identity, staged operations, budget and privacy decisions | P01 remains NO-GO |

Existing CI/image scanning and approval mechanisms must be reused, not cloned. `AGENTS.md` and role instructions guide behavior but **cannot replace** GitHub rulesets, execution isolation, least-privilege credentials and human review.

## Deferred capabilities

- **Hooks:** do not enable script hooks as an unreviewed security control; design/test an explicit threat model and install/trust only in a supported runtime.
- **Codex SDK / app-server / Agents API:** evaluate in a separate PR after local workflow metrics and an explicit owner decision on recurring cost and runtime boundaries.
- **Record & Replay / remote computer use:** optional and device/plan dependent; no setup or recording occurs here.
- **Autonomous scheduling:** out of scope until the owner approves a specific schedule, permissions and budget.

## References
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)
- [Existing project status](../STATE.md)
- [Current production readiness](DEVOBS_READINESS_CURRENT.md)

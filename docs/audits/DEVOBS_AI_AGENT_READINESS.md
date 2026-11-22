# Devobs — AI & multi-agent readiness audit

Audited SHA: `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` (VERIFIED). Evidence: local files, git metadata, fresh commands. All gates advisory; no runtime or live inference claimed.

## AI Intelligence capability status

| Capability | Implementation (evidence) | Tests | Status | Gap | Priority |
| --- | --- | --- | --- | --- | --- |
| Provider adapters (OpenAI, Gemini, local) | `scripts/devobs_intelligence/openai_error_diagnosis.py:1-20,26-34,60-82,145-160`; `gemini_error_diagnosis.py:1-30,67-100`; `local_model_error_diagnosis.py:1-28,63-90` — redaction, no-redirect, `store=False`, strict result schema, bounded bytes/tokens, loopback-only local endpoints | 3 provider test modules; prior batch 49 tests OK | VERIFIED_COMPLETE (offline) | Live model ID validity (`gpt-6-luna`) UNVERIFIED without network | P1 |
| Provider evaluation harness | `devobs/ai_evaluation/` exists ONLY on unmerged branch `feature/ai-provider-evaluation-finalization` @ `7dff0c0`; NOT on audited main | 16 tests on that branch | NOT ON MAIN | Do not claim as available on main; merge decision is owner's | P1 (decision) |
| Model selection / routing / kill switch | `scripts/devobs_intelligence/adviser.py:34-71` (max_model_calls == 1, `model_enabled`, `kill_switch`, category allowlist); `policy.py:1` ("No model can grant capabilities"); `api_app.py:260-279` | adviser/policy tests | VERIFIED_COMPLETE (deterministic) | No provider failover by design; document | P2 |
| Token and cost accounting | `MAX_OUTPUT_TOKENS=512`; API `latency_ms` (`api_app.py:279`); `agent-spec.yaml:4-10` (`budget_approval_is_dollar_cap=false`, `estimated_cost_usd_per_run: null`, `cost_status: unverified`) | `check_agent_spec.py` fresh PASS | PARTIAL | No token usage capture, no per-run USD ledger, no enforced dollar cap | P0 |
| Prompt-injection defenses | System prompts treat all log characters as untrusted; strict JSON schema `validate_diagnosis_result` (`openai…py:116-135`); category allowlist; `rules.py:22-30` known-signal mapping | provider + incident tests | PARTIAL | No adversarial injection corpus for these adapters; semantic residual risk | P1 |
| AI pull request review | `.github/workflows/ai-code-review.yml`, `pr-agent.yml`, `claude-code-assistant.yml`, gh-aw sources (`*.lock.yml`/`.md`); `agent-spec.yaml` gates direct providers on budget approval | `check_agent_spec.py` PASS; CI | PARTIAL | Inference results not evidenced at audited SHA; provider quota constraints historically noted | P1 |
| CI failure investigation | `scripts/ci_failure_intelligence.py`, evidence-gated breaker `.github/workflows/ai-provider-circuit-breaker.yml` | CI + tests | VERIFIED_COMPLETE (offline) | Live dispatch after merge UNVERIFIED | P2 |
| Log / incident summarization | `devobs/incident_intelligence/analyzer.py:1-9` deterministic, `DisabledAIProvider` no-op `:41-45`; `devobs/incidents/*` | `tests/incidents/` | VERIFIED_COMPLETE (offline) | No live consumption proof | P2 |
| Anomaly detection readiness | AI-9 synthetic metrics work on unmerged branches; on main: `docs/ai9/evidence.json` 7/7 UNVERIFIED, decision BLOCKED | `tests/test_ai9_evidence.py` | BLOCKED | Independent natural-incident corpus, detector GO, 7 signed controls | P0 |
| AI-generated runbooks | `devobs/ai_quality_gate/adapter.py` advisory notes; no execution authority | `tests/ai_quality_gate/` | PARTIAL (advisory) | No end-to-end verified runbook from live incident | P2 |
| Human approval enforcement | `scripts/human_approval_gate.py`: VERIFIED status + open unmerged PR + human + write + explicit APPROVE; final `PENDING HUMAN APPROVAL` | `tests/test_human_approval_gate.py` | VERIFIED_COMPLETE (source) | No console approval queue UI | P1 |
| AI-9 acceptance criteria | `scripts/check_ai9_evidence.py` 7 required controls, BLOCKED locked, auto-GO forbidden, SHA/reviewer/HTTPS/30-day freshness checks; `docs/ai9/evidence.json` 7/7 UNVERIFIED | `test_ai9_evidence.py` (20 OK in prior batch), AI9 Node tests | BLOCKED | All 7 controls need exact-SHA independent evidence | P0 |
| AI quality gate | `devobs/ai_quality_gate/models.py:71-105` schema forbids `merge_authorized=true`, forces `PENDING_HUMAN`, `offline=true`; `engine.py` audit events | fresh `unittest` 23 tests OK | VERIFIED_COMPLETE (offline) | Advisory only by design; never wire to auto-merge | P2 |

## Multi-agent operations capability status

| Capability | Implementation (evidence) | Tests | Status | Gap | Priority |
| --- | --- | --- | --- | --- | --- |
| Codex config & roles | `.codex/config.toml`, `.codex/agents/*.toml` (architecture, security, QA, operations), `.agents/skills/*` | `scripts/check_codex_capabilities.py`, `check_codex_docs_mcp.py` | PARTIAL (config) | Config is not runtime proof; `codex mcp list` and public docs lookup UNVERIFIED at this SHA | P0 |
| OpenCode integration | `docs/AI_MULTI_AGENT_WORKFLOW.md:9-25` defines Agent B role; isolated worktrees used in this audit | none (policy doc) | DOCUMENTED | No separate runtime evidence | P1 |
| MCP integration | AGENTS.md `openaiDeveloperDocs` guidance; `scripts/check_codex_docs_mcp.py` offline checks | offline checks | UNVERIFIED (runtime) | Trusted client unavailable; no harmless public lookup performed | P0 |
| Task contracts & dependency validation | `scripts/check_two_agent_tasks.py` unique IDs, ownership conflicts, dependency cycles, restricted actions; AUD-02 High fixed in `37475b0` (#732, VERIFIED ancestor of main) | 26 tests OK (prior fresh batch) | VERIFIED_COMPLETE (offline) | Remaining Medium audit findings UNVERIFIED at 10f8dd9 | P1 |
| File ownership / isolated worktrees | `docs/AI_MULTI_AGENT_WORKFLOW.md:19-21`, this audit's isolated branch/worktree | process evidence | VERIFIED (this session) | — | P2 |
| Resource-constrained scheduling | `docs/CODEX_AGENT_OPERATING_MODEL.md:104` autonomous scheduling explicitly deferred | none | PARTIAL (documented) | No scheduler runtime | P2 |
| DRY_RUN dispatch | `scripts/agent_dispatch_preflight.py:1-9,37-55,61-96` detects CLIs via `shutil.which` without invoking; writes instruction files | `tests/test_agent_dispatch_preflight.py` | VERIFIED_COMPLETE | PASS ≠ agent runtime acceptance (gate OPEN) | P0 |
| Agent execution evidence | `devobs/ai_quality_gate` audit events, `docs/agents/TWO_AGENT_COORDINATION.md` | `tests/ai_quality_gate/` 23 OK | PARTIAL | Self-asserted evidence risk (AUD-01/03/04/05/12 Medium, historical) | P1 |
| Agent permissions | `check_two_agent_tasks.py` `RESTRICTED_ACTIONS`, `APPROVAL_VALUE="pending_human"`; agent-spec gates | tests + `check_agent_spec.py` | VERIFIED_COMPLETE (policy) | GitHub rulesets external | P1 |
| Audit trails | `scripts/devobs_intelligence/audit_store.py` local hash chain; hardening `control_events.py` bounded events | tests | PARTIAL | No hosted tamper-resistant trail | P2 |
| Failure recovery / human-supervised execution | `docs/CODEX_AGENT_OPERATING_MODEL.md:73-88` proof gates; `docs/AI_MULTI_AGENT_WORKFLOW.md:13-25` no merge/deploy/spend without approval | policy + tests | VERIFIED_COMPLETE (policy) | Live recovery drill UNVERIFIED | P1 |

## Gate statements (fresh evidence)

- `python scripts/milestone_ledger.py --summary` → `ai9-detection-quality: BLOCKED`, `codex-agent-runtime-acceptance: OPEN`, `p01-managed-saas: BLOCKED`.
- `python scripts/check_agent_spec.py` → `Validated 7 agent specs, retry/production policy, direct-provider gates, Vertex failover, and all 5 gh-aw source/lock budget gates.` exit 0.
- `python -m unittest discover -s tests/ai_quality_gate -p "test_*.py"` → `Ran 23 tests`, `OK`, exit 0.
- `git merge-base --is-ancestor 37475b0 origin/main` → `ancestor_of_main=0` (AUD-02 fix present).

No live provider call, agent start, paid inference, MCP handshake or deployment occurred. The AI quality gate's advisory note cannot influence its decision and grants no authority (`devobs/ai_quality_gate/adapter.py`, `docs/ai-quality-gate.md`).

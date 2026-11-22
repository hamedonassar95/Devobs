# Devobs — Full platform gap audit (evidence-based, advisory)

**Audited source SHA:** `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` (`origin/main`, VERIFIED via `git rev-parse origin/main` after `git fetch origin`). Branch: `feature/devobs-production-gap-audit`, isolated worktree. Audit date 2026-11-22.

**Nature of evidence:** local files, git metadata and commands executed in this session. Historical CI runs, provider observations and owner decisions are cited from documents authored against earlier fixed SHAs and are labeled VERIFIED-as-document-content, NOT runtime proof. Per `AGENTS.md`, a repository configuration file, ledger entry or green CI job is never proof of a running service, an operating agent or production readiness. No network/provider/cloud/deploy command was run; no secret, token, `.env` value or credential was read. No open PRs existed at query time (`GET /repos/hamedonassar95/Devobs/pulls?state=open` → `OPEN_PR_COUNT=0`, unauthenticated read-only API).

**Gate baseline (VERIFIED, fresh command):** `python scripts/milestone_ledger.py --summary` →
`{"gate_statuses":{"ai9-detection-quality":"BLOCKED","codex-agent-runtime-acceptance":"OPEN","p01-managed-saas":"BLOCKED"},"latest_pr":717,"merged_milestones":304,"open_gates":3}`.
The ledger is an offline index; the latest merged PR recorded there (717) predates documented merges #741/#744 — a pre-existing staleness, not a gate change.

## Executive summary

Devobs has substantial **offline, advisory, fail-closed source controls** and a mature CI security posture (full-SHA action pinning, least-privilege workflows, hash-locked Python, Bandit, pip-audit, Gitleaks coverage verification, Trivy with cosign/checksum verification, SBOM, Zizmor/Scorecard informational reports). It has **no verified production runtime**: P01 is owner-signed NO-GO with all 8 acceptance controls BLOCKED, AI-9 is BLOCKED with all 7 controls UNVERIFIED, and Codex runtime acceptance is OPEN. Platform capabilities that are wrongly treated as "done" include billing/metering (missing), tenant lifecycle/retention (missing), an English LTR interface (missing), an approval-queue UI (missing), enforced dollar-cost caps (docs only), token/USD accounting (no usage capture), SLO/error budgets (docs only), and live OIDC/RLS/restore acceptance (source/disposable-CI evidence only).

A dated, concrete deadline exists: the Render Free PostgreSQL `devobs-ai-staging-db` reports expiry `2026-12-05T10:33:24.202776Z`; the offline guard freshly returned `REVIEW_REQUIRED` / exit 1. Planning authorization does **not** authorize deletion or any provider action.

**No claim in this audit promotes a gate, authorizes a merge/deploy/spend, or asserts production readiness.**

## Verified existing capabilities (selected, with evidence)

| Capability | Evidence (SHA 10f8dd9 unless noted) | Status |
| --- | --- | --- |
| Full-SHA action pinning gate | `scripts/check_action_pins.py`; fresh run: `Action pin check passed for 48 workflow and template files.` exit 0 | VERIFIED_COMPLETE (offline) |
| Agent-spec / direct-provider / budget-flag gates | `scripts/check_agent_spec.py`; fresh run: `Validated 7 agent specs, retry/production policy, direct-provider gates, Vertex failover, and all 5 gh-aw source/lock budget gates.` exit 0 | VERIFIED_COMPLETE (offline) |
| AI quality gate (`DRY_RUN`, `merge_authorized=false` schema-enforced) | `devobs/ai_quality_gate/models.py`; fresh `unittest` 23 tests OK | VERIFIED_COMPLETE (offline) |
| Human approval gate | `scripts/human_approval_gate.py`; requires VERIFIED evidence + human + write + explicit APPROVE | VERIFIED_COMPLETE (source) |
| Provider adapters (OpenAI/Gemini/local) | `scripts/devobs_intelligence/*_error_diagnosis.py`: redaction, no-redirect, strict schema, bounded bytes/tokens; offline provider test suites | VERIFIED_COMPLETE (offline) |
| Offline provider evaluation harness | `devobs/ai_evaluation/` exists only on unmerged branch `feature/ai-provider-evaluation-finalization` (`7dff0c0`), NOT on audited main | NOT ON MAIN — do not claim as available |
| PostgreSQL RLS (source + disposable CI) | `deploy/postgres/001_tenant_rls.sql`, `tests/test_postgres_rls_integration.py` | PARTIAL (hosted UNVERIFIED) |
| OIDC verifier (source) | `scripts/devobs_intelligence/oidc_tokens.py`, RS256/JWKS/audience/expiry checks; live IdP UNVERIFIED, prior staging `invalid_staging_config stage=oidc` | PARTIAL |
| Local observability stack | `monitoring/*` loopback-only, digest-pinned images; README states no application `/metrics` and no external receiver | VERIFIED_COMPLETE (local only) |
| Console Arabic RTL + demo labeling | `apps/ai-intelligence-console/index.html:2`, `src/App.tsx:448`; `DEMO ONLY` banner; preview-only controls | VERIFIED_COMPLETE (RTL) |
| Two-agent task contract | `scripts/check_two_agent_tasks.py`; AUD-02 High fixed in `37475b0` (#732, ancestor of main, VERIFIED) | VERIFIED_COMPLETE (offline) |
| Ledger/milestone tests | fresh `python -m unittest tests.test_milestone_ledger -q` → `Ran 86 tests`, `OK` | VERIFIED |

## Missing and partially implemented features (cross-domain summary)

Full per-capability tables with file:line evidence are in the four domain reports:
- [Security gap matrix](DEVOBS_SECURITY_GAP_MATRIX.md) — B/F/H/K
- [AI & agent readiness](DEVOBS_AI_AGENT_READINESS.md) — D/E
- [SaaS readiness](DEVOBS_SAAS_READINESS.md) — B, UX/ops
- [Integration matrix](DEVOBS_INTEGRATION_MATRIX.md) — J and external states
- Platform/CI/observability/UX details are consolidated in the [priority roadmap](../roadmap/DEVOBS_PRIORITY_REMEDIATION.md).

Highest-signal gaps:

1. **Billing/metering/quotas — MISSING.** `docs/PRODUCT_SAAS_READINESS.md:12-33`: "Stripe billing and metering not configured", plans DRAFT, "No billing system exists". No processor, webhook validation, quota enforcement, reconciliation or refund flow.
2. **Tenant lifecycle / retention / deletion — MISSING.** Target only in `docs/PRODUCT_SAAS_READINESS.md:16-23,35-41`; `docs/ENTERPRISE_OPERATIONS.md:68` requires tested policy before customer signup.
3. **Token/cost accounting — PARTIAL.** Only `MAX_OUTPUT_TOKENS=512` and API `latency_ms`; `agent-spec.yaml:4-10` has boolean budget flag, `estimated_cost_usd_per_run: null`, `cost_status: unverified`. `docs/P01_RENDER_BUDGET_ENVELOPE.md:3-21` targets are explicitly "not provider limits... not a guarantee". Fresh P01 docs confirm no enforced combined USD 100 cap.
4. **English LTR toggle — MISSING** (`apps/.../index.html:2` is hard-coded `lang="ar" dir="rtl"`; no `dir="ltr"`/i18n implementation found).
5. **Approval queue UI — MISSING.** Only a constant `requires_human_approval: true` in `LocalAi7Panel.tsx:12`; backend gate exists but no read-only view.
6. **Runtime SLO/error budgets — MISSING in implementation** (planning docs only; no `monitoring/*` rules for error-rate/latency SLOs).
7. **CodeQL authored config — PARTIAL.** No repo-authored CodeQL workflow; GitHub default setup status at this SHA UNVERIFIED. Prior audit records historical SUCCESS at `2d385b2`.
8. **Live OIDC/RLS/restore/provider acceptance — BLOCKED/UNVERIFIED.** All P01 controls BLOCKED; AI-9 7/7 UNVERIFIED; WIF preflight historically failed then partially passed before inference (docs/VERTEX_AI_FALLBACK.md:206-261).

## Stale, redundant or conflicting components (identified, NOT deleted)

- `docs/MILESTONE_LEDGER.json` `latest_pr: 717` vs documented merges #741/#744 — stale index; do not treat as live evidence.
- `docs/audits/TWO_AGENT_SECURITY_AUDIT_2026-11-21.md` records AUD-02 High as open at SHA `2d385b2`; **fixed at audited SHA** by `37475b0` (#732). Historical document, not a current finding.
- `scripts/integrations/graphify_portfolio.py` is explicitly legacy vs canonical `tools/graphify` (README tail); documented, not removed.
- `.github/workflows/*.lock.yml`/`.md` gh-aw sources vs generated workflows; agent-spec gates cover both but 10 `uses:` lacking version comments were noted in `docs/audits/DEVOBS_RECOVERY_AUDIT.md:67`.
- Multiple rollback runbooks (`docs/RELEASE_ROLLBACK.md`, `docs/ROLLBACK_RUNBOOK.md`, `docs/runbooks/*`) overlap in scope; consolidation candidate, not a defect.

## Priority classification (advisory; details in roadmap)

- **P0:** P01 NO-GO, cost enforcement (USD 0 activation / no enforced cap), backup+restore/DR, Render Free DB expiry owner decision, AI-9 gate, commercial-readiness BLOCKED, DRY_RUN dispatch not runtime acceptance, Codex runtime gate, SLO/error budgets.
- **P1:** hosted OIDC/RLS negative tests, Render `0.0.0.0/0` allowlist, V-01 review-count policy, wheel-hash runtime verification, WIF preflight completion, hosted rollback, token/cost capture, prompt-injection adversarial tests, approval-state visibility, English LTR decision, CI artifact trace, Dependabot alert human triage.
- **P2:** billing/metering design, tenant lifecycle/retention, audit anchoring, a11y tests, per-panel synthetic/live badges, K8s/Terraform apply design, OWASP abuse-case tests, zizmor/Scorecard review.
- **P3:** optional UX polish, Graphify/Plannotator optional integrations, future Pulumi/Azure work.

## Free vs paid dependencies

Free/known: GitHub Actions (with documented account compute constraints), Render **Free** web+Postgres (expiring, no managed backup), Vercel preview checks, Supabase project **INACTIVE**, static GitHub Pages, local Docker monitoring stack, public CodeQL/Trivy/Gitleaks/Zizmor/Scorecard tooling. Paid/blocked: OpenAI/Gemini inference (budget approval false, `DEVOBS_AI_BUDGET_APPROVED: "false"` in `render.yaml:19-24`), Stripe billing (not configured), GCP inference/WIF (preflight not fully successful), GitLab Premium mirroring (not configured), any backup product. All paid activation remains **BLOCKED** pending explicit owner approval.

## Verification evidence (fresh, this session)

| Command | Final output | Exit |
| --- | --- | ---: |
| `python scripts/milestone_ledger.py --summary` | gate statuses BLOCKED/OPEN/BLOCKED; 304 milestones | 0 |
| `python scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` | 0 |
| `python scripts/check_agent_spec.py` | `Validated 7 agent specs, ... all 5 gh-aw source/lock budget gates.` | 0 |
| `python -m unittest tests.test_milestone_ledger -q` | `Ran 86 tests in 2.310s` / `OK` | 0 |
| `python -m unittest discover -s tests/ai_quality_gate -p "test_*.py"` | `Ran 23 tests in 0.216s` / `OK` | 0 |
| `python scripts/check_render_free_expiry.py --json` | `{"status":"REVIEW_REQUIRED","expires_at":"2026-12-05T10:33:24.202776Z","paid_activation_authorized":false,...}` | 1 (expected fail-closed) |
| `git merge-base --is-ancestor 37475b0 origin/main` | `ancestor_of_main=0` (AUD-02 fix on main) | 0 |
| unauthenticated `GET /repos/.../pulls?state=open` | `OPEN_PR_COUNT=0` | 0 |

Could not run (reported, not passed): GitHub ruleset/GitLab/Render/GCP/Vercel live APIs, `gcloud`, Terraform plan/apply, container/Keycloak runtime, provider inference, `npm ci`/build (no `node_modules` locally), PostgreSQL RLS integration (needs local PG), Codex MCP probe (trusted client unavailable), secret-bearing OTel mount inspection (prohibited), full `tests/` discovery (known Windows-host failures in historical docs; not re-run).

## Rollback / non-action

This audit changed documentation only. Rollback = revert the audit commits on the feature branch; no production state, main branch, provider, CI gate or resource was altered. **Devobs is not production-ready** until all P01/AI-9/Codex acceptance gates pass with independently verifiable evidence and owner approval.

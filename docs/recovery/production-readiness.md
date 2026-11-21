# Production-readiness assessment — repository recovery hardening

**Reviewed revision (VERIFIED):** this branch is based on `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f`; hosted `main` matched that SHA at capture.
**Assessment time (VERIFIED):** 2026-11-21, ~14:20–14:45 UTC.
**Decision:** **NO-GO for production/SaaS release.** **CONDITIONAL-GO for a Draft PR review only**, after the eight validator fixes in this branch are reviewed and the dependency work below lands.

This is an evidence-based assessment, not an approval. No merge, deployment, ruleset change, provider activation, cost approval or live data access was performed.

## 1. Gate summary

| Gate / criterion | State | Evidence | Required owner action |
|---|---|---|---|
| P01 managed SaaS | **BLOCKED / NO-GO** | Ledger summary: `"p01-managed-saas": "BLOCKED"`; `docs/p01/P01_NO_GO_DECISION_2026-11-19.md` lists eight blocked controls; `docs/PRODUCT_SAAS_READINESS.md` states not sellable/no billing/no live tenant acceptance. VERIFIED. | Separate owner decision tied to an exact SHA and scope; no hosted configuration change by this agent. |
| AI-9 detection quality | **BLOCKED** | Ledger summary: `"ai9-detection-quality": "BLOCKED"`. Fresh `tests.test_incident_evals` → 1 error (`WinError 1314`), exit `1`. VERIFIED. | Approve a measured quality baseline and rerun on a capable host. |
| Codex runtime acceptance | **OPEN** | Ledger summary: `"codex-agent-runtime-acceptance": "OPEN"`; `docs/CODEX_AGENT_OPERATING_MODEL.md:36` requires an actual connected-client lookup; configuration is not runtime proof. VERIFIED. | Owner performs `codex mcp list` plus one harmless public lookup in a trusted client. |
| Phase 8 human approval | **PENDING HUMAN** | `docs/CODEX_AGENT_OPERATING_MODEL.md` and root `AGENTS.md` forbid agent self-approval. VERIFIED. | Explicit owner approval of the reviewed SHA and scope. |
| Full Python suite | **FAIL at base** | `Ran 1396 tests in 382.177s`, `FAILED (failures=47, errors=123, skipped=44)`, exit `1`. VERIFIED. | Land REC-B01 (`feature/windows-test-reliability` at `ace94c2f…`), then rerun the whole suite on the combined SHA. |
| Validator hardening (this change) | **PASS for its own scope** | `Ran 32 tests in 0.975s`, `OK`, exit `0`; compileall/action-pins/diff-check exit `0`. VERIFIED. | Code review; no claim about the full suite is made. |
| Hosted CI / CodeQL on exact head | **UNVERIFIED** | Public REST `core.remaining=0` at `14:23:22Z` (reset `15:05:02Z`); full check logs need sign-in. Earlier runs #739/#740 succeeded; owner's Draft PR #741 CI run `44913420874` FAILED. VERIFIED for those observations only. | Push the reviewed branch, wait for hosted checks, then confirm required checks on the exact head SHA. |
| Branch protection / rulesets | **UNVERIFIED** | Unauthenticated snapshot showed `protection.enabled=false`, `required_status_checks.enforcement_level="off"`, no contexts/checks; ruleset state needs auth. VERIFIED as a snapshot, not as current truth. | Owner verifies rulesets in an authenticated session. |
| Static/security scans | **PARTIAL** | Action pins PASS (48 files), YAML parse PASS (43 files), Bandit/Gitleaks/Trivy/actionlint/Semgrep CLI absent locally → SKIPPED. VERIFIED. | Rely on hosted CI results for the exact SHA; do not mark skipped tools PASS. |
| Keycloak / OIDC / JWKS / PKCE / RLS runtime | **BLOCKED** | AGENTS.md exception not active until the reconciliation PR merges; no per-run approval; no production access authorized. VERIFIED. | Owner decision with exact 40-char SHA, unique Compose project and test scope, after the activation condition is met. |
| Backup restore / alert delivery / provider billing | **UNVERIFIED** | No live test performed by design. VERIFIED. | Owner-approved staged evidence. |

## 2. What this change actually accomplishes

- Adds recovery documentation with VERIFIED/UNVERIFIED/ASSUMED labels and an explicit SKIPPED/BLOCKED inventory.
- Fixes six concrete validator input-validation defects (AUD-03/04/05/06/07/13/14) with behavioural regression tests; documents the two that cannot be trusted offline (AUD-01/AUD-12).
- Does **not** touch the Windows-reliability ownership, governance records, CI security gates, live services, P01/AI-9/Codex gates, skill trees or lockfiles. Those are enumerated in [`defect-register.md`](defect-register.md).

## 3. Blockers and exact owner decisions

1. **Windows test failures (P1).** Landing `feature/windows-test-reliability` (`ace94c2f…`) is required before the full suite can be green. Decision: review/merge that branch on its own merits, then rerun on the combined SHA. Until then the base suite stays FAIL.
2. **Stale lifecycle records (P2).** `docs/MILESTONE_LEDGER.json` (PR #717/304 milestones), `STATE.md` and `docs/DEVOBS_READINESS_CURRENT.md` trail PR #739. Decision: assign the reconciliation to the branch that already owns those files; do not edit them here.
3. **AUD-01 / AUD-12 (P1/P2).** Decision: approve an evidence contract binding `complete` to operator-supplied trusted CI/SHA proof plus human sign-off, and decide whether `previous_status` must be compared to a prior trusted manifest.
4. **Hosted verification.** Decision: authenticate GitHub tooling (or wait for REST reset), push the reviewed branch, and require green required checks and CodeQL on the exact head. PR #741's failure belongs to a different branch and must not be conflated.
5. **P01/AI-9/Codex gates.** Decision: separate, explicit approvals with evidence; none is implied by this work.
6. **Optional integration choices.** Graphify wheel hash pin, stale `bun.lock`, workflow template version comments, duplicated skill trees and the recovery-audit citation need owner decisions (REC-C04–C08).

## 4. Path to GO (all items required)

1. Land REC-B01 and rerun `python -m unittest discover -s tests -q` on the combined SHA; require zero failures/errors.
2. Reconcile governance records with exact SHAs and CI run IDs while preserving gate states.
3. Rerun validator suite, compileall, action pins, YAML parse and `git diff --check` on the final head.
4. Push the reviewed branch and obtain hosted CI + CodeQL success on that exact SHA; verify branch protection/rulesets in an authenticated session.
5. Obtain separate owner decisions for P01, AI-9, Codex runtime and Phase 8.
6. Only then consider a release decision tied to the reviewed SHA. **This document does not grant it.**

## 5. Rollback and safety

- This branch changed only `scripts/check_two_agent_tasks.py`, `tests/test_two_agent_tasks.py` and `docs/recovery/*.md`; `git diff --numstat` reports 68/12 and 58/0 for the two source/test files, and the four recovery documents are additional.
- Rollback is a local revert or reset of this unpublished branch to `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f`. No migration, secret, hosted state, ruleset, deployment or billing resource was created.
- Any future merge or deployment requires a separate reviewed SHA and explicit owner approval; CI passing does not authorize either.

## 6. Related evidence

- [`defect-register.md`](defect-register.md) — prioritized defects and ownership boundaries.
- [`verification-matrix.md`](verification-matrix.md) — exact commands, final output lines and SKIPPED/BLOCKED inventory.
- [`integration-assessment.md`](integration-assessment.md) — retained, candidate and rejected integrations.

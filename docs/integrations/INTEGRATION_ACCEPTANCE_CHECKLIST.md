# Devobs integration acceptance checklist

**Status:** DRAFT / REVIEW ONLY  
**Evidence snapshot:** 2026-11-15 (Asia/Amman)  
**Repository:** [hamedonassar95/Devobs](https://github.com/hamedonassar95/Devobs)  
**Baseline `main`:** `e0a55239ce8a8846a8235a5cc72587c9953b9b7d`

This is a reusable, **manual evidence checklist**, not an executable release gate, live integration, deployment approval, or replacement for `AGENTS.md`. It records decisions to make before accepting future open-source integrations. Recheck every status against current GitHub evidence at review time.

## Evidence baseline (2026-11-15)

- **VERIFIED:** `main` resolved to the baseline SHA above and the [exact-SHA main CI run 43735505166](https://github.com/hamedonassar95/Devobs/actions/runs/43735505166) completed successfully. That run tested repository code and published/verified the static site; it did **not** prove hosted API/SaaS readiness.
- **VERIFIED:** [PR #634](https://github.com/hamedonassar95/Devobs/pull/634) merged the *offline, synthetic* OTLP JSON `error_rate_pct` adapter. Existing local bridges include [CloudEvents CI](CLOUDEVENTS_CI_BRIDGE.md) and [Alertmanager exports](ALERTMANAGER_BRIDGE.md).
- **VERIFIED:** [PR #632](https://github.com/hamedonassar95/Devobs/pull/632) remained open at head `4691b3c6aff9d1e1d92907e6f8a849ac023f054e`; GitHub reported `mergeable_state: dirty`. No repair or merge was performed as part of this document.
- **VERIFIED:** The active [Protect main ruleset](https://github.com/hamedonassar95/Devobs/rules/24507159) requires `validate` and `CodeQL`; its required approving review count was zero at inspection. **Repository policy is stricter:** root [AGENTS.md](../../AGENTS.md) requires explicit owner approval for the reviewed full SHA and scope before merging or deploying.
- **VERIFIED:** [Milestone ledger](../MILESTONE_LEDGER.json) had 236 recorded items, latest PR #629, so it did not yet reflect merged PRs #631 and #634. This is an evidence-maintenance task, not proof that those merges failed.
- **BLOCKED:** P01 hosted staging remains `NO-GO`, and AI-9 real-world release remains `BLOCKED`; see [readiness](../DEVOBS_READINESS_CURRENT.md) and [AI-9 independent evaluation](../AI9_V3_INDEPENDENT_EVAL_GATE.md).
- **UNVERIFIED:** Live source authenticity, hosted identity/PKCE, end-to-end TLS and tenant isolation, recovery, enforceable combined billing cap, and independent labeled natural-incident evaluation.

## Acceptance checklist for each proposed integration

The reviewer must record **PASS / FAIL / NOT_RUN / BLOCKED** for every required item. A skipped check is not a pass.

### 1. Identity, scope and reuse

- [ ] Specify the repository, exact base SHA, exact candidate head SHA, PR URL, owner, and objective.
- [ ] Inspect current source, existing adapters, milestone ledger and README; explain why an existing CloudEvents, OTLP, Alertmanager, MCP, monitoring or CI capability cannot meet the goal without duplication.
- [ ] Identify the exact changed files, supported event/data schema, source repositories, output destinations and permitted operations.
- [ ] Identify software versions, immutable action/image pins and upstream license; document commercial-use constraints where relevant.
- [ ] Distinguish **source-only**, **offline synthetic**, **local runtime**, **authenticated staging**, and **production verified**. Never infer higher readiness from a lower-level test.

### 2. Trust, privacy and least privilege

- [ ] Define an explicit source allowlist, bounded payload/field limits, and deterministic fail-closed behavior.
- [ ] Reject malformed input, unexpected fields, duplicate JSON keys (including nested keys), oversized data, duplicate/replayed events and inconsistent status/commit claims when applicable.
- [ ] Treat self-reported `source`, `id`, GitHub URLs and commit SHAs as **claims**, not authenticated provenance. Define independent authentication/attestation before any live sender.
- [ ] Prove no credentials, customer details, private build logs, unredacted model prompts or secret-like values appear in artifacts, output, logs or dashboard responses.
- [ ] Verify read-only defaults, narrow GitHub Actions permissions, no unintended `repository_dispatch`, write APIs, webhook/listener, deploy, rollback, paid model invocation or external service.
- [ ] Record retention, consent, tenant/project boundary, and safe rollback/deactivation; mark live integration **BLOCKED** when these are unknown.

### 3. Behavioral and CI evidence

- [ ] Show a focused **negative behavioral test** failing before the fix and passing afterward, where applicable; retain its exact command, final output lines and reviewed SHA.
- [ ] Test valid, invalid, oversized, spoofed, duplicate/replay and partial-batch inputs; verify **no partial success output** after rejection.
- [ ] Confirm compatibility with existing AI-1 normalization and any affected AI-7 read-only boundary, without silently expanding schema or dashboards.
- [ ] Run relevant local syntax, lint, tests, security and contract checks; record any unavailable commands as `NOT_RUN` rather than claiming success.
- [ ] Require exact-head GitHub `validate` and CodeQL results; review any failing or skipped job, plus changed permissions/actions/dependencies. Recheck if the head SHA changes.
- [ ] Inspect final diff for unrelated files, unexpected new dependencies, hidden deployment or billing effects and unexplained behavior changes.

### 4. Decision and release boundaries

- [ ] Obtain a human review decision for this **exact full head SHA and scope**, even where the GitHub ruleset permits zero approving reviews.
- [ ] Do not merge, deploy, activate a recurring schedule, change secrets/provider/IAM, spend money or bypass a gate based on this checklist or on green CI alone.
- [ ] Keep P01 `NO-GO` and AI-9 `BLOCKED` unless their **separate** source-bound acceptance criteria and owner decisions are satisfied.
- [ ] On a verified merge, record PR number, full head and merge SHAs, CI run and limitations in a subsequent reviewed milestone-ledger/STATE update.

## Current implementation queue (advisory, one task at a time)

1. **PR #632 conflict reconciliation:** Reinspect the latest `main` and #632; propose a fresh feature branch from current `main` to port the final strict-JSON CineForge runner triage. Preserve #634 OTLP test registration and README entry; check `.github/workflows/ci.yml` and `README.md` for conflicts. Open a replacement PR only when implementation is separately authorized; do **not** merge or close #632 as a side effect.
2. **Evidence continuity:** After a verified integration merge, update the milestone ledger and STATE from actual PR, merge SHA and exact-SHA CI evidence. Avoid rewriting history or marking runtime gates complete.
3. **P01 design and evidence:** Plan how to demonstrate trusted OIDC/PKCE, certificate-validating PostgreSQL network paths, tenant isolation, restore drills and an enforceable owner-approved all-in cost cap **without activating paid services**.
4. **AI-9:** Prepare separately authorized provenance/privacy-reviewed natural-incident evaluation; do not rerun reserved synthetic holdout seeds or relax thresholds.
5. **Live sources:** Consider exactly one authenticated, minimized CI/telemetry sender only after trust, retention, access and review gates have passed.

## Per-integration decision record

| Field | Required entry |
| --- | --- |
| Integration / PR / owner | |
| Base SHA / reviewed full head SHA | |
| Data classification and source trust | |
| License and version evidence | |
| Negative test and complete command result | |
| Exact-SHA CI and CodeQL URLs | |
| Skipped, blocked and unknown checks | |
| Secret/privacy/tenant impact | |
| Deployment, provider and cost impact | |
| Human decision for exact SHA and scope | |
| Rollback or stop condition | |
| Final status: PASS / FAIL / NOT_RUN / BLOCKED | |

## References

- [GitHub rulesets documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub pull request checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-pull-requests/reviewing-changes-in-pull-requests/about-status-checks)
- [CloudEvents specification](https://github.com/cloudevents/spec)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [Devobs repository policy](../../AGENTS.md)

# Integration execution plan

Baseline: `f02319237b604d5447598cfb6f2d39e66e14d3f0`; 2026-11-21.
**VERIFIED:** readiness documentation and a dependency-free offline validator.
**UNVERIFIED:** provider accounts, authentication, live integration and total cost.
This plan does not authorize execution, deployment, migration or billing changes.

## Sequence and acceptance gates

| Priority | Task | Acceptance / stop condition |
| --- | --- | --- |
| 0 — this PR | Document [Pulumi](../integrations/PULUMI_DELIVERY_READINESS.md), [Catalyst](../integrations/AZURE_CATALYST_READINESS.md), and the [neutral contract](../architecture/MULTICLOUD_INTEGRATION_ARCHITECTURE.md) | Synthetic tests and existing relevant checks pass; provider/execution/production flags remain false |
| 1 — next implementation | Offline Pulumi Delivery assessment adapter using recorded, synthetic REST fixtures | Deterministic bounded evidence output; no HTTP, token, SDK, runner or pipeline creation |
| 2 — separate operator review | Confirm exact account, plan, permission, source-data and cost assumptions | Missing approval, unsupported API/schema or unenforceable spending boundary stops progress |
| 3 — separately authorized read-only trial | One scoped authenticated assessment or reviewed manual Catalyst export | Exact-SHA approval, allowlisted target, bounded requests and sanitized evidence; no mutation |
| 4 — future sandbox proposal | Review full intent, cloud identities, artifact digest, state ownership, recovery and price | No dual ownership, database migration, paid agent or production path without new authorization |
| 5 — future production decision | Existing human release gates and operational acceptance | Fixture PASS, model advice or vendor gate alone never authorizes production |

## One recommended next implementation task

**ASSUMED proposal:** add an offline `pulumi_delivery` metadata adapter that
accepts synthetic snapshots of the documented preview GET response schema,
normalizes run/stage/evidence references and feeds the existing integration
control plane. Do not add a parallel deployment controller.

Before coding, pin the reviewed API/schema version and define finite size/time
limits and fixed error codes. Test valid/missing/malformed fields, scope mismatch,
stale SHA/digest, duplicate evidence and unexpected auth/approval claims. Unknown
data must yield UNVERIFIED/BLOCKED; no result can set execution or production
authorization. No credentials or live API access are prerequisites for that task.

Catalyst remains a manual-onboarding evaluation until a supported automation
surface for the intended operation is verified. Do not invent an agent endpoint,
install an appliance or upload inventory to satisfy an offline test.

## Release, approval and rollback boundaries

Keep existing GitHub Actions checks, shared site staging, Pages publication,
GCP definitions and Terraform state ownership unchanged. Any future Delivery
stages must reference already-reviewed artifacts and retain separate human
sandbox/production decisions. Do not activate GitHub Apps, webhooks, OIDC trusts,
cloud permissions, schedules, external agents or paid models in this work.

For this change, rollback is a reviewed code/docs revert. No cloud rollback is
needed because no cloud state changes. A future resource rollback must be
specified and reviewed separately; it is not permission for destroy, database
restore/migration or bypassing existing [human approval](../../scripts/human_approval_gate.py).

## Validation and evidence recording

From the repository root, with Python available:

```sh
python -m unittest tests.test_integration_readiness -v
python -m compileall -q tests
python scripts/check_action_pins.py
git diff --check
```

The [tests](../../tests/test_integration_readiness.py) exercise the actual
[offline checker](../../scripts/check_integration_readiness.py) with synthetic
configuration, negative safety cases and real CLI subprocesses. They do not
authenticate a provider, verify quotas, create a resource or establish live
readiness. Existing relevant control-plane/human-gate tests should also run.
Report command, exit status and observed result; mark unavailable checks
**NOT RUN**, never green. Record exact PR/CI SHAs without relabeling blocked gates.

### Local results — 2026-11-21

**VERIFIED on the feature worktree:**

| Check | Observed result |
| --- | --- |
| Focused readiness unittest command above | PASS: 8 tests, including malformed/oversized integer JSON |
| Compileall command above | PASS: exit 0 |
| Action-pin command above | PASS: 48 workflow/template files |
| Full `unittest discover -s tests -q` in the existing local Python environment | PASS: 1672 tests, 37 skipped; skips are not runtime evidence |
| Existing Bandit, limited to the new checker | PASS: exit 0 |
| Relative Markdown links/paths and documented JSON example | PASS: 31 links, fence/whitespace checks and actual checker evaluation |
| Official external links | PASS: 14 URLs after replacing an obsolete Pulumi terms URL |
| Diff whitespace and changed-file review | PASS; only documentation, the offline checker and its tests change |
| Dedicated Markdown linter / Gitleaks | NOT RUN: executables unavailable; manual diff and bounded local link/format checks used |
| Live provider authentication, cloud plans, migration and deployment | NOT RUN: outside this task's authorization |

Local results are not hosted CI, account eligibility or production acceptance.

## Remaining prerequisites

- **UNVERIFIED:** Pulumi account/edition, remaining allowance and approval-gate
  entitlement; Azure subscription, tenant Copilot policy, roles and region.
- **UNVERIFIED:** exact future SDK licences, privacy/data-transfer acceptance,
  authenticated interoperability and an enforceable all-in cost boundary.
- **UNVERIFIED:** production recovery, hosted identity and independent AI-9
  evidence. Existing P01 NO-GO, AI-9 BLOCKED and Codex runtime OPEN remain unchanged.

**ASSUMED cost model:** provider subscription + workflow/agent use + source/target
cloud compute/storage/network + retention/backup + tax. Offline validation has no
provider charge; account-specific totals are unknown. Published free allowances
and trial periods are not spending caps. No quote or paid activation is approved.

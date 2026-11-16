# Devobs Security and Code-Quality Review — 2026-11-16

**Review status:** baseline complete; documentation-only change.
**Repository:** `hamedonassar95/Devobs`
**Review branch:** `feature/security-review-baseline`
**Exact base SHA:** `de306da3ced24bbc1815026d24e8a970c70d6c3f`
**Runtime behavior changed:** no.
**Repository settings changed:** no.

## Executive summary

One verified repository-governance gap needs an owner decision: the active `Protect main` ruleset requires CI and CodeQL but sets the required approving review count to zero. The current policy-audit script and its tests accept that value. A Phase 8B publisher also says that its PR is pending human approval, but its REST request does not ask GitHub to create a Draft PR. Required checks and a human-authorized merge remain in place; independent review is not enforced by the repository ruleset.

Two conditional risks are recorded separately. The tracked Bun lockfile no longer describes the current console manifest, although CI uses the matching npm lockfile. The API's request limits are process-local; their effective bound depends on the number of running workers and instances. No live P01 service was verified, and P01 remains **NO-GO / BLOCKED**.

No confirmed runtime code exploit was established in the reviewed authentication, tenant isolation, input-boundary, automation, or infrastructure paths. This is a point-in-time review of repository evidence, not proof that hosted runtime settings or controls are active.

## Review scope and method

The tracked-tree inventory contained 991 files (about 8.1 MB); every tracked file was read in a UTF-8 inventory pass, with no unreadable files. The whole tree was searched for workflow triggers and permissions, untrusted input use, shell/process execution, network requests and redirects, authentication/session handling, tenant/RLS controls, browser sinks, secret-handling references, and deployment settings. This is a lexical review, not a local Gitleaks scan. Line-focused review covered root `AGENTS.md`, `STATE.md`, `README.md`, the current readiness document and milestone ledger, authored workflows and generated agent workflows, the AI console, `scripts/ai_intelligence/`, `scripts/devobs_intelligence/`, security tests, dependency manifests and lockfiles, Docker/Render, deploy files, Terraform, Kubernetes, and monitoring. Historical docs and fixtures were included in the inventory/searches; conclusions below cite current source or direct API evidence.

Evidence labels:

- **VERIFIED** means the source, test output, or dated GitHub API result directly supports the statement.
- **POTENTIAL** means the implementation limitation is verified but its production exposure depends on unverified runtime or operator choices.
- **UNVERIFIED** means this checkout or available read-only GitHub access did not establish the claim.

No source, workflow, dependency, deployment, policy, or scanner configuration was changed. No secrets or environment values were inspected, no service/database/container was started, and no cloud or Terraform apply/destroy action was run. The Codex Security scan capability was not callable in this environment; the review used the repository's current checks, available local tests, source inspection, and public GitHub metadata instead. No scanner was added.

## Verified findings

### V-01 — Main does not require independent PR approval

- **Severity:** Moderate — security governance/control gap; no direct runtime exploit demonstrated.
- **Confidence:** High that the repository ruleset has zero required approvals. Medium that this is the complete effective rule set, because the classic branch-protection API returned HTTP 403 to the read identity and organization/enterprise policy visibility is not established.
- **Affected source and policy:** [Phase 8B PR creation, lines 188–205](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/.github/workflows/phase8b-patch-publisher.yml#L188), [repository-policy audit, lines 200–208](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/scripts/check_repo_policy.py#L200), [policy test fixture and passing-shape assertion, lines 45–69](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/tests/test_check_repo_policy.py#L45), and active [Protect main ruleset](https://github.com/hamedonassar95/Devobs/rules/24507159) / [ruleset API response](https://api.github.com/repos/hamedonassar95/Devobs/rulesets/24507159).
- **Evidence:** The current active repository ruleset response targets the default branch and reports `required_approving_review_count: 0`, `required_reviewers: []`, `require_code_owner_review: false`, and `require_last_push_approval: false`. It still requires strict `validate` and `CodeQL` checks and a code-scanning threshold. In the workflow, the PR body says `PENDING HUMAN APPROVAL`, but the `pulls.create` request contains no `draft` field. The existing policy checker only checks for the presence of a `pull_request` rule; the fixture sets the review count to zero and `test_accepts_current_policy_shape` expects no finding. GitHub's [ruleset review requirement documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging) and [create-a-pull-request API](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request) define the relevant controls.
- **Impact:** An authorized writer can merge a PR after its required checks pass without a separate approving reviewer, unless an additional rule outside the accessible ruleset applies. This weakens independent review of security-sensitive workflow, authorization, RLS, and recovery changes. It does **not** remove required CI/CodeQL checks or grant an agent merge authority.
- **Existing protection:** The active repository ruleset requires PRs, up-to-date branches, `validate`, `CodeQL`, and code scanning; its returned bypass list is empty. The Phase 8 AI generator is separately configured to create a Draft PR with an allowlisted file set. P01 and AI-9 are still blocked, and the human merge boundary remains unchanged.
- **Minimal remediation proposal:** In a later, separately owner-authorized policy change, require at least one independent approval (and last-push or Code Owner review for security-sensitive paths), update the existing policy checker and tests to reject a zero count, and have the manual Phase 8B publisher create a Draft PR until review is complete. A Draft state is a workflow aid, not a replacement for a required approval rule.

## Potential risks and unverified runtime assumptions

### P-01 — Tracked Bun lockfile is stale relative to the console manifest

- **Severity:** Low, conditional dependency-reproducibility risk; no current production exposure established.
- **Confidence:** High that the files disagree; medium that a developer or build uses Bun, because repository CI and the app setup guide use npm/Node.
- **Affected files:** [`apps/ai-intelligence-console/bun.lock`, lines 3–28](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/apps/ai-intelligence-console/bun.lock#L3), [`package.json`, lines 1–40](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/apps/ai-intelligence-console/package.json#L1), and [`package-lock.json`](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/apps/ai-intelligence-console/package-lock.json).
- **Evidence:** `bun.lock` identifies the workspace as `react-example` and declares older root ranges including `express ^4.21.2`, `@google/genai ^2.32.0`, and `vite ^8.3.0`; it lacks current direct entries such as `keycloak-js` and `express-rate-limit`. `package.json` declares `devobs-ai-intelligence-console`, `express ^5.3.0`, `@google/genai ^3.0.0`, `vite ^8.3.8`, `keycloak-js 26.2.5`, and `express-rate-limit ^8.7.4`. The npm lock's root dependency maps match `package.json` exactly. CI runs `npm ci` and `npm audit --audit-level=high` for console changes; it does not use Bun.
- **Impact:** If someone installs with Bun, they may resolve or retain a graph that differs from the graph tested by npm CI, or encounter a lockfile/manifest mismatch. No known vulnerable package or deployed use was established by this review.
- **Existing protection:** The npm lockfile is used by CI, npm audit is configured for console changes, and Dependabot updates the npm ecosystem weekly.
- **Minimal remediation proposal:** In a dependency-maintenance PR, either remove `bun.lock` and document npm as the only supported installer, or regenerate it using a reviewed, pinned Bun version and add a lock-consistency check. Do not upgrade packages as part of this security-review baseline.

### P-02 — API rate limits are per process, not a global spend/traffic ceiling

- **Severity:** Moderate before any hosted activation; current exposure unverified.
- **Confidence:** High in the code limitation; low in current exposure because no live P01 service, replica count, or provider-side spending cap was verified.
- **Affected source:** [`api_app.py`, lines 92–153](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/scripts/devobs_intelligence/api_app.py#L92) and [`render.yaml`, lines 13–24](https://github.com/hamedonassar95/Devobs/blob/de306da3ced24bbc1815026d24e8a970c70d6c3f/render.yaml#L13).
- **Evidence:** The limiter stores counters in process memory; its docstring says a gateway is needed globally. The diagnostic total limit is also process-local and explicitly not a monthly provider-enforced spend cap. The proposed Render command configures one Gunicorn worker, but the manifest does not prove the number of hosted instances or any deployed state.
- **Impact:** If the service is scaled across workers/instances or restarted, the aggregate limit can exceed a single process's configured limit. A request-rate limit also cannot guarantee an all-in monthly provider spend ceiling.
- **Existing protection:** Request, concurrency, diagnostic-per-principal, and per-process total limits exist; the proposed Render configuration uses one worker; diagnostics are disabled by default; the P01 ledger gate remains **BLOCKED / NO-GO**.
- **Minimal remediation proposal:** Before P01 activation, use a shared gateway/distributed limiter and a provider-enforced budget cap, then validate them in an explicitly authorized staging test. Keep the current blocked gate until that evidence exists.

### Runtime assumptions not verified

- **UNVERIFIED:** The repository contains strict OIDC, API authorization, tenant-scoped PostgreSQL RLS, and read-only database contracts, but this review did not connect to a hosted identity provider or database. CI's disposable PostgreSQL test is evidence for the tested source SHA, not hosted tenant isolation.
- **UNVERIFIED:** `render.yaml`, Terraform, Kubernetes, Docker, and monitoring files are configuration artifacts. No cloud resource, cluster, monitoring stack, or P01 service was inspected or changed.
- **UNVERIFIED:** The active ruleset endpoint was readable; the classic branch-protection endpoint returned HTTP 403. The report does not claim that no external organization or enterprise policy exists.
- **VERIFIED state:** The milestone ledger reports `p01-managed-saas=BLOCKED`, `ai9-detection-quality=BLOCKED`, and `codex-agent-runtime-acceptance=OPEN`. This review does not promote any gate.

## Existing controls reviewed

- **GitHub Actions and supply chain:** `python3 scripts/check_action_pins.py` validates full commit SHA pins across workflow/template files. The required CI workflow sets read-only defaults and scopes write permissions to jobs that publish, dispatch, or create PRs. In the reviewed authored workflows, untrusted values are passed through environment variables or structured JSON; no direct event/input interpolation into the reviewed shell commands was found. `workflow_run` handlers use trusted `main` tooling and source/run checks. The failover workflow binds its receipt to the failed run, checks the expected workflow/job, and revalidates a trusted incident before dispatch.
- **Agent and prompt boundaries:** Incident investigation requires a trusted bot-created incident and a human-applied `human-reviewed` label; its GitHub tools are read-only and its output is a report for review. Phase 8 recovery generation is budget-gated, uses live evidence gates, restricts files, and creates a Draft PR. These controls bound the agent, but do not substitute for the main-branch review rule noted in V-01.
- **Authentication and data access:** API token validation pins issuer/audience/client, RS256, short token lifetime and a supplied public JWKS; tenant/project/service authorization is derived from the verified subject. PostgreSQL access is read-only, transaction-local, parameterized, checks forced RLS and policy text, and rejects owner/BYPASSRLS roles. The AI console's Firestore rules deny all reads/writes; OIDC session tokens stay in memory; the optional diagnostic proxy requires explicit configuration, bearer auth, a fixed HTTPS origin, redacted bounded input, service bindings, and rejects redirects.
- **Input, SSRF, and browser controls:** API request sizes, paths and methods are bounded; provider collectors use fixed provider origins and reject redirects; the local AI-7 bridge uses a fixed loopback URL, host/origin checks, size limits, and a strict output allowlist. The only `innerHTML` assignment found in application source clears a component with the constant empty string; no untrusted HTML sink was found by the whole-tree scan.
- **Containers, orchestration, infrastructure, and observability:** The runtime image is digest-pinned and runs as UID 101; Kubernetes disables service-account automount for the web pod, uses non-root/read-only-root/capability-drop settings and `ClusterIP`; optional local monitoring binds published ports to loopback and keeps the exporter internal. Terraform contains only the reviewed Artifact Registry resource and a placeholder state bucket. These are source-level controls, not live deployment evidence.
- **Dependencies and scanners:** Python requirements are hash-locked; `package-lock.json` matches the console manifest; Terraform provider is version/hash-pinned. CI configures Bandit, pip-audit, Gitleaks, Trivy image/SBOM policy, CodeQL, npm audit for console changes, and dependency updates. Existing tests cover token validation, tenant denials, policy drift, secret-scan coverage, action pins, Trivy report policy, agent incident guards, and human-approval gates. No duplicate scanner was added.

## Remediation ranking for subsequent independent PRs

1. **Main review policy (highest priority):** obtain the owner's policy decision, require an independent approval on `main`, and extend `scripts/check_repo_policy.py` plus its current tests to fail closed when the required approval count is absent or zero. Keep `validate`, CodeQL, and code-scanning requirements intact.
2. **Recovery PR state:** change the manual Phase 8B publisher to request Draft PR creation and align it with the existing AI patch generator. Preserve the allowlist, live preflight, status checks, and human review; do not enable auto-merge.
3. **P01 rate/spend boundary:** before any P01 activation, implement shared rate limiting and enforceable provider-side spend controls, then prove them in approved staging. Keep P01 **NO-GO** until live identity, RLS, restore, network, budget, and owner evidence are complete.

Separate low-priority maintenance: decide whether Bun is supported and remove or refresh the stale lockfile under a reviewed/pinned toolchain. This review does not change dependencies.

## Verification record

### Local checks

| Status | Command/check | Evidence |
|---|---|---|
| PASS | `python3 scripts/milestone_ledger.py --summary` | `{"gate_statuses":{"ai9-detection-quality":"BLOCKED","codex-agent-runtime-acceptance":"OPEN","p01-managed-saas":"BLOCKED"},"latest_pr":666,"merged_milestones":270,"open_gates":3,"repository":"hamedonassar95/Devobs"}` |
| PASS | `python3 scripts/check_action_pins.py` | `Action pin check passed for 45 workflow and template files.` |
| PASS | `python3 scripts/check_site.py` | `Page contract and HTTP smoke checks passed.` |
| PASS | `python3 -m unittest discover -s tests -p '<file pattern>' -q`, applied individually to the 18 patterns below | 165 Python tests, all `OK`; counts by pattern are listed below. |
| PASS | `node --test tests/incident_guard.test.cjs` | `tests 22`, `pass 22`, `fail 0`, `skipped 0`. |
| PASS | `git diff --check` and `git diff --cached --check` | No output; both working-tree and staged diffs passed with exit 0 after removing trailing spaces. |
| PASS | Existing local link checks | `test_github_mcp_example.py`: 2 tests `OK`; the new README link target is also checked directly. No repository-wide Markdown link checker was found. |
| BLOCKED | `npm test --prefix apps/ai-intelligence-console` | Exit 1 before test assertions: Node reported `ERR_MODULE_NOT_FOUND: Cannot find package 'tsx'`; `node_modules` is absent. No dependencies were installed. |
| BLOCKED | `tests/test_postgres_rls_integration.py` locally | `psycopg` is unavailable and no database/runtime was started. The exact-base hosted CI `postgres-rls` job passed against its disposable PostgreSQL service. |
| BLOCKED locally / PASS on baseline CI | Bandit, pip-audit, Gitleaks, Trivy, and CodeQL | The corresponding local executables are unavailable. Exact-base hosted CI's `security` job passed Bandit, pip-audit, and Gitleaks; its container image build/smoke/Trivy job passed; all three CodeQL analysis jobs passed. No local tool was installed. |

Python unittest patterns and actual outputs:

| Pattern | Output |
|---|---|
| `test_intelligence_api_security.py` | `Ran 22 tests ... OK` |
| `test_intelligence_oidc_metadata.py` | `Ran 5 tests ... OK` |
| `test_intelligence_oidc_rotation.py` | `Ran 5 tests ... OK` |
| `test_intelligence_tenant_scope.py` | `Ran 11 tests ... OK` |
| `test_human_approval_gate.py` | `Ran 10 tests ... OK` |
| `test_incident_guard.py` | `Ran 6 tests ... OK` |
| `test_phase8_live_planner.py` | `Ran 8 tests ... OK` |
| `test_phase8_readonly_evidence_workflow.py` | `Ran 4 tests ... OK` |
| `test_phase8b_ai_publisher_policy.py` | `Ran 3 tests ... OK` |
| `test_recovery_patch_guard.py` | `Ran 11 tests ... OK` |
| `test_action_pins.py` | `Ran 4 tests ... OK` |
| `test_actionlint_gate.py` | `Ran 5 tests ... OK` |
| `test_check_repo_policy.py` | `Ran 16 tests ... OK` |
| `test_gitleaks_coverage.py` | `Ran 19 tests ... OK` |
| `test_trivy_report_policy.py` | `Ran 17 tests ... OK` |
| `test_trivy_sbom_policy.py` | `Ran 11 tests ... OK` |
| `test_python_dependency_automation.py` | `Ran 6 tests ... OK` |
| `test_github_mcp_example.py` | `Ran 2 tests ... OK` |

### Exact-base hosted evidence

These results are for the reviewed base SHA, not this documentation branch:

- [CI run 43858192397](https://github.com/hamedonassar95/Devobs/actions/runs/43858192397) completed successfully on `de306da3ced24bbc1815026d24e8a970c70d6c3f`; its `security`, `postgres-rls`, `terraform-validate`, container image/Trivy, Python 3.12/3.15, Node, and `validate` jobs succeeded. Conditional incident drill and actionlint/ShellCheck install steps were skipped for the push event.
- [CodeQL run 43858190907](https://github.com/hamedonassar95/Devobs/actions/runs/43858190907) completed successfully on the same SHA; `Analyze (actions)`, `Analyze (python)`, and `Analyze (javascript-typescript)` succeeded.

The review PR's exact-head checks and mergeability must be checked after publication; baseline success does not predict the PR result.

## Rollback and release boundaries

This change is limited to this report and one README link. Revert the documentation commit (or close the Draft PR) to roll it back; there are no runtime artifacts, settings, secrets, deployments, migrations, or infrastructure resources to undo. Do not merge this PR until its exact-head required CI and CodeQL checks pass and a human reviewer decides to proceed. This report does not authorize any production change or alter the P01 **NO-GO**, AI-9 **BLOCKED**, or human-approval boundary.

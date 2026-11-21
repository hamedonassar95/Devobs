# Draft PR Handoff — Open-Source Integration Readiness Engine

This file contains the exact Draft PR title and body to use if `gh` remains unavailable. No PR was created from this workspace.

## Title

`feat(integrations): open-source readiness engine`

## Base and head

- Base: `main`
- Head: `feature/open-source-integration-readiness`
- Base SHA at task start: `4e1dc8f2c9c7a4caf896d7daf681b35be2e22937`
- Current base after reconciliation: `cfa1e17ee1575da90a0bb4fe30800c6df3b68668` (PR #738)
- Final head SHA: record from `git rev-parse HEAD` after the final local commit.

## Body

### Objective

Add a focused, offline-first engine that inventories declared integrations, checks versioned compatibility and readiness metadata, detects missing configuration without exposing values, finds ownership/dependency conflicts, and emits reproducible JSON and Markdown reports. It closes the gap between the existing manual integration checklist and an executable, advisory preflight gate. It does not make production, merge, deploy, runtime, or approval decisions.

### Architecture

A versioned local JSON catalog is loaded by `catalog.py`, normalized under fixed byte/count/string limits, and evaluated by a pure function in `evaluator.py`. `compatibility.py` parses bounded numeric version requirements; `security.py` handles redaction, path safety, license policy, and human-approval validation; `reporting.py` renders stable JSON/Markdown plus structured CLI diagnostics; `cli.py` exposes `python -m devobs.integration_readiness.cli`.

No clock, random source, socket, subprocess, package installer, cloud SDK, service client, secret, or environment value is used. `evaluation_date` and `scope_sha` are explicit catalog fields, so repeated runs are byte-identical and approvals cannot silently drift across revisions.

Boundary: current main already contains `devobs/integration_control/` from PR #738. That engine evaluates PR readiness and agent-task coordination snapshots. This one evaluates a static OSS integration catalog for exact versions, licenses, declared config keys, dependencies, tools, and security evidence. Neither grants merge or production authority, and this PR does not modify the control plane.

Full design: `docs/architecture/OPEN_SOURCE_INTEGRATIONS.md`.
OSS evidence for 28 candidates: `docs/architecture/OPEN_SOURCE_INTEGRATIONS_RESEARCH.md`.
Operator runbook: `docs/runbooks/OPEN_SOURCE_INTEGRATION_READINESS.md`.

### Changed files

- `devobs/integration_readiness/`: models, bounded catalog loader, version parser, redaction/path/license/approval policy, evaluator, renderers, CLI, package exports.
- `fixtures/integration_readiness/catalog.v1.json`: offline catalog with 11 declared integrations from the reviewed repository baseline.
- `tests/integration_readiness/`: 35 behavioral tests using the repository's `unittest` convention.
- `docs/architecture/OPEN_SOURCE_INTEGRATIONS.md`: architecture, decision model, security posture, limitations.
- `docs/architecture/OPEN_SOURCE_INTEGRATIONS_RESEARCH.md`: 28-candidate official-source/license/maintenance/cost review.
- `docs/runbooks/OPEN_SOURCE_INTEGRATION_READINESS.md`: usage, exit codes, validation commands, stop conditions.
- `README.md`: user-facing usage pointer and commands.
- `docs/OPEN_SOURCE_INTEGRATION_READINESS_HANDOFF.md`: this PR body.

No CI workflow, action pin, permission, classifier, deployment path, or `devobs/integration_control` file is changed by this PR; current main already compiles/scans `devobs` and classifies `devobs/**/*.py` as Python source.

### Verification evidence

Local checks performed in the isolated worktree at the final reviewed SHA:

```text
python -m compileall -q devobs
compileall_devobs_exit=0

python -m unittest discover -s tests/integration_readiness -p "test_*.py" -v
Ran 35 tests in 0.226s
OK
unittest_exit=0

python -m unittest tests.test_python_source_coverage tests.test_python_dependency_automation -v
Ran 9 tests in 0.029s
OK
coverage_tests_exit=0

python -m unittest discover -s tests/integration_control -p "test_*.py"
Ran 23 tests in 0.072s
OK
control_tests_exit=0

git diff --check cfa1e17ee1575da90a0bb4fe30800c6df3b68668..HEAD
full_diff_check_exit=0

python scripts/milestone_ledger.py --summary
{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN", "p01-managed-saas": "BLOCKED"}, "latest_pr": 717, "merged_milestones": 304, "open_gates": 3, "repository": "hamedonassar95/Devobs"}
milestone_ledger_exit=0

python scripts/check_action_pins.py
Action pin check passed for 48 workflow and template files.
action_pins_exit=0

python scripts/check_agent_spec.py
Validated 7 agent specs, retry/production policy, direct-provider gates, Vertex failover, and all 5 gh-aw source/lock budget gates.
agent_spec_exit=0
```

Default fixture report:

```text
decision=POLICY_VIOLATION
digest=a5453410254a99bac73eee2c9aba7b4fb44a1783b6ebaa99f8c5cb0c9b1f9087
counts={"by_priority": {"P0": 1, "P1": 0, "P2": 0, "P3": 0}, "errors": 1, "findings": 1, "integrations": 11, "warnings": 0}
codes=["UNSUPPORTED_LICENSE"]
```

The 35 tests cover the required scenarios: empty catalog, valid/remediated metadata, missing config, invalid version/spec, unsupported and missing dependency, dependency cycle, ownership conflict, blocked integration, secret redaction, malformed JSON, oversized input, determinism, offline operation, missing tool, human approval (including non-human and stale-scope rejection), schema mismatch, valid report/schema, failed security requirement, unsupported/restricted license, no-side-effect guardrails, artifact integrity, CLI diagnostics, and CI classification.

NOT RUN locally:

```text
python -m pytest -q tests/integration_readiness
No module named pytest

python -m ruff check devobs/integration_readiness tests/integration_readiness
No module named ruff

python -m bandit --version
No module named bandit

python scripts/validate_ai_eval_fixtures.py
{"error": "dataset_digest_mismatch"}

python scripts/verify_gitleaks_coverage.py
Gitleaks coverage verification failed: GitHub Actions job summary path is missing

python scripts/assess_change.py
FileNotFoundError: [WinError 2] The system cannot find the file specified  # hard-coded /usr/bin/git on Windows
```

The first three are missing local tools. The last three are environment/pre-existing constraints unrelated to this diff: a Windows line-ending-sensitive dataset digest, a missing GitHub Actions step-summary path, and a Linux-only Git path. The `is_python` classifier behavior is covered by a passing behavioral test. No dependency was installed to work around these limits. Hosted CI evidence is not yet available; do not merge before the branch CI run is reviewed.

### Security findings

- P0, VERIFIED: the shipped catalog records the existing Terraform `1.17.0` pin as `BUSL-1.1`, which this offline policy classifies as restricted. The default report is therefore `POLICY_VIOLATION`; this is an intentionally surfaced policy conflict, not a claim that CI is broken.
- VERIFIED: Cosign pin drift exists (`cosign-installer v4.1.3`, `cosign-release v3.0.6`, latest `v3.1.4`). The fixture records the binary version actually used and notes the installer/binary distinction; upgrade is deferred to an owner-reviewed change.
- VERIFIED: existing CI already covers CodeQL, Trivy with CycloneDX SBOM, Gitleaks, Cosign, Conftest/OPA, Terraform validate-only, action pins, Bandit, pip-audit, and Dependabot. No duplicate scanning pipeline was introduced.
- VERIFIED: current main PR #738 added `devobs/integration_control/` for PR/task coordination snapshots. This PR does not modify it and adds no agent, PR adapter, merge path, or second control plane.
- VERIFIED: official Dependabot docs state that GitHub Actions alerts are generated only for semantic-version actions, not SHA-pinned actions. This limitation is documented, not silently trusted.
- Engine controls: recursive redaction reuses the repository helper; secret-like key values are never emitted; command-like config keys are rejected and never executed; paths reject traversal/absolute/drive/null-byte forms; approvals require a human identity, valid date, and matching scope SHA.
- No secret, token, credential, private key, TLS material, production environment, cloud account, hosted identity provider, Keycloak runtime, container, paid inference, or customer data was accessed.

### OSS license findings

- Approved in this policy: Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MIT, MPL-2.0, Python-2.0, Unlicense, Zlib.
- Restricted and surfaced by the engine: AGPL-3.0 variants, BUSL-1.1, CC-BY-NC-4.0, Commons-Clause, Elastic-2.0, GPL-3.0 variants, SSPL-1.0.
- VERIFIED license caveats: Grafana OSS and Loki are AGPL-3.0; Terraform 1.17.0 is BUSL-1.1; Redis 8+ is tri-licensed AGPL-3.0/SSPL-1.0/RSAL-2.0; LiteLLM core is MIT but enterprise terms are UNKNOWN/BLOCKED; Semgrep CE has LGPL-2.1 engine plus a separate rules license.
- BLOCKED: Redis newest stable version could not be verified from the official feed excerpt; no Redis pin was added.
- No candidate was installed, upgraded, enabled, or authorized by this PR. `SELECT` in the research appendix means retain under existing scope or advance only under separate owner approval.

### Known limitations

- The catalog is declared fixture data, not live discovery or proof of hosted configuration.
- `READY_FOR_HUMAN_REVIEW` is advisory only and never grants merge, deploy, or production authority.
- License classification is a deterministic policy filter, not legal advice.
- Offline numeric version comparison does not resolve package ecosystems or hosted version APIs.
- The engine does not verify that referenced evidence paths still contain the claimed evidence in another branch; owners must review them.
- Approval records in the fixture are synthetic test data, not real authorizations.
- Hosted CI, release gates, P01, AI-9, Codex runtime acceptance, live integrations, and production telemetry/SLOs are not established by this PR.
- `docs/runbooks/INTEGRATION_READINESS.md` is owned by another active branch, so a distinct runbook path was used.

### Remaining blockers

- BLOCKED: Draft PR creation from this workspace because `gh` is unavailable.
- BLOCKED: P01 managed SaaS and AI-9 detection quality (ledger statuses).
- OPEN: Codex agent runtime acceptance (ledger status).
- BLOCKED: live hosted integration identity/connectivity and production telemetry evidence.
- BLOCKED: owner decision on the Terraform `BUSL-1.1` exception versus migration.
- NOT RUN: pytest, Ruff, Bandit, hosted CI, containers, cloud, Keycloak, and paid inference.

### Human review checklist

- [ ] Confirm the final head SHA and that the branch contains only this task's files.
- [ ] Review the P0 `UNSUPPORTED_LICENSE` finding and decide: documented owner exception or separate migration.
- [ ] Verify CI passes on both Python 3.12 and 3.15, including the final `validate` gate.
- [ ] Verify the existing Gitleaks, Trivy/SBOM, Cosign, Conftest, action-pin, and agent-spec gates remain green.
- [ ] Review official license links in `OPEN_SOURCE_INTEGRATIONS_RESEARCH.md`; do not treat them as legal advice.
- [ ] Confirm no secret, token, credential, TLS material, environment value, or production data appears in the diff or reports.
- [ ] Confirm the scope boundary with `devobs/integration_control/` remains clean: no PR readiness, agent task, or merge-authority logic was copied or modified.
- [ ] Confirm no new workflow, duplicate scanner, paid service, cloud resource, deploy, merge, or release-gate change was introduced.
- [ ] Keep this PR as Draft; do not merge or deploy without explicit owner approval for the final reviewed SHA and scope.

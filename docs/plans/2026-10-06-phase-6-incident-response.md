# Phase 6 Incident Response Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe observability and incident-triage layer that detects failed production pipeline workflows, gathers structured evidence, recommends a response, and prepares a constrained AI handoff.

**Architecture:** A Python standard-library classifier converts GitHub Actions metadata into a deterministic incident schema and Markdown report. A `workflow_run` GitHub Actions workflow monitors the existing `CI -> Deploy Pages -> Deployment Health Check` chain on `main`, uploads evidence, and creates a deduplicated issue; a manual dry-run path validates the automation without damaging production.

**Tech Stack:** Python 3 standard library, `unittest`, GitHub Actions, GitHub CLI, GitHub Issues, GitHub Actions artifacts.

## Global Constraints

- Preserve protected `main`; all changes go through a PR and existing checks.
- Do not automatically execute rollback in Phase 6.
- Do not collect raw job logs automatically.
- Use least-privilege `GITHUB_TOKEN` permissions.
- AI output may recommend actions but may not directly mutate production state.

---

### Task 1: Deterministic incident classifier

**Files:**
- Create: `scripts/incident_triage.py`
- Test: `tests/test_incident_triage.py`

**Interfaces:**
- Consumes: workflow name, conclusion, run metadata, structured jobs JSON.
- Produces: incident JSON schema and Markdown report.

- [x] **Step 1: Add the focused failing test**
  - CI failure => `validation/high/FIX_FORWARD`.
  - deployment failure => `deployment/high/MANUAL_REVIEW`.
  - health-check failure => `production-verification/critical/ROLLBACK_CANDIDATE`.
  - cancelled run => `MANUAL_REVIEW` and automatic rollback disabled.
  - Markdown contains run evidence and guardrails.
- [x] **Step 2: Verify the relevant failure**
  - Run: `python3 -m unittest tests/test_incident_triage.py -v`
  - Observed: non-zero result from unimplemented classifier behavior.
- [x] **Step 3: Implement the minimum behavior**
  - Pure classifier plus CLI; automatic rollback and direct push always disabled.
- [x] **Step 4: Verify the focused pass**
  - Run: `python3 -m unittest tests/test_incident_triage.py -v`
  - Observed: all five Phase 6 classifier tests pass.
- [ ] **Step 5: Run the affected integration check**
  - Run: `python3 -m unittest discover -s tests -v`
  - Expected: all repository tests pass in GitHub CI.
- [x] **Step 6: Commit the passing deliverable**
  - Commit: `feat: add deterministic incident triage`.

### Task 2: Production workflow monitor

**Files:**
- Create: `.github/workflows/incident-response.yml`

**Interfaces:**
- Consumes: completed `CI`, `Deploy Pages`, and `Deployment Health Check` runs on `main`.
- Produces: evidence artifact, workflow summary, and deduplicated GitHub issue.

- [x] Add a safe manual dry-run path that cannot alter production.
- [x] Collect structured workflow metadata and job summaries only.
- [x] Invoke the deterministic classifier and create `incident.json` + `incident.md`.
- [x] Upload the evidence bundle with 14-day retention.
- [x] Add deduplicated issue creation for real incidents.
- [ ] Validate the workflow through PR CI/CodeQL and a post-merge manual dry run.

### Task 3: Operational documentation and AI boundary

**Files:**
- Create: `docs/INCIDENT_RESPONSE.md`

**Interfaces:**
- Consumes: incident schema and rollback runbook.
- Produces: operator policy for evidence, response decisions, safe testing, and AI handoff.

- [x] Document monitored workflows and decision matrix.
- [x] Document evidence retention and raw-log exclusion.
- [x] Document the human approval boundary for rollback.
- [x] Document AI-allowed and AI-prohibited operations.
- [x] Cross-reference `docs/ROLLBACK_RUNBOOK.md`.

## Unresolved externally observable decisions

- AI provider/agent authentication is intentionally not activated in this phase. Enabling GitHub Agentic Workflows or another provider requires a separately approved credential and billing decision.

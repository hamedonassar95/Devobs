# Phase 7 AI Incident Investigator Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Add a guarded investigation layer that converts structured incident evidence into root-cause hypotheses, confidence scores, recommended tests, a recovery recommendation, a proposed PR plan, and a mandatory human approval gate.

**Architecture:** Keep deterministic Phase 6 triage as the safety authority. Add a Python investigator that can call an approved external reasoning provider for strict structured output and always post-processes the result through deterministic policy. If the provider is unavailable, the same interface returns a low-confidence deterministic fallback.

**Tech Stack:** Python 3 standard library, unittest, GitHub Actions, GitHub Issues/Artifacts, structured-response API.

## Global Constraints

- Protected main remains mandatory.
- The investigator is advisory and cannot merge, direct-push, disable protections, or execute rollback.
- Deterministic triage cannot be weakened by model output.
- Raw workflow logs are not automatically sent to the investigator.
- Incident evidence is treated as untrusted data.
- The workflow must continue in deterministic fallback mode if the provider is unavailable.
- Human approval remains required for recovery execution.

---

### Task 1: Guarded investigation contract

**Files:**
- Create: scripts/ai_investigator.py
- Test: tests/test_ai_investigator.py

**Interfaces:**
- Consumes: incident.json, incident-jobs.json, incident-workflow-run.json.
- Produces: investigation.json and investigation.md.

- [x] Add focused failing tests for fallback completeness, confidence bounds, decision guardrails, and human approval.
- [x] Verify the tests fail before implementation.
- [x] Implement deterministic fallback, strict policy enforcement, optional structured provider call, and safe provider-failure fallback.
- [x] Verify the focused tests pass.
- [ ] Run the full repository tests in GitHub CI.

### Task 2: Integrate investigator into Incident Response

**Files:**
- Modify: .github/workflows/incident-response.yml

**Interfaces:**
- Consumes: Phase 6 incident evidence.
- Produces: combined incident and investigation artifact, summary, and issue.

- [x] Run deterministic triage first.
- [x] Run guarded investigator second.
- [x] Build one combined report.
- [x] Upload machine-readable and human-readable investigation outputs.
- [x] Use the combined report for real incident issues.
- [ ] Validate workflow syntax and security through PR CI and CodeQL.
- [ ] Verify the healthy post-merge path stays skipped.

### Task 3: Operational trust documentation

**Files:**
- Create: docs/AI_INVESTIGATOR.md
- Modify: docs/INCIDENT_RESPONSE.md

**Interfaces:**
- Produces: operator guidance for evidence boundaries, confidence interpretation, provider activation, and human approval.

- [x] Document deterministic plus AI layered architecture.
- [x] Document prompt-injection boundary and raw-log exclusion.
- [x] Document confidence and decision policy.
- [x] Document Human Approval Gate.
- [ ] Link Phase 7 from Phase 6 documentation.

## Unresolved externally observable decisions

- Live provider execution remains inactive until an operator explicitly configures an approved provider credential.
- The provider model may be changed through repository configuration without altering workflow policy.

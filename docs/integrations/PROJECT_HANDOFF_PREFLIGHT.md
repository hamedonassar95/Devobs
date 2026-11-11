# Devobs ecosystem — offline project handoff preflight

**Status: PROTOTYPE / REVIEW ONLY.** This helper does not authenticate owners, verify redaction, inspect files, transfer data, authorize publishing, deploy software or merge code. All four projects retain independent repositories, data and owners.

## Proposed cross-project review paths

| Source | Destination | Candidate artifact | Purpose |
| --- | --- | --- | --- |
| Devobs | devobs-saas | ci_report | Public-redacted CI/security evidence for separate human review |
| Devobs | phone-repair-assistant-v2 | ci_report | Public-redacted CI/security evidence for separate human review |
| Devobs | al-dala-mobile | ci_report | Public-redacted CI/security evidence for separate human review |
| phone-repair-assistant-v2 | al-dala-mobile | knowledge_package | Public-redacted technical knowledge after technical and destination-owner reviews |

Every other direction or artifact type is denied. Customer data, secrets, non-redacted classifications, missing required reviews and any action other than review are denied.

## Local use (no external account or cloud)

Prepare a local JSON object containing exactly these fields:

- source, destination, artifact_type, intent, classification
- contains_customer_data, contains_secrets, technical_reviewed, destination_owner_reviewed

Use intent = review, classification = public_redacted, supported source/destination/artifact, and boolean flags. Never place actual customer data, credentials, device identifiers or private work orders in the input.

From a local checkout:

    python3 scripts/project_handoff_gate.py --request /path/to/sanitized-request.json
    python3 -m unittest discover -s tests -p 'test_project_handoff_gate.py' -v

A REVIEW_ONLY result (CLI exit 0) merely permits **consideration** of a later independent human review; it is never permission to transfer, publish or use the artifact. DENY returns exit 1; unreadable/bad JSON returns exit 2. The flags are self-declarations and cannot prove redaction or reviewer identity. No network calls, external credentials, hosted API, new workflow, automation schedule or billable operations are involved.

## Next acceptance gates

1. Verify separate repository ownership and least-privileged access for each proposed integration.
2. Define a versioned knowledge package format and independently test redaction against synthetic negative fixtures.
3. Add evidence-backed provenance and authenticated approvals before connecting real data or permitting any outward transmission.
4. Keep technical acceptance with the repair reviewer, and publication decisions with the AL-DALA MOBILE owner.
5. Retain P01 NO-GO, AI-9 FAIL and Codex runtime OPEN until independently reviewed operational evidence changes the gates.

This is an additional local guardrail, not a replacement for existing CI, CodeQL, Trivy, tenant isolation or the Phase 8 human approval gate. References: docs/PROJECT_ECOSYSTEM_EXECUTION_PLAN.md, docs/INTEGRATION_WORKFLOW.md, and AGENTS.md.

# Repair knowledge package — offline Devobs review preflight

**Status:** Source-only prototype. The checker can classify one local JSON packet as **DENY** or **REVIEW_ONLY**. Passing means a candidate may be presented to independent reviewers; it is **not** privacy clearance, proof of reviewer identity, artifact provenance, transfer permission, approval to publish, a SaaS runtime, or commercial acceptance.

## Intended handoff

- Source: PHONE REPAIR ASSISTANT v2.
- Destination: AL-DALA MOBILE.
- Devobs owns only offline schema/preflight, versioning and advisory results.
- The repair specialist still owns the diagnosis; AL-DALA MOBILE owns editorial/publication decisions.
- No customer contact, IMEI, serial, raw customer log, private photo, credentials, payment data, or unreviewed diagnosis may enter this public repository.

## V1 packet example — synthetic only

~~~json
{
  "schema_version": 1,
  "source": "phone-repair-assistant-v2",
  "destination": "al-dala-mobile",
  "topic_id": "safe-observation-example",
  "review_date": "2026-11-01",
  "device_family": "Example phone family",
  "symptom": "The device does not start consistently.",
  "safe_next_step": "Record the observation for a trained reviewer.",
  "evidence": [{
    "level": "POSSIBLE",
    "statement": "A configuration issue is one possible explanation.",
    "source_reference": "https://example.org/technical-reference"
  }],
  "technical_reviewed": true,
  "destination_owner_reviewed": true,
  "rights_reviewed": true,
  "contains_customer_data": false,
  "contains_secrets": false,
  "classification": "public_redacted",
  "intent": "review"
}
~~~

The fictional example.org fixture is **not** a verified technical reference. Real packets must cite verifiable source material and pass manual review. Each evidence item has exactly three fields: level, statement, source_reference. Allowed levels: CONFIRMED, INFERENCE, POSSIBLE, UNKNOWN. A CONFIRMED statement requires a nonempty HTTPS source reference; this tool does not establish that a source supports a statement.

## Offline procedure

Use a trusted Devobs checkout; keep the input **synthetic or already redacted**, outside the repository:

~~~sh
python3 scripts/repair_knowledge_handoff.py --package /path/to/synthetic-packet.json
python3 -m unittest discover -s tests -p 'test_repair_knowledge_handoff.py' -v
~~~

- Exact fields, schema v1, review declarations, permitted project direction, evidence types, bounded input (8 KiB), and review-only intent are checked.
- Duplicate JSON keys, embedded credentials in evidence URLs, suspicious contact/serial/secret text, unknown keys, missing declared reviews and publish/deploy intents are rejected.
- A successful result is only REVIEW_ONLY plus a deterministic SHA-256 digest of canonical JSON; no customer text is printed. Failure returns DENY and a limited reason. No network, external account, file write, deployment or AI inference occurs.
- SHA-256 identifies canonicalized content; it is **not** a signature or proof of provenance. Reviewer booleans are untrusted self-declarations. Heuristic secret/PII checks are incomplete and cannot replace independent privacy/rights review.
- REVIEW_ONLY cannot override Phase 8 human approval, CI, CodeQL, Trivy, tenant isolation, P01 NO-GO, AI-9 FAIL or Codex runtime OPEN.

## Production gates not met

1. Authenticated reviewer identity and tamper-evident approval bound to the content digest.
2. Human verification of content rights, diagnosis evidence and privacy classification; synthetic negative-case testing.
3. Signed source provenance and least-privileged, separately approved cross-repository read connector.
4. Isolated staging test accounts and sanitized data; audit, rollback, incident recovery and owner-approved spending controls.
5. After P01/AI-9/production approval, a separate, controlled publication workflow may be proposed.

## Official engineering references

- OpenAI Docs MCP: https://developers.openai.com/learn/docs-mcp
- OpenAI Agents SDK: https://developers.openai.com/api/docs/guides/agents/sdk
- OWASP Agentic Security: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OWASP MCP Top 10: https://owasp.org/projects/mcp-top-10
- GitHub Actions security: https://docs.github.com/en/actions/concepts/security
- Repository policy: AGENTS.md; docs/PROJECT_ECOSYSTEM_EXECUTION_PLAN.md; docs/integrations/PROJECT_HANDOFF_PREFLIGHT.md.

**No new runtime service or external integration is activated by this feature.**

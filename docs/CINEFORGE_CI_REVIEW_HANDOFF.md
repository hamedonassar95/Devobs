# CineForge-AI CI metadata review in Devobs (read-only proposal)

**Status: REVIEW CONTRACT ONLY — no active integration.** This document is
about the privately owned CineForge-AI Android project and the public Devobs
automation repository. No private source code, build log, media, credential,
customer data, token or Firebase configuration may cross this boundary.

## Scope

The existing offline `scripts/project_handoff_gate.py` now recognizes the
single review route `cineforge-ai -> devobs` for `ci_report` ONLY.
It does not fetch GitHub data, dispatch workflows, transfer files, authorize
access or execute changes. Its `REVIEW_ONLY` result is not authorization.
Inputs are self-declared and require independent owner review before
any redacted material is separately shared.

The Android repository's GitHub-hosted CI has exhibited failures without
runner steps. Zero executed steps do NOT prove a Kotlin, Gradle, lint or app
failure. No Devobs workflow can repair GitHub billing, runner allocation,
or account settings by bypassing those restrictions.

## Offline demonstration with synthetic flags

Create a local **synthetic** file outside the public repository, containing:

```json
{
  "source": "cineforge-ai",
  "destination": "devobs",
  "artifact_type": "ci_report",
  "intent": "review",
  "classification": "public_redacted",
  "contains_customer_data": false,
  "contains_secrets": false,
  "technical_reviewed": false,
  "destination_owner_reviewed": true
}
```

Run `python3 scripts/project_handoff_gate.py --request /path/to/synthetic-request.json`.
Expected decision: `REVIEW_ONLY`; no network, data transfer or external AI call.
Use `python3 -m unittest discover -s tests -p 'test_project_handoff_gate.py' -v`
for the acceptance checks.

A request declaring private or unreviewed classification, secrets, customer
information, missing owner review, unknown route, or any execution intent
must yield `DENY`. The handoff gate checks the declared flags, **not** whether
the source material was actually sanitized.

## Next human-reviewed steps, not enabled here

1. In the private CineForge-AI repository, determine the GitHub Actions
   top-level failure banner, runner capacity and account restrictions. Do
   not repeatedly rerun failed jobs without new evidence.
2. Once a runner is allocated, require Android compile, unit/Robolectric
   tests, lint, and AI-call security audit on the reviewed commit.
3. Only after confirming ownership, authorization, retention and a minimal
   metadata schema should a separate PR consider forwarding a sanitized
   status/provenance event to Devobs. A public receiver must reject arbitrary
   payloads, and must not have access to the private source repository.
4. Preserve explicit human approval for PR merge, deployment, cost
   changes or provider execution.

**Forbidden:** opening an automatic cross-repository secret/token channel,
copying private workflows or source into Devobs, or using a public runner
as a workaround to leak private repository content.

See `AGENTS.md`, `docs/AI_REPOSITORY_DISPATCH.md`, and
`docs/LIVEOPS_CI_INTEGRATION.md` for existing governance patterns.

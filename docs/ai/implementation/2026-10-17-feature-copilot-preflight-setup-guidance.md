---
phase: implementation
title: Copilot preflight remediation
description: Implementation and verification record for actionable credential setup guidance
---

# Implementation

## Lifecycle progress

- [x] Phase 2: requirements reviewed; preflight was failing before inference due to a token-format mismatch.
- [x] Phase 3: design reviewed; a local dependency-free checker keeps the preflight testable and network-free.
- [x] Phase 4: implementation plan created with separate tests, workflow wiring, docs, and hosted checks.
- [x] Phase 5: checker and workflow updates implemented; the token value is never written to output.
- [x] Phase 6: planning updated to record implementation and local verification.
- [x] Phase 7: implementation checked against the design; only token presence/prefix is inspected.
- [x] Phase 8: focused and full tests plus security and workflow checks passed.
- [x] Phase 9: final diff review completed; GitHub Codex review found no issues; PR #173 and hosted checks completed.

## Code changes

- `scripts/check_copilot_preflight.py` validates only whether the secret is present and starts with `github_pat_`. It writes a GitHub Actions job summary with separate missing/malformed guidance and explicitly limits what a passing format check proves.
- `.github/workflows/ai-provider-preflight.yml` checks out the source with the existing pinned checkout action, disables persisted credentials, and invokes the tested checker with the secret in its environment.
- `tests/test_ai_provider_preflight.py` covers missing, malformed, and accepted-prefix inputs, the workflow contract, output-summary behavior, and token non-disclosure.
- `docs/INVESTIGATOR_ACCEPTANCE.md` records the latest hosted failure and distinguishes the Copilot secret from the policy-audit secret.

## Security constraints

No network or AI API request is made. No secret value is printed, persisted, or included in a summary. The Copilot job retains only `contents: read`; this change adds no write permission, cloud resource, or dependency. A passing prefix check does not validate the Copilot Requests permission or model access.

## Local evidence

- Focused preflight tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ai_provider_preflight -v` — 7 passed.
- Full Python suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` — 169 passed.
- Node guard suite: `node --test tests/incident_guard.test.cjs` — 22 passed.
- Action pin validation: `python3 scripts/check_action_pins.py` — 31 workflow/template files passed.
- Site contract and HTTP smoke test: `python3 scripts/check_site.py` — passed.
- Bandit: `python3 -m bandit -r scripts -x scripts/check_site.py` — no findings.
- AI DevKit base lint: 7 checks passed; feature lint: 16 checks passed.
- `git diff --check` — passed.

## Hosted evidence

- PR #173: https://github.com/hamedonassar95/Devobs/pull/173 — merged at `e8a2f93`.
- PR CI run [39055176742](https://github.com/hamedonassar95/Devobs/actions/runs/39055176742), CodeQL run [117461686279](https://github.com/hamedonassar95/Devobs/actions/runs/117461686279), and Gitleaks all passed.
- GitHub Codex review completed with no findings. The separate OpenAI-backed AI Code Review workflow skipped its model request because `OPENAI_API_KEY` is not configured.
- Post-merge CI run [39055525802](https://github.com/hamedonassar95/Devobs/actions/runs/39055525802) and Push on main run [39055525679](https://github.com/hamedonassar95/Devobs/actions/runs/39055525679) succeeded.

The current Copilot credential has not been validated after this change. The owner must configure a dedicated fine-grained PAT with account permission `Copilot Requests: Read` as `COPILOT_GITHUB_TOKEN`, then rerun **Actions → AI Provider Preflight** on `main`. The preflight only checks token presence and prefix; it makes no model request and does not prove Copilot access or quota. `POLICY_AUDIT_TOKEN` remains a separate read-only repository-policy credential.

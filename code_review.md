# Devobs code review guide

Review the proposed diff against the current base branch. Report only actionable issues introduced by the change.

## Check

- Correctness: look for regressions, broken edge cases, and behavior that conflicts with the stated intent.
- Security: preserve least privilege; do not widen GitHub Actions permissions, expose secrets, or trust untrusted pull request input in privileged jobs.
- Workflows: verify triggers, job conditions, concurrency, pinned action references, and failure behavior in `.github/workflows/`.
- Deployment: keep GitHub Pages and Vercel as the configured targets. Do not trigger or imply an AWS deployment unless a workflow is explicitly dispatched and confirmed.
- Tests: check whether the change adds or updates focused tests and whether relevant CI checks pass.

## Report findings

For each finding, include severity, file and line, concrete impact, and a practical fix. Verify the claim against the changed code and available CI evidence. Mark uncertainty clearly; omit speculative concerns and style-only preferences.

If there are no actionable findings, say so. A code review is advisory and does not approve or merge a pull request.

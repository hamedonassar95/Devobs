# Controlled Rollback Runbook

## Purpose

This runbook documents the safe rollback procedure validated during **Phase 5 — Controlled Rollback**.

The goal is to restore a known-good application state without rewriting Git history, bypassing branch protection, or force-pushing to `main`.

## Validated rehearsal

Rehearsal ID: `RB-20261006`

Known-good baseline:

- Commit: `24e7baaf0ffbf2e83980e791e58403004a872f86`
- `index.html` blob: `05d8faa88384dbfa78df19ab6546be681bfab168`

Forward test change:

- PR: `#12`
- Commit: `fd6ec6b0e61d5f0de38ef67acf47aaecf9f0dfb7`
- Change: temporary `RB-20261006` marker added to the page

Rollback:

- PR: `#13`
- Commit: `4e6638d63f2eeff13841e1ee2523a64650d5ec38`
- Result: exact original `index.html` bytes restored

Verification after rollback:

- Current `index.html` blob matches the baseline blob exactly.
- Comparing the baseline commit with the rollback commit returns **no changed files**.
- Git history remains intact: the rollback is a new forward commit, not a reset.
- No force-push, branch-protection bypass, workflow edit, or database recovery was used.

## Standard rollback procedure

1. **Identify the last known-good commit**
   - Record the commit SHA and the affected file/object SHAs when practical.

2. **Confirm the failure scope**
   - Determine whether the issue is application content, workflow/configuration, infrastructure, or data.
   - Do not use this application-file procedure to claim database recovery.

3. **Create a dedicated rollback branch**
   - Branch from the current protected `main`.

4. **Restore only the affected files**
   - Restore their exact known-good contents.
   - Avoid unrelated cleanup or feature changes in the rollback.

5. **Open a rollback PR**
   - Reference the bad change and the known-good baseline.
   - Document expected restored state.

6. **Require normal validation**
   - CI must pass.
   - Security checks such as CodeQL must pass when configured.
   - Do not bypass required checks.

7. **Merge through the protected branch flow**
   - Never force-push or rewrite `main`.

8. **Verify production**
   - Confirm deployment succeeded.
   - Confirm the deployment health check passed.
   - Verify the faulty marker/behavior is absent.
   - Compare the restored source to the known-good baseline.

9. **Record evidence**
   - Save PR numbers, commit SHAs, workflow runs, and final verification results.

## Decision rule

Use a rollback when restoring the previous known-good state is safer and faster than fixing forward.

Use a forward fix instead when:

- data migrations make rollback unsafe;
- external systems have already consumed the new state;
- security remediation must remain in place;
- reverting would reintroduce a known vulnerability.

## Phase 5 exit criteria

Phase 5 is complete when all of the following are true:

- a controlled forward change was deployed;
- a rollback was performed through the protected PR workflow;
- validation checks passed;
- production was restored;
- source equality with the known-good baseline was verified;
- the procedure is documented and repeatable.

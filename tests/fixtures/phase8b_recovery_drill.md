# Phase 8B Controlled Recovery Drill

This file is a non-production fixture used to prove the isolated recovery write path.

- Base: `main`
- Scope: documentation-only
- Production behavior: none
- Merge authority: human only
- Deployment authority: none
- Rollback authority: none
- Final state: `PENDING HUMAN APPROVAL`

The drill demonstrates that a proposed recovery change can exist on a dedicated branch
without modifying `main`. Deleting the branch fully reverses the drill.

# DevObs releases, change governance and GitLab replica

## One original repository

Canonical source: https://github.com/hamedonassar95/Devobs. Never promote a new repository to primary or switch away from the protected `main`. All changes are proposed in feature branches, submitted to PR, reviewed and merged by the owner. No automatic production merge is authorized.

## Conventional commits and semantic versions (proposed process)

- Use `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `test(scope): ...`, or `chore(scope): ...` in the PR/commit title.
- Suggest major for a reviewed breaking public API contract, minor for backward-compatible capability, patch for compatible repair. Versioning remains **manual** until public API semantics and release tooling are approved.
- Do not imply automatic semantic-release or changelog currently runs. Existing `v1.0.0` tag is a historical baseline, not proof of enterprise product versioning.
- Proposed release checklist: reviewed PR; exact-commit CI `validate`, CodeQL and security scans; a pinned release manifest; accurate changelog with security/legal notices; human approval; staged smoke check; recorded rollback/restore plan.
- Planned changelog entries must link the underlying PR or release; never invent passing checks.

## GitLab backup/mirroring — only with a vetted destination

Official GitLab guidance distinguishes:
- GitLab **push mirroring**: pushes FROM a GitLab project to another remote. It is **not** a toggle in GitHub to back it up to GitLab.
- GitLab **pull mirroring**: pulls FROM GitHub into GitLab, subject to GitLab Premium/Ultimate eligibility for GitLab.com. Do not assume the current account supports it.
- A separately designed GitHub Action `git push --mirror` approach would require a restricted write credential to the destination and carefully scoped source/target refs. It must not be configured until recipient repository, protection policy, credential lifecycle and failure handling are reviewed.
- Mirror the original DevObs only to a newly authorized destination; do not overwrite unrelated existing GitLab projects.
- Never mirror secrets/CI variables. Do not enable mirrored-trigger pipelines by default.
- Verify that a representative commit, tag and file can be restored to an isolated test repository; keep independent encrypted backups and retention before describing the mirror as disaster recovery.

**Status: no mirror configured or used by this change.**

References: https://docs.gitlab.com/user/project/repository/mirror/ and https://docs.gitlab.com/user/project/repository/mirror/pull/ .

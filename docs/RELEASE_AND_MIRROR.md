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

**VERIFIED — read-only destination check, 2026-11-04:** the authenticated GitLab account is `hamedonassar95`; searching its owned projects for `Devobs` returned no match. The canonical GitHub source `hamedonassar95/Devobs` is public and uses `main`. This search does not rule out a destination under another namespace or project name. No GitLab project was created and no mirroring setting or credential was changed.

**Proposed, not enabled:** use a new private GitLab project such as `hamedonassar95/Devobs-mirror`, with one-way GitHub-to-GitLab pull mirroring of the canonical repository. First confirm the GitLab plan supports pull mirroring, choose the exact destination and branch/ref scope, set protection that permits only controlled mirror updates, and define sync failure and recovery behavior. If a credential is required, the owner must enter it directly in GitLab's UI; never expose it to this session or store it in this repository or CI. A mirror is replication, not a tested backup.

References: https://docs.gitlab.com/user/project/repository/mirror/ and https://docs.gitlab.com/user/project/repository/mirror/pull/ .

## GitLab replica and GitBook: read-only snapshot — 2026-11-17 (VERIFIED)

- Canonical GitHub `main`: `b2ccdcf5aaddb1a0b6c8423b98f19ed3e02245c5`, following merged [PR #678](https://github.com/hamedonassar95/Devobs/pull/678). Exact-merge [CI 44034639484](https://github.com/hamedonassar95/Devobs/actions/runs/44034639484) passed. Only the static Pages release is shown as deployed, not a hosted multi-tenant API.
- Existing public GitLab [hamedonassar95/Devobs](https://gitlab.com/hamedonassar95/Devobs) was confirmed as an import from `https://github.com/hamedonassar95/Devobs.git` with `import_status=finished`. Its `main` read `663b0b29f7b8f92c256d401cc84f735fb3cb7dc5`; **it does not match the canonical revision**, so it is not a current release or recovery replica. No GitLab pipelines were returned by the list endpoint; a separate latest-pipeline call returned HTTP 403. Pipeline execution and access are **UNVERIFIED**, not passed.
- GitBook `Devobs Documentation` stayed private and Git Sync imported the GitHub merge SHA successfully into `docs/gitbook-sync-prep/`. This is documentation sync, **not** GitLab repository mirroring.
- GitLab's official [pull mirroring](https://docs.gitlab.com/user/project/repository/mirror/pull/) requires Premium or Ultimate on GitLab.com. No subscription or mirror configuration is approved. Do not enable overwrite-diverged-branches, mirrored-trigger pipelines, credentials, schedule, push-to-main, or automatic production steps. Review cost, ref scope and repo ownership with the owner before any replication activation.
- The optional [GitLab read-only CI audit](GITLAB_READONLY_CI_AUDIT.md) already exists; do not create duplicate pipelines or treat it as proof of GitLab CI activity. A future candidate is a separately approved, token-free public-SHA parity probe, fail-closed and explicitly manual-only.

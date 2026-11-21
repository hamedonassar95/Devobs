# AI Multi-Agent Repository Workflow

**Version:** 1.0  
**Purpose:** Reusable, human-supervised development workflow for Codex, OpenCode, and other coding agents across GitHub repositories.  
**Applies to:** Any project, including CineForge-AI and Devobs.  
**Status:** Template — adopt explicitly within each repository; it does not automatically change repository settings.

## 1. Working model

- **Coordinator (ChatGPT / project owner):** Assess current repo status, select independent tasks, assign ownership, review PRs and test evidence, track roadmap/blockers, decide merge sequence. Only the owner approves merges, releases and paid operations.
- **Agent A — Codex:** Implement an isolated feature, code review, unit tests, or other clearly scoped tasks in its own branch/worktree.
- **Agent B — OpenCode:** Implement a different isolated task; preferably tasks benefiting from the user's local Windows/Android toolchain, such as APK builds, local integration checks, device-test support. Responsibilities can change depending on the project.
- **Repository:** GitHub remains the source of truth for code, PRs, audit trail, and accepted work. Local worktrees are isolated working directories.

## 2. Mandatory controls

1. Read and obey **root `AGENTS.md`** before any edit. If instructions conflict, stop and clarify.
2. Verify repository identity, active branch, latest `origin/main`, and current open PRs before starting.
3. **One atomic task per agent** and a unique branch per task: `feature/<short-task-name>`.
4. **Separate git worktrees** when both agents use the same computer. Never share a writable working directory.
5. Assign **non-overlapping file ownership** whenever possible. If both tasks affect the same file, serialize them or coordinate an explicit integration order; a different branch by itself is not sufficient to avoid conflicts.
6. Never commit directly to `main`, force-push, auto-merge, or merge without owner approval.
7. Submit a **Draft PR** with purpose, changed files, evidence, risks, blockers and rollback/verification notes; await review.
8. Follow least privilege. Never paste or commit passwords, tokens, API keys, signing credentials, private logs or personal data. Use approved secret management only.
9. No paid inference, spending-limit changes, deployment, production resource changes or publication without explicit cost disclosure and owner approval.
10. Do not claim passing tests, working APKs, deployed services or genuine AI renders without reproducible evidence.
11. On GitHub Actions zero-step runner failures, check documented account billing/runner blockers before blaming source code; never silently alter billing.
12. Keep docs/README and relevant tests updated for each feature. Validate against actual project toolchain; report PASS / FAIL / BLOCKED / NOT_RUN separately.
13. An unmerged Draft PR is **not** part of `main`. Build a baseline APK from reviewed `main`, or explicitly label an experimental branch APK.

## 3. Parallel task assignment template

| Field | Agent A: Codex | Agent B: OpenCode |
| --- | --- | --- |
| Repo | `<owner>/<repo>` | `<owner>/<repo>` |
| Objective | `<self-contained feature>` | `<independent verification/infrastructure task>` |
| Branch | `feature/<agent-a-task>` | `feature/<agent-b-task>` |
| Worktree | `<isolated path A>` | `<isolated path B>` |
| Owned files | `<explicit list>` | `<explicit non-overlapping list>` |
| Tests | `<explicit commands>` | `<explicit commands>` |
| Delivery | Draft PR, no merge | Draft PR, no merge |
| Dependencies | `<none or accepted PR>` | `<none or accepted PR>` |

## 4. Required task order

1. **Audit:** Read `AGENTS.md`, inspect `main`/open PRs, check if feature already exists, verify prerequisites.
2. **Plan:** Define objective, branch, exact files, implementation, verification, delivery, risks.
3. **Execute:** Work exclusively in assigned branch/worktree; preserve unrelated edits.
4. **Verify:** Run available lint/tests/build/security checks, document blocked prerequisites accurately.
5. **Deliver:** Push feature branch; create Draft PR; give URL and evidence.
6. **Review:** Coordinator/owner compares diff, validates results, checks overlap and security.
7. **Integrate:** Owner approves merge order. Once approved and merged, update other agent's baseline/rebase safely; do not force-push or overwrite work.
8. **Track:** Update roadmap with DONE / IN PROGRESS / NEXT / BLOCKED; record exact PR and SHA.

## 5. Task prompt requirements

Every implementation prompt must include:

- **Objective** — one clear sentence.
- **Branch** — `feature/<short-task-name>`, never `main`.
- **Files** — explicit files to create, modify, and inspect.
- **Implementation details** — existing architecture to reuse, pinned versions, least-privilege design, no unnecessary paid integrations.
- **Verification** — exact lint, tests, build and security validations.
- **Delivery** — a Draft PR with evidence; **do not merge**.
- **Compliance** — read and follow root `AGENTS.md`.

## 6. Daily coordinator report

```text
Repository: <owner/repo>
Main SHA: <sha>
Agent A / Codex: <task, branch, PR, status>
Agent B / OpenCode: <task, branch, PR, status>
Verified tests: <exact commands/results>
Blockers: <facts and evidence links>
Overlap/conflict risk: <files or dependencies>
Next owner decision: <single approval/priority>
Next tasks: <non-overlapping ordered tasks>
```

## 7. CineForge-AI example (adapt after checking current main)

- **Codex:** `feature/storyboard-lighting-effects` — implement selected-scene Lighting Effects presets (`Golden Hour`, `Blue Hour`, `Studio Key`) and isolated tests; Draft PR.
- **OpenCode:** `feature/android-private-debug-apk` — validate Android build using local Windows toolchain, attempt a debug APK, calculate SHA-256, document manual device smoke test; Draft PR.
- **Dependency:** Finish/review the existing Pacing Guide PR before assigning overlapping Storyboard files; do not run both agents against the same editable checkout.
- **Known issue (2026-11-20):** Hosted Actions runs were blocked by account compute/budget constraints, separately documented in CineForge-AI. Local verification may proceed without interpreting this as a source compilation failure.

## 8. How to reuse

1. Store this document in each repository as `docs/AI_MULTI_AGENT_WORKFLOW.md`, or store a canonical copy in a dedicated template repository and reference it from each project.
2. Add this rule to **root `AGENTS.md`** in each repository (without overwriting existing content):

   > When two coding agents work in parallel, follow `docs/AI_MULTI_AGENT_WORKFLOW.md`. Each agent must use a separate feature branch and isolated worktree, avoid overlapping files, run project-specific verification, and open a Draft PR. Never merge, deploy, spend, or change protected settings without explicit owner approval.

3. Put a short pointer to this policy in each ChatGPT Project's instructions. Adjust task-specific versions, paths, tests and permissions for each repository.
4. A shared document is a **policy**, not an automation: tasks still need to be assigned and launched explicitly in Codex/OpenCode.
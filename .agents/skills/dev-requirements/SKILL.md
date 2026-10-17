---
name: dev-requirements
description: AI DevKit · Requirements phase guidance for starting features and reviewing requirements. Use when the user wants to capture a new requirement, clarify product scope, initialize feature docs, review requirements, or run dev-lifecycle phases 1-2.
---

# Dev Requirements

Run the requirements phases for configured AI docs features. Before making docs or code changes, propose the concrete plan for this phase and wait for user approval unless the user already approved the exact phase plan.

## Phase Contract

1. Run `npx ai-devkit@latest lint` before phase work.
2. If working on a named feature, run `npx ai-devkit@latest lint --feature <name>`.
3. If lint fails because project docs are not initialized, run `npx ai-devkit@latest init -a -e claude --built-in --yes`, then rerun lint.
4. Read existing configured AI docs and keep diffs minimal. Do not assume `docs/ai`; it is only the default docs directory.
5. Ask until every material product, UX, architecture, scope, validation, rollout, contradiction, trade-off, or open question is answered, explicitly deferred, or accepted as a named assumption.
6. Ask one decision at a time, with why it matters, 2-3 viable options when useful, and a recommended answer.
7. Do not create, update, approve, or transition past requirements while material open questions remain.
8. Restate the shared understanding before updating docs or suggesting the next phase.
9. If parent `dev-lifecycle` established usable task tracing, emit requirements phase, clarification/progress, blocker/open-question, and next-step events per `task`.

## New Requirement

Use for Phase 1 or `/new-requirement`.

1. Search AI DevKit memory for relevant past features or conventions with `npx ai-devkit@latest memory search --query "<feature/topic>"`. If unfamiliar, check the `memory` skill first.
2. Clarify feature name in kebab-case, problem, target users, key user stories, scope, non-goals, success criteria, UX, constraints, rollout, and validation.
3. Brainstorm alternatives to confirm this is the right thing to build. Present 2-3 approaches with one-line trade-offs and a recommendation.
4. Store reusable answers after clarification.
5. Use `dev-worktree` to create or resume the active feature workspace with normalized `<name>`.
6. Initialize docs with `npx ai-devkit@latest docs init-feature <name>` from the active worktree/repository. Use the returned paths when filling the requirements document because `paths.docs` may customize the docs directory.
7. Fill only the requirements doc: problem statement, goals/non-goals, user stories, success criteria, constraints, and open questions. Leave later-phase documents at their templates until their phase runs.
8. Do not create an implementation plan during Phase 1. Phase 4 must plan from requirements and design after both reviews pass.
9. If task tracing is available, record draft progress and the next review step per `task`.

Next: `dev-requirements` review, then `dev-design`.

## Review Requirements

Use for Phase 2.

1. Run `npx ai-devkit@latest lint --feature <name>` and review the requirements doc path it validates. If manual path resolution is unavoidable, first resolve `.ai-devkit.json` `paths.docs`, falling back to `docs/ai`.
2. Check it against the `README.md` template.
3. Search memory for relevant conventions or past patterns.
4. Review each section: problem statement, goals/non-goals, success criteria, user stories, constraints, open questions, template compliance.
5. Resolve every gap, contradiction, ambiguity, open question, or implicit assumption.
6. Brainstorm alternatives for key decisions and trade-offs before accepting the first approach.
7. Update the requirements doc with clarified answers and chosen options.
8. Store reusable clarifications in memory.
9. If task tracing is available, record validation progress, next step, or blockers per `task`.
10. Summarize what was validated, what was updated, and remaining open items.
11. Only after the review passes, mark `Phase 2: requirements review complete` in the feature's implementation document. If fundamental gaps remain, leave it unchecked and reset Phase 3 and later review markers.

Next: `dev-design`. If fundamental gaps remain unresolvable, return to New Requirement.

# Devobs AI Intelligence — durable milestone ledger

The machine-readable [MILESTONE_LEDGER.json](MILESTONE_LEDGER.json) prevents repeated proposals for milestones already merged into the canonical `main` branch. It stores **references to evidence**, not runtime state, and is always rechecked against GitHub before a new release decision.

## Routine for every Codex task

1. Read `AGENTS.md`, `STATE.md` and the milestone ledger **before** planning work. Run `python3 scripts/milestone_ledger.py --summary`.
2. Check whether the work already exists: match on the milestone's purpose, not only its identifier. Read its PR and exact commit/CI run before declaring it complete or requesting rework.
3. Select **one** unresolved gate, record its acceptance criteria and use a separate feature branch/worktree. Do not automatically unblock gates based on textual claims.
4. After the owner merges a tested PR, append **one** new milestone entry in the next documentation change with the exact PR number, full PR head SHA, merge SHA, corresponding green CI run ID and verification limits.
5. Keep milestones sorted by increasing PR number. Never mark gates COMPLETE inside the unresolved-gates array; move work to a separately evidenced merged milestone after verification. A new feature may close one gate without changing others.
6. Run `python3 -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` and `python3 scripts/milestone_ledger.py`. Existing CI security checks enforce ledger formatting on every run.

The current ledger is a **baseline**, not a declaration that these are all past milestones. `STATE.md` and linked PR history contain many additional past changes; add older items only with verified links and full SHA evidence, not by guessing.

## Security and evidence limits

- The checker validates schema, references and uniqueness **offline**. It does not call GitHub or certify a PR was merged, a workflow passed or services are deployed.
- To verify freshness, an operator must inspect the named PR/commit and CI results on GitHub, including whether the check corresponds to the reviewed head SHA.
- No tokens, credentials, personal data, customer telemetry, billing decisions or production state are stored.
- Blocked AI-9 and P01 gates remain blocked until independently verified acceptance evidence and owner approval exist.
- Nothing in this ledger authorizes a merge, workflow dispatch, paid AI usage or deployment.

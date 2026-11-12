---
phase: planning
title: Project Planning & Task Breakdown
description: Add a bounded, optional Gmail summary action
---

# Plan

- [x] Review source and official API; retain send-only behavior.
- [x] Add fixed preview, recipient validation, consent, tests and docs.
- [ ] Pass exact-head CI/CodeQL and verify post-merge CI.
- [ ] Live OAuth only after owner configures Google; not a merge gate.
Risk: `gmail.send` acts as the chosen account. Mitigation: fixed text, one recipient, preview, confirmation and one attempt per page. Mock tests use no credentials.

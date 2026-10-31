---
name: devobs-openart-mcp-handoff
description: Prepare and review private Devobs AI Intelligence image/video requests for OpenArt, using an offline manifest and explicit separate credit approval. Use only for creative media work, not incident diagnosis or AI-9 alerts.
---

# Devobs OpenArt MCP creative handoff

## Before starting
1. Read root `AGENTS.md`, `docs/MILESTONE_LEDGER.json`, `docs/OPENART_MCP_INTEGRATION.md` and current project status. Do not repeat an existing approved creative deliverable.
2. Do not assume `@OpenArt` in ChatGPT is an installed CLI/server in the Devobs repository. OpenArt MCP is user-authorized through OAuth, never a hardcoded project secret.
3. Separate creative copy from verified engineering facts. Never portray private incident logs, actual customer data, secrets or fabricated SaaS readiness.
4. Prefer one private asset draft, using `docs/examples/devobs_openart_brief.json` as a starting structure.

## Execution
1. Write a private, `DRAFT` request. Run `python3 scripts/openart_media_request.py --input <path>` and capture its request SHA256; this is **not** permission to generate.
2. Read-only: inspect account credits and model/mode capabilities with OpenArt's connector; get the exact credit quote for output duration, resolution and quantity.
3. Stop on zero/insufficient credits, missing authorization, untrusted reference files or privacy concerns. Obtain explicit per-generation owner approval for both scope and price before any request that spends credits.
4. For authorized work, call OpenArt through its official MCP/plugin only in an operator-controlled trusted environment; do not invent REST API endpoints or run a CLI install script automatically.
5. Inspect the delivered image/video, language, text, visual safety, credit receipt and provider result. Do not claim a PENDING job is complete.
6. Save a reviewable GitHub receipt after generation with request hash, cost, model, nonsecret ID, QA result and caveats; do not publish media or merge changes without owner approval.

## No-go
- Never add model API keys, OAuth secrets or user data to a manifest or repository.
- Never auto-trigger media generation from CI, an alert, a PR comment, a detector result or a schedule.
- Never modify `AI-9 FAIL` or `P01 NO-GO` based on creative content or a green media contract test.

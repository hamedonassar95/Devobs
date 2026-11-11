# Agent integration map

This directory documents where agent-related code belongs. The existing source of truth is:

- `.codex/agents/` for repository-scoped Codex role instructions.
- `.agents/skills/` for reusable development and operating procedures.
- `scripts/ai_intelligence/` and related tests for the local AI-1 through AI-7 pipeline.

Do not copy those implementations here. The optional local code-assistance path uses upstream Aider with the existing Ollama runtime; see [`docs/LOCAL_AI_CODE_ASSISTANT.md`](../docs/LOCAL_AI_CODE_ASSISTANT.md). It is interactive, loopback-only, and configured not to commit automatically. LangGraph, CrewAI, AutoGen, Dify, Flowise and OpenHands remain candidates for separate review. Coding agents must stay advisory and must not merge, deploy, change IAM, or access secrets.

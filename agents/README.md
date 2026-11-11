# Agent integration map

This directory documents where agent-related code belongs. The existing source of truth is:

- `.codex/agents/` for repository-scoped Codex role instructions.
- `.agents/skills/` for reusable development and operating procedures.
- `scripts/ai_intelligence/` and related tests for the local AI-1 through AI-7 pipeline.

Do not copy those implementations here. LangGraph, CrewAI, AutoGen, Dify, Flowise, OpenHands, and Aider remain candidates for separate review. Add one only when it has a distinct use case, a verified license, bounded permissions, and passing project checks. Coding agents must stay advisory and must not merge, deploy, change IAM, or access secrets.

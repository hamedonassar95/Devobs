# AI automation governance and evidence

This repository uses AI for bounded code review, incident summaries, and draft recovery suggestions. The workloads are advisory: CI and a maintainer remain responsible for merge and production decisions. The machine-readable inventory is [`agent-spec.yaml`](../agent-spec.yaml); CI validates its objective, measurable outcome, retry ceiling, cost status, workflow path, and production-write policy.

## Operating policy

- Record an objective and baseline metric before treating an agent as a product capability. Current baselines are marked `not_measured`; the repository does not claim an ROI improvement yet.
- Treat every hosted model as potentially billable until the account plan, quotas, and invoices confirm otherwise. The `DEVOBS_AI_BUDGET_APPROVED=true` repository variable gates the direct OpenAI and Anthropic workflows and the Vertex AI fallback. It is an explicit operator approval switch, **not** a dollar budget or proof of a free tier. Leave it unset unless a maintainer has reviewed the applicable billing terms.
- GitHub Copilot-based gh-aw workflows retain their issue-review/manual-dispatch gates and GH-AW AI-credit limits. Credits do not establish a USD ceiling, so cost and entitlement remain account-dependent. The gh-aw source and generated lock files must be updated together using the pinned compiler before adding new cost gates; that compiler is not available in this environment.
- No agent may mutate production. CI is the deterministic quality/security gate; agent outputs are comments or draft PRs. Any future production action must be implemented as a separate workflow with explicit human approval, least-privilege identity, and a bounded rollback plan.
- Keep inference to one provider call per run and no more than three repair attempts. The current SaaS alert analyzer remains a single advisory call with local deterministic fallback and request caps; its monthly cost is unknown until measured from the provider account.
- Do not claim a semantic layer or small-model routing until a shared business vocabulary, evaluation corpus, and measured cost/quality comparison exist. The SaaS currently uses fixed rules by default and one fixed optional model; local rules are not generative AI.

## Findings applied in this review

1. Direct Codex and Claude actions now require the explicit budget approval switch before reading their provider secrets or starting inference. The automatic Vertex fallback uses the same switch.
2. The SaaS contact endpoint uses bounded request parsing and database-backed rate limits; AI requests have an atomic per-organization and shared daily cap.
3. CI validates that agent inventory entries have a concrete objective and metric, mark missing baselines honestly, do not claim unsupported per-run prices, stay within three retries, and cannot write to production.

## Evidence and limits

Gartner's June 2025 press release predicts that more than 40% of agentic AI projects will be canceled by the end of 2027 due to cost, unclear value, or inadequate risk controls. This is a forecast, not a measured cancellation rate. Do not use the previously repeated “80% accuracy improvement” as a Gartner fact; it is not supported by the cited release. Vendor-sponsored semantic-layer results should be labeled as vendor research until independently replicated.

The repository does not currently have a measured quality baseline, independent semantic-layer benchmark, inference-dollar ledger, or account-level spend enforcement. Request counts and provider credit caps are not equivalent to dollars. Review provider invoices and configure provider-side budgets/alerts before authorizing hosted-model execution.

## References

- [Gartner, 25 June 2025: Over 40% of agentic AI projects predicted to be canceled by end of 2027](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP Agentic AI threat: Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
- [NIST Generative AI Profile, AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions OIDC federation with Google Cloud](https://docs.github.com/en/actions/how-tos/secure-your-work/security-hardening-your-deployments/oidc-in-google-cloud-platform)
- [Cloudflare Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)

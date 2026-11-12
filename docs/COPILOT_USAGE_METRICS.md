# GitHub Copilot usage metrics

## What this repository supports

CI validates the shared Python test suite on Python 3.12 and 3.15. The security job rejects mutable GitHub Actions references and now fails if an active workflow YAML introduces a `pull_request_target` trigger. Existing GitHub-managed CodeQL analysis and Gitleaks remain in place; this repository does not add duplicate scanning workflows.

Dependabot continues to check Actions, Python, and the AI console's npm dependencies weekly. Python updates explicitly target `main` and receive the existing `python` label plus `python-3.15`; Actions updates keep `github_actions` and add `ci-security`.

## Read a downloaded usage report

`scripts/copilot_metrics_report.py` summarizes local `.ndjson` report files containing GitHub's `totals_by_local_byok` fields. It prints aggregate request and token counts by BYOK kind and client surface. It does not make network requests, download signed report URLs, write repository settings, or expose user identifiers in its output.

```sh
python3 scripts/copilot_metrics_report.py --input ./copilot-usage.ndjson
```

For multiple disjoint shards from one report, repeat `--input` for each shard. Do not combine overlapping reports; the script does not infer whether input files overlap.

The Copilot usage metrics API provides organization and enterprise reports. An authorized organization or enterprise operator must obtain the NDJSON report through GitHub and save it locally first. It is not a personal-account `/users/{owner}/copilot/metrics` endpoint. A local parse failure, missing field, or unavailable metric is reported as an error or unknown value; it is never converted to zero.

### API and budget boundary

The [current REST reference](https://docs.github.com/en/rest/copilot/copilot-metrics?apiVersion=2026-03-10) lists `2026-03-10` as its latest API version and documents organization/enterprise report endpoints that return short-lived NDJSON download links. It does not document the proposed `2026-11-01` API version or the `/users/{owner}/copilot/metrics` path from the supplied draft. These reports measure usage, not a guaranteed provider charge in USD. The budget gate therefore remains a manual operator decision; missing or unavailable report data must never set `DEVOBS_AI_BUDGET_APPROVED=true`.

## Budget and model limits

These reports contain usage counts, not a reliable USD charge for the model provider. BYOK usage is a subset of Copilot request totals, client telemetry can be unavailable or undercounted, and a BYOK provider may bill separately. The report tool therefore computes no estimated spend and cannot approve or reject a budget.

`DEVOBS_AI_BUDGET_APPROVED` remains a manually reviewed inference gate. This variable is an operator acknowledgment, not a spending limit. The metrics tool neither reads nor changes it. See [AI Governance](AI_GOVERNANCE_2027.md) for the existing budget policy.

The proposed model identifiers `gemini-4-carbon` and `claude-fable-5.2` are not introduced as repository defaults. Model selection, provider credentials, and spending controls stay in the operator's trusted client configuration. Existing MCP examples and `.codex/config.toml` are preserved; the active documentation MCP entry is not proof that any other integration is connected.

## References

- [GitHub Copilot usage metrics reference](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics) — BYOK field definitions, telemetry coverage, and the distinction between Copilot charges and provider billing.
- [GitHub Copilot usage metrics REST API](https://docs.github.com/en/rest/copilot/copilot-usage-metrics) — organization and enterprise report endpoints and NDJSON download links.
- [GitHub Copilot usage and spending](https://docs.github.com/en/copilot/how-tos/manage-and-track-spending/monitor-ai-usage) — account-level usage and spending views.

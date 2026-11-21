# CI Failure Intelligence

`scripts/ci_failure_intelligence.py` is a read-only, deterministic GitHub Actions diagnostic tool. It analyzes failed workflow metadata, jobs, steps, and sanitized log excerpts to produce evidence-based JSON and Markdown reports.

## What it does

- Retrieves failed workflow metadata and jobs via GitHub Actions API (read-only) when `--repo` and `--run-id` are provided.
- Supports offline mode with `--run-json` and `--jobs-json`.
- Identifies failing jobs/steps, classifies errors by category, detects repeated failure signatures, and correlates with commit evidence.
- Distinguishes code failures from infrastructure failures; marks ambiguous cases `UNVERIFIED`.
- Labels findings `VERIFIED`, `INFERRED`, or `UNVERIFIED`.
- Redacts secrets/tokens/private keys from logs and report output.
- Supports optional AI summaries through an injectable interface; defaults to deterministic rule-based summary when AI is unavailable.

## Safety

- Read-only: never modifies code, reruns workflows, merges PRs, or deploys.
- Treats logs/metadata as untrusted input.
- Fails closed on missing logs, missing metadata, or API errors.
- Does not invent root causes.

## Usage

```bash
# Offline (synthetic/sanitized inputs)
python3 scripts/ci_failure_intelligence.py --run-json run.json --jobs-json jobs.json --json-out report.json --md-out report.md

# Read-only GitHub API (requires GITHUB_TOKEN or GH token in env; no write permissions needed)
python3 scripts/ci_failure_intelligence.py --repo hamedonassar95/Devobs --run-id 123456789 --json-out report.json --md-out report.md
```

## Tests

```bash
python3 -m unittest tests.test_ci_failure_intelligence -v
```

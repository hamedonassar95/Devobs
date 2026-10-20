# Optional OpenAI Decisions incident triage

`scripts/openai_decisions_triage.py` is a local, optional classifier for
redacted incident text. In one request it asks three typed questions:

- Predicate: whether the evidence explicitly confirms a security impact.
- Choice: whether the incident is CI/CD, deployment, monitoring, security, data
  storage, billing, or another category.
- Score: severity from informational through critical.

The answers are advisory. They do not trigger CI/CD, change an incident's
priority, or approve a deployment or recovery action. The deterministic offline
dataset evaluator remains the default and makes no network requests.

## Cost and data controls

**This API is not free.** OpenAI currently lists Decisions input at **$0.10 per
1 million tokens** for `gpt-6-luna`; regional-processing premiums and
long-context multipliers can apply. Review the current pricing and account terms
before use. The script makes no request unless all of these gates pass:

1. `DEVOBS_AI_BUDGET_APPROVED` is exactly `true` in the process environment.
2. The operator passes `--confirm-billable` for that invocation.
3. The operator passes `--confirm-data-redacted` after removing secrets and
   personal data from the incident text.
4. `OPENAI_API_KEY` is already available in the process environment.

The first gate is an operator approval switch, not a spending cap. The script
does not estimate or enforce a dollar ceiling. It sends the supplied text to
OpenAI, caps input at 64,000 UTF-8 bytes, makes one request with no retries, and
does not print or store the input or API key. It rejects redirects to avoid
forwarding authorization to another host. No API key belongs in this repository,
a command-line argument, or chat.

## Run only after billing and data review

Prepare a local text file containing only the minimum redacted evidence needed.
After reviewing billing, expose the API key through your approved secret
manager, then run:

```bash
export DEVOBS_AI_BUDGET_APPROVED=true
python3 scripts/openai_decisions_triage.py \
  --input-file /path/to/redacted-incident.txt \
  --confirm-billable \
  --confirm-data-redacted
```

The tool prints only the validated typed answers and marks the result
`advisory_only`. Keep the budget gate unset to disable this integration. It is
not wired into CI or any automatic incident workflow.

## API behavior and limitations

The implementation uses the dedicated `POST /v1/decisions` endpoint, the
currently documented `gpt-6-luna` model, and predicate, choice, and score
questions. The API is in public beta. Model confidence and probabilities are
not a substitute for a locally validated threshold; calibrate them against
human-reviewed incident examples before using them for routing or prioritizing
work.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions),
[Decisions create API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create),
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing), and
[data controls](https://developers.openai.com/api/docs/guides/your-data).

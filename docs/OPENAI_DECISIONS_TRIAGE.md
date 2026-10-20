# Optional OpenAI Decisions incident triage

`scripts/openai_decisions_triage.py` is a local, optional classifier for
redacted incident text. It accepts text only; image and URL inputs are not
implemented, which keeps this incident path narrow and easier to review. In one
request it asks three independent typed questions:

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
forwarding authorization to another host. It also blocks common API-key,
authorization-header, JWT, and database-URL patterns and reports only their line
numbers; this check is best-effort and does not establish that text is safe.
Review and redact the text manually. No API key belongs in this repository, a
command-line argument, or chat.

OpenAI states that abuse-monitoring logs may include API inputs, outputs, and
derived metadata and are retained for up to 30 days by default, subject to the
policy exceptions described in its data-controls guide. Zero Data Retention and
Modified Abuse Monitoring require eligibility and approval; this repository
does not claim either is enabled. Check your organization's actual data controls
before sending incident material. Configure account-side usage notifications
and limits as well; the local approval switch is not a financial cap.

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
work. The existing evaluator's single historic incident example does not
calibrate these Decisions answers. The local tests validate request and response
contracts only; they do not measure model classification quality.

## OpenAI guidance applied

| Guidance | Application in this repository |
| --- | --- |
| Use Decisions for typed predicate, choice, and ordered score outputs; keep independent questions together and include a fallback choice. | One request asks three independent questions and includes `other`; the response is checked against exact names, types, categories, and score levels. |
| Write questions around observable criteria; use labeled examples to choose confidence thresholds. | The instructions ask for evidence-backed incident labels. There is no automatic threshold or action; human-labeled Decisions evaluation is still needed. |
| Treat user-supplied content as untrusted and keep keys in a secure server-side environment. | The prompt tells the model not to follow instructions embedded in incident text; the tool scans common secret patterns, reads the key only from the process environment, and never prints it. |
| Minimize retained/sent data and check account data controls. | Text-only local input, 64 KB cap, manual redaction confirmation, no storage, and an explicit warning about default abuse-monitoring retention. |
| Build evaluations from reviewed examples and ground truth. | The offline evaluator remains separate and deterministic. Its current single case is not evidence that the Decisions classifier is accurate. |
| Handle errors and rate limits deliberately. | One request, no hidden retries, sanitized failure messages, strict response validation, and a reported numeric `Retry-After` delay for HTTP 429 when supplied; any retry is manual. |

These controls apply to the current local classifier and the repository's OpenAI
Codex review workflow. They do not mean every OpenAI platform guide or account
setting has been configured or verified.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions),
[Decisions create API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create),
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing), and
[data controls](https://developers.openai.com/api/docs/guides/your-data),
[production best practices](https://developers.openai.com/api/docs/guides/production-best-practices),
[prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering),
[working with evals](https://developers.openai.com/api/docs/guides/evals),
[graders](https://developers.openai.com/api/docs/guides/graders),
[rate limits](https://developers.openai.com/api/docs/guides/rate-limits), and
[error codes](https://developers.openai.com/api/docs/guides/error-codes).

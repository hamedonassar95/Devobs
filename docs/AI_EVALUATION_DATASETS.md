# Offline AI evaluation datasets

The incident-investigator evaluation cases live in
[`tests/fixtures/ai-evals/incident-investigator.jsonl`](../tests/fixtures/ai-evals/incident-investigator.jsonl).
Each JSONL row binds a prompt version to trusted input facts and a human-annotated
reference. Add reviewed edge cases over time; keep synthetic or redacted incident
data in this version-controlled corpus.

Candidate model outputs are supplied separately as JSONL with one row per case:

```json
{"case_id":"incident-131-evidence-quality","output_text":"<the complete investigation comment>"}
```

Run the offline graders against reports already produced by an approved workflow:

```bash
python3 scripts/evaluate_incident_investigator.py \
  --dataset tests/fixtures/ai-evals/incident-investigator.jsonl \
  --outputs /path/to/candidate-outputs.jsonl
```

The default acceptance threshold is 100%. Use `--minimum-pass-rate 0` to inspect a
failing report without making the command fail. The JSON summary identifies the
case, prompt version, and failed graders but never echoes report text. The summary
breaks scores down by prompt version to support controlled comparisons. Candidate
reports may contain operational details; keep their output file private and out of
Git.

## Current rubric

The initial row converts the five-check historical benchmark documented in
[`INVESTIGATOR_ACCEPTANCE.md`](INVESTIGATOR_ACCEPTANCE.md):

1. Name the observed failed job and step exactly.
2. State that missing logs leave the original cause unknown.
3. Keep every causal hypothesis at or below the evidence-based confidence cap.
4. Acknowledge the later successful run and do not recommend repeating it as the
   next test.
5. Do not use an unrelated change as causal evidence unless the report explicitly
   disclaims the connection.

The historical report scored `0/5`. That is a retrospective single-case baseline,
not a measured result for the current prompt or model. The corpus currently has one
case, so it is not a statistically reliable estimate of general model quality.

## How this relates to OpenAI Datasets

This repository uses the useful parts of the OpenAI dataset workflow—versioned
examples, reference facts, output annotation, and multiple graders—but keeps them
in JSONL and evaluates them locally. The graders are deterministic string and
Python checks; the runner makes no network requests and invokes no model. Review
candidate reports from a cost-authorized run only; do not trigger an inference run
just to populate this corpus.

OpenAI's current documentation says Evals becomes read-only on October 31, 2026,
with the dashboard and API scheduled to shut down on November 30, 2026. The Evals
guide points to asynchronous runs for larger-scale tracking, while the dataset
guide recommends expanding examples as edge cases are discovered. This repository
keeps that dataset and its review history portable beyond the platform transition.

Sources: [Getting started with datasets](https://developers.openai.com/api/docs/guides/evaluation-getting-started),
[Graders](https://developers.openai.com/api/docs/guides/graders),
[Working with evals](https://developers.openai.com/api/docs/guides/evals),
[OpenAI deprecations](https://developers.openai.com/api/docs/deprecations#2026-06-03-evals-platform).

# Offline AI evaluation datasets

This repository has two separate, local evaluation paths. Both consume saved
candidate outputs, make no provider calls, and report case IDs and metrics
without echoing incident text. Dataset labels and generated candidate outputs
are different things: the corpus currently contains synthetic, unreviewed
examples and is not evidence of production model quality.

The Decisions fixture is pinned by
[`evaluation-policy-v1.json`](ai/evaluation-policy-v1.json) and checked in CI
with `python3 scripts/validate_ai_eval_fixtures.py`. The validator checks the
fixture digest, synthetic label status, prompt version, row schema, category
and severity labels, and duplicate case IDs. Its report contains only the
policy version, row count, and SHA-256 digest. This is fixture integrity and
schema validation; it does not detect semantic data poisoning, evaluate a live
model, or authorize production use. Updating the fixture requires a deliberate
policy-version and digest update in the same reviewed change.

## Incident investigator reports

Cases are in
[`tests/fixtures/ai-evals/incident-investigator.jsonl`](../tests/fixtures/ai-evals/incident-investigator.jsonl).
The corpus has 10 examples: one historical record and nine synthetic,
unreviewed scenarios. Five deterministic graders check observed failure
evidence, uncertainty, confidence caps, later-run chronology and test choice,
and causal relevance. The historical benchmark's recorded `0/5` is a
retrospective score for that historical report; it is not a current model
measurement.

Candidate reports use one JSON object per line:

```json
{"case_id":"incident-ci-test-failure","output_text":"<the complete investigation comment>"}
```

Run the graders against saved reports:

```bash
python3 scripts/evaluate_incident_investigator.py \
  --dataset tests/fixtures/ai-evals/incident-investigator.jsonl \
  --outputs /path/to/candidate-outputs.jsonl
```

The default acceptance threshold is 100%. Use `--minimum-pass-rate 0` to inspect
a failing report without making the command fail. The JSON summary identifies
the case, prompt version, and failed graders, but never echoes report text.
Keep candidate reports private and out of Git because they may contain
operational details.

## OpenAI Decisions triage

The typed-classification dataset is
[`tests/fixtures/ai-evals/decisions-triage.jsonl`](../tests/fixtures/ai-evals/decisions-triage.jsonl).
It contains 28 synthetic, unreviewed cases: four for each of the seven
configured categories, both security-impact labels, every severity level, and
an insufficient-evidence example containing an instruction-injection attempt.
The binary security-impact labels are imbalanced (6 positive, 22 negative), and
the severity levels are not evenly represented. These are coverage probes, not
a representative sample of production incidents.

`tests/test_openai_decisions_triage.py::OpenAIDecisionsTriageTests.test_prompt_injection_stays_in_untrusted_incident_input`
checks that a synthetic injection string remains in the incident `input` field,
is not copied into the fixed question instructions, and each question marks
incident text as untrusted. This is an offline request-boundary regression
test; it does not call a model or demonstrate that a model will resist
injection.

The offline evaluator validates a complete, one-to-one set of saved outputs
and computes:

- security-impact confusion counts, accuracy, precision, recall, F1, ROC AUC,
  and Brier score;
- category top-1 accuracy, supported-category macro recall, support counts,
  confusion matrix, and multiclass Brier score;
- severity exact accuracy, mean absolute error, supported-level macro recall,
  support counts, confusion matrix, and multiclass Brier score.

The multiclass Brier scores are the unnormalized sum of squared probability
errors across classes, averaged across examples. ROC AUC is `null` when the
evaluated labels do not contain both classes. The security predicate threshold
defaults to `0.5` only as a diagnostic; it has not been calibrated or approved
for production decisions.

Save one normalized result per case in a private JSONL file. `result` should be
the complete normalized result object printed by
[`scripts/openai_decisions_triage.py`](../scripts/openai_decisions_triage.py),
including `model`, `prompt_version`, `advisory_only`, and `answers`. The
evaluator rejects results generated with a different prompt version than the
dataset case:

```json
{"case_id":"ci-cd-test-assertion","result":{"model":"gpt-6-luna","prompt_version":"decisions-triage-v1","advisory_only":true,"answers":{"confirmed_security_impact":{"type":"predicate","probability":0.08},"incident_category":{"type":"choice","choice":"ci_cd","confidence":0.91,"probabilities":[{"value":"ci_cd","probability":0.91},{"value":"deployment","probability":0.02},{"value":"monitoring","probability":0.01},{"value":"security","probability":0.02},{"value":"data_store","probability":0.01},{"value":"billing","probability":0.01},{"value":"other","probability":0.02}]},"incident_severity":{"type":"score","score":1.1,"confidence":0.7,"probabilities":[{"value":0,"label":"informational","probability":0.1},{"value":1,"label":"low","probability":0.7},{"value":2,"label":"medium","probability":0.2},{"value":3,"label":"high","probability":0.0},{"value":4,"label":"critical","probability":0.0}]}}}}
```

Then run the evaluator locally:

```bash
python3 -m scripts.evaluate_decisions_triage \
  --dataset tests/fixtures/ai-evals/decisions-triage.jsonl \
  --outputs /path/to/decisions-outputs.jsonl
```

This evaluator never makes API calls. Producing real candidate outputs would
require separately authorized, billable Decisions requests and manually
reviewed/redacted input. No such requests were made while preparing this
corpus. Do not commit the output file: it can contain sensitive incident
information.

Before making quality claims, replace or supplement synthetic labels with
expert-reviewed cases drawn from representative, redacted incidents. Have
reviewers label independently without seeing model output, adjudicate
disagreements, record the rubric and prompt version, and keep a held-out set
for final comparisons. Choose decision thresholds from the error costs and
reviewed examples. A successful local evaluator run proves schema and metric
calculation only; it does not establish model quality, safety, ROI, or
production readiness.

## OpenAI evaluation guidance and portability

This structure follows the useful dataset workflow: version examples, keep
reference labels separate from generated outputs, annotate outputs, and apply
multiple graders. The deterministic checks stay in this repository so they can
be reviewed and run locally. See OpenAI's [getting-started guide for
datasets](https://developers.openai.com/api/docs/guides/evaluation-getting-started),
[graders](https://developers.openai.com/api/docs/guides/graders), and
[Evals guide](https://developers.openai.com/api/docs/guides/evals).

The supplied OpenAI documentation states that the hosted Evals platform is
scheduled to become read-only on October 31, 2026, and shut down on November
30, 2026; verify the [current deprecation notice](https://developers.openai.com/api/docs/deprecations#2026-06-03-evals-platform)
before relying on that service. Portable JSONL preserves the local corpus and
rubrics independently of that dashboard transition.

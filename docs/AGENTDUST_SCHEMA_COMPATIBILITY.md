# AgentDust v1.8.1 Schema Compatibility

## Reviewed source

The upstream release tag [`v1.8.1`](https://github.com/hamzahamidi/agentdust/tree/v1.8.1) resolves to source commit [`bab2a6b9fca0ba822ebf1bce1b6239a262eeec25`](https://github.com/hamzahamidi/agentdust/commit/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25). The tag is annotated but its GitHub tag-object response reports it as unsigned. This review reads source at the pinned commit; it does not cryptographically prove that an npm archive was built from that source.

Relevant source:

* [`doctor.rs`](https://github.com/hamzahamidi/agentdust/blob/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25/crates/agentdust-core/src/doctor.rs) defines `REPORT_VERSION`, `Counts`, `SessionSummary`, and the serialized `JsonView`.
* [`class.rs`](https://github.com/hamzahamidi/agentdust/blob/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25/crates/agentdust-core/src/class.rs) defines the six class names.
* [`classifier.rs`](https://github.com/hamzahamidi/agentdust/blob/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25/crates/agentdust-core/src/classifier.rs) classifies each process once.
* [`finding.rs`](https://github.com/hamzahamidi/agentdust/blob/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25/crates/agentdust-core/src/finding.rs) defines the serialized finding fields.
* [`doctor_report.rs`](https://github.com/hamzahamidi/agentdust/blob/bab2a6b9fca0ba822ebf1bce1b6239a262eeec25/crates/agentdust-core/tests/doctor_report.rs) tests the class counts and report behavior with synthetic fixtures.

## Upstream v1 report shape

The report version constant is `1` (`u32`). On Linux, the serialized top-level object contains:

* `version`: integer `1`.
* `owned_classes`: `{available: boolean, reason: string | null}`.
* `cgroup_unit_evidence`: `{available: boolean}`. Non-Linux builds serialize `launchd` in its place.
* `sessions`: six nonnegative `usize` values: `records`, `skipped_lines`, `active`, `ended`, `unknown`, and `degraded`.
* `unexplained_tags`: a `usize` count.
* `counts`: the six class counts below, each serialized from `usize`.
* `findings`: a vector of `ModelFinding` records. Each has `item_id: string`, `class: string`, `exe_base: string | null`, `pid: i32`, `age_secs: u64`, `evidence: string[]`, and `cwd_relation: string`.

The class keys are exactly:

`managed`, `owned-live`, `owned-ended`, `likely-owned`, `suspect`, `unknown`.

The six count categories are mutually exclusive. `diagnose` visits each classified process once and calls `Counts::add` once; that method increments exactly one slot selected by the process's single `Class`. The sum of the six values therefore equals the number of classified processes (`processes_seen` internally; it is not a top-level JSON field). The `findings` vector is a selected display list, not a complete copy of those counts: upstream lists only selected classes.

## Devobs validation policy

The local adapter is the single implementation of report validation used by both its CLI and the sandbox Workflow. It validates the required envelope fields `version`, `counts`, and `findings`; it intentionally allows additional top-level fields, including the other fields in the upstream report. It checks the six exact count keys, integer/nonnegative types, and findings array shape/count. It does not validate every upstream metadata field or inspect individual findings, and does not copy findings into its output.

Devobs applies additional resource limits that are not specified by the upstream Rust report types:

| Limit | Devobs rule | Upstream v1 source |
| --- | --- | --- |
| Encoded report size | 2 MiB maximum | No corresponding cap in `JsonView` |
| Container nesting | 64 levels maximum | No corresponding cap in `JsonView` |
| JSON nodes | 100,000 maximum, counting object/array starts, strings (including keys), and primitive tokens | No corresponding cap in `JsonView` |
| Integer token length | 20 decimal digits maximum before Python integer conversion | Rust fields are `u32`, `usize`, `i32`, and `u64`; JSON parser does not impose this Devobs limit |
| Per-class count | 10,000,000 maximum | `Counts` uses `usize`; no 10,000,000 cap is declared upstream |
| Findings array | 10,000 elements maximum | The upstream field is a `Vec`; no 10,000 element cap is declared in `JsonView` |

Six accepted counters yield a maximum sum of 60,000,000, checked before output. The 10,000,000 limit is a conservative Devobs policy for a single-host report, not a product guarantee. It may reject a future or unusually large upstream report; confirm it against trusted producer data before integrating broadly. The tests use only synthetic report values.

## Unified validator flow

The sandbox Workflow previously carried a second Python implementation of JSON parsing and schema checks. The proposed local Workflow change removes that validator and calls `scripts/agentdust_readonly_adapter.py` in `--workflow-summary` mode. The adapter's existing `summarize_report` remains the only report-validation implementation. The workflow-summary mode emits only fixed CI fields and an allowlisted error code; it does not emit raw JSON, findings, paths, or Doctor stderr. Its own synthetic unit suite runs before the Doctor command.

The Workflow obtains the adapter and tests from the same event commit using the runner's preinstalled Git client, validates the expected repository/ref/SHA, and verifies the fetched SHA before use. It adds no GitHub Action, package, secret, or write permission. This requires read-only network access to the public Devobs repository; a fetch or SHA mismatch fails closed.

The existing Workflow trigger and permission block are preserved: `push` only on `test/agentdust-doctor-diagnostics`, filtered to changes at `.github/workflows/agentdust-doctor-sandbox.yml`, with `contents: read`. A push to `feature/agentdust-readonly-adapter` will not start this AgentDust Workflow. A later push to the diagnostics branch that changes the Workflow file will start it automatically and run the pre-existing isolated Doctor check. Because the current path filter names only the Workflow file, changes to the adapter alone do not start that run. No Workflow was run as part of this change.

## Trust boundary and remaining limits

Structural validation means only that the recognized report envelope fits Devobs' rules. It does not prove that a report came from AgentDust, that the npm package is authentic, that the report matches the current host, or that its contents authorize any action. Package provenance and source identity must be verified independently. The adapter remains read-only, performs no network access or subprocess execution, and is not an isolation boundary for its Python process.

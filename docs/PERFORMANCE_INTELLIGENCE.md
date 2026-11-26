# Devobs Performance Intelligence

**Status:** experimental local tooling; manual invocation only. This foundation
does not establish production performance, service readiness, or an automatic
release gate.

## Purpose and source provenance

The engine measures three existing, deterministic, offline Python operations:

| Stable benchmark ID | Existing operation | Synthetic workload |
| --- | --- | --- |
| `devobs.event_evidence.parse_events.v1` | `scripts/devobs_intelligence/contracts.py::parse_events` | Valid event envelopes with synthetic identifiers and digests |
| `devobs.task_graph.evaluate.v1` | `scripts/check_two_agent_tasks.py::evaluate` | A valid dependency chain and synthetic task manifest |
| `devobs.evaluation_splits.summarize.v1` | `scripts/devobs_intelligence/evaluation_splits.py::summarize_review_splits` | Opaque deterministic tokens and non-sensitive category labels |

The checked-in `tests/fixtures/performance/baseline.json` stores only bounded
workload sizes. It contains no timing values and is **not** a performance
baseline. The engine uses pyperf calibration, warmups, repeated measurements and
worker processes. It writes native pyperf JSON plus versioned Devobs summary
JSON and CSV under the operating system temporary directory.

The existing Graphify benchmark measures Graphify extraction and search; this
engine does not replace or duplicate that specialized interface. Existing
OpenTelemetry instrumentation also remains the telemetry interface; this phase
does not add exporters, metrics or background collection.

## pyperformance and upstream scope

**VERIFIED:** `hamedonassar95/pyperformance` is a fork of
[`python/pyperformance`](https://github.com/python/pyperformance). The fork
revision checked for this task is
[`286ace79124a337a64094b94b61511c96824472e`](https://github.com/hamedonassar95/pyperformance/commit/286ace79124a337a64094b94b61511c96824472e).
The [fork-to-parent comparison](https://github.com/hamedonassar95/pyperformance/compare/8a0713cfb4b76bd31336a88cf5b40a9a397991be...286ace79124a337a64094b94b61511c96824472e)
reports one changed file, `LICENSE`; no fork-specific runtime or benchmark
implementation was identified. The fork's license file records MIT. The
official [`psf/pyperf`](https://github.com/psf/pyperf)
package used here is also MIT licensed; Devobs consumes the pinned package and
does not copy its implementation.

The optional [pyperformance suite integration](PYPERFORMANCE_INTEGRATION.md)
adds a separate, manually invoked adapter for the pinned upstream source
revision. It does not copy upstream source into Devobs. The adapter verifies the
source archive SHA-256, accepts only a fixed list of reviewed workloads, uses an
exact hash-verified wheelhouse, disables package indexes during execution, and
places all temporary environments and reports outside the repository.

The upstream package is versioned `1.14.0` at the pinned source commit, while
PyPI's `1.14.0` release predates that commit. The adapter therefore records both
the package version and the exact verified upstream commit. The full suite is
**not** enabled: the current scope allows 50 reviewed standard-library
workloads. The pinned inventory covers all 75 upstream groups; 25 remain
deferred for missing dependency locks or workload-specific process, socket or
side-effect review. See the [complete workload audit](PYPERFORMANCE_WORKLOAD_AUDIT_2026-11-26.md).
`compile`, `compile_all`, `upload`, and venv removal are not exposed by the adapter.

| Capability in the upstream project | This Devobs phase |
| --- | --- |
| pyperf-based calibrated and repeated local timing | Implemented for the three named offline Devobs functions |
| pyperformance interpreter workload corpus | Optional pinned source integration; 50 reviewed benchmark groups can run offline, with 25 groups explicitly deferred |
| Full upstream workload corpus and third-party dependency set | Not enabled; deferred groups require separate dependency and side-effect review |
| Compare Python interpreter builds | Offline report comparison supports an explicit cross-version opt-in; each run still uses the current pinned environment and no arbitrary interpreter path is accepted |
| pyperf host tuning and hardware normalization helpers | Deliberately not automated; operator-controlled comparison guidance only |
| Fork-specific runtime additions | None found in the inspected fork-to-parent diff |

This is an optional adapter, not a wholesale fork or complete suite transfer.
The integration guide records the source revision, artifact digests, approved
workload subset, exact setup commands, limitations and next review steps.

## Dependency and installation

Performance tooling is separate from production and API dependencies:

- [`pyperf==2.11.0`](https://pypi.org/project/pyperf/2.11.0/) is the direct
  benchmark runner. Its published metadata requires Python 3.11 or newer and
  declares `psutil>=5.9.0` on non-Emscripten platforms.
- `psutil==7.2.2` is the exact resolved runtime dependency. Both packages and
  their supported release artifacts are hash-pinned in
  `requirements-performance.lock`.
- The lock hashes were checked against the official PyPI JSON release metadata;
  the pyperf wheel SHA-256 is
  `11c0034bb29a79796417a6e5a7852ff4814a33cce24aeb6d268676c3a52dfda6`.
- Devobs report schemas accept Python 3.12 and 3.15, matching the repository
  CI matrix. This environment has Python 3.12.14; Python 3.15 is not installed
  here, so the 3.15 execution path is **NOT RUN** even though pyperf's published
  metadata supports Python 3.11 and newer.

Create an isolated environment outside the repository, then install only the
hash-verified performance lock:

```sh
python3.12 -m venv /tmp/devobs-performance-venv
/tmp/devobs-performance-venv/bin/python -m pip install --require-hashes -r requirements-performance.lock
```

The exact mode options and pyperf command are visible without running a suite:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python -m performance_intelligence.benchmark_engine --help
```

## Manual execution

The default is a short smoke measurement:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python -m performance_intelligence.benchmark_engine --mode smoke
```

For a larger repeated-measurement collection:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python -m performance_intelligence.benchmark_engine --mode statistical
```

You can specify a directory under the system temporary directory. A path inside
the repository or outside the OS temporary directory is rejected. Existing
reports fail closed; replace them only by adding `--overwrite`:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python -m performance_intelligence.benchmark_engine --mode smoke --output-dir /tmp/devobs-performance --overwrite
```

The `smoke` preset uses one worker process, one warmup, three values and a
bounded execution timeout. It verifies that the suite can run; it is not
statistically useful for regression claims. The `statistical` preset uses five
worker processes, three warmups and twenty values per benchmark, with both a
per-worker timeout and a whole-run timeout. It collects stronger evidence but
does not itself establish statistical significance or comparability across
different machines. The pyperf Runner uses automatic loop calibration (`loops`
defaults to `0`).

The outer process uses an argument vector, never a shell, and kills its
process group on POSIX timeout. pyperf's worker timeout is also set. A failed,
timed-out, incomplete or invalid run produces no successful summary.
Source revision collection fails if the Git worktree is dirty. The engine does
not execute fixture text, call the network, read environment variables, or
invoke hosted services.

## Outputs and schema

Each invocation writes three files named with the 12-character source revision
prefix and measurement mode:

1. `.pyperf.json`: native pyperf JSON, converted with pyperf's documented
   `convert --remove-all-metadata` option to remove host, executable and other
   machine metadata while retaining benchmark names and values.
2. `.json`: Devobs summary schema version `1`.
3. `.csv`: one row per benchmark with the same safe metadata and summary values.

The summary schema is:

```json
{
  "schema_version": 1,
  "source_sha": "40 lowercase hexadecimal characters",
  "python_version": "3.12.0",
  "platform": "linux",
  "architecture": "x86_64",
  "measurement_mode": "smoke",
  "benchmarks": [
    {
      "benchmark_id": "devobs.event_evidence.parse_events.v1",
      "benchmark_name": "Parse synthetic event evidence",
      "mean_seconds": 0.01,
      "median_seconds": 0.01,
      "standard_deviation_seconds": 0.001,
      "sample_count": 3
    }
  ]
}
```

The example values above illustrate field types only; they are not benchmark
results. The writer rejects empty suites, unsupported schemas, missing or
unexpected metadata, non-finite or negative durations, fewer than two samples,
unsafe destinations and existing outputs without explicit overwrite consent.
Output metadata is allowlisted to source SHA, Python version, coarse platform,
architecture and mode. It excludes hostnames, paths, executable names,
environment dumps, credentials and customer data.

To inspect generated native data with the official CLI:

```sh
/tmp/devobs-performance-venv/bin/python -m pyperf check /tmp/devobs-performance/devobs-perf-<sha>-smoke.pyperf.json
/tmp/devobs-performance-venv/bin/python -m pyperf show /tmp/devobs-performance/devobs-perf-<sha>-smoke.pyperf.json
```

`check` and `show` are read-only inspection commands. See the official
[pyperf API](https://pyperf.readthedocs.io/en/latest/api.html),
[CLI reference](https://pyperf.readthedocs.io/en/latest/cli.html),
[user guide](https://pyperf.readthedocs.io/en/latest/user_guide.html),
[PyPI metadata](https://pypi.org/project/pyperf/2.11.0/),
[Python subprocess timeouts](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate),
and [pip hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/).
pyperf's per-worker `--timeout` option is implemented in the
[2.11.0 runner source](https://github.com/psf/pyperf/blob/2.11.0/pyperf/_runner.py#L187-L190).

## Memory, comparison, and local dashboard export

### Sampled Linux memory

The Devobs runner and the reviewed upstream adapter accept `--metric memory`
with either `--mode smoke` or `--mode statistical`. It is Linux-only and uses
pyperf 2.11.0 `--track-memory`. The pinned implementation samples
`/proc/self/smaps` about every 10 ms and adds `Private_Clean` and
`Private_Dirty`; the summary calls this `peak_private_bytes`. This is sampled
process-private memory, not RSS, total host memory, or a continuous system
metric. Sampling has overhead and can miss shorter peaks. Memory and execution
time are separate runs and must not be compared with each other. pyperf emits
one memory sample per worker process: Devobs memory smoke mode uses three
workers, and statistical mode uses twenty so its reports meet the comparison
minimum. The upstream adapter's pyperf fast/rigorous presets determine its
worker count independently.

Example Devobs run:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python \
  -m performance_intelligence.benchmark_engine \
  --mode smoke --metric memory --output-dir /tmp/devobs-performance
```

The upstream adapter takes the same metric option after `run`, alongside its
required verified source archive and hash-locked wheelhouse. It retains its
fixed allowlist and timeout boundaries.

Official implementation references checked on 2026-11-26: pyperf's
[`--track-memory` runner option](https://github.com/psf/pyperf/blob/2.11.0/pyperf/_runner.py)
and [Linux sampler](https://github.com/psf/pyperf/blob/2.11.0/pyperf/_linux_memory.py).

### Baseline/candidate comparisons

Comparison is an explicit offline command over two already-created JSON
summaries. It accepts only statistical reports with at least 20 samples per
benchmark, the same metric, suite/version, benchmark ID set, platform and
architecture. For upstream pyperformance reports it also requires the same
pinned upstream suite revision. The operator must confirm both runs used the
same physical host; Devobs cannot independently verify that claim. Different
Python versions require an additional explicit option:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python \
  -m performance_intelligence.comparison \
  /tmp/devobs-performance/baseline.json \
  /tmp/devobs-performance/candidate.json \
  --same-host-confirmed
```

For an intentional cross-version analysis, append
`--allow-python-version-change`. The output records whether the comparison is
`source_revision`, `python_version`, `mixed`, or `repeatability`. It reports a
two-sided Welch comparison, an unadjusted 95% confidence interval, and
Holm-adjusted p-values across benchmarks. The status labels are advisory only;
they are not an automatic regression gate. The model assumes independent
samples and cannot remove machine noise, interpreter build differences,
thermal changes, workload bias, or pyperf sample correlation. Identical input
report files are rejected so one report cannot be presented as two runs.
Comparison JSON and CSV are written to an OS temporary directory, without
overwriting existing output unless `--overwrite` is explicit.

To compare interpreter releases, run the same clean source SHA and statistical
mode once in each interpreter's isolated environment, with the same lock and
physical host. Use separate output directories because a report filename is
based on source revision and mode; then compare the two JSON summaries with the
explicit Python-version opt-in. Devobs does not select or install interpreters.
The report schema accepts Python 3.12 and 3.15 only; the 3.15 path is not
runtime-tested in this environment.

When source SHA and Python version are identical, a statistically significant
difference is labeled `REPEATABILITY_VARIATION`; it is not labeled an
improvement or regression because no code or interpreter change separates the
runs.

### Prometheus and Grafana

An explicit export converts one validated summary or comparison report into a
small Prometheus textfile. It writes the fixed ignored path
`monitoring/performance-metrics/devobs_performance.prom`; an existing file
requires `--overwrite`:

```sh
PYTHONPATH=scripts /tmp/devobs-performance-venv/bin/python \
  -m performance_intelligence.prometheus_export \
  /tmp/devobs-performance/<validated-report>.json
```

The file contains allowlisted benchmark IDs, source SHAs, Python versions,
measurement mode and numeric values only. It is written atomically with mode
`0644` so the existing Node Exporter process (UID 65534) can read it through a
read-only mount. It contains no customer inputs, local paths or hostnames. The
Node Exporter textfile collector is available only through the existing
optional `linux-host` monitoring profile. Use the local setup and rollback
steps in [`monitoring/README.md`](../monitoring/README.md). On Docker Desktop,
host metrics describe the Linux VM rather than the physical Windows/macOS host.
Prometheus scrapes the file; it does not launch or schedule benchmarks. The
dashboard panels describe manually exported local reports and are not live
service telemetry.

### Reproducibility and limitations

For comparisons, use the same Python patch version, platform and architecture,
power policy, machine class, workload fixture, mode, dependency lock and source
revision protocol. Avoid concurrent CPU-intensive work. Retain the source SHA
with reports. The engine does not pin CPU frequency, change system tuning, or
claim a comparable host from its metadata. Shared/virtualized hardware, thermal
state, operating system scheduling and Python build differences can change
results. A smoke run is only a functionality check. No timing threshold is used
in unit tests and this PR makes no performance-improvement claim.

## Rollback and future contract

Rollback is local and reversible: stop invoking the manual CLI and remove only
the generated report files from the chosen temporary directory. No application
runtime, CI workflow, service configuration, telemetry, database or release
gate depends on this package. Removing the optional venv is separate local
housekeeping.

Later, independently reviewed phases may define adapters for:

1. Linux memory allocation or RSS measurements with separate semantics from
   the current sampled private-memory metric;
2. reusable GitHub Actions workflows, only after workflow/security review;
3. deterministic performance recommendations; and
4. optional AI analysis with explicit human approval.

These are design targets, not implemented capabilities. No automatic jobs,
hosted AI, deployment action, or production performance gate is enabled by this
PR. The optional local memory, comparison and Prometheus textfile paths require
manual invocation. P01 remains NO-GO/BLOCKED, AI-9 remains BLOCKED and Codex
runtime acceptance remains OPEN.

### خلاصة بالعربية

هذا المحرك أداة محلية اختيارية وتشغيلها يدوي فقط. يقيس ثلاث وظائف موجودة
تستخدم بيانات اصطناعية، ويمكنه مقارنة تقارير إحصائية متوافقة، وقياس ذاكرة
خاصة مُعيّنة على Linux، وتصدير تقرير يدوي إلى جامع Prometheus المحلي الاختياري.
قياس `smoke` للتأكد من التشغيل ولا يثبت تحسناً أو تراجعاً. المقارنات استشارية
وليست بوابة إصدار. مجموعة pyperformance الكاملة لم تُفعّل: 50 من أصل 75 مجموعة
مراجعة ومسموحة، و25 مؤجلة لحين مراجعة الاعتماديات والآثار الجانبية.

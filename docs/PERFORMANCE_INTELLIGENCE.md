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
**not** enabled: the current scope allows only reviewed standard-library
workloads. Other benchmark dependencies and behaviors remain blocked pending
their own review; `compile`, `compile_all`, `upload`, and venv removal are not
exposed by the adapter.

| Capability in the upstream project | This Devobs phase |
| --- | --- |
| pyperf-based calibrated and repeated local timing | Implemented for the three named offline Devobs functions |
| pyperformance interpreter workload corpus | Optional pinned source integration; 8 reviewed benchmark groups can run offline |
| Full upstream workload corpus and third-party dependency set | Not enabled; each additional workload requires dependency and side-effect review |
| Run/compare across Python interpreter builds | pyperformance's upstream tools remain available only for separately reviewed local use; Devobs does not expose arbitrary interpreters |
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

## Reproducibility and limitations

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

1. optional pyperformance interpreter benchmarks and their dependency/data
   footprint;
2. Linux memory metrics;
3. baseline/candidate comparison and statistical regression detection;
4. reusable GitHub Actions workflows, only after workflow/security review;
5. deterministic performance recommendations;
6. optional AI analysis with explicit human approval; and
7. Prometheus/Grafana reporting through existing telemetry interfaces.

These are design targets, not implemented capabilities. No automatic jobs,
telemetry exporter, hosted AI, deployment action, or production performance gate
is enabled by this PR. P01 remains NO-GO/BLOCKED, AI-9 remains BLOCKED and Codex
runtime acceptance remains OPEN.

### خلاصة بالعربية

هذا المحرك أداة محلية اختيارية وتشغيلها يدوي فقط. يقيس ثلاث وظائف موجودة
تستخدم بيانات اصطناعية، ولا يتصل بخدمات مباشرة ولا يغيّر إعدادات الإنتاج أو
CI. قياس `smoke` للتأكد من التشغيل فقط ولا يثبت تحسناً أو تراجعاً. مجموعة
pyperformance الكاملة لم تُنقل في هذه المرحلة؛ المقارنة أثبتت أن نسخة fork لا
تضيف ميزة تنفيذية خاصة، ودمج اختبارات المفسّر مؤجل إلى مرحلة مستقلة ومراجعة.

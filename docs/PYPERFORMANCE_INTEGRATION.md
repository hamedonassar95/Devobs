# Optional pyperformance integration

**Status:** local experimental tooling; manual invocation only. The adapter is
not a CI job, production performance gate, deployment mechanism or performance
claim. It supplements the three Devobs-specific benchmarks in
[`PERFORMANCE_INTELLIGENCE.md`](PERFORMANCE_INTELLIGENCE.md) and does not alter
application runtime dependencies.

## Provenance and current upstream state

The user's [`hamedonassar95/pyperformance` fork](https://github.com/hamedonassar95/pyperformance)
is a fork of [`python/pyperformance`](https://github.com/python/pyperformance).
At the time of this review, the fork had one fork-only `LICENSE` change and was
nine upstream commits behind. The fork-only change adds no benchmark runner or
workload implementation. Devobs therefore consumes the official upstream
source without copying it.

The pinned upstream commit is
[`c3550b5bae544706a4541234a05ea105de5f9984`](https://github.com/python/pyperformance/commit/c3550b5bae544706a4541234a05ea105de5f9984),
dated 2026-11-24 and marked signature-verified by GitHub. That source reports
package version `1.14.0`. PyPI's `1.14.0` release was uploaded on 2026-02-07,
so a version string alone would not identify the reviewed source. Devobs pins
the upstream source archive by SHA-256:

```text
910a21415b63ddad748025bbb148b0c2e78f39927e6d3fdcbee7d76d750cb249
```

The exact URL and digest are recorded in
[`requirements-performance-suite-source.lock`](../requirements-performance-suite-source.lock)
and in the adapter contract. The archive is checked before extraction; archive
paths are constrained and links are rejected except for two known top-level
development convenience links, which are intentionally omitted. Runtime
benchmark code comes from the verified archive, not this repository.

### Official references checked on 2026-11-26

- [Upstream usage guide at the pinned commit](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/doc/usage.rst)
- [Pinned upstream project metadata](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyproject.toml)
- [Pinned upstream runtime requirements](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/requirements/requirements.txt)
- [Official PyPI release metadata for pyperformance 1.14.0](https://pypi.org/project/pyperformance/1.14.0/)
- [Official pyperf 2.11.0 release](https://pypi.org/project/pyperf/2.11.0/)
- [pyperf CLI documentation](https://pyperf.readthedocs.io/en/latest/cli.html) and [API documentation](https://pyperf.readthedocs.io/en/latest/api.html)
- [pip hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/)
- [Python subprocess timeout behavior](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate)

The current PyPI versions verified for this integration were `pyperformance`
1.14.0, `pyperf` 2.11.0, `packaging` 26.4, `psutil` 7.2.2, `setuptools`
84.2.1 and `wheel` 0.48.0. The runtime versions are pinned in
[`requirements-performance-suite.lock`](../requirements-performance-suite.lock);
the temporary-venv installation tools are pinned in
[`requirements-performance-suite-toolchain.lock`](../requirements-performance-suite-toolchain.lock).
These dependencies are optional and separate from production requirements.

## Workload scope

The adapter accepts only these upstream workload groups, inspected at the
pinned commit. Their `pyproject.toml` files require `pyperf` and no other
per-benchmark package; their code uses Python's standard library and fixed or
seeded benchmark inputs.

| Upstream group and source | Output measurements | Input / behavior reviewed |
| --- | --- | --- |
| [`base64`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_base64/run_benchmark.py) | 11 encode/decode cases | Fixed-seed deterministic byte inputs |
| [`float`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_float/run_benchmark.py) | `float` | Deterministic artificial numeric workload |
| [`json_dumps`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_json_dumps/run_benchmark.py) | `json_dumps` | Fixed synthetic dictionaries and lists |
| [`json_loads`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_json_loads/run_benchmark.py) | `json_loads` | Fixed-seed synthetic objects |
| [`regex_compile`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_regex_compile/run_benchmark.py) | `regex_compile` | Fixed regular-expression patterns |
| [`regex_dna`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_regex_dna/run_benchmark.py) | `regex_dna` | Deterministically generated sequence inputs |
| [`regex_effbot`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_regex_effbot/run_benchmark.py) | `regex_effbot` | Fixed benchmark strings and expressions |
| [`regex_v8`](https://github.com/python/pyperformance/blob/c3550b5bae544706a4541234a05ea105de5f9984/pyperformance/data-files/benchmarks/bm_regex_compile/bm_regex_v8.py) | `regex_v8` | Static benchmark patterns; no network access |

The allowlist is enforced in code and reports. Users cannot pass arbitrary
benchmark names, manifests, source paths, Python executables, or shell commands.
Smoke mode can run the approved set or a subset. Statistical mode requires an
explicit selection of at most three groups to stay within the outer timeout.

The full upstream suite remains **not enabled**. Some workloads have third-party
requirements, external binaries, server or socket behavior, large data files,
or more complex build steps. Each one must be inspected and added to a new
reviewed dependency lock before it can run offline. The adapter does not expose
`compile`, `compile_all`, `upload`, arbitrary `show`/`compare` paths, or venv
creation/recreation/removal. `pyperformance`'s default suite setup can install
per-benchmark requirements, so running its unrestricted command is outside this
integration's safety contract.

## Offline and execution controls

- Manual command only. No workflow, schedule, daemon, background service or
  automatic performance recommendation is added.
- Python 3.12 and POSIX are required by this adapter version.
- The exact official archive and each wheel are SHA-256 verified.
- `PIP_NO_INDEX=1`, a validated local wheelhouse, disabled pip configuration,
  and an explicit child environment prevent network package resolution and
  parent environment leakage during execution.
- The adapter launches fixed argument vectors with `shell=False`, sets the
  target interpreter to the current pinned Python, caps worker and whole-suite
  timeouts, and terminates the process group on timeout.
- Source archive, extracted suite, temporary venvs, raw results and final
  reports stay outside the repository under the system temporary directory.
- The worktree must be clean. Reports contain only source revisions, suite
  identity, Python version, coarse platform/architecture, mode, safe benchmark
  IDs and validated timing values. No paths, hostnames, environment variables,
  credentials or customer data are emitted.
- Existing output files are never overwritten unless the operator supplies
  `--overwrite`.

## Installation and use

Create an isolated environment and fetch the exact source archive plus local
wheelhouse. These setup commands download only SHA-256-pinned artifacts. The
adapter verifies the source archive again and checks each wheel before taking a
private copy. During benchmark execution, package indexes are disabled; missing
artifacts make the run fail closed.

```sh
python3.12 -m venv /tmp/devobs-pyperformance-venv
mkdir -m 700 -p /tmp/devobs-pyperformance-source /tmp/devobs-pyperformance-wheelhouse
/tmp/devobs-pyperformance-venv/bin/python -m pip install \
  --require-hashes --only-binary=:all: \
  -r requirements-performance-suite-toolchain.lock
/tmp/devobs-pyperformance-venv/bin/python -m pip download \
  --no-deps --no-build-isolation --require-hashes \
  --dest /tmp/devobs-pyperformance-source \
  -r requirements-performance-suite-source.lock
/tmp/devobs-pyperformance-venv/bin/python -m pip download \
  --require-hashes --only-binary=:all: \
  --dest /tmp/devobs-pyperformance-wheelhouse \
  -r requirements-performance-suite-toolchain.lock
```

Run one short bounded smoke workload:

```sh
PYTHONPATH=scripts /tmp/devobs-pyperformance-venv/bin/python \
  -m performance_intelligence.pyperformance_adapter run \
  --mode smoke --benchmark float \
  --source-archive /tmp/devobs-pyperformance-source/c3550b5bae544706a4541234a05ea105de5f9984 \
  --wheelhouse /tmp/devobs-pyperformance-wheelhouse \
  --output-dir /tmp/devobs-pyperformance-results
```

For stronger local measurements, explicitly choose up to three approved groups:

```sh
PYTHONPATH=scripts /tmp/devobs-pyperformance-venv/bin/python \
  -m performance_intelligence.pyperformance_adapter run \
  --mode statistical --benchmark float,json_dumps \
  --source-archive /tmp/devobs-pyperformance-source/c3550b5bae544706a4541234a05ea105de5f9984 \
  --wheelhouse /tmp/devobs-pyperformance-wheelhouse \
  --output-dir /tmp/devobs-pyperformance-results
```

`smoke` uses upstream `--fast` and verifies that the integration works. It is
not statistically useful evidence. `statistical` uses upstream `--rigorous`,
but remains sensitive to machine load, power policy, thermal state, OS
scheduling and interpreter build. Neither mode automatically compares a
baseline or claims a regression/improvement.

## Reports

Each completed run writes three files, named with the Devobs source SHA and
measurement mode:

1. `*.pyperf.json`: native pyperf JSON converted with
   `--remove-all-metadata`, normalized to an allowlisted report shape, then
   checked with `python -m pyperf check`. The normalization accommodates
   pyperf's single-benchmark and multi-benchmark name placement while keeping
   only the benchmark name, time unit, samples and warmups.
2. `*.json`: Devobs summary schema version 1.
3. `*.csv`: one row per approved output measurement.

The summary includes `source_sha`, `suite_name`, `suite_version`,
`suite_source_sha`, `python_version`, `platform`, `architecture`,
`measurement_mode`, and for each benchmark its namespaced ID, mean, median,
standard deviation and sample count. Values are derived from the native pyperf
samples; this guide contains no fabricated timings. Reports reject empty or
incomplete suites, invalid or non-finite values, unexpected metadata, schema
mismatches and overwrite attempts.

Use pyperf's documented read-only inspection commands on generated native JSON:

```sh
/tmp/devobs-pyperformance-venv/bin/python -m pyperf check \
  /tmp/devobs-pyperformance-results/devobs-pyperformance-<sha>-smoke.pyperf.json
/tmp/devobs-pyperformance-venv/bin/python -m pyperf show \
  /tmp/devobs-pyperformance-results/devobs-pyperformance-<sha>-smoke.pyperf.json
```

The suite's upstream compare/show features remain available for later deliberate
local analysis, but the adapter does not accept arbitrary report paths or
baseline files. Baseline/candidate comparison and regression policy need a
separate schema and review.

## Future integrations and rollback

The following stay planned: audit and lock the remaining upstream workloads;
baseline/candidate comparison; statistical regression detection; Linux memory
metrics; reusable CI workflows; deterministic recommendations; optional AI
analysis with human approval; and Prometheus/Grafana reporting through existing
telemetry interfaces. This change adds no OpenTelemetry duplicate, workflow,
scheduled job, external AI call or production gate.

Rollback is local: stop invoking the adapter and remove the optional temporary
environment, wheelhouse, source archive and reports using ordinary local
housekeeping. No application service, CI job, deployment, database or release
gate depends on these files. P01 remains BLOCKED, AI-9 remains BLOCKED and
Codex runtime acceptance remains OPEN.

### بالعربية

أضفنا تكاملًا اختياريًا ومحدودًا مع `pyperformance` الرسمي. يعمل يدويًا فقط،
ويقبل ثماني مجموعات فُحصت عند commit محدد، ويتحقق من SHA للمصدر والعجلات، ويمنع
اتصال pip بالشبكة أثناء القياس. لا نشغّل بقية المجموعة الكاملة لأن بعض اختبارات
المصدر تحتاج حزمًا أو أدوات أو سلوكًا لم يُراجع بعد. لا يتغير تشغيل التطبيق أو
CI، وقياس `smoke` لا يثبت تحسنًا. يلزم مراجعة مستقلة قبل توسيع القائمة أو ربط
النتائج ببوابات الإصدار.

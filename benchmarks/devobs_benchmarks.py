"""pyperf entry point; runs only fixed synthetic offline workloads."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pyperf  # noqa: E402

from performance_intelligence.benchmark_engine import benchmark_definitions  # noqa: E402


def main() -> None:
    runner = pyperf.Runner()
    for benchmark in benchmark_definitions():
        runner.bench_func(benchmark.benchmark_id, benchmark.run)


if __name__ == "__main__":
    main()

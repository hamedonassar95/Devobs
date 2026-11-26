"""Immutable provenance and reviewed workload scope for the upstream adapter."""

PY_PERFORMANCE_VERSION = "1.14.0"
PY_PERFORMANCE_COMMIT = "c3550b5bae544706a4541234a05ea105de5f9984"
PY_PERFORMANCE_ARCHIVE_SHA256 = "910a21415b63ddad748025bbb148b0c2e78f39927e6d3fdcbee7d76d750cb249"
PY_PERFORMANCE_ARCHIVE_URL = (
    "https://codeload.github.com/python/pyperformance/tar.gz/"
    f"{PY_PERFORMANCE_COMMIT}"
)

# Every entry below was inspected at the pinned source commit. These workloads
# have no per-benchmark requirements beyond the pinned pyperf runtime and use
# deterministic/std-library inputs. The remaining upstream corpus is inventory
# only until each dependency and side effect is separately reviewed.
SAFE_BENCHMARK_OUTPUTS = {
    "base64": (
        "base64_small", "base64_large", "urlsafe_base64_small", "base32_small",
        "base32_large", "base16_small", "base16_large", "ascii85_small",
        "ascii85_large", "base85_small", "base85_large",
    ),
    "float": ("float",),
    "json_dumps": ("json_dumps",),
    "json_loads": ("json_loads",),
    "regex_compile": ("regex_compile",),
    "regex_dna": ("regex_dna",),
    "regex_effbot": ("regex_effbot",),
    "regex_v8": ("regex_v8",),
}
SAFE_BENCHMARK_NAMES = frozenset(SAFE_BENCHMARK_OUTPUTS)
OUTPUT_NAMES = frozenset(name for names in SAFE_BENCHMARK_OUTPUTS.values() for name in names)

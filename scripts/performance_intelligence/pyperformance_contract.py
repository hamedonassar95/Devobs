"""Immutable provenance and reviewed workload scope for the upstream adapter."""

import hashlib
import json
import re
from pathlib import Path

PY_PERFORMANCE_VERSION = "1.14.0"
PY_PERFORMANCE_COMMIT = "c3550b5bae544706a4541234a05ea105de5f9984"
PY_PERFORMANCE_ARCHIVE_SHA256 = "910a21415b63ddad748025bbb148b0c2e78f39927e6d3fdcbee7d76d750cb249"
PY_PERFORMANCE_ARCHIVE_URL = (
    "https://codeload.github.com/python/pyperformance/tar.gz/"
    f"{PY_PERFORMANCE_COMMIT}"
)

INVENTORY_PATH = Path(__file__).with_name("pyperformance_workload_inventory.json")


def _load_reviewed_inventory() -> dict[str, tuple[str, ...]]:
    """Load the reviewed, pinned-source inventory and fail closed on drift."""
    try:
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        if (not isinstance(inventory, dict)
                or inventory.get("schema_version") != 1
                or inventory.get("upstream_commit") != PY_PERFORMANCE_COMMIT
                or inventory.get("upstream_archive_sha256") != PY_PERFORMANCE_ARCHIVE_SHA256
                or inventory.get("benchmark_group_count") != 75
                or not isinstance(inventory.get("groups"), list)
                or len(inventory["groups"]) != 75):
            raise ValueError
        reviewed: dict[str, tuple[str, ...]] = {}
        seen: set[str] = set()
        for group in inventory["groups"]:
            if not isinstance(group, dict):
                raise ValueError
            name = group.get("name")
            status = group.get("status")
            outputs = group.get("outputs")
            dependencies = group.get("declared_dependencies")
            undeclared = group.get("undeclared_runtime_dependencies")
            if (not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_]*", name)
                    or name in seen
                    or status not in {"INTEGRATED", "DEFERRED"}
                    or not isinstance(outputs, list)
                    or not isinstance(dependencies, list)
                    or any(not isinstance(item, str) for item in dependencies)
                    or not isinstance(undeclared, list)
                    or any(not isinstance(item, str) for item in undeclared)):
                raise ValueError
            seen.add(name)
            if status == "INTEGRATED":
                if (dependencies or undeclared or not outputs
                        or any(not isinstance(item, str)
                               or not re.fullmatch(r"[a-z][a-z0-9_]*", item)
                               for item in outputs)
                        or len(set(outputs)) != len(outputs)):
                    raise ValueError
                reviewed[name] = tuple(outputs)
            elif outputs:
                raise ValueError
        if len(seen) != 75 or [group["name"] for group in inventory["groups"]] != sorted(seen):
            raise ValueError
        catalog_digest = hashlib.sha256(
            ("\n".join(group["name"] for group in inventory["groups"]) + "\n").encode("utf-8")
        ).hexdigest()
        if catalog_digest != inventory.get("catalog_names_sha256"):
            raise ValueError
        flattened = [output for outputs in reviewed.values() for output in outputs]
        if len(flattened) != len(set(flattened)):
            raise ValueError
        return reviewed
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        raise RuntimeError("pyperformance_workload_inventory_invalid") from None


# Only groups that have no undeclared or additional package dependencies and
# whose fixed input and side-effect profile were reviewed can execute.
SAFE_BENCHMARK_OUTPUTS = _load_reviewed_inventory()
SAFE_BENCHMARK_NAMES = frozenset(SAFE_BENCHMARK_OUTPUTS)
OUTPUT_NAMES = frozenset(name for names in SAFE_BENCHMARK_OUTPUTS.values() for name in names)

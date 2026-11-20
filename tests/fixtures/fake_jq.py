"""Fail-closed jq subset used by offline site health-check tests.

Only the expressions present in ``scripts/check_vercel_site.sh`` are accepted.
An unknown filter is an error, so a workflow change cannot silently pass while
being tested against a stale fixture.
"""

from __future__ import annotations

import json
import re
import sys
from typing import TextIO

CONTRACT_SHAPE_FILTER = (
    '.required_text_any | type == "array" and length > 0 '
    'and all(.[]; type == "string" and length > 0)'
)
CONTRACT_MARKER_FILTER = '.required_text_any | index("Devobs") != null'
CONTRACT_ITEMS_FILTER = ".required_text_any[]"
CONTRACT_JSON_FILTER = ".required_text_any"
MANIFEST_SHA_FILTER = (
    'select(.schema_version == 1) | .source_sha | select(test("^[0-9a-f]{40}$"))'
)
FILTER_EXPRESSIONS = (
    CONTRACT_SHAPE_FILTER,
    CONTRACT_MARKER_FILTER,
    CONTRACT_ITEMS_FILTER,
    CONTRACT_JSON_FILTER,
    MANIFEST_SHA_FILTER,
)


def _normalize_filter(filter_expression: str) -> str:
    return re.sub(r"\s+", " ", filter_expression).strip()


def _evaluate(filter_expression: str, value: object) -> list[object] | None:
    normalized = _normalize_filter(filter_expression)
    required = value.get("required_text_any") if isinstance(value, dict) else None
    if normalized == _normalize_filter(CONTRACT_SHAPE_FILTER):
        valid = (
            isinstance(required, list)
            and bool(required)
            and all(isinstance(item, str) and bool(item) for item in required)
        )
        return [valid]
    if normalized == _normalize_filter(CONTRACT_MARKER_FILTER):
        return ["Devobs" in required] if isinstance(required, list) else [False]
    if normalized == _normalize_filter(CONTRACT_ITEMS_FILTER):
        return list(required) if isinstance(required, list) else []
    if normalized == _normalize_filter(CONTRACT_JSON_FILTER):
        return [required] if isinstance(required, list) else []
    if normalized == _normalize_filter(MANIFEST_SHA_FILTER):
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            return []
        sha = value.get("source_sha")
        if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha):
            return [sha]
        return []
    return None


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("missing jq arguments", file=err)
        return 2

    flags = ""
    if args[0].startswith("-"):
        flags = args.pop(0)[1:]
        if any(flag not in "erc" for flag in flags):
            print("unsupported jq flag", file=err)
            return 2
    if len(args) != 2:
        print("missing jq filter or file", file=err)
        return 2
    filter_expression, path = args
    try:
        with open(path, encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"invalid jq input: {type(exc).__name__}", file=err)
        return 2

    results = _evaluate(filter_expression, value)
    if results is None:
        print(f"unsupported jq filter: {filter_expression}", file=err)
        return 2
    if not results:
        return 4 if "e" in flags else 0

    for result in results:
        if "c" in flags:
            print(json.dumps(result, separators=(",", ":")), file=out)
        elif "r" in flags and isinstance(result, str):
            print(result, file=out)
        else:
            print(json.dumps(result), file=out)
    if "e" in flags and not any(bool(result) for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

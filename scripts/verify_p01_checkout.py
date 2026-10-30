#!/usr/bin/env python3
"""Fail closed unless P01 evidence checks target the exact checked-out main SHA.

Offline guard only: this does not authenticate evidence or authorize deployment.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_MAIN_REF = "refs/heads/main"


class InvalidCheckout(ValueError):
    """Non-sensitive reason that P01 evidence review must stop."""


def verify(expected_sha: str, checkout_sha: str, event_ref: str) -> None:
    """Require an exact, lowercase SHA from a main-branch dispatch."""
    if type(expected_sha) is not str or _SHA.fullmatch(expected_sha) is None:
        raise InvalidCheckout("invalid requested source SHA")
    if event_ref != _MAIN_REF:
        raise InvalidCheckout("workflow must run from main")
    if type(checkout_sha) is not str or _SHA.fullmatch(checkout_sha) is None:
        raise InvalidCheckout("invalid checked-out commit SHA")
    if checkout_sha != expected_sha:
        raise InvalidCheckout("reviewed SHA differs from checked-out commit")



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--checkout-sha", required=True)
    args = parser.parse_args(argv)
    try:
        # Read GITHUB_REF rather than trusting a caller-provided branch name.
        verify(args.expected_sha, args.checkout_sha, os.environ.get("GITHUB_REF", ""))
    except InvalidCheckout as exc:
        print(f"P01 CHECKOUT NO-GO: {exc}", file=sys.stderr)
        return 1
    print("P01 checkout: exact main SHA verified; evidence still requires independent review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

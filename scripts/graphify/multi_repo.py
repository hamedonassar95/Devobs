#!/usr/bin/env python3
"""CLI entry point for centralized offline Graphify multi-repo orchestration."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.graphify.multi_repo import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

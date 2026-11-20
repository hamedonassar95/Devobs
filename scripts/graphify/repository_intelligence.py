#!/usr/bin/env python3
"""CLI entry point for local Repository Intelligence.

Run from any directory; use absolute source/output paths for clarity. See
``docs/architecture/graphify-integration.md`` for the verified capability
boundary and the required external output-root layout.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify.repository_intelligence import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

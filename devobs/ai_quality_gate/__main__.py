"""Allow ``python -m devobs.ai_quality_gate`` to run the advisory CLI."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
docs/scripts/validate-ssot-roots.py

Canonical entrypoint for validating SSOT root placement rules.

This script delegates to the governance validator under docs/scripts/_ia/,
keeping a stable, short path for humans and automation.

Exit codes:
  0 = OK
  1 = Execution/config error
  2 = SSOT root policy violation
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    delegate = repo_root / "docs" / "scripts" / "_ia" / "validators" / "validate-ssot-roots.py"

    if not delegate.exists():
        print(f"[ERROR] Delegate validator not found: {delegate}", file=sys.stderr)
        return 1

    # Execute delegate as __main__ to preserve its CLI contract.
    sys.path.insert(0, str(delegate.parent))
    runpy.run_path(str(delegate), run_name="__main__")
    return 0  # delegate exits via SystemExit; this is a fallback.


if __name__ == "__main__":
    raise SystemExit(main())

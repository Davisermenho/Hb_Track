#!/usr/bin/env python3
"""
HB Track — render_policy_md.py (CANONICAL GENERATOR)

SSOT -> DERIVED MD generator.
Uses policy_lib for all deterministic rendering logic.

Reads:
  - scripts/_policy/scripts.policy.yaml (SSOT)
Validates:
  - scripts/_policy/scripts.policy.schema.json (JSON Schema)
Renders (DERIVED):
  - docs/_canon/_agent/SCRIPTS_classification.md

Determinism goals:
  - stable ordering (by policy_lib)
  - stable whitespace (LF normalized)
  - no timestamps in MD (only in manifest)
  - deterministic exit codes

Exit codes:
  0 = OK
  2 = POLICY_INVALID
  3 = HARNESS_ERROR

Version: 1.0.0 (canonical generator)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import centralized policy library
try:
    from policy_lib import load_policy, render_derived_md, DERIVED_MD_RELPATH
except ImportError:
    # Fallback for direct execution
    import os
    sys.path.insert(0, str(Path(__file__).parent))
    from policy_lib import load_policy, render_derived_md, DERIVED_MD_RELPATH


def main() -> int:
    """
    Canonical generator entrypoint.
    Loads policy, renders MD, writes to DERIVED location.
    """
    repo_root = Path().cwd().resolve()

    # Use canonical DERIVED path from policy_lib
    out_md_path = repo_root / DERIVED_MD_RELPATH

    # Allow overriding output path for testing
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 < len(sys.argv):
            out_md_path = Path(sys.argv[idx + 1]).resolve()

    try:
        # Load and validate policy (policy_lib handles all validation)
        policy = load_policy(repo_root)

        # Render deterministic MD
        md = render_derived_md(policy)

        # Write to DERIVED location (deterministic: UTF-8, LF)
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_md_path.write_text(md, encoding="utf-8", newline="\n")

        print(f"[OK] Rendered: {out_md_path}")
        return 0

    except FileNotFoundError as e:
        print(f"[HARNESS_ERROR] {e}")
        return 3
    except ValueError as e:
        print(f"[POLICY_INVALID] {e}")
        return 2
    except Exception as e:
        print(f"[HARNESS_ERROR] {type(e).__name__}: {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

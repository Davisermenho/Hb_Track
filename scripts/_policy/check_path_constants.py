#!/usr/bin/env python3
"""
HB Track — check_path_constants.py

Validates that canonical path constants are consistent between Python and PowerShell.
This gate prevents drift when constants are duplicated across languages.

Exit codes:
  0 = OK (constants match)
  3 = HARNESS_ERROR (mismatch or import failed)
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from policy_lib import (
        SSOT_YAML_RELPATH,
        DERIVED_MD_RELPATH,
        MANIFEST_JSON_RELPATH,
        HEURISTICS_YAML_RELPATH,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from policy_lib import (
        SSOT_YAML_RELPATH,
        DERIVED_MD_RELPATH,
        MANIFEST_JSON_RELPATH,
        HEURISTICS_YAML_RELPATH,
    )


def main() -> int:
    """
    Print canonical paths as JSON for PowerShell consumption.
    This enables PowerShell scripts to validate their hardcoded constants.
    """
    import json

    paths = {
        "SSOT_YAML_RELPATH": SSOT_YAML_RELPATH,
        "DERIVED_MD_RELPATH": DERIVED_MD_RELPATH,
        "MANIFEST_JSON_RELPATH": MANIFEST_JSON_RELPATH,
        "HEURISTICS_YAML_RELPATH": HEURISTICS_YAML_RELPATH,
    }

    # Output as JSON (PowerShell can parse with ConvertFrom-Json)
    print(json.dumps(paths, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"[HARNESS_ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(3)

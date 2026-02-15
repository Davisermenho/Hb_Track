#!/usr/bin/env python3
"""
HB Track — generate_manifest.py

Generates policy.manifest.json with file hashes and metadata.

Exit codes:
  0 = OK
  3 = HARNESS_ERROR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import policy_lib
try:
    from policy_lib import generate_manifest, MANIFEST_JSON_RELPATH
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from policy_lib import generate_manifest, MANIFEST_JSON_RELPATH


def main() -> int:
    """Generate and write policy manifest."""
    repo_root = Path().cwd().resolve()
    manifest_path = repo_root / MANIFEST_JSON_RELPATH

    try:
        manifest = generate_manifest(repo_root)
        
        # Write manifest (pretty JSON)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.write("\n")  # Final newline

        print(f"[OK] Generated manifest: {manifest_path}")
        print(f"     Schema version: {manifest['schema_version']}")
        print(f"     Generated: {manifest['generated_utc']}")
        return 0

    except Exception as e:
        print(f"[HARNESS_ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

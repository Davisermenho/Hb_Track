#!/usr/bin/env python3
#
# HB Track — gen_scripts_policy_md.py (WRAPPER FOR COMPATIBILITY)
#
# HB_SCRIPT_KIND: generate
# HB_SCRIPT_SCOPE: docs
# HB_SCRIPT_SIDE_EFFECTS: filesystem_write,process_spawn
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: main()
# HB_SCRIPT_OUTPUTS: docs/_canon/_agent/SCRIPTS_classification.md
#
"""
DEPRECATED: This file is now a compatibility wrapper.
The canonical generator is scripts/_policy/render_policy_md.py

This wrapper preserves CLI compatibility:
  python scripts/generate/docs/gen_scripts_policy_md.py --check
  python scripts/generate/docs/gen_scripts_policy_md.py --write

All logic is delegated to the canonical generator.

Exit codes:
  0 = OK
  2 = POLICY_INVALID or DRIFT
  3 = HARNESS_ERROR

Version: 1.0.0 (wrapper)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_ERROR = 3


def main() -> int:
    """
    Compatibility wrapper: delegates to canonical generator.
    
    --check: render to temp, compare with existing
    --write: render and write to canonical location
    """
    repo_root = Path(__file__).resolve().parents[3]  # go up from scripts/generate/docs/ to repo root
    canonical_generator = repo_root / "scripts" / "_policy" / "render_policy_md.py"
    derived_path = repo_root / "docs" / "_canon" / "_agent" / "SCRIPTS_classification.md"

    # Print canonical generator info for debugging
    print(f"[WRAPPER] CANONICAL_GENERATOR={canonical_generator.relative_to(repo_root)}", file=sys.stderr)

    # Check arguments
    if "--check" in sys.argv:
        mode = "check"
    elif "--write" in sys.argv:
        mode = "write"
    else:
        print("[ERROR] Usage: gen_scripts_policy_md.py (--check | --write)", file=sys.stderr)
        print("[INFO] This is a compatibility wrapper for scripts/_policy/render_policy_md.py", file=sys.stderr)
        return EXIT_ERROR

    try:
        if not canonical_generator.exists():
            print(f"[HARNESS_ERROR] Canonical generator not found: {canonical_generator}", file=sys.stderr)
            return EXIT_ERROR

        if mode == "write":
            # Delegate to canonical generator
            result = subprocess.run(
                [sys.executable, str(canonical_generator)],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            
            # Pass through output
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            
            return result.returncode

        elif mode == "check":
            # Render to temp file and compare
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp_path = Path(tmp.name)

            try:
                # Generate to temp
                result = subprocess.run(
                    [sys.executable, str(canonical_generator), "--out", str(tmp_path)],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    print(f"[ERROR] Canonical generator failed:", file=sys.stderr)
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)
                    return result.returncode

                # Compare
                if not derived_path.exists():
                    print(f"[FAIL] Derived MD missing: {derived_path}", file=sys.stderr)
                    return EXIT_FAIL

                current = derived_path.read_text(encoding="utf-8")
                generated = tmp_path.read_text(encoding="utf-8")

                # Normalize EOL for comparison
                current_norm = current.replace("\r\n", "\n").replace("\r", "\n")
                generated_norm = generated.replace("\r\n", "\n").replace("\r", "\n")

                if current_norm == generated_norm:
                    print("[OK] Derived MD is up-to-date")
                    return EXIT_PASS
                else:
                    print(f"[FAIL] Derived MD has drift. Run with --write to update:", file=sys.stderr)
                    print(f"  python scripts/generate/docs/gen_scripts_policy_md.py --write", file=sys.stderr)
                    print(f"  (or use canonical: python scripts/_policy/render_policy_md.py)", file=sys.stderr)
                    return EXIT_FAIL

            finally:
                tmp_path.unlink(missing_ok=True)

    except Exception as e:
        print(f"[HARNESS_ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

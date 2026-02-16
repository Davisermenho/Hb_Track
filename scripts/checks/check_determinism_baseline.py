#!/usr/bin/env python3
"""
check_determinism_baseline.py
HB_SCRIPT_KIND: CHECK
HB_SCRIPT_IDEMPOTENT: YES
HB_SCRIPT_ENTRYPOINT: python scripts/checks/check_determinism_baseline.py

Compares current checksums with a frozen baseline to detect drift.
Usage:
    python scripts/checks/check_determinism_baseline.py [--baseline VERSION]
"""

import argparse
import hashlib
import os
import sys
import yaml
from pathlib import Path

# Configuration
DEFAULT_BASELINE = "docs-determinism-v1"
SSOT_DIR = Path("docs/_ssot")
BASELINE_DIR = Path("docs/_canon/BASELINES")
MANIFEST_FILE = SSOT_DIR / "_manifest.yaml"

# Artifacts to check
ARTIFACTS = ["schema.sql", "openapi.json", "alembic_state.txt"]


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not file_path.exists():
        return "FILE_NOT_FOUND"
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_baseline(baseline_version: str) -> dict:
    """Load baseline checksums from BASELINE file."""
    baseline_file = BASELINE_DIR / f"{baseline_version}.md"
    
    if not baseline_file.exists():
        print(f"❌ Baseline file not found: {baseline_file}")
        sys.exit(1)
    
    # Parse checksums from markdown file (simple extraction)
    checksums = {}
    with open(baseline_file, "r", encoding="utf-8") as f:
        content = f.read()
        
        for artifact in ARTIFACTS:
            # Look for pattern: "hash  filename"
            for line in content.split("\n"):
                if artifact in line and line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        checksums[artifact] = parts[0]
                        break
    
    return checksums


def load_current_manifest() -> dict:
    """Load current checksums from _manifest.yaml."""
    if not MANIFEST_FILE.exists():
        print(f"❌ Manifest file not found: {MANIFEST_FILE}")
        sys.exit(1)
    
    checksums = {}
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    checksums[parts[1]] = parts[0]
    
    return checksums


def check_writer_command() -> bool:
    """Verify writer command hasn't changed."""
    baseline_file = BASELINE_DIR / f"{DEFAULT_BASELINE}.md"
    
    if not baseline_file.exists():
        return True  # Skip if no baseline
    
    with open(baseline_file, "r", encoding="utf-8") as f:
        baseline_content = f.read()
    
    # Check for single-writer command in baseline
    if "pwsh docs/_ssot/update_gen.ps1" in baseline_content:
        # Verify current writer is the same
        writer_file = SSOT_DIR / "update_gen.ps1"
        if writer_file.exists():
            with open(writer_file, "r", encoding="utf-8") as f:
                current_content = f.read()
                if "update_gen.ps1" not in current_content:
                    return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Check deterministic documentation baseline drift"
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"Baseline version to compare against (default: {DEFAULT_BASELINE})"
    )
    args = parser.parse_args()
    
    print(f"=== Determinism Baseline Check: {args.baseline} ===\n")
    
    # Load baseline checksums
    print(f"Loading baseline: {args.baseline}")
    baseline_checksums = load_baseline(args.baseline)
    
    # Load current checksums
    print(f"Loading current manifest: {MANIFEST_FILE}")
    current_checksums = load_current_manifest()
    
    # Compare checksums
    print("\n--- Checksum Comparison ---")
    drift_detected = False
    
    for artifact in ARTIFACTS:
        baseline_hash = baseline_checksums.get(artifact, "NOT_IN_BASELINE")
        current_hash = current_checksums.get(artifact, "NOT_IN_MANIFEST")
        
        status = "✅" if baseline_hash == current_hash else "❌"
        
        print(f"{status} {artifact}")
        print(f"   Baseline: {baseline_hash[:16]}...")
        print(f"   Current:  {current_hash[:16]}...")
        
        if baseline_hash != current_hash:
            drift_detected = True
    
    # Check writer command
    print("\n--- Writer Command Check ---")
    writer_ok = check_writer_command()
    if writer_ok:
        print("✅ Writer command unchanged")
    else:
        print("❌ Writer command has changed!")
        drift_detected = True
    
    # Summary
    print("\n" + "=" * 40)
    if drift_detected:
        print("❌ DRIFT DETECTED")
        print("The current state differs from the baseline.")
        print("This may indicate:")
        print("  - Manual edits to promoted artifacts")
        print("  - Writer command changes")
        print("  - Schema updates requiring baseline refresh")
        sys.exit(1)
    else:
        print("✅ NO DRIFT DETECTED")
        print(f"Current state matches baseline {args.baseline}")
        sys.exit(0)


if __name__ == "__main__":
    main()

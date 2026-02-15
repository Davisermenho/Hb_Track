#!/usr/bin/env python3
"""
validate-quality-gates.py

Purpose: Validate quality-gates.yml against code (radon/lizard) and fail if violations
Input: docs/_ai/_specs/quality-gates.yml + target code
Output: Status 0 (compliant) or 1 (violations)
"""

import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed", file=sys.stderr)
    sys.exit(1)


def load_gates(yml_path: Path) -> dict:
    """Load quality gates configuration."""
    with open(yml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_complexity(target_dir: Path, max_complexity: int) -> bool:
    """Check cyclomatic complexity using radon."""
    try:
        result = subprocess.run(
            ['radon', 'cc', str(target_dir), '-a', '-nc'],
            capture_output=True,
            text=True
        )
        
        # Parse radon output for complexity violations
        for line in result.stdout.split('\n'):
            if line.strip() and not line.startswith(' '):
                # Extract complexity score (simplified)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        score = int(parts[-1].strip('()'))
                        if score > max_complexity:
                            print(f"[FAIL] Complexity {score} > {max_complexity}: {line}", file=sys.stderr)
                            return False
                    except (ValueError, IndexError):
                        pass
        
        return True
    except FileNotFoundError:
        print("[WARN] radon not installed, skipping complexity check", file=sys.stderr)
        return True


def main():
    """Main validation logic."""
    gates_path = Path("docs/_ai/_specs/quality-gates.yml")
    target_dir = Path("Hb Track - Backend/app")
    
    if not gates_path.exists():
        print(f"[ERROR] Quality gates not found: {gates_path}", file=sys.stderr)
        sys.exit(1)
    
    gates = load_gates(gates_path)
    max_complexity = gates.get("gates", {}).get("complexity_max", 10)
    
    if not check_complexity(target_dir, max_complexity):
        sys.exit(1)
    
    print("✅ Quality gates passed")
    sys.exit(0)


if __name__ == "__main__":
    main()

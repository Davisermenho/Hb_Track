#!/usr/bin/env python3
"""
validate-approved-commands.py

Purpose: Verify scripts/workflows use only approved commands from whitelist
Input: scripts/**/*.py, docs/_ai/_context/approved-commands.yml
Output: Status 0 (all approved) or 1 (unauthorized uses found)
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed", file=sys.stderr)
    sys.exit(1)


def load_whitelist(yml_path: Path) -> set:
    """Load approved commands from YAML."""
    with open(yml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    commands = set()
    for category in data.get("categories", {}).values():
        for cmd in category:
            # Extract command name (first word)
            cmd_name = cmd.strip().split()[0] if cmd.strip() else ""
            if cmd_name:
                commands.add(cmd_name)
    
    return commands


def scan_scripts(scripts_dir: Path, whitelist: set) -> list:
    """Scan scripts for unauthorized commands."""
    violations = []
    
    for script in scripts_dir.rglob("*.py"):
        content = script.read_text(encoding='utf-8')
        
        # Simple pattern: subprocess.run([...])
        for match in re.finditer(r'subprocess\.(?:run|call|Popen)\(\[([^\]]+)\]', content):
            cmd_args = match.group(1)
            # Extract first command
            cmd = cmd_args.split(',')[0].strip().strip('"\'')
            
            if cmd and cmd not in whitelist:
                violations.append({
                    "file": str(script),
                    "command": cmd,
                    "context": match.group(0)[:100]
                })
    
    return violations


def main():
    """Main validation logic."""
    whitelist_path = Path("docs/_ai/_context/approved-commands.yml")
    scripts_dir = Path("scripts")
    
    if not whitelist_path.exists():
        print(f"[ERROR] Whitelist not found: {whitelist_path}", file=sys.stderr)
        sys.exit(1)
    
    whitelist = load_whitelist(whitelist_path)
    violations = scan_scripts(scripts_dir, whitelist)
    
    if violations:
        print(f"[FAIL] Found {len(violations)} unauthorized command(s):", file=sys.stderr)
        for v in violations:
            print(f"  {v['file']}: {v['command']}", file=sys.stderr)
        sys.exit(1)
    
    print("✅ All commands are approved")
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
extract-troubleshooting.py

Purpose: Convert docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md → troubleshooting-map.json
Input: docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md
Output: docs/_ai/_maps/troubleshooting-map.json
"""

import json
import re
import sys
from pathlib import Path


def extract_troubleshooting(md_path: Path) -> dict:
    """Extract troubleshooting map from canonical markdown."""
    content = md_path.read_text(encoding='utf-8')
    
    troubleshooting_map = {
        "version": "1.0",
        "source": "docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md",
        "exit_codes": {}
    }
    
    # Pattern: ## Exit Code N: Description
    exit_code_pattern = r'## Exit Code (\d+): (.+)'
    
    current_exit_code = None
    current_section = None
    
    for line in content.split('\n'):
        ec_match = re.match(exit_code_pattern, line)
        if ec_match:
            exit_code = ec_match.group(1)
            description = ec_match.group(2).strip()
            current_exit_code = exit_code
            troubleshooting_map["exit_codes"][exit_code] = {
                "description": description,
                "symptoms": [],
                "causes": [],
                "solutions": []
            }
        
        # Collect symptoms/causes/solutions (simplified)
        if current_exit_code:
            if line.startswith("### Sintomas"):
                current_section = "symptoms"
            elif line.startswith("### Causa Raiz"):
                current_section = "causes"
            elif line.startswith("### Soluções") or line.startswith("### Solução"):
                current_section = "solutions"
            elif line.startswith("- ") and current_section:
                troubleshooting_map["exit_codes"][current_exit_code][current_section].append(
                    line[2:].strip()
                )
    
    return troubleshooting_map


def main():
    """Main extraction logic."""
    md_path = Path("docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md")
    output_path = Path("docs/_ai/_maps/troubleshooting-map.json")
    
    if not md_path.exists():
        print(f"[ERROR] Source not found: {md_path}", file=sys.stderr)
        sys.exit(1)
    
    troubleshooting = extract_troubleshooting(md_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(troubleshooting, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted troubleshooting for {len(troubleshooting['exit_codes'])} exit codes to {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

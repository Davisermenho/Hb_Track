#!/usr/bin/env python3
"""
extract-approved-commands.py

Purpose: Convert docs/_canon/08_APPROVED_COMMANDS.md → approved-commands.yml
Input: docs/_canon/08_APPROVED_COMMANDS.md
Output: docs/_ai/_context/approved-commands.yml
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed", file=sys.stderr)
    sys.exit(1)


def extract_commands(md_path: Path) -> dict:
    """Extract approved commands from canonical markdown."""
    content = md_path.read_text(encoding='utf-8')
    
    commands = {
        "version": "1.0",
        "source": "docs/_canon/08_APPROVED_COMMANDS.md",
        "categories": {}
    }
    
    # Pattern: ### Categoria N: Nome
    category_pattern = r'### Categoria \d+: (.+)'
    # Pattern: ```powershell ... ```
    code_block_pattern = r'```(?:powershell|bash)\n(.*?)\n```'
    
    current_category = None
    
    for line in content.split('\n'):
        cat_match = re.match(category_pattern, line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            commands["categories"][current_category] = []
    
    # Extract code blocks (simplified - full implementation would parse more robustly)
    for match in re.finditer(code_block_pattern, content, re.DOTALL):
        cmd = match.group(1).strip()
        if current_category and cmd:
            commands["categories"][current_category].append(cmd)
    
    return commands


def main():
    """Main extraction logic."""
    md_path = Path("docs/_canon/08_APPROVED_COMMANDS.md")
    output_path = Path("docs/_ai/_context/approved-commands.yml")
    
    if not md_path.exists():
        print(f"[ERROR] Source not found: {md_path}", file=sys.stderr)
        sys.exit(1)
    
    commands = extract_commands(md_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(commands, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ Extracted {len(commands['categories'])} categories to {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

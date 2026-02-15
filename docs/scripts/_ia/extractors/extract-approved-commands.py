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
    lines = md_path.read_text(encoding='utf-8').splitlines()
    
    commands = {
        "version": "1.0",
        "source": "docs/_canon/08_APPROVED_COMMANDS.md",
        "categories": {}
    }
    
    # Pattern to match categories regardless of header level
    category_pattern = re.compile(r'^#+ Categoria \d+: (.+)')
    
    current_category = None
    in_code_block = False
    current_block = []
    
    for line in lines:
        # Check for category header
        cat_match = category_pattern.match(line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            if current_category not in commands["categories"]:
                commands["categories"][current_category] = []
            continue
            
        # Handle code blocks
        if line.startswith('```'):
            if in_code_block:
                # Ending code block
                if current_category and current_block:
                    for b_line in current_block:
                        # Clean line: strip whitespace
                        clean_line = b_line.strip()
                        # Remove leading bullet points (-, *)
                        clean_line = re.sub(r'^[-*]\s+', '', clean_line)
                        # Ignore empty lines or comments
                        if clean_line and not clean_line.startswith('#'):
                            # Add to category
                            commands["categories"][current_category].append(clean_line)
                current_block = []
                in_code_block = False
            else:
                # Starting code block
                in_code_block = True
            continue
            
        # Accumulate lines if inside a block
        if in_code_block:
            current_block.append(line)
    
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
        yaml.safe_dump(commands, f, default_flow_style=False, allow_unicode=True)
    
    print(f"OK: Extracted {len(commands['categories'])} categories to {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

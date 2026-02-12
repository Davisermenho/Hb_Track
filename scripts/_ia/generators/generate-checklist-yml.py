#!/usr/bin/env python3
"""
generate-checklist-yml.py

Purpose: Convert CHECKLIST-CANONICA-MODELS.md → checklist-models.yml
Input: docs/execution_tasks/CHECKLIST-CANONICA-MODELS.md
Output: docs/_ai/_specs/checklist-models.yml
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed", file=sys.stderr)
    sys.exit(1)


def main():
    """Main generation logic."""
    # Simplified implementation - TODO: full parsing
    checklist = {
        "version": "1.0",
        "source": "docs/execution_tasks/CHECKLIST-CANONICA-MODELS.md",
        "steps": [
            {"id": "STEP_0", "name": "Definir Schema (DDL)", "required": True},
            {"id": "STEP_1", "name": "Agent Guard (Baseline)", "required": True},
            {"id": "STEP_2", "name": "Parity Pre-Check", "required": True}
        ]
    }
    
    output_path = Path("docs/_ai/_specs/checklist-models.yml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(checklist, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ Generated checklist YAML: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

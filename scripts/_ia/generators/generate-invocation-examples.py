#!/usr/bin/env python3
"""
generate-invocation-examples.py

Purpose: Generate invocation-examples.yml from EXEC_TASK files
Input: docs/execution_tasks/EXEC_TASK_*.md
Output: docs/_ai/_specs/invocation-examples.yml
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
    examples = {
        "version": "1.0",
        "source": "docs/execution_tasks/EXEC_TASK_*.md",
        "examples": [
            {
                "task": "models_validation",
                "command": "python scripts/model_requirements.py --table <T> --profile strict",
                "exit_codes": {"0": "pass", "4": "requirements_violation"}
            }
        ]
    }
    
    output_path = Path("docs/_ai/_specs/invocation-examples.yml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(examples, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ Generated invocation examples: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

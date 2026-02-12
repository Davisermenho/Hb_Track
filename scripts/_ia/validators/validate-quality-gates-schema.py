#!/usr/bin/env python3
"""
validate-quality-gates-schema.py

Purpose: Validate quality-gates.yml against quality-gates.schema.json
Input: docs/_ai/_specs/quality-gates.yml + docs/_ai/_schemas/quality-gates.schema.json
Output: Exit 0 (valid), 1 (missing/parse error), 2 (schema validation failed)
"""

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed. Run: pip install PyYAML>=6.0.1", file=sys.stderr)
    sys.exit(1)

try:
    from jsonschema import validate, ValidationError
except ImportError:
    print("[ERROR] jsonschema not installed. Run: pip install jsonschema>=4.21.0", file=sys.stderr)
    sys.exit(1)


def main():
    """Main validation logic."""
    # Define paths
    schema_path = Path("docs/_ai/_schemas/quality-gates.schema.json")
    yaml_path = Path("docs/_ai/_specs/quality-gates.yml")
    
    # Check if files exist
    if not schema_path.exists():
        print(f"[ERROR] Schema not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
    
    if not yaml_path.exists():
        print(f"[ERROR] YAML artifact not found: {yaml_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load schema
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to parse schema: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load YAML artifact
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, IOError) as e:
        print(f"[ERROR] Failed to parse YAML: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate against schema
    try:
        validate(instance=data, schema=schema)
        print(f"✅ {yaml_path} is valid according to {schema_path}")
        sys.exit(0)
    except ValidationError as e:
        print(f"[ERROR] Schema validation failed:", file=sys.stderr)
        print(f"  Path: {' -> '.join(str(p) for p in e.path)}", file=sys.stderr)
        print(f"  Message: {e.message}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

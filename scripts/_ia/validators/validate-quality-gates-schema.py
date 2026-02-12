#!/usr/bin/env python3
"""
validate-quality-gates-schema.py

Purpose: Validate docs/_ai/_specs/quality-gates.yml against JSON schema
Input: docs/_ai/_specs/quality-gates.yml + docs/_ai/_schemas/quality-gates.schema.json
Output: Status 0 (valid) or 1 (schema violation)
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
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("[ERROR] jsonschema not installed. Run: pip install jsonschema>=4.21.0", file=sys.stderr)
    sys.exit(1)


def load_yaml(yaml_path: Path) -> dict:
    """Load YAML file."""
    if not yaml_path.exists():
        print(f"[ERROR] YAML file not found: {yaml_path}", file=sys.stderr)
        return None
    
    print(f"[INFO] Loading YAML: {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema."""
    if not schema_path.exists():
        print(f"[ERROR] Schema file not found: {schema_path}", file=sys.stderr)
        return None
    
    print(f"[INFO] Loading schema: {schema_path}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_against_schema(data: dict, schema: dict) -> bool:
    """Validate data against JSON schema."""
    try:
        validate(instance=data, schema=schema)
        print("[SUCCESS] ✅ Validation passed")
        return True
    except ValidationError as e:
        print("[ERROR] ❌ Schema validation failed", file=sys.stderr)
        print(f"[ERROR] {e.message}", file=sys.stderr)
        if e.path:
            print(f"[ERROR] Path: {' -> '.join(str(p) for p in e.path)}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected validation error: {e}", file=sys.stderr)
        return False


def main():
    """Main validation logic."""
    # Define paths relative to repo root
    repo_root = Path.cwd()
    yaml_path = repo_root / 'docs' / '_ai' / '_specs' / 'quality-gates.yml'
    schema_path = repo_root / 'docs' / '_ai' / '_schemas' / 'quality-gates.schema.json'
    
    print("[INFO] Starting quality gates schema validation")
    
    # Load files
    data = load_yaml(yaml_path)
    if data is None:
        sys.exit(1)
    
    schema = load_schema(schema_path)
    if schema is None:
        sys.exit(1)
    
    # Validate
    if validate_against_schema(data, schema):
        print("[INFO] Quality gates specification is valid")
        sys.exit(0)
    else:
        print("[ERROR] Quality gates specification is invalid", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

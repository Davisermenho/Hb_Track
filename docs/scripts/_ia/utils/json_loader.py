#!/usr/bin/env python3
"""
json_loader.py - JSON loader with error handling and validation

Purpose: Centralized JSON loading with validation and error messages
Input: filepath to JSON
Output: Parsed dict or exception with context
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Parsed JSON as dict
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Malformed JSON in {filepath}: {e.msg}",
            e.doc,
            e.pos
        )


def load_json_safe(filepath: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Load JSON with fallback to default.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is malformed
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return load_json(filepath)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] {e}", file=sys.stderr)
        return default if default is not None else {}


if __name__ == "__main__":
    # Smoke test
    import tempfile
    
    # Test valid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"test": "value"}')
        temp_path = f.name
    
    result = load_json(temp_path)
    assert result == {"test": "value"}, "Valid JSON load failed"
    
    # Test safe loader
    result_safe = load_json_safe("nonexistent.json", default={"fallback": True})
    assert result_safe == {"fallback": True}, "Safe loader fallback failed"
    
    print("✅ json_loader.py: All tests passed")
    sys.exit(0)

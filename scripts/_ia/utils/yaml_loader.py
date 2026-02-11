#!/usr/bin/env python3
"""
yaml_loader.py - YAML loader with error handling

Purpose: Centralized YAML loading with validation
Input: filepath to YAML
Output: Parsed dict or exception with context
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed. Run: pip install PyYAML>=6.0.1", file=sys.stderr)
    sys.exit(1)


def load_yaml(filepath: str) -> Dict[str, Any]:
    """
    Load YAML file with error handling.
    
    Args:
        filepath: Path to YAML file
        
    Returns:
        Parsed YAML as dict
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {filepath}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Malformed YAML in {filepath}: {e}")


def load_yaml_safe(filepath: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Load YAML with fallback to default.
    
    Args:
        filepath: Path to YAML file
        default: Default value if file doesn't exist or is malformed
        
    Returns:
        Parsed YAML or default value
    """
    try:
        return load_yaml(filepath)
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"[WARN] {e}", file=sys.stderr)
        return default if default is not None else {}


if __name__ == "__main__":
    print("✅ yaml_loader.py: Module loaded successfully")
    sys.exit(0)

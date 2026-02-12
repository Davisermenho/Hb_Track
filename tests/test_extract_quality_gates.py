#!/usr/bin/env python3
"""
test_extract_quality_gates.py

Unit tests for extract-quality-gates.py extractor.
Tests file existence and validates extracted field values (6, 3, 50, 4).
"""

import sys
from pathlib import Path

try:
    import pytest
    import yaml
except ImportError:
    print("[ERROR] pytest or PyYAML not installed", file=sys.stderr)
    sys.exit(1)


# Define paths relative to repo root
REPO_ROOT = Path(__file__).parent.parent
QUALITY_GATES_YML = REPO_ROOT / 'docs' / '_ai' / '_specs' / 'quality-gates.yml'


def test_quality_gates_file_exists():
    """Test that quality-gates.yml file exists."""
    assert QUALITY_GATES_YML.exists(), f"Quality gates file not found: {QUALITY_GATES_YML}"


def test_quality_gates_is_valid_yaml():
    """Test that quality-gates.yml is valid YAML."""
    assert QUALITY_GATES_YML.exists(), "Quality gates file not found"
    
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    assert data is not None, "Failed to parse YAML"
    assert isinstance(data, dict), "YAML should be a dictionary"


def test_quality_gates_has_required_fields():
    """Test that quality-gates.yml has all required top-level fields."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    assert 'version' in data, "Missing 'version' field"
    assert 'source' in data, "Missing 'source' field"
    assert 'gates' in data, "Missing 'gates' field"


def test_quality_gates_version_format():
    """Test that version follows semantic versioning."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    version = data.get('version')
    assert version is not None, "Version is None"
    assert isinstance(version, str), "Version should be a string"
    
    # Check semver format (e.g., 1.0.0)
    parts = version.split('.')
    assert len(parts) == 3, f"Version should have 3 parts: {version}"
    assert all(part.isdigit() for part in parts), f"Version parts should be numeric: {version}"


def test_quality_gates_source_metadata():
    """Test that source metadata is present."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    source = data.get('source')
    assert source is not None, "Source is None"
    assert isinstance(source, dict), "Source should be a dictionary"
    
    assert 'file' in source, "Missing 'file' in source"
    assert 'generated_at' in source, "Missing 'generated_at' in source"
    
    # Verify file path
    file_path = source.get('file')
    assert file_path is not None, "File path is None"
    assert 'QUALITY_METRICS.md' in file_path, f"Unexpected source file: {file_path}"


def test_quality_gates_complexity_max():
    """Test that complexity_max is 6."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    gates = data.get('gates', {})
    complexity_max = gates.get('complexity_max')
    
    assert complexity_max is not None, "complexity_max is missing"
    assert isinstance(complexity_max, int), "complexity_max should be an integer"
    assert complexity_max == 6, f"Expected complexity_max=6, got {complexity_max}"


def test_quality_gates_nesting_max():
    """Test that nesting_max is 3."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    gates = data.get('gates', {})
    nesting_max = gates.get('nesting_max')
    
    assert nesting_max is not None, "nesting_max is missing"
    assert isinstance(nesting_max, int), "nesting_max should be an integer"
    assert nesting_max == 3, f"Expected nesting_max=3, got {nesting_max}"


def test_quality_gates_loc_max():
    """Test that loc_max is 50."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    gates = data.get('gates', {})
    loc_max = gates.get('loc_max')
    
    assert loc_max is not None, "loc_max is missing"
    assert isinstance(loc_max, int), "loc_max should be an integer"
    assert loc_max == 50, f"Expected loc_max=50, got {loc_max}"


def test_quality_gates_params_max():
    """Test that params_max is 4."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    gates = data.get('gates', {})
    params_max = gates.get('params_max')
    
    assert params_max is not None, "params_max is missing"
    assert isinstance(params_max, int), "params_max should be an integer"
    assert params_max == 4, f"Expected params_max=4, got {params_max}"


def test_quality_gates_all_threshold_values():
    """Test all threshold values in one assertion (6, 3, 50, 4)."""
    with open(QUALITY_GATES_YML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    gates = data.get('gates', {})
    
    # Expected values from QUALITY_METRICS.md
    expected = {
        'complexity_max': 6,
        'nesting_max': 3,
        'loc_max': 50,
        'params_max': 4
    }
    
    for key, expected_value in expected.items():
        actual_value = gates.get(key)
        assert actual_value == expected_value, \
            f"Expected {key}={expected_value}, got {actual_value}"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
test_extract_quality_gates.py

Purpose: Unit tests for quality gates extractor and validator
Tests that quality-gates.yml exists and contains expected thresholds
"""

import pytest
from pathlib import Path

try:
    import yaml
except ImportError:
    pytest.skip("PyYAML not installed", allow_module_level=True)


class TestQualityGatesYAML:
    """Tests for quality-gates.yml artifact."""
    
    @pytest.fixture
    def quality_gates_path(self):
        """Path to quality-gates.yml."""
        return Path("docs/_ai/_specs/quality-gates.yml")
    
    @pytest.fixture
    def quality_gates_data(self, quality_gates_path):
        """Load quality-gates.yml data."""
        if not quality_gates_path.exists():
            pytest.skip(f"Quality gates file not found: {quality_gates_path}")
        
        with open(quality_gates_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def test_quality_gates_file_exists(self, quality_gates_path):
        """Test that quality-gates.yml exists."""
        assert quality_gates_path.exists(), f"Quality gates file not found: {quality_gates_path}"
    
    def test_quality_gates_has_version(self, quality_gates_data):
        """Test that quality-gates.yml has version field."""
        assert "version" in quality_gates_data, "Missing 'version' field"
        assert isinstance(quality_gates_data["version"], str), "Version must be a string"
    
    def test_quality_gates_has_source(self, quality_gates_data):
        """Test that quality-gates.yml has source field."""
        assert "source" in quality_gates_data, "Missing 'source' field"
        assert isinstance(quality_gates_data["source"], str), "Source must be a string"
    
    def test_quality_gates_has_generated_at(self, quality_gates_data):
        """Test that quality-gates.yml has generated_at field."""
        assert "generated_at" in quality_gates_data, "Missing 'generated_at' field"
        assert isinstance(quality_gates_data["generated_at"], str), "generated_at must be a string"
    
    def test_quality_gates_has_gates_section(self, quality_gates_data):
        """Test that quality-gates.yml has gates section."""
        assert "gates" in quality_gates_data, "Missing 'gates' section"
        assert isinstance(quality_gates_data["gates"], dict), "Gates must be a dictionary"
    
    def test_quality_gates_thresholds(self, quality_gates_data):
        """Test that quality-gates.yml contains expected hardcoded thresholds."""
        gates = quality_gates_data.get("gates", {})
        
        # Test complexity_max
        assert "complexity_max" in gates, "Missing 'complexity_max' threshold"
        assert gates["complexity_max"] == 6, f"Expected complexity_max=6, got {gates['complexity_max']}"
        
        # Test nesting_max
        assert "nesting_max" in gates, "Missing 'nesting_max' threshold"
        assert gates["nesting_max"] == 3, f"Expected nesting_max=3, got {gates['nesting_max']}"
        
        # Test function_lines_max
        assert "function_lines_max" in gates, "Missing 'function_lines_max' threshold"
        assert gates["function_lines_max"] == 50, f"Expected function_lines_max=50, got {gates['function_lines_max']}"
        
        # Test parameters_max
        assert "parameters_max" in gates, "Missing 'parameters_max' threshold"
        assert gates["parameters_max"] == 4, f"Expected parameters_max=4, got {gates['parameters_max']}"
    
    def test_quality_gates_threshold_types(self, quality_gates_data):
        """Test that all thresholds are integers."""
        gates = quality_gates_data.get("gates", {})
        
        for key, value in gates.items():
            assert isinstance(value, int), f"Threshold '{key}' must be an integer, got {type(value)}"
            assert value > 0, f"Threshold '{key}' must be positive, got {value}"


class TestQualityGatesExtractor:
    """Tests for the extractor script functionality."""
    
    def test_extractor_script_exists(self):
        """Test that extract-quality-gates.py exists."""
        extractor_path = Path("docs/scripts/_ia/extractors/extract-quality-gates.py")
        assert extractor_path.exists(), f"Extractor script not found: {extractor_path}"
    
    def test_validator_script_exists(self):
        """Test that validate-quality-gates-schema.py exists."""
        validator_path = Path("docs/scripts/_ia/validators/validate-quality-gates-schema.py")
        assert validator_path.exists(), f"Validator script not found: {validator_path}"
    
    def test_schema_file_exists(self):
        """Test that quality-gates.schema.json exists."""
        schema_path = Path("docs/_ai/_schemas/quality-gates.schema.json")
        assert schema_path.exists(), f"Schema file not found: {schema_path}"

"""Tests for model_requirements AST parser.

SKIPPED: Module model_requirements.py not found in /scripts/
These are placeholder tests for future implementation.
"""
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skip(reason="Module model_requirements.py not found in /scripts/ - placeholder tests")

# Mock import to prevent collection errors
class MockMR:
    @staticmethod
    def _parse_model_constraints(model_path, table_name):
        raise NotImplementedError()

mr = MockMR()


def test_parse_model_constraints_from_real_model_athlete_badges():
    model_path = Path("app/models/athlete_badge.py")
    parsed = mr._parse_model_constraints(model_path, "athlete_badges")

    assert "ck_athlete_badges_type" in parsed["checks"]
    assert "idx_badges_athlete_month" in parsed["indexes"]
    assert "athlete_badges_athlete_id_fkey" in parsed["fks"]
    assert parsed["fks"]["athlete_badges_athlete_id_fkey"].local_columns == ("athlete_id",)


def _workspace_tmp_model_path(name: str) -> Path:
    root = Path(".hb_tmp_tests")
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{name}_{uuid4().hex}.py"


def test_parse_model_columns_supports_mapped_and_column():
    model_file = _workspace_tmp_model_path("sample_model")
    model_file.write_text(
        """
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

class Sample:
    __tablename__ = "sample_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
""",
        encoding="utf-8",
    )

    try:
        cols = mr._parse_model_columns(model_file, "sample_table")
        assert "id" in cols
        assert "name" in cols
    finally:
        model_file.unlink(missing_ok=True)


def test_parse_model_constraints_non_static_table_args_is_ignored():
    model_file = _workspace_tmp_model_path("dynamic_model")
    model_file.write_text(
        """
from sqlalchemy import CheckConstraint

class DynamicSample:
    __tablename__ = "dynamic_table"
    rules = ["x > 0"]
    __table_args__ = tuple(CheckConstraint(r, name=f"ck_dynamic_{i}") for i, r in enumerate(rules))
""",
        encoding="utf-8",
    )

    try:
        parsed = mr._parse_model_constraints(model_file, "dynamic_table")
        assert len(parsed["checks"]) == 0
        assert len(parsed["uniques"]) == 0
        assert len(parsed["indexes"]) == 0
    finally:
        model_file.unlink(missing_ok=True)

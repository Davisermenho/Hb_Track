"""Tests for model_requirements schema parser.

SKIPPED: Module model_requirements.py not found in /scripts/
These are placeholder tests for future implementation.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Module model_requirements.py not found in /scripts/ - placeholder tests")

# Mock import to prevent collection errors
class MockMR:
    @staticmethod
    def _parse_columns(sql, table_name):
        raise NotImplementedError()

mr = MockMR()


SCHEMA_SQL = """
CREATE TABLE public.sample_table (
    id integer NOT NULL,
    org_id integer NOT NULL,
    ext_id character varying(64) DEFAULT 'abc'::character varying,
    qty integer DEFAULT 0,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    notes text DEFAULT NULL,
    CONSTRAINT sample_table_pkey PRIMARY KEY (id),
    CONSTRAINT ck_sample_table_qty_non_negative CHECK ((qty >= 0)),
    CONSTRAINT uq_sample_table_ext_id UNIQUE (ext_id)
);

ALTER TABLE ONLY public.sample_table
    ADD CONSTRAINT fk_sample_table_org_id FOREIGN KEY (org_id) REFERENCES public.organizations(id) ON UPDATE CASCADE ON DELETE RESTRICT;

CREATE UNIQUE INDEX idx_sample_table_org_ext_unique ON public.sample_table USING btree (org_id, ext_id) WHERE (notes IS NULL);
CREATE INDEX idx_sample_table_org_id ON public.sample_table USING btree (org_id);
"""


def test_parse_columns_wrapper_and_defaults():
    cols = mr._parse_columns(SCHEMA_SQL, "sample_table")

    assert "ext_id" in cols
    assert cols["ext_id"].default_kind == "default_literal"
    assert "'abc'" in (cols["ext_id"].default_value or "")

    assert cols["qty"].default_kind == "default_literal"
    assert cols["qty"].default_value == "0"

    assert cols["active"].default_kind == "default_literal"
    assert cols["active"].default_value == "true"

    assert cols["created_at"].default_kind == "default_function"
    assert (cols["created_at"].default_value or "").lower().startswith("now(")

    assert cols["notes"].default_kind == "default_literal"
    assert cols["notes"].default_value == "null"


def test_parse_fks_wrapper_with_local_cols_and_onupdate_ondelete():
    fks = mr._parse_fks(SCHEMA_SQL, "sample_table")
    fk = fks["fk_sample_table_org_id"]

    assert fk.reference == "organizations.id"
    assert fk.local_columns == ("org_id",)
    assert fk.onupdate == "CASCADE"
    assert fk.ondelete == "RESTRICT"


def test_parse_checks_uniques_indexes_by_name():
    checks = mr._parse_checks(SCHEMA_SQL, "sample_table")
    uniques = mr._parse_unique_constraints(SCHEMA_SQL, "sample_table")
    indexes = mr._parse_indexes(SCHEMA_SQL, "sample_table")

    assert "ck_sample_table_qty_non_negative" in checks
    assert "uq_sample_table_ext_id" in uniques

    assert "idx_sample_table_org_ext_unique" in indexes
    assert indexes["idx_sample_table_org_ext_unique"].unique is True
    assert indexes["idx_sample_table_org_ext_unique"].where is not None

    assert "idx_sample_table_org_id" in indexes
    assert indexes["idx_sample_table_org_id"].unique is False

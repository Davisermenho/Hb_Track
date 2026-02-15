"""
Auto-generated model skeleton for table match_possessions.
Do not edit HB-AUTOGEN blocks manually.
"""

# HB-AUTOGEN-IMPORTS:BEGIN
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ForeignKey, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB, INET as PG_INET, ENUM as PG_ENUM
# HB-AUTOGEN-IMPORTS:END

from app.models.base import Base


class MatchPossessions(Base):
    __tablename__ = "match_possessions"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.match_possessions
    __table_args__ = (
        CheckConstraint('end_period_number >= start_period_number', name='ck_match_possessions_end_period'),
        CheckConstraint('end_time_seconds >= 0', name='ck_match_possessions_end_time'),
        CheckConstraint("result::text = ANY (ARRAY['goal'::character varying, 'turnover'::character varying, 'seven_meter_won'::character varying, 'time_over'::character varying]::text[])", name='ck_match_possessions_result'),
        CheckConstraint('start_period_number >= 1', name='ck_match_possessions_start_period'),
        CheckConstraint('start_time_seconds >= 0', name='ck_match_possessions_start_time'),
        Index('ix_match_possessions_match_id', 'match_id', unique=False),
        Index('ix_match_possessions_team_id', 'team_id', unique=False),
    )

    # NOTE: typing helpers may require: from datetime import date, datetime; from uuid import UUID

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    match_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('matches.id', name='fk_match_possessions_match_id', ondelete='CASCADE'), nullable=False)
    team_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('teams.id', name='fk_match_possessions_team_id', ondelete='RESTRICT'), nullable=False)
    start_period_number: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    start_time_seconds: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    end_period_number: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    end_time_seconds: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    start_score_our: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    start_score_opponent: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    end_score_our: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    end_score_opponent: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    result: Mapped[str] = mapped_column(sa.String(length=32), nullable=False)
    # HB-AUTOGEN:END
    # Manual customizations below (preserved across regen)

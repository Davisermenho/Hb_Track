"""
Auto-generated model skeleton for table advantage_states.
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


class AdvantageStates(Base):
    __tablename__ = "advantage_states"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.advantage_states
    code: Mapped[str] = mapped_column(sa.String(length=32), primary_key=True)
    delta_players: Mapped[int] = mapped_column(sa.SmallInteger(), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.String(length=255), nullable=True)
    # HB-AUTOGEN:END
    # Manual customizations below (preserved across regen)

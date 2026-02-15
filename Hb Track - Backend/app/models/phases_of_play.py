"""
Auto-generated model skeleton for table phases_of_play.
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


class PhasesOfPlay(Base):
    __tablename__ = "phases_of_play"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.phases_of_play
    code: Mapped[str] = mapped_column(sa.String(length=32), primary_key=True)
    description: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    # HB-AUTOGEN:END
    # Manual customizations below (preserved across regen)

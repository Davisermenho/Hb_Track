"""
Auto-generated model skeleton for table event_types.
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


class EventTypes(Base):
    __tablename__ = "event_types"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.event_types
    code: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    description: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    is_shot: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    is_possession_ending: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    # HB-AUTOGEN:END
    # Manual customizations below (preserved across regen)

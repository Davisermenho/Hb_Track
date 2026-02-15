"""
Auto-generated model skeleton for table event_subtypes.
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


class EventSubtypes(Base):
    __tablename__ = "event_subtypes"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.event_subtypes
    __table_args__ = (
        Index('ix_event_subtypes_event_type_code', 'event_type_code', unique=False),
    )

    code: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    event_type_code: Mapped[str] = mapped_column(sa.String(length=64), ForeignKey('event_types.code', name='fk_event_subtypes_event_type_code', ondelete='RESTRICT'), nullable=False)
    description: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    # HB-AUTOGEN:END
    # Manual customizations below (preserved across regen)

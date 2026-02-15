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
import uuid
from app.models.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"


# HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.refresh_tokens
    __table_args__ = (
        Index('ix_refresh_tokens_token_hash', 'token_hash', unique=True),
    )

    # NOTE: typing helpers may require: from datetime import date, datetime; from uuid import UUID

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text('gen_random_uuid()'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', name='refresh_tokens_user_id_fkey', ondelete='CASCADE'), nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('refresh_tokens.id', name='refresh_tokens_parent_id_fkey', ondelete='SET NULL'), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    ip_address: Mapped[Optional[object]] = mapped_column(PG_INET(), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(sa.Text(), nullable=True)
    # HB-AUTOGEN:END

    # Indexes

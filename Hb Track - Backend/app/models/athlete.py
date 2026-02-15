"""
Model Athlete - Atletas do sistema.

Regras:
- R6: Atletas vinculam-se via team_registrations (vínculo esportivo)
- R12: Papel atleta permanente no histórico
- R13/R14: Estados (ativa, lesionada, dispensada) - via athlete_state_history
- RF1.1: Atleta pode ser cadastrada sem equipe (vínculo opcional)
- R32: Atleta sem team_registration não opera
- RDB4: Soft delete obrigatório
- RDB7: Histórico de estados dedicado
- RD13: Goleiras não têm posição ofensiva

ESTRUTURA CANÔNICA (V1.2 Normalizada - 31/12/2025):
- id (uuid, PK)
- person_id (uuid, FK, NOT NULL)
- organization_id (uuid, FK, NULL) - DERIVADO automaticamente de team_registrations
- state (varchar, NOT NULL) - 'ativa', 'dispensada', 'arquivada'
- injured (boolean, NOT NULL)
- medical_restriction (boolean, NOT NULL)
- suspended_until (date, NULL)
- load_restricted (boolean, NOT NULL)
- athlete_name (varchar, NOT NULL)
- birth_date (date, NOT NULL)
- athlete_nickname, shirt_number (NULL)
- main_defensive_position_id, secondary_defensive_position_id (FK, NULL)
- main_offensive_position_id, secondary_offensive_position_id (FK, NULL)
- schooling_id (FK, NULL)
- guardian_name, guardian_phone (NULL)
- athlete_photo_path (NULL)
- registered_at (timestamptz, NOT NULL)
- athlete_age_at_registration (int, NULL)
- created_at, updated_at (timestamptz, NOT NULL)
- deleted_at (timestamptz, NULL), deleted_reason (text, NULL)

CAMPOS REMOVIDOS (usar tabelas normalizadas):
- athlete_rg, athlete_cpf → person_documents
- athlete_phone, athlete_email → person_contacts
- zip_code, street, neighborhood, city, state_address, address_number, address_complement → person_addresses
"""

# HB-AUTOGEN-IMPORTS:BEGIN
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ForeignKey, CheckConstraint, Index, UniqueConstraint, select, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, column_property, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB, INET as PG_INET, ENUM as PG_ENUM
# HB-AUTOGEN-IMPORTS:END
from enum import Enum

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.team_registration import TeamRegistration


class AthleteState(str, Enum):
    """
    Estados possíveis do atleta (R12, REGRAS.md V1.2).
    
    IMPORTANTE: 'lesionada' NÃO é um estado - é uma flag (injured=true).
    Estados base são: ativa, dispensada, arquivada.
    """
    ATIVA = "ativa"
    DISPENSADA = "dispensada"
    ARQUIVADA = "arquivada"


class Athlete(Base):
    """
    Representa um atleta no sistema.

    Estrutura real do banco de dados V1.2.
    """
    __tablename__ = "athletes"


    # HB-AUTOGEN:BEGIN
    # AUTO-GENERATED FROM DB (SSOT). DO NOT EDIT MANUALLY.
    # Table: public.athletes
    __table_args__ = (
        CheckConstraint('deleted_at IS NULL AND deleted_reason IS NULL OR deleted_at IS NOT NULL AND deleted_reason IS NOT NULL', name='ck_athletes_deleted_reason'),
        CheckConstraint('shirt_number IS NULL OR shirt_number >= 1 AND shirt_number <= 99', name='ck_athletes_shirt_number'),
        CheckConstraint("state::text = ANY (ARRAY['ativa'::character varying, 'dispensada'::character varying, 'arquivada'::character varying]::text[])", name='ck_athletes_state'),
        Index('idx_athletes_person_deleted', 'person_id', 'deleted_at', unique=False, postgresql_where=sa.text('(deleted_at IS NULL)')),
        Index('ix_athletes_birth_date', 'birth_date', unique=False),
        Index('ix_athletes_medical_flags', 'state', unique=False, postgresql_where=sa.text('((deleted_at IS NULL) AND ((injured = true) OR (medical_restriction = true) OR (load_restricted = true)))')),
        Index('ix_athletes_organization_id', 'organization_id', unique=False, postgresql_where=sa.text('(deleted_at IS NULL)')),
        Index('ix_athletes_person_id', 'person_id', unique=False),
        Index('ix_athletes_person_id_active', 'person_id', unique=False, postgresql_where=sa.text('(deleted_at IS NULL)')),
        Index('ix_athletes_state', 'state', unique=False),
        Index('ix_athletes_state_active', 'state', unique=False, postgresql_where=sa.text('(deleted_at IS NULL)')),
    )

    # NOTE: typing helpers may require: from datetime import date, datetime; from uuid import UUID

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    person_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('persons.id', name='fk_athletes_person_id', ondelete='RESTRICT'), nullable=False)
    state: Mapped[str] = mapped_column(sa.String(length=20), nullable=False, server_default=sa.text("'ativa'::character varying"))
    injured: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.text('false'))
    medical_restriction: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.text('false'))
    suspended_until: Mapped[Optional[date]] = mapped_column(sa.Date(), nullable=True)
    load_restricted: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.text('false'))
    athlete_name: Mapped[str] = mapped_column(sa.String(length=100), nullable=False)
    birth_date: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    athlete_nickname: Mapped[Optional[str]] = mapped_column(sa.String(length=50), nullable=True)
    shirt_number: Mapped[Optional[int]] = mapped_column(sa.Integer(), nullable=True)
    main_defensive_position_id: Mapped[Optional[int]] = mapped_column(sa.Integer(), ForeignKey('defensive_positions.id', name='fk_athletes_main_defensive_position_id', ondelete='SET NULL'), nullable=True)
    secondary_defensive_position_id: Mapped[Optional[int]] = mapped_column(sa.Integer(), ForeignKey('defensive_positions.id', name='fk_athletes_secondary_defensive_position_id', ondelete='SET NULL'), nullable=True)
    main_offensive_position_id: Mapped[Optional[int]] = mapped_column(sa.Integer(), ForeignKey('offensive_positions.id', name='fk_athletes_main_offensive_position_id', ondelete='SET NULL'), nullable=True)
    secondary_offensive_position_id: Mapped[Optional[int]] = mapped_column(sa.Integer(), ForeignKey('offensive_positions.id', name='fk_athletes_secondary_offensive_position_id', ondelete='SET NULL'), nullable=True)
    schooling_id: Mapped[Optional[int]] = mapped_column(sa.Integer(), ForeignKey('schooling_levels.id', name='fk_athletes_schooling_id', ondelete='SET NULL'), nullable=True)
    guardian_name: Mapped[Optional[str]] = mapped_column(sa.String(length=100), nullable=True)
    guardian_phone: Mapped[Optional[str]] = mapped_column(sa.String(length=20), nullable=True)
    athlete_photo_path: Mapped[Optional[str]] = mapped_column(sa.String(length=500), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    athlete_age_at_registration: Mapped[Optional[int]] = mapped_column(sa.Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    deleted_reason: Mapped[Optional[str]] = mapped_column(sa.Text(), nullable=True)
    organization_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('organizations.id', name='fk_athletes_organization_id', ondelete='RESTRICT'), nullable=True)
    # HB-AUTOGEN:END
    # ==================== RELATIONSHIPS ====================
    team_registrations: Mapped[list["TeamRegistration"]] = relationship(
        "TeamRegistration",
        back_populates="athlete",
        lazy="selectin"
    )
    
    wellness_posts = relationship(
        "WellnessPost",
        back_populates="athlete",
        lazy="selectin"
    )

    person: Mapped["Person"] = relationship(
        "Person",
        lazy="selectin",
    )
    
    medical_cases = relationship(
        "MedicalCase",
        back_populates="athlete",
        lazy="selectin"
    )

    # ==================== HELPERS ====================
    @property
    def is_active_athlete(self) -> bool:
        """Retorna True se atleta não foi soft-deleted."""
        return self.deleted_at is None

    @property
    def current_state(self) -> AthleteState:
        """Retorna o estado atual como enum."""
        return AthleteState(self.state)

    @property
    def is_goalkeeper(self) -> bool:
        """Retorna True se a posição defensiva principal é goleira (id=5)."""
        return self.main_defensive_position_id == 5

    def calculate_age(self, reference_date: Optional[date] = None) -> int:
        """
        Calcula idade da atleta em uma data de referência.

        Args:
            reference_date: Data de referência (padrão: hoje)

        Returns:
            Idade em anos completos
        """
        if reference_date is None:
            reference_date = date.today()

        age = reference_date.year - self.birth_date.year

        # Ajustar se ainda não fez aniversário no ano de referência
        if (reference_date.month, reference_date.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1

        return age

    @property
    def current_age(self) -> int:
        """Calcula idade atual."""
        return self.calculate_age()

    def __repr__(self) -> str:
        return f"<Athlete {self.athlete_name} ({self.state})>"

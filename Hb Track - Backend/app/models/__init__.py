# Models package
"""
Exporta Base e todos os models SQLAlchemy.

FASE 5 - Modelos conforme RAG V1.1:
- R1: Person (entidade raiz)
- R2/R3: User (usuários + superadmin)
- R4: Role (papéis)
- R6-R8: Membership (vínculos)
- R12-R14: Athlete + AthleteState (atletas + estados)
- R15: Category (categorias por idade)
- R17: TeamRegistration (inscrições)
- R18: TrainingSession (treinos)
- R19: Match (jogos)
- R20: MatchEvent (estatísticas primárias)
- R34: Organization (clube único V1)
- RF6: Team (equipes)

V1.2 - Estrutura normalizada de Pessoas:
- PersonContact (telefone, email, whatsapp)
- PersonAddress (endereços)
- PersonDocument (CPF, RG, CNH)
- PersonMedia (fotos, arquivos)
"""

from app.models.base import Base
from app.models.role import Role
from app.models.person import Person, PersonContact, PersonAddress, PersonDocument, PersonMedia
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.season import Season
from app.models.category import Category
from app.models.team import Team
from app.models.athlete import Athlete, AthleteState
# NOTA: athlete_state.py referencia tabela athlete_states que não existe no DB atual
# from app.models.athlete_state import AthleteStateHistory
from app.models.defensive_position import DefensivePosition
from app.models.offensive_position import OffensivePosition
from app.models.schooling_level import SchoolingLevel
from app.models.team_registration import TeamRegistration
from app.models.training_cycle import TrainingCycle
from app.models.training_microcycle import TrainingMicrocycle
from app.models.training_session import TrainingSession
from app.models.exercise import Exercise
from app.models.session_exercise import SessionExercise
from app.models.training_analytics_cache import TrainingAnalyticsCache
from app.models.training_alert import TrainingAlert
from app.models.training_suggestion import TrainingSuggestion
from app.models.export_job import ExportJob
from app.models.export_rate_limit import ExportRateLimit
from app.models.match import Match, MatchStatus, MatchType
from app.models.match_event import MatchEvent, EventType
from app.models.wellness_post import WellnessPost
from app.models.medical_case import MedicalCase
from app.models.idempotency_key import IdempotencyKey
from app.models.refresh_token import RefreshToken
from app.models.email_queue import EmailQueue
from app.models.competition import Competition
from app.models.competition_season import CompetitionSeason
# V2: Competition Module with AI
from app.models.competition_phase import CompetitionPhase
from app.models.competition_opponent_team import CompetitionOpponentTeam
from app.models.competition_match import CompetitionMatch
from app.models.competition_standing import CompetitionStanding

__all__ = [
    # Base
    "Base",
    # Core entities (R1-R4)
    "Role",
    "Person",
    "PersonContact",      # V1.2
    "PersonAddress",      # V1.2
    "PersonDocument",     # V1.2
    "PersonMedia",        # V1.2
    "User",
    "PasswordReset",
    # Organization & Access (R34, R6-R8)
    "Organization",
    "Membership",
    "Season",
    # Categories & Teams (R15, RF6)
    "Category",
    "Team",
    # Athletes (R12-R14)
    "Athlete",
    "AthleteState",
    # "AthleteStateHistory",  # Tabela não existe no DB atual
    "DefensivePosition",
    "OffensivePosition",
    "SchoolingLevel",
    # Team Registrations (R17)
    "TeamRegistration",
    # Training (R18)
    "TrainingCycle",
    "TrainingMicrocycle",
    "TrainingSession",
    "Exercise",
    "SessionExercise",
    "TrainingAnalyticsCache",
    "TrainingAlert",
    "TrainingSuggestion",
    "ExportJob",
    "ExportRateLimit",
    # Matches (R19, R20)
    "Match",
    "MatchStatus",
    "MatchType",
    "MatchEvent",
    "EventType",
    # Wellness & Medical
    "WellnessPost",
    "MedicalCase",
    # Idempotency (Ficha Única)
    "IdempotencyKey",
    # Email Queue
    "EmailQueue",
    # Competitions (V2 - Module with AI)
    "Competition",
    "CompetitionSeason",
    "CompetitionPhase",
    "CompetitionOpponentTeam",
    "CompetitionMatch",
    "CompetitionStanding",
]

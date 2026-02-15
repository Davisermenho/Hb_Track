"""
Contexto de execução para rastreabilidade e auditoria

FASE 6 - Autenticação JWT Real + Permissões Canônicas

Referências RAG:
- R6: Vínculo organizacional (pessoa, papel, clube, temporada)
- R33: Nada acontece fora de um vínculo
- R31: Ações críticas auditáveis
- R32: Log obrigatório (quem, quando, o quê)
- R3: Super Admin pode operar sem vínculo
- R42: Vínculo ativo obrigatório (exceto superadmin)
- R25/R26: Permissões por papel

Arquitetura de Permissões:
- Mapa canônico em app/core/permissions_map.py (FONTE ÚNICA)
- Permissões resolvidas no momento da autenticação
- ExecutionContext carrega permissões já resolvidas
- /auth/context é apenas um espelho
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field
import logging
import json
import asyncio

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError
from jose import JWTError

from app.core.db import get_async_db
from app.core.permissions_map import get_permissions_for_role

logger = logging.getLogger(__name__)


# ============================================================================
# ExecutionContext Dataclass
# ============================================================================

@dataclass
class ExecutionContext:
    """
    Contexto de execução resolvido para uma requisição autenticada.
    
    ARQUITETURA CANÔNICA:
    - Estado puro (zero lógica de negócio)
    - Permissões já resolvidas do mapa canônico
    - Criado UMA VEZ por requisição
    - Reutilizado em todos os endpoints via Depends()
    
    IMPORTANTE:
    - NÃO adicionar lógica de negócio aqui
    - NÃO fazer queries no banco
    - Apenas métodos helpers de verificação
    """
    user_id: UUID
    email: str
    role_code: str
    request_id: str
    person_id: Optional[UUID] = None
    is_superadmin: bool = False
    organization_id: Optional[UUID] = None
    membership_id: Optional[UUID] = None
    team_ids: List[UUID] = field(default_factory=list)
    permissions: Dict[str, bool] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def can(self, permission: str) -> bool:
        """Verifica se o contexto possui uma permissão específica"""
        return self.permissions.get(permission, False)
    
    def can_bypass_rules(self) -> bool:
        """R3: Superadmin pode ignorar travas operacionais"""
        return self.is_superadmin

    def has_active_membership(self) -> bool:
        """R42: Verifica se o ator tem vínculo ativo (ou se é superadmin)"""
        return self.is_superadmin or (self.membership_id is not None)

    def requires(self, permission: str) -> None:
        """
        Garante que o contexto possui uma permissão.
        Levanta HTTPException se não tiver.
        """
        if not self.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão necessária: {permission}"
            )
    
    def has_any(self, permissions: List[str]) -> bool:
        """Verifica se possui QUALQUER UMA das permissões listadas"""
        return any(self.can(perm) for perm in permissions)
    
    def has_all(self, permissions: List[str]) -> bool:
        """Verifica se possui TODAS as permissões listadas"""
        return all(self.can(perm) for perm in permissions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (útil para serialização)"""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "role_code": self.role_code,
            "request_id": self.request_id,
            "person_id": str(self.person_id) if self.person_id else None,
            "is_superadmin": self.is_superadmin,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "membership_id": str(self.membership_id) if self.membership_id else None,
            "team_ids": [str(tid) for tid in self.team_ids],
            "permissions": self.permissions,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def to_audit_dict(self) -> Dict[str, Any]:
        """Formato canônico para audit_logs (JSONB)"""
        return {
            "actor_user_id": str(self.user_id),
            "actor_role": self.role_code,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "request_id": self.request_id,
            "is_superadmin": self.is_superadmin,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    x_organization_id: Optional[str] = Header(None, alias="x-organization-id"),
    db: AsyncSession = Depends(get_async_db)
) -> ExecutionContext:
    """
    Obtém contexto de execução a partir do JWT

    FASE 6: Autenticação JWT Real
    AUTH-CONTEXT-SSOT-002: Precedência COOKIE > BEARER com fallback

    Fluxo (AUTH-CONTEXT-SSOT-002):
    1. Tenta cookie PRIMEIRO (hb_access_token, access_token, hb_session)
    2. Se cookie INVÁLIDO/EXPIRADO, tenta Bearer (fallback)
    3. Se Bearer usado em mutation path, emite warning (soft deprecation)
    4. Decodifica JWT e busca usuário
    5. Valida vínculo ativo (R42, RF3) exceto superadmin
    6. Retorna ExecutionContext

    Raises:
        HTTPException 401: Token inválido ou ausente
        HTTPException 403: Usuário sem vínculo ativo (R42)
    """
    from app.core.security import decode_access_token
    from app.models.user import User
    from app.models.membership import OrgMembership  # V1.2: Renomeado de Membership
    from app.models.organization import Organization
    from app.schemas.error import ErrorCode

    # AUTH-CONTEXT-SSOT-002: Mutation paths requiring Cookie+CSRF (soft deprecation for Bearer)
    PATHS_MUTATION_LIST = [
        "/api/v1/training_sessions",
        "/api/v1/seasons",
        "/api/v1/users",
    ]

    # Verificar se token foi fornecido
    # AUTH-CONTEXT-SSOT-002: Priority COOKIE > BEARER (com fallback se cookie inválido)
    token = None
    auth_method = None
    cookie_found_but_invalid = False

    # 1. Try Cookie FIRST (COOKIE > BEARER precedence)
    token = request.cookies.get("hb_access_token")
    if token:
        auth_method = "COOKIE"
    
    # Fallback to access_token cookie (alternative)
    if not token:
        token = request.cookies.get("access_token")
        if token:
            auth_method = "COOKIE"
    
    # Fallback to legacy session cookie
    if not token:
        session_cookie = request.cookies.get("hb_session")
        if session_cookie:
            try:
                session_data = json.loads(session_cookie)
                token = session_data.get("accessToken")
                if token:
                    auth_method = "COOKIE"
            except json.JSONDecodeError:
                pass

    # Try to decode cookie token if found
    if token and auth_method == "COOKIE":
        try:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if not user_id_str:
                # Cookie invalid, try fallback to Bearer
                cookie_found_but_invalid = True
                token = None
                auth_method = None
        except JWTError:
            # Cookie invalid/expired, try fallback to Bearer
            cookie_found_but_invalid = True
            token = None
            auth_method = None
            logger.debug("Cookie token invalid/expired, attempting Bearer fallback")

    # 2. Fallback to Bearer if cookie invalid/absent (FALLBACK_TO_BEARER policy)
    if not token and credentials:
        token = credentials.credentials
        auth_method = "BEARER"
        
        # AUTH-CONTEXT-SSOT-002: Soft deprecation warning for Bearer in mutations
        request_path = request.url.path
        is_mutation_path = any(
            request_path.startswith(mutation_path) 
            for mutation_path in PATHS_MUTATION_LIST
        )
        unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}
        
        if is_mutation_path and request.method in unsafe_methods:
            logger.warning(
                "Bearer token used for mutation endpoint. Deprecated. Hard block on 2026-06-01.",
                extra={
                    "path": request_path,
                    "method": request.method,
                    "code": "BEARER_MUTATION_DEPRECATED",
                    "enforcement_date": "2026-06-01"
                }
            )

    # 3. Log auth method for debugging (DEBUG level)
    if auth_method:
        logger.debug(
            f"Authentication resolved: {auth_method}",
            extra={
                "auth_method": auth_method,
                "path": request.url.path,
                "cookie_fallback": cookie_found_but_invalid
            }
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Token de autenticação não fornecido"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    request_id = x_request_id or str(uuid4())

    try:
        # Decodificar JWT (se não foi decodificado ainda na tentativa de cookie)
        if auth_method != "COOKIE" or cookie_found_but_invalid:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")

            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": ErrorCode.UNAUTHORIZED.value,
                        "message": "Token inválido: subject ausente"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )

        user_id = UUID(user_id_str)

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Token inválido ou expirado"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Buscar usuário
    result = await db.execute(
        select(User).where(
            User.id == str(user_id),
            User.deleted_at.is_(None)
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Usuário não encontrado"
            }
        )

    # Validar vínculo ativo (R42, RF3) exceto superadmin (R3)
    membership_id = None
    organization_id = None
    role_code = "dirigente" if user.is_superadmin else "atleta"

    if not user.is_superadmin:
        now = datetime.now(timezone.utc)
        # V1.2: OrgMembership não tem status, usa start_at/end_at
        result = await db.execute(
            select(OrgMembership).where(
                OrgMembership.person_id == user.person_id,
                OrgMembership.deleted_at.is_(None),
                OrgMembership.start_at <= now,
                (OrgMembership.end_at.is_(None)) | (OrgMembership.end_at >= now),
            )
        )
        active_membership = result.scalars().first()

        if not active_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": ErrorCode.NO_ACTIVE_MEMBERSHIP.value,
                    "message": "Usuário sem vínculo ativo não pode operar",
                    "details": {"constraint": "R42"}
                }
            )

        # Converter IDs garantindo compatibilidade com objetos UUID nativos do driver
        membership_id = active_membership.id if isinstance(active_membership.id, UUID) else UUID(str(active_membership.id))
        organization_id = active_membership.organization_id if isinstance(active_membership.organization_id, UUID) else UUID(str(active_membership.organization_id))

        # Buscar role code
        from app.models.role import Role
        result = await db.execute(
            select(Role).where(Role.id == active_membership.role_id)
        )
        role = result.scalars().first()
        role_code = role.code if role else "atleta"

    else:
        # Superadmin pode não ter vínculo (R3)
        membership_id = None
        role_code = "dirigente"  # Default para superadmin

        # V1.2: Superadmin pode escolher organização via header x-organization-id
        if x_organization_id:
            try:
                organization_id = UUID(x_organization_id)
                # Validar que a organização existe
                result = await db.execute(
                    select(Organization).where(
                        Organization.id == organization_id,
                        Organization.deleted_at.is_(None)
                    )
                )
                org = result.scalars().first()
                if not org:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "INVALID_ORGANIZATION",
                            "message": f"Organização {x_organization_id} não encontrada"
                        }
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "INVALID_ORGANIZATION_ID",
                        "message": "x-organization-id deve ser um UUID válido"
                    }
                )
        else:
            # Buscar primeira organização (único clube - R34)
            result = await db.execute(
                select(Organization).where(Organization.deleted_at.is_(None))
            )
            org = result.scalars().first()
            organization_id = org.id if isinstance(org.id, UUID) else UUID(str(org.id)) if org else UUID('00000000-0000-0000-0000-000000000000')

    # Criar contexto
    def to_uuid(val):
        if val is None: return None
        if isinstance(val, UUID): return val
        return UUID(str(val))

    user_id_uuid = to_uuid(user.id)
    person_id_uuid = to_uuid(user.person_id)

    # Resolver permissões do mapa canônico
    permissions = get_permissions_for_role(role_code)

    # Buscar team_ids (equipes que o usuário tem acesso)
    team_ids: List[UUID] = []
    if person_id_uuid and organization_id:
        from app.models.team_registration import TeamRegistration
        from app.models.athlete import Athlete
        from app.models.team import Team

        # Se for atleta, buscar equipes onde está registrado
        result = await db.execute(
            select(Athlete).where(
                Athlete.person_id == str(person_id_uuid),
                Athlete.deleted_at.is_(None)
            )
        )
        athlete = result.scalars().first()

        if athlete:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(TeamRegistration).join(
                    Team, TeamRegistration.team_id == Team.id
                ).where(
                    TeamRegistration.athlete_id == athlete.id,
                    TeamRegistration.deleted_at.is_(None),
                    Team.organization_id == str(organization_id),
                    (TeamRegistration.end_at.is_(None)) | (TeamRegistration.end_at >= now)
                )
            )
            registrations = result.scalars().all()

            team_ids = [to_uuid(reg.team_id) for reg in registrations]

    return ExecutionContext(
        user_id=user_id_uuid,
        email=user.email,
        role_code=role_code,
        request_id=request_id,
        person_id=person_id_uuid,
        is_superadmin=user.is_superadmin,
        organization_id=organization_id,
        membership_id=membership_id,
        team_ids=team_ids,
        permissions=permissions,
    )

def require_role(allowed_roles: list[str]):
    """
    Dependency para validar papel (FASE 6)

    Referências RAG:
    - R25: Permissões por papel
    - R26: Hierarquia (dirigente > coordenador > treinador > atleta)
    - R3: Superadmin bypassa todas as verificações

    Args:
        allowed_roles: Lista de papéis autorizados

    Returns:
        Dependency function que valida papel e retorna ExecutionContext

    Raises:
        HTTPException 403: Se papel não autorizado

    Exemplo:
        @router.post("/athletes")
        async def create_athlete(
            ctx: ExecutionContext = Depends(require_role(["coordenador", "dirigente"]))
        ):
            ...
    """
    from app.schemas.error import ErrorCode
    
    async def dependency(ctx: ExecutionContext = Depends(get_current_context)) -> ExecutionContext:
        if ctx.is_superadmin:
            return ctx  # Bypass (R3)
        
        if ctx.role_code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": ErrorCode.FORBIDDEN.value,
                    "message": f"Papel '{ctx.role_code}' não autorizado para esta operação",
                    "details": {
                        "constraint": "R25",
                        "allowed_roles": allowed_roles,
                        "user_role": ctx.role_code
                    }
                }
            )
        
        return ctx
    
    return dependency


# Contexto mock para desenvolvimento/testes (FASE 2 - mantido para compatibilidade)
def get_mock_context() -> ExecutionContext:
    """
    Contexto mock para testes e desenvolvimento inicial

    ATENÇÃO: Use get_current_context() em produção
    """
    return ExecutionContext(
        user_id=uuid4(),
        email="mock@test.com",
        role_code="coordenador",
        request_id="mock-request-id",
        person_id=uuid4(),
        is_superadmin=False,
        organization_id=uuid4(),
        membership_id=uuid4(),
        team_ids=[],
        permissions=get_permissions_for_role("coordenador"),
    )

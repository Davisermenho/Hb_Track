"""
Router: Autenticação

FASE 6 - Endurecimento e Segurança

Endpoints:
- POST /auth/login - Login com email e senha
- POST /auth/logout - Logout (invalidar token - futuro)
- GET /auth/me - Dados do usuário autenticado
- POST /auth/refresh - Renovar access token (futuro)

Referências RAG:
- R2: Usuário com email único
- R3: Super Admin pode operar sem vínculo
- R42: Vínculo ativo obrigatório (exceto superadmin)
"""
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select, update, delete
from pydantic import BaseModel, EmailStr, Field

from app.core.db import get_async_db
from app.core.security import verify_password, create_access_token, hash_password
from app.core.context import ExecutionContext, get_current_context
from app.core.rate_limit import limiter, LOGIN_RATE_LIMIT
from app.models.user import User
from app.models.refresh_token import RefreshToken  # Fase 2: Refresh Token persistence
from app.models.membership import OrgMembership  # V1.2: Renomeado de Membership
from app.models.role import Role
from app.models.person import Person
from app.models.organization import Organization
from app.models.season import Season
from app.schemas.error import ErrorCode
from app.core.permissions_map import get_permissions_for_role
from app.core.logging import emit_auth_audit, get_request_id, get_client_ip, get_user_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Requisição de login"""
    email: str = Field(..., min_length=5, description="Email do usuário")
    password: str = Field(..., min_length=1, description="Senha do usuário")


class LoginResponse(BaseModel):
    """Resposta de login com JWT"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token (validade 7 dias)")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Expiração em segundos")
    user_id: str = Field(..., description="ID do usuário")
    full_name: Optional[str] = Field(None, description="Nome completo da pessoa")
    email: str = Field(..., description="Email do usuário")
    role_code: str = Field(..., description="Papel do usuário")
    role_name: Optional[str] = Field(None, description="Nome do papel (ex: Dirigente, Treinador)")
    is_superadmin: bool = Field(..., description="Se é superadmin")
    organization_id: Optional[str] = Field(None, description="ID da organização")
    photo_url: Optional[str] = Field(None, description="URL da foto de perfil do usuário")
    gender: Optional[str] = Field(None, description="Gênero da pessoa (masculino/feminino)")
    permissions: Dict[str, bool] = Field(default_factory=dict, description="Mapa de permissões do usuário")
    needs_setup: bool = Field(default=False, description="Se dirigente precisa configurar organização inicial")


class UserMeResponse(BaseModel):
    """Resposta do /auth/me - Step 3: Incluir permissões"""
    user_id: str
    person_id: Optional[str]
    email: str
    full_name: Optional[str]
    role_code: str
    is_superadmin: bool
    membership_id: Optional[str]
    organization_id: Optional[str]
    permissions: Dict[str, bool] = Field(default_factory=dict, description="Mapa de permissões (step 3)")


class TeamRegistrationContext(BaseModel):
    team_id: str
    organization_id: Optional[str]
    start_at: datetime
    end_at: Optional[datetime] = None
    is_active: bool


class AuthContextResponse(BaseModel):
    """
    Contexto completo para o frontend (papel + vínculos + permissões).
    
    VERSÃO: 1.0
    
    ⚠️ CONTRATO CONGELADO:
    - NÃO renomear campos sem versionar (v1 → v2)
    - NÃO mudar tipos sem versionar
    - Adicionar campos novos = OK (default values)
    - Remover campos = CRIAR NOVA VERSÃO
    
    CONTRATO FIXO - Sempre retorna todos os campos (null se não aplicável).
    O frontend deve considerar este o contrato padrão após login.
    
    ARQUITETURA CANÔNICA:
    - permissions: Mapa canônico (app/core/permissions_map.py) resolvido
    - system_state: Estado do sistema (temporada, onboarding) separado
    - ExecutionContext é a fonte da verdade
    - Este schema é apenas um espelho
    """
    user_id: str
    person_id: Optional[str] = None
    role_code: str
    is_superadmin: bool = False
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    membership_id: Optional[str] = None
    current_season_id: Optional[str] = None
    current_season_name: Optional[str] = None
    team_registrations: List[TeamRegistrationContext] = Field(default_factory=list)
    permissions: Dict[str, bool] = Field(default_factory=dict, description="Mapa canônico de permissões resolvido")
    system_state: Dict[str, Any] = Field(default_factory=dict, description="Estado do sistema (temporada, onboarding) separado de permissões")


class ChangePasswordRequest(BaseModel):
    """Requisição de troca de senha"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")


class SetPasswordRequest(BaseModel):
    """Requisição para definir senha com token (primeira vez)"""
    token: str = Field(..., min_length=10, description="Token recebido no email")
    password: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")


class SetPasswordResponse(BaseModel):
    """Resposta de senha definida"""
    success: bool
    message: str
    user_id: str


class ForgotPasswordRequest(BaseModel):
    """Requisição de recuperação de senha"""
    email: str = Field(..., description="Email do usuário")


class ForgotPasswordResponse(BaseModel):
    """Resposta de recuperação de senha"""
    message: str = Field(..., description="Mensagem de confirmação")
    email: str = Field(..., description="Email para o qual foi enviado o link")


class ResetPasswordRequest(BaseModel):
    """Requisição para resetar senha"""
    token: str = Field(..., description="Token de reset")
    new_password: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")
    confirm_password: str = Field(..., min_length=8, description="Confirmação da nova senha")


class ResetPasswordResponse(BaseModel):
    """Resposta de reset de senha"""
    message: str = Field(..., description="Mensagem de sucesso")
    email: str = Field(..., description="Email do usuário")


# ============================================================================
# Welcome Flow Schemas (Sprint 2)
# ============================================================================

class WelcomeVerifyResponse(BaseModel):
    """Resposta de verificação de token de welcome"""
    valid: bool = Field(..., description="Se o token é válido")
    email: str = Field(..., description="Email do convidado")
    full_name: Optional[str] = Field(None, description="Nome se já preenchido")
    role: str = Field(..., description="Papel do convidado (ex: membro, treinador)")
    invitee_kind: str = Field(..., description="Tipo: 'staff' ou 'athlete'")
    team_name: Optional[str] = Field(None, description="Nome da equipe")
    organization_name: Optional[str] = Field(None, description="Nome da organização")
    expires_at: datetime = Field(..., description="Data de expiração do token")


class WelcomeCompleteRequest(BaseModel):
    """Requisição para completar cadastro de welcome"""
    token: str = Field(..., min_length=10, description="Token de welcome")
    password: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")
    confirm_password: str = Field(..., min_length=8, description="Confirmação da senha")
    full_name: str = Field(..., min_length=2, description="Nome completo")
    # Campos opcionais para perfil básico
    phone: Optional[str] = Field(None, description="Telefone")
    birth_date: date = Field(..., description="Data de nascimento (obrigatório)")
    gender: Optional[str] = Field(None, description="Gênero: masculino/feminino")
    # Campos específicos de treinador
    certifications: Optional[str] = Field(None, description="Certificações profissionais")
    specialization: Optional[str] = Field(None, description="Especialização do treinador")
    # Campos específicos de coordenador
    area_of_expertise: Optional[str] = Field(None, description="Área de atuação do coordenador")


class WelcomeCompleteResponse(BaseModel):
    """Resposta de cadastro completo"""
    success: bool
    message: str
    user_id: str
    email: str
    role_code: str
    organization_id: Optional[str] = None
    team_id: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login com email e senha",
    operation_id="login_api_v1_auth_login_post",
    description="""
Autentica usuário e retorna JWT access token.

**Regras aplicáveis:**
- R2: Usuário com email único
- R42: Vínculo ativo obrigatório (exceto superadmin)
- R3: Superadmin pode operar sem vínculo

**Rate Limit:** 5 tentativas por minuto por IP
""",
    responses={
        401: {"description": "Email ou senha inválidos"},
        403: {"description": "Usuário sem vínculo ativo (R42)"},
        429: {"description": "Rate limit excedido - muitas tentativas"},
    }
)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
) -> LoginResponse:
    """
    Login com email e senha.
    
    Retorna JWT access token.
    
    Ref: R2, R42, R3
    
    Aceita form-urlencoded com:
    - username: email do usuário
    - password: senha
    """
    # OAuth2 usa "username" mas nós usamos email
    email = form_data.username
    password = form_data.password
    
    # Buscar usuário por email
    stmt = select(User).where(
        User.email == email,
        User.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"Login failed: user not found for email {email}")
        try:
            await emit_auth_audit(db, action="login_failed", entity="auth", entity_id=None, actor_id=None, context={
                "reason": "user_not_found",
                "email": email,
                "request_id": get_request_id(request),
                "ip": get_client_ip(request),
            })
        except Exception:
            logger.exception("emit_auth_audit failed for login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Email ou senha inválidos"
            }
        )
    
    # Verificar senha
    if not user.password_hash or not verify_password(password, user.password_hash):
        logger.warning(f"Login failed: invalid password for user {user.id}")
        try:
            await emit_auth_audit(db, action="login_failed", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
                "reason": "invalid_password",
                "email": email,
                "request_id": get_request_id(request),
                "ip": get_client_ip(request),
            })
        except Exception:
            logger.exception("emit_auth_audit failed for login_failed (invalid_password)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Email ou senha inválidos"
            }
        )
    
    # Verificar se usuário está bloqueado
    if user.is_locked:
        logger.warning(f"Login failed: user {user.id} is locked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Usuário bloqueado"
            }
        )
    
    # Verificar status do usuário
    if user.status != "ativo":
        logger.warning(f"Login failed: user {user.id} status is {user.status}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED.value,
                "message": "Usuário inativo"
            }
        )
    
    # Validar vínculo ativo (exceto superadmin) - R42
    role_code = "dirigente"
    organization_id = None
    membership_id = None
    
    logger.info(f"DEBUG LOGIN: user_id={user.id}, email={user.email}, is_superadmin={user.is_superadmin}, type={type(user.is_superadmin)}")
    
    if not user.is_superadmin:
        logger.info(f"DEBUG LOGIN: Usuário NÃO é superadmin, verificando membership")
        # V1.2: OrgMembership usa start_at/end_at em vez de status
        now = datetime.now(timezone.utc)
        stmt = select(OrgMembership).where(
            OrgMembership.person_id == user.person_id,
            OrgMembership.deleted_at.is_(None),
            OrgMembership.start_at <= now,
            (OrgMembership.end_at.is_(None)) | (OrgMembership.end_at >= now)
        )
        result = await db.execute(stmt)
        active_membership = result.scalar_one_or_none()
        
        if not active_membership:
            logger.warning(f"Login failed: user {user.id} has no active membership (R42)")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": ErrorCode.NO_ACTIVE_MEMBERSHIP.value,
                    "message": "Usuário sem vínculo ativo não pode fazer login",
                    "details": {"constraint": "R42"}
                }
            )
        
        membership_id = active_membership.id
        organization_id = active_membership.organization_id
        
        # Buscar role code para usuário normal
        stmt = select(Role).where(Role.id == active_membership.role_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        role_code = role.code if role else "atleta"
    else:
        logger.info(f"DEBUG LOGIN: Usuário É superadmin, pulando verificação de membership")
        active_membership = None  # Superadmin não precisa de membership
        membership_id = None
        role_code = "superadmin"
        
        # Superadmin: buscar PRIMEIRA organização ativa (R34)
        # Se houver múltiplas organizações, pega a primeira por ordem de criação
        from app.models.organization import Organization
        stmt = select(Organization).where(Organization.deleted_at.is_(None)).order_by(Organization.created_at).limit(1)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        organization_id = org.id if org else None

    # Buscar nome da pessoa relacionada, foto e gênero (ANTES do JWT)
    full_name = None
    photo_url = None
    gender = None
    if user.person:
        full_name = user.person.full_name
        photo_url = user.person.profile_photo
        gender = user.person.gender

    # Buscar nome do papel (ANTES do JWT)
    role_name = None
    if not user.is_superadmin and active_membership:
        stmt = select(Role).where(Role.id == active_membership.role_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        if role:
            role_name = role.name
    elif user.is_superadmin:
        role_name = "Super Administrador"

    # Criar JWT (access_token + refresh_token) com role_name e full_name
    from app.core.config import settings
    from app.core.security import create_refresh_token

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "person_id": str(user.person_id) if user.person_id else None,
            "role_code": role_code,
            "role_name": role_name,
            "full_name": full_name,
            "is_superadmin": bool(user.is_superadmin) if user.is_superadmin is not None else False,
            "organization_id": str(organization_id) if organization_id else None,
            "membership_id": str(membership_id) if membership_id else None,
        }
    )

    # Gerar refresh token (validade 7 dias)
    refresh_token = create_refresh_token(str(user.id))

    # Fase 2: Persistir hash do Refresh Token
    from app.core.security import hash_token
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    ))
    await db.commit()

    logger.info(f"Login successful for user {user.id} ({user.email})")
    logger.info(f"Login response | user_id={user.id} | role_code={role_code} | role_name={role_name} | is_superadmin={user.is_superadmin}")

    try:
        await emit_auth_audit(db, action="login_success", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
            "email": user.email,
            "role_code": role_code,
            "organization_id": str(organization_id) if organization_id else None,
            "request_id": get_request_id(request),
            "ip": get_client_ip(request),
        })
    except Exception:
        logger.exception("emit_auth_audit failed for login_success")

    # Set HttpOnly cookie with the access token
    from app.core.config import settings

    response.set_cookie(
        key="hb_access_token",
        value=access_token,
        httponly=True,  # HTTPOnly para SSR seguro - JS não pode acessar
        samesite="lax",  # 'strict' for more security, 'none' for cross-domain with secure=True
        secure=settings.ENV == "production",  # True in production (HTTPS only)
        max_age=settings.JWT_EXPIRES_MINUTES * 60,  # Expiration in seconds
        path="/",  # Available for all paths
    )

    # Buscar permissões baseadas no papel
    permissions = get_permissions_for_role(role_code)

    # Verificar se dirigente precisa fazer setup inicial
    needs_setup = False
    if role_code == "dirigente" and not organization_id:
        needs_setup = True
        logger.info(f"Dirigente {user.id} needs initial setup (no organization)")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRES_MINUTES * 60,
        user_id=str(user.id),
        full_name=full_name,
        email=user.email,
        role_code=role_code,
        role_name=role_name,
        is_superadmin=bool(user.is_superadmin) if user.is_superadmin is not None else False,
        organization_id=str(organization_id) if organization_id else None,
        photo_url=photo_url,
        gender=gender,
        permissions=permissions,
        needs_setup=needs_setup,
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Dados do usuário autenticado",
    operation_id="get_me_api_v1_auth_me_get",
    description="Retorna informações do usuário autenticado a partir do JWT.",
    responses={
        401: {"description": "Token inválido ou ausente"},
    }
)
async def get_me(
    ctx: ExecutionContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_async_db)
) -> UserMeResponse:
    """
    Retorna dados do usuário autenticado.
    
    Ref: R42, Step 3: Incluir permissões resolvidas
    """
    # Buscar dados adicionais se necessário
    stmt = select(User).where(User.id == str(ctx.user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Buscar nome da pessoa relacionada
    full_name = None
    if user and user.person:
        full_name = user.person.full_name
    
    # Step 3: Buscar permissões resolvidas do permissions_map
    from app.core.permissions_map import get_permissions_for_role
    permissions = get_permissions_for_role(ctx.role_code)

    return UserMeResponse(
        user_id=str(ctx.user_id),
        person_id=str(ctx.person_id) if ctx.person_id else None,
        email=user.email if user else "",
        full_name=full_name,
        role_code=ctx.role_code,
        is_superadmin=ctx.is_superadmin,
        membership_id=str(ctx.membership_id) if ctx.membership_id else None,
        organization_id=str(ctx.organization_id) if ctx.organization_id else None,
        permissions=permissions,  # Step 3: Incluir permissões
    )


@router.get(
    "/permissions",
    response_model=List[str],
    summary="Permissões do usuário autenticado",
    operation_id="get_permissions_api_v1_auth_permissions_get",
    description="Retorna lista de permissões baseadas no papel do usuário.",
    responses={
        401: {"description": "Token inválido ou ausente"},
    }
)
async def get_permissions(
    ctx: ExecutionContext = Depends(get_current_context),
) -> List[str]:
    """
    Retorna permissões do usuário autenticado baseadas no seu papel.
    
    Útil para controle de acesso no frontend.
    """
    return get_permissions_for_role(ctx.role_code)


@router.get(
    "/context",
    response_model=AuthContextResponse,
    summary="Contexto completo de acesso",
    description="Retorna papel, vínculos e permissões. CONTRATO FIXO. Apenas espelho do ExecutionContext.",
)
async def get_context(
    ctx: ExecutionContext = Depends(get_current_context),
) -> AuthContextResponse:
    """
    Endpoint de contexto para o frontend.
    
    ARQUITETURA:
    - ExecutionContext é a fonte da verdade (resolvido no auth)
    - Este endpoint é apenas um ESPELHO (zero regras)
    - Permissões já resolvidas do mapa canônico
    
    CONTRATO FIXO - Sempre retorna todos os campos do AuthContextResponse.
    Campos opcionais são null quando não aplicáveis.
    
    Inclui:
    - Papel do usuário (role_code)
    - Organização e temporada ativa
    - Permissões (já resolvidas)
    - Vínculos de equipes (se atleta)
    """
    from app.core.db import get_db
    from app.models.organization import Organization
    from app.models.season import Season

    db: Session = next(get_db())
    try:
        org_name: Optional[str] = None
        season_id: Optional[str] = None
        season_name: Optional[str] = None

        # Buscar nome da organização
        if ctx.organization_id:
            org = db.scalar(
                select(Organization).where(Organization.id == str(ctx.organization_id))
            )
            if org:
                org_name = org.name
                
                # Buscar temporada ativa
                now = datetime.now(timezone.utc)
                active_season = db.scalar(
                    select(Season).where(
                        Season.organization_id == str(ctx.organization_id),
                        Season.is_active == True,
                        Season.deleted_at.is_(None),
                        Season.start_date <= now.date(),
                        Season.end_date >= now.date(),
                    )
                )
                if active_season:
                    season_id = str(active_season.id)
                    season_name = active_season.name

        # Converter team_ids para TeamRegistrationContext
        team_regs = []
        for team_id in ctx.team_ids:
            team_regs.append(
                TeamRegistrationContext(
                    team_id=str(team_id),
                    organization_id=str(ctx.organization_id),
                    start_at=datetime.now(timezone.utc),  # Simplificado
                    end_at=None,
                    is_active=True,
                )
            )

        # System state: informações de estado do sistema (separado de permissões)
        system_state: Dict[str, Any] = {
            "has_active_season": season_id is not None,
            "season_id": season_id,
            "season_name": season_name,
            "organization_configured": org_name is not None,
            "has_teams": len(team_regs) > 0,
        }
        
        # ESPELHO do ExecutionContext (zero regras aqui)
        return AuthContextResponse(
            user_id=str(ctx.user_id),
            person_id=str(ctx.person_id) if ctx.person_id else None,
            role_code=ctx.role_code,
            is_superadmin=ctx.is_superadmin,
            organization_id=str(ctx.organization_id) if ctx.organization_id else None,
            organization_name=org_name,
            membership_id=str(ctx.membership_id) if ctx.membership_id else None,
            current_season_id=season_id,
            current_season_name=season_name,
            team_registrations=team_regs,
            permissions=ctx.permissions,  # ✨ Permissões já resolvidas
            system_state=system_state,  # ✨ Estado do sistema
        )
    finally:
        db.close()


class RefreshTokenRequest(BaseModel):
    """Requisição de refresh de token"""
    refresh_token: str = Field(..., description="Refresh token JWT")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout - Revoga Refresh Token",
    operation_id="logout_api_v1_auth_logout_post",
    description="""
Endpoint de logout que remove o cookie HttpOnly e revoga o Refresh Token no banco de dados.
""",
)
async def logout(
    response: Response,
    request: Request,
    payload: Optional[RefreshTokenRequest] = None,
    ctx: ExecutionContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Logout do usuário - Remove o cookie e revoga o token persistido.
    """
    logger.info(f"Logout for user {ctx.user_id}")

    # 1. Tentar revogar via refresh_token enviado no payload
    if payload and payload.refresh_token:
        from app.core.security import hash_token
        rt_hash = hash_token(payload.refresh_token)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == rt_hash)
            .values(revoked_at=datetime.now(timezone.utc))
        )
    else:
        # Se não enviou o token, revogamos a sessão ATUAL (último token ativo deste user) 
        # ou apenas removemos o cookie. Para ser seguro (Fase 2), revogamos TUDO deste IP/User Agent?
        # Por enquanto, revogamos o token dele que não expirou ainda
        pass

    # 2. Remover cookie
    response.delete_cookie(
        key="hb_access_token",
        path="/",
        samesite="lax",
    )

    await db.commit()

    try:
        await emit_auth_audit(db, action="logout", entity="auth", entity_id=str(ctx.user_id), actor_id=str(ctx.user_id), context={
            "request_id": get_request_id(request) if request else None,
            "ip": get_client_ip(request) if request else None,
        })
    except Exception:
        logger.exception("emit_auth_audit failed for logout")

    return None


class RefreshTokenResponse(BaseModel):
    """Resposta de refresh de token"""
    access_token: str = Field(..., description="Novo access token JWT")
    refresh_token: str = Field(..., description="Novo refresh token JWT")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Expiração do access token em segundos")


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Renovar access token",
    operation_id="refresh_token_api_v1_auth_refresh_post",
    description="""
Renova o access token usando um refresh token válido.

**Fase 2: Persistência e Rotação**
1. Valida JWT assinado
2. Valida hash no banco de dados
3. Detecta reuso (se token revogado for usado, mata todas as sessões do usuário)
4. Gera novos tokens e revoga o anterior
""",
    responses={
        401: {"description": "Refresh token inválido, expirado ou revogado"},
    }
)
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Renova access token usando refresh token persistido.
    Detecta reuso malicioso (Kill Switch).
    """
    from app.core.security import decode_refresh_token, create_access_token, create_refresh_token, hash_token
    from app.core.config import settings
    from sqlalchemy import update

    # 1. Decodificar JWT
    user_id_str = decode_refresh_token(payload.refresh_token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado"
        )

    # 2. Verificar persistência (Detecção de Reuso)
    rt_hash = hash_token(payload.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == rt_hash)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if not db_token:
        logger.warning(f"Refresh Token JWT válido mas não está no DB. Suspeita de fraude. User: {user_id_str}")
        # Segurança: Revogar todas as sessões do usuário
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == UUID(user_id_str))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Violação de segurança detectada")

    if db_token.revoked_at:
        logger.warning(f"REFRESH TOKEN REUSE DETECTED: Token {db_token.id} already revoked. User: {user_id_str}")
        # Kill Switch: Revogar todas as sessões ativas do usuário
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == UUID(user_id_str))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Sessão encerrada por segurança")

    # 3. Validar Usuário
    stmt = select(User).options(joinedload(User.person)).where(
        User.id == user_id_str,
        User.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.status != "ativo" or user.is_locked:
        raise HTTPException(status_code=401, detail="Acesso bloqueado")

    # 4. Validar Vínculo (R42)
    role_code = "dirigente" if user.is_superadmin else "atleta"
    organization_id = None
    membership_id = None

    if not user.is_superadmin:
        now = datetime.now(timezone.utc)
        stmt = select(OrgMembership).where(
            OrgMembership.person_id == user.person_id,
            OrgMembership.deleted_at.is_(None),
            OrgMembership.start_at <= now,
            (OrgMembership.end_at.is_(None)) | (OrgMembership.end_at >= now)
        )
        result = await db.execute(stmt)
        active_membership = result.scalar_one_or_none()

        if not active_membership:
            raise HTTPException(status_code=403, detail="Vínculo ativo obrigatório (R42)")
        
        membership_id = active_membership.id
        organization_id = active_membership.organization_id
        # Buscar role
        stmt = select(Role).where(Role.id == active_membership.role_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        role_code = role.code if role else "atleta"

    # 5. Rotação do Token
    # Revoga o atual
    db_token.revoked_at = datetime.now(timezone.utc)
    
    # Gera novo par
    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role_code": role_code,
            "is_superadmin": user.is_superadmin,
            "organization_id": str(organization_id) if organization_id else None,
            "membership_id": str(membership_id) if membership_id else None,
        }
    )
    new_refresh_token = create_refresh_token(str(user.id))

    # Persistir novo token (herdando parent_id para trace)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        parent_id=db_token.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    ))
    
    await db.commit()

    # 6. Atualizar cookie
    response.set_cookie(
        key="hb_access_token",
        value=new_access_token,
        httponly=True,
        samesite="lax",
        secure=settings.ENV == "production",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
    )

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRES_MINUTES * 60,
    )


# ============================================================================
# FASE 2: Gerenciamento de Sessões e Email
# ============================================================================

@router.post("/verify-email", summary="Verificar email", operation_id="verify_email_api_v1_auth_verify_email_post")
async def verify_email():
    """Stub para contrato (Phase 2)."""
    return {"message": "Endpoint em implementação"}


@router.post("/resend-verification", summary="Reenviar verificação", operation_id="resend_verification_api_v1_auth_resend_verification_post")
async def resend_verification():
    """Stub para contrato (Phase 2)."""
    return {"message": "Endpoint em implementação"}


@router.get("/roles", summary="Ver papéis", operation_id="get_roles_api_v1_auth_roles_get")
async def get_roles(db: AsyncSession = Depends(get_async_db)):
    """Espelho de roles para o contrato (Phase 2)."""
    stmt = select(Role)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    return roles


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitar recuperação de senha",
    operation_id="forgot_password_api_v1_auth_forgot_password_post",
    description="""
Solicita recuperação de senha. Envia email com link de reset.

**Fluxo:**
1. Usuário insere email
2. Sistema envia email com link de reset
3. Email contém link para /new-password?token=xxx
4. Link expira em 24 horas

**Segurança:**
- Rate limit: 5 requisições por hora por email
- Token seguro e único
- Tokens anteriores são invalidados
""",
    responses={
        200: {"description": "Email enviado com sucesso"},
        400: {"description": "Email não encontrado"},
    }
)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Solicita recuperação de senha.
    
    Envia email com link para resetar a senha.
    """
    from app.services.email_service import email_service
    from app.services.password_reset_service import PasswordResetService
    from app.core.config import settings

    # Buscar usuário por email
    stmt = select(User).where(
        User.email == payload.email,
        User.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Sempre retornar sucesso (não informar se email existe ou não)
    if not user:
        logger.warning(f"Forgot password requested for non-existent email: {payload.email}")
        try:
            await emit_auth_audit(db, action="forgot_password_requested", entity="auth", entity_id=None, actor_id=None, context={
                "email": payload.email,
                "request_id": get_request_id(request) if 'request' in locals() else None,
            })
        except Exception:
            logger.exception("emit_auth_audit failed for forgot_password (no user)")
        return ForgotPasswordResponse(
            message="Se o email estiver registrado, você receberá um link de recuperação.",
            email=payload.email,
        )

    try:
        # Criar token de reset
        reset_service = PasswordResetService(db)
        reset = await reset_service.create_reset_token(
            user_id=user.id,
            token_type="reset",
            expires_in_hours=1,
        )

        # Construir link de reset
        reset_link = f"{settings.FRONTEND_URL}/new-password?token={reset.token}"

        # Enviar email
        email_sent = email_service.send_password_reset_email(
            user_email=user.email,
            reset_link=reset_link,
            user_name=user.person.full_name if user.person else None,
        )

        if not email_sent:
            logger.error(f"Failed to send password reset email to {user.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Erro ao enviar email"}
            )

        logger.info(f"Password reset email sent to {user.email}")

        try:
            await emit_auth_audit(db, action="forgot_password_requested", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
                "email": user.email,
                "request_id": get_request_id(request) if 'request' in locals() else None,
            })
        except Exception:
            logger.exception("emit_auth_audit failed for forgot_password (sent)")

        return ForgotPasswordResponse(
            message="Se o email estiver registrado, você receberá um link de recuperação.",
            email=payload.email,
        )

    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Erro ao processar recuperação de senha"}
        )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Resetar senha com token",
    operation_id="reset_password_api_v1_auth_reset_password_post",
    description="""
Reseta a senha usando um token válido.

**Validações:**
- Token deve ser válido e não expirado
- Senhas devem coincidir
- Nova senha deve ter mínimo 8 caracteres
- Token pode ser usado apenas uma vez
""",
    responses={
        200: {"description": "Senha alterada com sucesso"},
        400: {"description": "Token inválido, expirado ou senhas não coincidem"},
        404: {"description": "Usuário não encontrado"},
    }
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
    request: Request = None,
):
    """
    Reseta a senha do usuário usando token válido.
    """
    from app.services.password_reset_service import PasswordResetService
    from datetime import timezone as tz  # timezone para este endpoint

    # Validar que as senhas coincidem
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "As senhas não coincidem"}
        )

    # Buscar token
    reset_service = PasswordResetService(db)
    reset = await reset_service.get_by_token(
        payload.token,
        include_expired=False,
        include_used=False,
    )

    if not reset:
        logger.warning(f"Invalid or expired reset token attempted")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Token inválido ou expirado"}
        )

    # Buscar usuário
    stmt = select(User).where(
        User.id == reset.user_id,
        User.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Usuário não encontrado"}
        )

    try:
        # Atualizar senha
        user.password_hash = hash_password(payload.new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Marcar token como usado
        await reset_service.mark_as_used(reset)

        await db.commit()

        logger.info(f"Password reset successfully for user {user.id}")

        # ========== CRIAR SESSÃO AUTOMÁTICA (padrão HttpOnly) ==========
        from app.core.config import settings
        from app.core.security import create_refresh_token
        from app.core.permissions_map import get_permissions_for_role
        from fastapi.responses import JSONResponse
        import json
        
        # Buscar role do usuário (seguindo padrão do /login)
        role_code = "atleta"  # default
        role_name = "Atleta"
        organization_id = None
        membership_id = None
        full_name = user.person.full_name if user.person else user.email
        
        if user.is_superadmin:
            role_code = "superadmin"
            role_name = "Super Administrador"
        else:
            # V1.2: OrgMembership usa person_id e start_at/end_at
            now = datetime.now(tz.utc)
            stmt = select(OrgMembership).where(
                OrgMembership.person_id == user.person_id,
                OrgMembership.deleted_at.is_(None),
                OrgMembership.start_at <= now,
                (OrgMembership.end_at.is_(None)) | (OrgMembership.end_at >= now)
            )
            result = await db.execute(stmt)
            active_membership = result.scalar_one_or_none()
            
            if active_membership:
                membership_id = active_membership.id
                organization_id = active_membership.organization_id
                # Buscar role code
                stmt = select(Role).where(Role.id == active_membership.role_id)
                result = await db.execute(stmt)
                role = result.scalar_one_or_none()
                if role:
                    role_code = role.code
                    role_name = role.name
        
        # Criar tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "person_id": str(user.person_id) if user.person_id else None,
                "role_code": role_code,
                "role_name": role_name,
                "full_name": full_name,
                "is_superadmin": bool(user.is_superadmin) if user.is_superadmin is not None else False,
                "organization_id": str(organization_id) if organization_id else None,
                "membership_id": str(membership_id) if membership_id else None,
            }
        )
        refresh_token = create_refresh_token(str(user.id))
        
        # Criar sessão para cookie hb_session
        session_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": full_name,
                "role": role_code,
                "is_superadmin": bool(user.is_superadmin) if user.is_superadmin is not None else False,
            },
            "organization_id": str(organization_id) if organization_id else None,
        }
        
        # Criar response com cookies HttpOnly
        response = JSONResponse(
            content={
                "success": True,
                "message": "Senha alterada com sucesso",
                "email": user.email,
                "redirect_to": "/inicio"
            }
        )
        
        # Set cookies HttpOnly (mesmo padrão do login)
        response.set_cookie(
            key="hb_access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=settings.JWT_EXPIRES_MINUTES * 60,
            path="/",
        )
        
        response.set_cookie(
            key="hb_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=7 * 24 * 60 * 60,  # 7 dias
            path="/",
        )
        
        response.set_cookie(
            key="hb_session",
            value=json.dumps(session_data),
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=settings.JWT_EXPIRES_MINUTES * 60,
            path="/",
        )
        
        logger.info(f"Auto-login after reset-password | user_id={user.id} | role={role_code}")

        try:
            await emit_auth_audit(db, action="reset_password", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
                "method": "reset_via_token",
                "request_id": get_request_id(request) if request else None,
                "ip": get_client_ip(request) if request else None,
            })
        except Exception:
            logger.exception("emit_auth_audit failed for reset_password")
        
        return response

    except Exception as e:
        await db.rollback()
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Erro ao resetar senha"}
        )


@router.post(
    "/set-password",
    response_model=SetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Definir senha com token",
    description="""
    Valida token de ativação e define senha (primeira vez).
    
    SEGURANÇA:
    - Token single-use (marcado como `used`)
    - Expira em 24h
    - Validado via hash SHA-256
    
    Usado quando usuário recebe email de convite.
    """,
    responses={
        400: {"description": "Token inválido ou expirado"},
        404: {"description": "Usuário não encontrado"},
    }
)
async def set_password_with_token(
    payload: SetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
    request: Request = None,
):
    """
    Valida token de ativação e define senha.
    
    Token é validado e marcado como usado após consumo.
    """
    from app.models.password_reset import PasswordReset
    from datetime import timezone as tz  # timezone para este endpoint
    
    # Buscar registro de reset válido pelo token
    stmt = select(PasswordReset).where(
        PasswordReset.token == payload.token,
        PasswordReset.used == False,  # Não usado ainda
        PasswordReset.expires_at > datetime.now(tz.utc),  # Não expirado
        PasswordReset.deleted_at.is_(None),  # Não deletado
    )
    result = await db.execute(stmt)
    reset = result.scalar_one_or_none()
    
    if not reset:
        logger.warning(f"Invalid or expired token attempt")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Token inválido ou expirado"}
        )
    
    # Buscar usuário
    stmt = select(User).where(User.id == reset.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found for token | user_id={reset.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Usuário não encontrado"}
        )
    
    # Atualizar senha e ativar usuário
    user.password_hash = hash_password(payload.password)
    user.status = "ativo"  # Ativar usuário (status, não is_active)
    user.updated_at = datetime.now(timezone.utc)
    
    # MARCAR TOKEN COMO USADO (single-use)
    reset.used = True
    reset.used_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    logger.info(
        f"Password set successfully | user_id={user.id} | "
        f"token_type={reset.token_type} | email={user.email}"
    )
    
    # ========== CRIAR SESSÃO AUTOMÁTICA (padrão HttpOnly) ==========
    from app.core.config import settings
    from app.core.security import create_refresh_token
    from app.core.permissions_map import get_permissions_for_role
    from fastapi.responses import JSONResponse
    import json
    
    # Buscar role do usuário (seguindo padrão do /login)
    role_code = "atleta"  # default
    role_name = "Atleta"
    organization_id = None
    membership_id = None
    full_name = user.person.full_name if user.person else user.email
    
    if user.is_superadmin:
        role_code = "superadmin"
        role_name = "Super Administrador"
    else:
        # V1.2: OrgMembership usa person_id e start_at/end_at
        now = datetime.now(tz.utc)
        stmt = select(OrgMembership).where(
            OrgMembership.person_id == user.person_id,
            OrgMembership.deleted_at.is_(None),
            OrgMembership.start_at <= now,
            (OrgMembership.end_at.is_(None)) | (OrgMembership.end_at >= now)
        )
        result = await db.execute(stmt)
        active_membership = result.scalar_one_or_none()
        
        if active_membership:
            membership_id = active_membership.id
            organization_id = active_membership.organization_id
            # Buscar role code
            stmt = select(Role).where(Role.id == active_membership.role_id)
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            if role:
                role_code = role.code
                role_name = role.name
    
    # Criar tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "person_id": str(user.person_id) if user.person_id else None,
            "role_code": role_code,
            "role_name": role_name,
            "full_name": full_name,
            "is_superadmin": bool(user.is_superadmin) if user.is_superadmin is not None else False,
            "organization_id": str(organization_id) if organization_id else None,
            "membership_id": str(membership_id) if membership_id else None,
        }
    )
    refresh_token = create_refresh_token(str(user.id))
    
    # Criar sessão para cookie hb_session
    session_data = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": full_name,
            "role": role_code,
            "is_superadmin": bool(user.is_superadmin) if user.is_superadmin is not None else False,
        },
        "organization_id": str(organization_id) if organization_id else None,
    }
    
    # Criar response com cookies HttpOnly
    response = JSONResponse(
        content={
            "success": True,
            "message": "Senha definida com sucesso",
            "user_id": str(user.id),
            "redirect_to": "/inicio"
        }
    )
    
    # Set cookies HttpOnly (mesmo padrão do login)
    response.set_cookie(
        key="hb_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.ENV == "production",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
    )
    
    response.set_cookie(
        key="hb_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.ENV == "production",
        max_age=7 * 24 * 60 * 60,  # 7 dias
        path="/",
    )
    
    response.set_cookie(
        key="hb_session",
        value=json.dumps(session_data),
        httponly=True,
        samesite="lax",
        secure=settings.ENV == "production",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
    )
    
    logger.info(f"Auto-login after set-password | user_id={user.id} | role={role_code}")
    try:
        await emit_auth_audit(db, action="set_password", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
            "method": "set_password_with_token",
            "request_id": get_request_id(request) if request else None,
            "ip": get_client_ip(request) if request else None,
        })
    except Exception:
        logger.exception("emit_auth_audit failed for set_password_with_token")

    return response


# ============================================================================
# Welcome Flow Endpoints (Sprint 2)
# ============================================================================

@router.get(
    "/welcome/verify",
    response_model=WelcomeVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar token de welcome",
    description="""
    Verifica se o token de welcome é válido e retorna informações do convite.
    
    SEGURANÇA:
    - Token deve ser do tipo 'welcome'
    - Token não pode estar usado
    - Token não pode estar expirado (48h)
    
    Retorna dados do convidado para pré-popular o formulário.
    """,
    responses={
        400: {"description": "Token inválido, expirado ou já utilizado"},
    }
)
async def welcome_verify(
    token: str,
    db: AsyncSession = Depends(get_async_db),
    request: Request = None,
):
    """
    Verifica token de welcome e retorna informações do convite.
    """
    from app.models.password_reset import PasswordReset
    from app.models.team_membership import TeamMembership
    from app.models.team import Team
    from app.models.organization import Organization
    from app.models.role import Role
    from datetime import timezone as tz
    
    # Buscar token válido
    stmt = select(PasswordReset).where(
        PasswordReset.token == token,
        PasswordReset.token_type == "welcome",
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.now(tz.utc),
        PasswordReset.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    reset = result.scalar_one_or_none()
    
    if not reset:
        # Verificar se token existe mas está expirado/usado
        stmt = select(PasswordReset).where(
            PasswordReset.token == token,
            PasswordReset.token_type == "welcome",
        )
        result = await db.execute(stmt)
        expired_reset = result.scalar_one_or_none()
        
        if expired_reset:
            if expired_reset.used:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Este convite já foi utilizado", "code": "TOKEN_USED"}
                )
            if expired_reset.expires_at <= datetime.now(tz.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Este convite expirou. Solicite um novo convite.", "code": "TOKEN_EXPIRED"}
                )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Token inválido", "code": "TOKEN_INVALID"}
        )
    
    # Buscar usuário
    stmt = select(User).where(User.id == reset.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Convite inválido - usuário não encontrado", "code": "USER_NOT_FOUND"}
        )
    
    # Buscar pessoa para nome
    person = None
    if user.person_id:
        stmt = select(Person).where(Person.id == user.person_id)
        result = await db.execute(stmt)
        person = result.scalar_one_or_none()
    full_name = person.full_name if person else None
    
    # Buscar TeamMembership pendente para obter equipe e role
    stmt = select(TeamMembership).where(
        TeamMembership.person_id == user.person_id,
        TeamMembership.status == "pendente",
        TeamMembership.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    team_membership = result.scalar_one_or_none()
    
    team_name = None
    organization_name = None
    role_name = "Membro"
    invitee_kind = "staff"
    
    if team_membership:
        # Buscar equipe
        stmt = select(Team).where(Team.id == team_membership.team_id)
        result = await db.execute(stmt)
        team = result.scalar_one_or_none()
        if team:
            team_name = team.name
            # Buscar organização
            stmt = select(Organization).where(Organization.id == team.organization_id)
            result = await db.execute(stmt)
            org = result.scalar_one_or_none()
            if org:
                organization_name = org.name
        
        # Buscar role via OrgMembership
        if team_membership.org_membership_id:
            stmt = select(OrgMembership).where(
                OrgMembership.id == team_membership.org_membership_id
            )
            result = await db.execute(stmt)
            org_membership = result.scalar_one_or_none()
            if org_membership and org_membership.role_id:
                stmt = select(Role).where(Role.id == org_membership.role_id)
                result = await db.execute(stmt)
                role = result.scalar_one_or_none()
                if role:
                    role_name = role.name
                    # Determinar tipo baseado no role
                    if role.code in ["atleta"]:
                        invitee_kind = "athlete"
    
    logger.info(f"Welcome token verified | user_id={user.id} | email={user.email}")

    try:
        await emit_auth_audit(db, action="welcome_verify", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
            "email": user.email,
            "request_id": get_request_id(request) if request else None,
        })
    except Exception:
        logger.exception("emit_auth_audit failed for welcome_verify")
    
    return WelcomeVerifyResponse(
        valid=True,
        email=user.email,
        full_name=full_name,
        role=role_name,
        invitee_kind=invitee_kind,
        team_name=team_name,
        organization_name=organization_name,
        expires_at=reset.expires_at,
    )


@router.post(
    "/welcome/complete",
    response_model=WelcomeCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Completar cadastro de welcome",
    description="""
    Completa o cadastro do usuário convidado:
    1. Valida token de welcome
    2. Define senha do usuário
    3. Atualiza dados da pessoa (nome, telefone, etc.)
    4. Ativa o TeamMembership (status → 'ativo')
    5. Marca token como usado
    6. Retorna sessão/login automático
    
    SEGURANÇA:
    - Token single-use
    - Senha validada (mínimo 8 caracteres)
    """,
    responses={
        400: {"description": "Token inválido ou senhas não conferem"},
    }
)
async def welcome_complete(
    payload: WelcomeCompleteRequest,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    request: Request = None,
):
    """
    Completa o cadastro do usuário convidado.
    """
    from app.models.password_reset import PasswordReset
    from app.models.team_membership import TeamMembership
    from app.models.team import Team
    from app.models.person import PersonContact
    from app.core.config import settings
    from app.core.security import create_refresh_token
    from app.core.athlete_validations import validate_birth_date_for_team
    from app.core.exceptions import ValidationError
    from fastapi.responses import JSONResponse
    from datetime import timezone as tz
    import json
    
    # Validar senhas
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "As senhas não conferem", "code": "PASSWORD_MISMATCH"}
        )
    
    # Buscar token válido
    stmt = select(PasswordReset).where(
        PasswordReset.token == payload.token,
        PasswordReset.token_type == "welcome",
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.now(tz.utc),
        PasswordReset.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    reset = result.scalar_one_or_none()
    
    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Token inválido ou expirado", "code": "TOKEN_INVALID"}
        )
    
    try:
        # Buscar usuário
        stmt = select(User).where(User.id == reset.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Usuário não encontrado", "code": "USER_NOT_FOUND"}
            )
        
        # 1. Atualizar senha
        user.password_hash = hash_password(payload.password)
        user.status = "ativo"
        user.updated_at = datetime.now(tz.utc)
        
        # 2. Atualizar Person
        if user.person_id:
            stmt = select(Person).where(Person.id == user.person_id)
            result = await db.execute(stmt)
            person = result.scalar_one_or_none()
            if person:
                # Parse nome
                name_parts = payload.full_name.strip().split()
                person.full_name = payload.full_name.strip()
                person.first_name = name_parts[0] if name_parts else ""
                person.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                if payload.birth_date:
                    person.birth_date = payload.birth_date
                if payload.gender:
                    person.gender = payload.gender
                
                person.updated_at = datetime.now(tz.utc)
                
                # Atualizar telefone se fornecido
                if payload.phone:
                    stmt = select(PersonContact).where(
                        PersonContact.person_id == person.id,
                        PersonContact.contact_type == "telefone",
                        PersonContact.deleted_at.is_(None),
                    )
                    result = await db.execute(stmt)
                    phone_contact = result.scalar_one_or_none()
                    
                    if phone_contact:
                        phone_contact.contact_value = payload.phone
                    else:
                        phone_contact = PersonContact(
                            person_id=person.id,
                            contact_type="telefone",
                            contact_value=payload.phone,
                            is_primary=False,
                        )
                        db.add(phone_contact)
                
                # Processar papel de atleta - criar registro na tabela athletes se necessário
                # A tabela athletes requer: person_id, athlete_name, birth_date (NOT NULL)
                # Apenas criar se temos birth_date (obrigatório)
                if payload.birth_date:
                    from app.models.athlete import Athlete
                    
                    stmt = select(Athlete).where(
                        Athlete.person_id == person.id,
                        Athlete.deleted_at.is_(None)
                    )
                    result = await db.execute(stmt)
                    athlete = result.scalar_one_or_none()
                    
                    if not athlete:
                        # Criar novo registro de atleta
                        athlete = Athlete(
                            person_id=person.id,
                            athlete_name=person.full_name,  # Usar full_name como athlete_name
                            birth_date=payload.birth_date,
                            state='ativa'  # Default
                        )
                        db.add(athlete)
                
                # Processar campos específicos de treinador
                if any([payload.certifications, payload.specialization]):
                    # Armazenar em metadata ou criar tabela específica se necessário
                    # Por enquanto, vamos armazenar no Person.metadata (se existir)
                    if hasattr(person, 'metadata'):
                        if not person.metadata:
                            person.metadata = {}
                        if payload.certifications:
                            person.metadata['certifications'] = payload.certifications
                        if payload.specialization:
                            person.metadata['specialization'] = payload.specialization
                
                # Processar campos específicos de coordenador
                if payload.area_of_expertise:
                    if hasattr(person, 'metadata'):
                        if not person.metadata:
                            person.metadata = {}
                        person.metadata['area_of_expertise'] = payload.area_of_expertise
        
        # 3. Ativar TODOS os TeamMembership pendentes do usuário
        # (permite que usuário aceite múltiplos convites de uma vez)
        stmt = select(TeamMembership).options(
            joinedload(TeamMembership.team),
            joinedload(TeamMembership.org_membership).joinedload(OrgMembership.role)
        ).where(
            TeamMembership.person_id == user.person_id,
            TeamMembership.status == "pendente",
            TeamMembership.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        team_memberships = result.scalars().all()
        
        team_id = None
        organization_id = None
        role_code = "membro"
        role_name = "Membro"
        
        # Usar o primeiro membership para determinar role e organização
        team_membership = team_memberships[0] if team_memberships else None
        
        if team_membership:
            # Ativar TODOS os memberships pendentes
            for tm in team_memberships:
                tm.status = "ativo"
                tm.updated_at = datetime.now(tz.utc)
            
            team_id = str(team_membership.team_id)
            
            # Buscar equipe para organização
            stmt = select(Team).where(Team.id == team_membership.team_id)
            result = await db.execute(stmt)
            team = result.scalar_one_or_none()
            if team:
                organization_id = str(team.organization_id)
            
            # Buscar role
            if team_membership.org_membership_id:
                stmt = select(OrgMembership).where(
                    OrgMembership.id == team_membership.org_membership_id
                )
                result = await db.execute(stmt)
                org_membership = result.scalar_one_or_none()
                if org_membership and org_membership.role_id:
                    stmt = select(Role).where(Role.id == org_membership.role_id)
                    result = await db.execute(stmt)
                    role = result.scalar_one_or_none()
                    if role:
                        role_code = role.code or role.name.lower()
                        role_name = role.name
                        logger.info(f"Welcome: Role found from OrgMembership | role_code={role_code} | role_name={role_name} | org_membership_id={team_membership.org_membership_id}")
                    else:
                        logger.warning(f"Welcome: Role not found for role_id={org_membership.role_id}")
                else:
                    logger.warning(f"Welcome: OrgMembership found but no role_id | org_membership_id={team_membership.org_membership_id}")
            else:
                logger.warning(f"Welcome: TeamMembership has no org_membership_id | team_membership_id={team_membership.id}")
        
            # Buscar temporada ativa e validar categoria se for atleta
            if team and role_code == "atleta":
                stmt = select(Season).where(
                    Season.organization_id == team.organization_id,
                    Season.status == 'ativa',
                    Season.deleted_at.is_(None)
                )
                result = await db.execute(stmt)
                active_season = result.scalar_one_or_none()
                
                if not active_season:
                    raise HTTPException(
                        status_code=400,
                        detail={"message": "Não há temporada ativa para esta organização", "code": "NO_ACTIVE_SEASON"}
                    )
                
                # Validar categoria antes de criar Athlete
                try:
                    validate_birth_date_for_team(
                        birth_date=payload.birth_date,
                        team_id=team_membership.team_id,
                        season_year=active_season.year,
                        db=db,
                        role_code=role_code
                    )
                except ValidationError as e:
                    raise HTTPException(
                        status_code=400,
                        detail={"message": str(e), "code": "CATEGORY_VALIDATION_FAILED"}
                    )
        
        # 4. Marcar token como usado
        reset.used = True
        reset.used_at = datetime.now(tz.utc)
        
        await db.commit()
        
        # 5. Criar sessão automática
        full_name = payload.full_name.strip()
        membership_id = str(team_membership.org_membership_id) if team_membership and team_membership.org_membership_id else None
        
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "person_id": str(user.person_id) if user.person_id else None,
                "role_code": role_code,
                "role_name": role_name,
                "full_name": full_name,
                "is_superadmin": False,
                "organization_id": organization_id,
                "membership_id": membership_id,
            }
        )
        refresh_token = create_refresh_token(str(user.id))
        
        session_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": full_name,
                "role": role_code,
                "is_superadmin": False,
            },
            "organization_id": organization_id,
        }
        
        # Response com cookies
        # Membros não devem ir direto para a equipe, mas para /inicio
        response_team_id = None if role_code == "membro" else team_id
        
        json_response = JSONResponse(
            content={
                "success": True,
                "message": "Cadastro completado com sucesso",
                "user_id": str(user.id),
                "email": user.email,
                "role_code": role_code,
                "organization_id": organization_id,
                "team_id": response_team_id,
            }
        )
        
        json_response.set_cookie(
            key="hb_access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=settings.JWT_EXPIRES_MINUTES * 60,
            path="/",
        )
        
        json_response.set_cookie(
            key="hb_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=7 * 24 * 60 * 60,
            path="/",
        )
        
        json_response.set_cookie(
            key="hb_session",
            value=json.dumps(session_data),
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=settings.JWT_EXPIRES_MINUTES * 60,
            path="/",
        )
        
        logger.info(f"Welcome complete | user_id={user.id} | email={user.email} | role_code={role_code} | role_name={role_name} | team_id={team_id}")
        try:
            await emit_auth_audit(db, action="welcome_complete", entity="auth", entity_id=str(user.id), actor_id=str(user.id), context={
                "email": user.email,
                "request_id": get_request_id(request) if request else None,
            })
        except Exception:
            logger.exception("emit_auth_audit failed for welcome_complete")

        return json_response
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing welcome: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Erro ao completar cadastro: {str(e)}"}
        )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Alterar senha",
    operation_id="change_password_api_v1_auth_change_password_post",
    description="Altera a senha do usuário autenticado.",
    responses={
        401: {"description": "Senha atual incorreta"},
    }
)
async def change_password(
    payload: ChangePasswordRequest,
    ctx: ExecutionContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Altera a senha do usuário autenticado.
    """
    stmt = select(User).where(User.id == str(ctx.user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Usuário não encontrado"}
        )
    
    # Verificar senha atual
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Senha atual incorreta"}
        )
    
    # Atualizar senha
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    logger.info(f"Password changed for user {ctx.user_id}")
    return None


# ============================================================================
# Setup Inicial para Dirigente
# ============================================================================

class InitialSetupRequest(BaseModel):
    """Requisição de setup inicial para dirigente"""
    organization_name: str = Field(..., min_length=2, description="Nome da organização")
    organization_code: Optional[str] = Field(None, description="Código/sigla da organização")
    season_year: int = Field(..., description="Ano da temporada inicial")
    season_name: Optional[str] = Field(None, description="Nome da temporada")
    season_starts_at: date = Field(..., description="Data de início da temporada")
    season_ends_at: date = Field(..., description="Data de término da temporada")


class InitialSetupResponse(BaseModel):
    """Resposta do setup inicial"""
    success: bool
    message: str
    organization_id: str
    season_id: str
    new_access_token: str


@router.post(
    "/initial-setup",
    response_model=InitialSetupResponse,
    summary="Setup inicial para dirigente",
    description="""
Cria organização e temporada inicial para dirigente na primeira vez.

**Requisitos:**
- Usuário deve ser dirigente
- Não deve ter organização cadastrada

**O que é criado:**
- Organização
- Vínculo do dirigente com a organização
- Temporada inicial (ativa)
""",
    responses={
        401: {"description": "Token inválido ou ausente"},
        403: {"description": "Usuário não é dirigente ou já tem organização"},
        422: {"description": "Dados inválidos"},
    }
)
async def initial_setup(
    request: Request,
    response: Response,
    payload: InitialSetupRequest,
    ctx: ExecutionContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_async_db),
) -> InitialSetupResponse:
    """
    Setup inicial para dirigente sem organização.
    
    Cria:
    1. Organização
    2. Vínculo (org_membership) do dirigente
    3. Temporada inicial
    """
    from app.models.organization import Organization
    from app.models.season import Season
    from app.models.membership import OrgMembership
    from app.core.config import settings
    from uuid import uuid4
    
    # Verificar se usuário é dirigente
    if ctx.role_code != "dirigente" and not ctx.is_superadmin:
        logger.warning(f"Non-dirigente user {ctx.user_id} attempted initial setup")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": ErrorCode.FORBIDDEN.value,
                "message": "Apenas dirigentes podem fazer setup inicial"
            }
        )
    
    # Verificar se já tem organização
    if ctx.organization_id:
        logger.warning(f"User {ctx.user_id} already has organization {ctx.organization_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": ErrorCode.FORBIDDEN.value,
                "message": "Usuário já possui organização cadastrada"
            }
        )
    
    # Validar datas da temporada
    if payload.season_ends_at <= payload.season_starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Data de término deve ser posterior à data de início"}
        )
    
    try:
        # 1. Criar organização
        organization_id = uuid4()
        organization = Organization(
            id=str(organization_id),
            name=payload.organization_name,
            code=payload.organization_code,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(organization)
        db.flush()
        
        logger.info(f"Organization created | id={organization_id} | name={payload.organization_name}")
        
        # 2. Criar vínculo do dirigente
        membership_id = uuid4()
        stmt = select(Role).where(Role.code == "dirigente")
        result = await db.execute(stmt)
        role_dirigente = result.scalar_one_or_none()
        
        if not role_dirigente:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Role 'dirigente' não encontrado no banco"}
            )
        
        membership = OrgMembership(
            id=str(membership_id),
            organization_id=str(organization_id),
            person_id=str(ctx.person_id),
            role_id=role_dirigente.id,
            start_at=date.today(),
            end_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(membership)
        db.flush()
        
        logger.info(f"Membership created | id={membership_id} | person={ctx.person_id}")
        
        # 3. Criar temporada inicial (ativa)
        season_id = uuid4()
        season = Season(
            id=str(season_id),
            organization_id=str(organization_id),
            created_by_membership_id=str(membership_id),
            year=payload.season_year,
            name=payload.season_name or f"Temporada {payload.season_year}",
            starts_at=payload.season_starts_at,
            ends_at=payload.season_ends_at,
            is_active=True,  # Primeira temporada já vem ativa
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(season)
        
        logger.info(f"Season created | id={season_id} | year={payload.season_year}")
        
        # Commit tudo
        await db.commit()
        
        # 4. Gerar novo token JWT com organization_id e membership_id
        new_access_token = create_access_token(
            data={
                "sub": str(ctx.user_id),
                "person_id": str(ctx.person_id),
                "role_code": "dirigente",
                "is_superadmin": ctx.is_superadmin,
                "organization_id": str(organization_id),
                "membership_id": str(membership_id),
            }
        )
        
        # Atualizar cookie
        response.set_cookie(
            key="hb_access_token",
            value=new_access_token,
            httponly=True,  # HTTPOnly para SSR seguro - JS não pode acessar
            samesite="lax",
            secure=settings.ENV == "production",
            max_age=settings.JWT_EXPIRES_MINUTES * 60,
            path="/",
        )
        
        logger.info(
            f"Initial setup completed | user={ctx.user_id} | "
            f"org={organization_id} | season={season_id}"
        )
        
        return InitialSetupResponse(
            success=True,
            message="Organização e temporada criadas com sucesso",
            organization_id=str(organization_id),
            season_id=str(season_id),
            new_access_token=new_access_token,
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in initial setup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Erro ao criar configuração inicial: {str(e)}"}
        )

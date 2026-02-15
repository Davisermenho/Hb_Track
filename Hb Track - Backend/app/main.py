"""
Aplicação principal FastAPI - HB Tracking

FASE 7 - Preparação para Produção

Referências RAG:
- R31: Ações críticas auditáveis
- R32: Log obrigatório (quem, quando, o quê)
- R34: Clube único na V1
- R42: Modo somente leitura sem vínculo ativo
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.csrf import CSRFMiddleware
from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError, ConflictError
from app.api.v1 import api_router
from app.schemas.error import ErrorCode
import logging
import traceback

# Configurar logging estruturado (FASE 7)
setup_logging(settings.ENV, settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION_NUMBER,
    docs_url=f"/api/{settings.API_VERSION}/docs",
    redoc_url=f"/api/{settings.API_VERSION}/redoc",
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json"
)

# ============================================================================
# Middlewares - Ordem Importa!
# FastAPI processa middlewares em ordem REVERSA (LIFO - Last In First Out)
# ============================================================================

# CORS - Adicionar PRIMEIRO para ser executado por ÚLTIMO (mais externo)
# Isso garante que o CORS processe OPTIONS antes de qualquer autenticação
if settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Organization-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600
    )
else:
    # Dev mode: permite localhost E 127.0.0.1
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# Security Headers (depois do CORS)
app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=settings.is_production,
    hsts_max_age=settings.HSTS_MAX_AGE,
    hsts_include_subdomains=settings.HSTS_INCLUDE_SUBDOMAINS,
    hsts_preload=settings.HSTS_PRELOAD
)

# Request ID (depois de Security Headers)
app.add_middleware(RequestIDMiddleware)

# CSRF Protection (depois de Request ID, antes de rate limiting)
# Valida X-CSRF-Token para métodos unsafe (POST/PUT/PATCH/DELETE) com Cookie auth
app.add_middleware(CSRFMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# ============================================================================
# Exception Handlers Globais (FASE 6)
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para erros de validação Pydantic
    
    Retorna erro 422 com detalhes dos campos inválidos.
    Serializa ValueError objects para JSON-safe dict.
    """
    # Serializar errors() para JSON-safe format
    errors = []
    for error in exc.errors():
        # Converter ValueError/Exception objects para strings
        error_dict = {
            "loc": error.get("loc", []),
            "msg": str(error.get("msg", "")),
            "type": error.get("type", "value_error")
        }
        # Adicionar ctx se existir e for serializável
        if "ctx" in error and isinstance(error["ctx"], dict):
            error_dict["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        errors.append(error_dict)
    
    logger.warning(f"Validation error: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": ErrorCode.VALIDATION_ERROR.value,
            "message": "Erro de validação",
            "details": {"errors": errors},
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """
    Handler para NotFoundError - recursos não encontrados
    
    Mapeia exceção de serviço para HTTP 404.
    """
    logger.info(f"NotFoundError: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_code": "NOT_FOUND",
            "message": exc.message,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(ForbiddenError)
async def forbidden_error_handler(request: Request, exc: ForbiddenError):
    """
    Handler para ForbiddenError - acesso negado
    
    Mapeia exceção de serviço para HTTP 403.
    """
    logger.warning(f"ForbiddenError: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error_code": "FORBIDDEN",
            "message": exc.message,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(ValidationError)
async def custom_validation_error_handler(request: Request, exc: ValidationError):
    """
    Handler para ValidationError customizado
    
    Mapeia exceção de serviço para HTTP 422.
    """
    logger.warning(f"ValidationError: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": exc.message,
            "field": exc.field,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(ConflictError)
async def conflict_error_handler(request: Request, exc: ConflictError):
    """
    Handler para ConflictError - conflitos de dados
    
    Mapeia exceção de serviço para HTTP 409.
    """
    logger.warning(f"ConflictError: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_code": "CONFLICT",
            "message": exc.message,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Handler para erros de integridade do banco
    
    Mapeia constraints do PostgreSQL para error codes específicos.
    """
    logger.error(f"IntegrityError: {exc}")
    
    # Detectar constraint específica
    error_msg = str(exc.orig) if exc.orig else str(exc)
    error_code = "DATABASE_CONSTRAINT_VIOLATION"
    message = "Violação de constraint do banco de dados"
    
    # RDB10: Team registration overlap
    if "uq_team_reg_active_athlete_team_season" in error_msg:
        error_code = ErrorCode.TEAM_REG_OVERLAP.value
        message = "Atleta já possui inscrição ativa nesta equipe/temporada (RDB10)"
    
    # RDB9: Membership overlap
    elif "membership" in error_msg.lower() and "overlap" in error_msg.lower():
        error_code = ErrorCode.MEMBERSHIP_OVERLAP.value
        message = "Vínculo sobrepõe período existente (RDB9)"
    
    # RDB8: Season overlap
    elif "season" in error_msg.lower() and "overlap" in error_msg.lower():
        error_code = ErrorCode.SEASON_OVERLAP.value
        message = "Temporada sobrepõe período existente (RDB8)"
    
    # Unique constraint (email, cpf, etc)
    elif "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
        if "email" in error_msg.lower():
            error_code = ErrorCode.DUPLICATE_USER.value
            message = "Email já cadastrado"
        elif "cpf" in error_msg.lower():
            error_code = ErrorCode.DUPLICATE_PERSON.value
            message = "CPF já cadastrado"
        else:
            message = "Registro duplicado"
    
    # Foreign key constraint
    elif "foreign key" in error_msg.lower() or "violates foreign key" in error_msg.lower():
        message = "Referência inválida: registro referenciado não existe"
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_code": error_code,
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler genérico para erros não tratados
    
    Retorna erro 500 e registra stack trace no log.
    """
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    # Em produção, não expor detalhes do erro
    if settings.is_production:
        message = "Erro interno do servidor"
    else:
        message = f"Erro interno: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR.value,
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


# ============================================================================
# Routers
# ============================================================================

# Incluir routers
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - redirect para docs"""
    return JSONResponse(
        content={
            "message": "HB Tracking API",
            "version": settings.API_VERSION_NUMBER,
            "docs": f"/api/{settings.API_VERSION}/docs"
        }
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Evento de startup da aplicação.
    
    Executa:
    1. Warmup do banco de dados (acordar Neon)
    2. Healthcheck inicial
    3. Log de inicialização
    4. Step 17: Iniciar background tasks (WebSocket cleanup, notification cleanup)
    """
    logger.info(
        f"🚀 HB Tracking API {settings.API_VERSION_NUMBER} iniciando...",
        extra={
            "environment": settings.ENV,
            "log_level": settings.LOG_LEVEL
        }
    )
    
    # OBRIGATÓRIO: Warmup do banco no boot (proteção contra cold start do Neon)
    from app.core.db import warmup_database, healthcheck_db
    
    if warmup_database():
        # Healthcheck completo após warmup
        health = healthcheck_db()
        if health["status"] == "healthy":
            logger.info(f"✅ Database: PostgreSQL {health.get('pg_version', 'unknown')}")
            logger.info(f"📊 Ambiente: {settings.ENV}")
            logger.info(f"🚀 HB Tracking API {settings.API_VERSION_NUMBER} pronta para receber requests")
        else:
            logger.warning(f"⚠️ Database health check retornou: {health}")
    else:
        logger.error("❌ Falha no warmup do banco de dados. A aplicação pode ter problemas no primeiro request.")
        logger.info(f"📊 Ambiente: {settings.ENV}")
    
    # Step 17: Iniciar background tasks
    from app.core.background_tasks import start_background_tasks
    start_background_tasks()
    logger.info("✅ Background tasks iniciadas (WebSocket cleanup, notification cleanup)")
    
    logger.info(f"🚀 HB Tracking API {settings.API_VERSION_NUMBER} iniciada")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 HB Tracking API encerrada")

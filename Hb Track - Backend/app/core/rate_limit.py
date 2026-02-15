"""
Rate Limiting configuration using SlowAPI

Implementa rate limiting para proteger endpoints sensíveis,
especialmente o endpoint de login contra ataques de força bruta.

NOTA: Em ENV=test, rate limiting é efetivamente desabilitado (10000/min)
para garantir testes determinísticos.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Detectar ambiente de teste (ENV=test OU E2E=1)
IS_TEST_ENV = (
    os.getenv("ENV", "").lower() == "test" or 
    os.getenv("E2E", "").lower() in ("1", "true", "yes")
)

# Limites para teste (efetivamente desabilitados)
TEST_RATE_LIMIT = "10000/minute"

# Configurar limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[TEST_RATE_LIMIT if IS_TEST_ENV else "200/minute"],
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Configurável via REDIS_URL, fallback in-memory
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler customizado para erros de rate limit

    Retorna JSON com informações sobre o limite excedido
    """
    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)} on {request.url.path}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Muitas requisições. Tente novamente em alguns instantes.",
            "detail": str(exc.detail),
        },
        headers={"Retry-After": "60"},
    )


# Rate limits específicos para diferentes endpoints
# Em teste, todos usam limite alto para evitar 429
LOGIN_RATE_LIMIT = TEST_RATE_LIMIT if IS_TEST_ENV else "5/minute"
REGISTER_RATE_LIMIT = TEST_RATE_LIMIT if IS_TEST_ENV else "3/hour"
PASSWORD_RESET_RATE_LIMIT = TEST_RATE_LIMIT if IS_TEST_ENV else "3/hour"
API_DEFAULT_RATE_LIMIT = TEST_RATE_LIMIT if IS_TEST_ENV else "100/minute"

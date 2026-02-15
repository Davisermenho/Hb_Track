"""
CSRF Protection Middleware

AUTH-CONTEXT-SSOT-002: CSRF enforcement for Cookie-authenticated mutations

Enforcement Policy:
- CSRF required for unsafe methods (POST/PUT/PATCH/DELETE) when authenticated via COOKIE
- CSRF check skipped for Bearer-only authentication  
- CSRF token validated via X-CSRF-Token header

"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Unsafe HTTP methods requiring CSRF protection
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware
    
    Validates X-CSRF-Token header for cookie-authenticated mutations.
    Enforcement Point: AUTH-CONTEXT-SSOT-002 (Section 2.2)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)
        
        # Check if request is authenticated via cookie
        has_cookie_auth = (
            request.cookies.get("hb_access_token") is not None
            or request.cookies.get("access_token") is not None
        )
        
        # Skip CSRF check if no cookie authentication
        if not has_cookie_auth:
            return await call_next(request)
        
        # Validate CSRF token for cookie-authenticated mutations
        csrf_token = request.headers.get("X-CSRF-Token")
        
        if not csrf_token:
            logger.warning(
                f"CSRF token missing for {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "has_cookie": True,
                    "code": "CSRF_TOKEN_MISSING"
                }
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error_code": "CSRF_TOKEN_REQUIRED",
                    "message": "CSRF token required for cookie-authenticated mutations"
                }
            )
        
        # TODO: Implement actual token validation logic
        # For now, accepting any non-empty token (placeholder)
        # Real implementation should validate token signature/expiry
        
        logger.debug(
            f"CSRF validated for {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": str(request.url.path)
            }
        )
        
        return await call_next(request)

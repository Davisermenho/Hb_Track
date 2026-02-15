"""
Middleware package for HB Track
"""
from app.middleware.csrf import CSRFMiddleware

__all__ = ["CSRFMiddleware"]

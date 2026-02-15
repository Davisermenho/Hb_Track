"""
INV-AUTH-002: CSRF Required for Cookie-Authenticated Mutations

AUTH-CONTEXT-SSOT-002 (AC-A2)
Evidence: app/middleware/csrf.py :: CSRFMiddleware

Validates that:
1. Cookie-authenticated POST/PUT/PATCH/DELETE without CSRF token returns 403
2. Cookie-authenticated mutation WITH CSRF token succeeds (not blocked by CSRF)
3. Bearer-authenticated mutation skips CSRF check (no 403 for missing CSRF)

SSOT: app/middleware/csrf.py lines ~30-70
"""
import pytest
from fastapi import status


def test_cookie_mutation_without_csrf_returns_403(
    client, 
    auth_cookies, 
    test_season_data
):
    """
    Cookie-authenticated mutation without X-CSRF-Token should return 403
    
    Setup: Valid cookie, no CSRF token, POST request
    Expected: 403 Forbidden (CSRF_TOKEN_REQUIRED)
    """
    response = client.post(
        "/api/v1/seasons",
        json=test_season_data,
        cookies=auth_cookies,  # Valid cookie
        # No X-CSRF-Token header
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "CSRF_TOKEN_REQUIRED"


def test_cookie_mutation_with_csrf_succeeds(
    client,
    auth_cookies,
    test_season_data
):
    """
    Cookie-authenticated mutation WITH X-CSRF-Token should NOT return 403 for CSRF
    
    Setup: Valid cookie + X-CSRF-Token header, POST request
    Expected: NOT 403 (might be 201 Created, 422 Validation, etc - but not CSRF block)
    """
    response = client.post(
        "/api/v1/seasons",
        json=test_season_data,
        cookies=auth_cookies,
        headers={"X-CSRF-Token": "valid_csrf_token"},  # CSRF token present
    )
    
    # Should NOT be blocked by CSRF (403 with CSRF_TOKEN_REQUIRED)
    # Acceptable responses: 201 Created, 422 Validation Error, 403 Permission Denied (NOT csrf), etc
    assert response.status_code != status.HTTP_403_FORBIDDEN or (
        response.status_code == status.HTTP_403_FORBIDDEN 
        and response.json().get("error_code") != "CSRF_TOKEN_REQUIRED"
    )


def test_bearer_mutation_skips_csrf_check(
    client,
    auth_headers,
    test_season_data
):
    """
    Bearer-authenticated mutation should skip CSRF check (no 403 for missing CSRF)
    
    Setup: Valid Bearer token (no cookie), no CSRF token, POST request  
    Expected: NOT 403 CSRF_TOKEN_REQUIRED (Bearer bypasses CSRF check per design)
    """
    response = client.post(
        "/api/v1/seasons",
        json=test_season_data,
        headers=auth_headers,  # Bearer token only
        # No cookie, no CSRF token
    )
    
    # Should NOT be blocked by CSRF middleware (Bearer skips CSRF)
    # May fail for other reasons (permissions, validation), but not CSRF
    assert response.status_code != status.HTTP_403_FORBIDDEN or (
        response.status_code == status.HTTP_403_FORBIDDEN
        and response.json().get("error_code") != "CSRF_TOKEN_REQUIRED"
    )

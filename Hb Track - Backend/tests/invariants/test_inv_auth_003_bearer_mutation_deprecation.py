"""
INV-AUTH-003: Bearer Mutation Deprecation Warning

AUTH-CONTEXT-SSOT-002 (AC-A3)
Evidence: app/core/context.py :: get_current_context (lines ~177-195)

Validates that:
1. Bearer-only authentication on mutation endpoint works (soft deprecation, not hard block)
2. Warning log emitted with code BEARER_MUTATION_DEPRECATED
3. Warning includes enforcement_date (2026-06-01)

SSOT: app/core/context.py lines ~177-195 (PATHS_MUTATION_LIST + warning logic)
"""
import pytest
import logging
from fastapi import status


def test_bearer_mutation_works_with_warning(
    client,
    auth_headers,
    test_training_session_data,
    caplog
):
    """
    Bearer token on mutation endpoint should:
    1. Allow execution (soft deprecation, not hard block)
    2. Emit warning log with code BEARER_MUTATION_DEPRECATED
    
    Setup: Valid Bearer token (no cookie), POST to mutation endpoint
    Expected: 
    - Status: 200/201 (or business logic error, NOT 403 for Bearer usage)
    - Log: WARNING with code=BEARER_MUTATION_DEPRECATED
    """
    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/v1/training_sessions",
            json=test_training_session_data,
            headers=auth_headers,  # Bearer only, no cookie
        )
    
    # Should NOT be blocked (soft deprecation)
    # Acceptable: 201 Created, 422 Validation, 403 Permission Denied - but executable
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
        status.HTTP_422_UNPROCESSABLE_ENTITY,  # Validation error
        status.HTTP_403_FORBIDDEN,  # Permission error (not Bearer block)
    ]
    
    # Verify deprecation warning was logged
    warning_found = False
    for record in caplog.records:
        if record.levelname == "WARNING" and "BEARER_MUTATION_DEPRECATED" in str(record):
            warning_found = True
            # Verify enforcement date is mentioned
            assert "2026-06-01" in str(record), "Enforcement date should be in warning"
            break
    
    assert warning_found, "Bearer mutation deprecation warning not found in logs"


def test_bearer_readonly_no_warning(
    client,
    auth_headers,
    caplog
):
    """
    Bearer token on read-only endpoint should NOT emit deprecation warning
    
    Setup: Valid Bearer token, GET request (read-only)
    Expected: No BEARER_MUTATION_DEPRECATED warning
    """
    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/api/v1/training_sessions",
            headers=auth_headers,
        )
    
    # GET should succeed without warning
    assert response.status_code == status.HTTP_200_OK
    
    # Verify NO deprecation warning for read-only
    for record in caplog.records:
        assert "BEARER_MUTATION_DEPRECATED" not in str(record), \
            "Deprecation warning should NOT appear for GET requests"


def test_cookie_mutation_no_bearer_warning(
    client,
    auth_cookies,
    test_training_session_data,
    caplog
):
    """
    Cookie-authenticated mutation should NOT emit Bearer deprecation warning
    
    Setup: Valid cookie (no Bearer header), POST to mutation endpoint
    Expected: No BEARER_MUTATION_DEPRECATED warning
    """
    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/v1/training_sessions",
            json=test_training_session_data,
            cookies=auth_cookies,
            headers={"X-CSRF-Token": "valid_token"},  # Include CSRF to pass middleware
        )
    
    # Cookie mutation should not trigger Bearer warning
    for record in caplog.records:
        if "BEARER_MUTATION_DEPRECATED" in str(record):
            pytest.fail("Bearer deprecation warning should NOT appear for cookie auth")

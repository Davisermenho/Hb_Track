"""
OpenAPI Contract Test

AUTH-CONTEXT-SSOT-002 (AC-A4)
Evidence: docs/_generated/openapi.json

Validates that:
1. OpenAPI spec contains securitySchemes: cookieAuth + csrfToken
2. Mutation paths require BOTH (AND logic): security: [{"cookieAuth": [], "csrfToken": []}]
3. All paths in PATHS_MUTATION_LIST exist in OpenAPI spec

SSOT: docs/_generated/openapi.json
AUTHORITY: Regenerated via scripts/inv.ps1 refresh
"""
import json
import pytest
from pathlib import Path


# AUTH-CONTEXT-SSOT-002: Mutation paths requiring Cookie+CSRF
PATHS_MUTATION_LIST = [
    "/api/v1/training_sessions",
    "/api/v1/seasons",
    "/api/v1/users",
]

# Mutation methods requiring CSRF
UNSAFE_METHODS = ["post", "put", "patch", "delete"]


@pytest.fixture(scope="module")
def openapi_spec():
    """Load OpenAPI specification from generated artifact"""
    backend_root = Path(__file__).parent.parent.parent
    openapi_path = backend_root / "docs" / "_generated" / "openapi.json"
    
    assert openapi_path.exists(), f"OpenAPI spec not found at {openapi_path}"
    
    with open(openapi_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    
    return spec


def test_security_schemes_exist(openapi_spec):
    """
    Validate that openapi.json contains required securitySchemes
    
    Expected:
    - cookieAuth: type=apiKey, in=cookie, name=hb_access_token
    - csrfToken: type=apiKey, in=header, name=X-CSRF-Token
    """
    components = openapi_spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    
    # Validate cookieAuth exists
    assert "cookieAuth" in security_schemes, "cookieAuth scheme missing"
    cookie_auth = security_schemes["cookieAuth"]
    assert cookie_auth.get("type") == "apiKey", "cookieAuth should be apiKey type"
    assert cookie_auth.get("in") == "cookie", "cookieAuth should be in cookie"
    assert cookie_auth.get("name") == "hb_access_token", "cookieAuth should use hb_access_token"
    
    # Validate csrfToken exists
    assert "csrfToken" in security_schemes, "csrfToken scheme missing"
    csrf_token = security_schemes["csrfToken"]
    assert csrf_token.get("type") == "apiKey", "csrfToken should be apiKey type"
    assert csrf_token.get("in") == "header", "csrfToken should be in header"
    assert csrf_token.get("name") == "X-CSRF-Token", "csrfToken should use X-CSRF-Token header"


def test_mutation_paths_exist(openapi_spec):
    """
    Validate that all PATHS_MUTATION_LIST exist in OpenAPI spec
    
    AUTH-CONTEXT-SSOT-002: Paths must exist before modifying security requirements
    """
    paths = openapi_spec.get("paths", {})
    
    for mutation_path in PATHS_MUTATION_LIST:
        assert mutation_path in paths, f"Path {mutation_path} not found in OpenAPI spec"


def test_mutation_paths_require_cookie_and_csrf(openapi_spec):
    """
    Validate that mutation operations require BOTH cookieAuth AND csrfToken
    
    Expected security definition (AND logic):
    security: [{"cookieAuth": [], "csrfToken": []}]
    
    This applies to POST/PUT/PATCH/DELETE operations on PATHS_MUTATION_LIST
    """
    paths = openapi_spec.get("paths", {})
    
    for mutation_path in PATHS_MUTATION_LIST:
        path_item = paths.get(mutation_path, {})
        
        for method in UNSAFE_METHODS:
            if method not in path_item:
                continue  # Method not defined for this path
            
            operation = path_item[method]
            security = operation.get("security", [])
            
            # Validate security requirement exists
            assert len(security) > 0, \
                f"{method.upper()} {mutation_path}: security requirement missing"
            
            # Validate AND logic: BOTH cookieAuth AND csrfToken in single object
            has_correct_security = False
            for security_req in security:
                if "cookieAuth" in security_req and "csrf Token" in security_req:
                    has_correct_security = True
                    # Validate both are empty arrays (no scopes)
                    assert security_req["cookieAuth"] == [], \
                        f"{method.upper()} {mutation_path}: cookieAuth should have empty scopes"
                    assert security_req["csrfToken"] == [], \
                        f"{method.upper()} {mutation_path}: csrfToken should have empty scopes"
                    break
            
            assert has_correct_security, \
                f"{method.upper()} {mutation_path}: must require BOTH cookieAuth AND csrfToken (AND logic)"


def test_bearer_not_in_mutation_security(openapi_spec):
    """
    Validate that Bearer auth is NOT an alternative for mutations
    
    AUTH-CONTEXT-SSOT-002: Runtime allows Bearer (with warning), but contract enforces Cookie+CSRF
    """
    paths = openapi_spec.get("paths", {})
    
    for mutation_path in PATHS_MUTATION_LIST:
        path_item = paths.get(mutation_path, {})
        
        for method in UNSAFE_METHODS:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            security = operation.get("security", [])
            
            # Validate that Bearer/HTTPBearer is NOT listed as alternative for mutations
            for security_req in security:
                assert "HTTPBearer" not in security_req, \
                    f"{method.upper()} {mutation_path}: Bearer should not be in security (contract strict)"
                assert "bearerAuth" not in security_req, \
                    f"{method.upper()} {mutation_path}: bearerAuth should not be in security (contract strict)"

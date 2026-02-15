# ARCH_REQUEST: AUTH-CONTEXT-SSOT-002

**ID:** AUTH-CONTEXT-SSOT-002  
**Canonical ID:** ARCH-AUTH-PRECEDENCE-001  
**Status:** DRAFT (Refined)  
**Created:** 2026-02-14  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0  
**Determinism Level:** STRICT (User Review Applied)

---

## 1. CONTEXT & MOTIVATION

**Current State:**
- Multiple authentication sources (JWT Bearer, Cookie, CSRF) coexist without explicit precedence
- `app/core/context.py` contains implicit ordering but lacks formal documentation
- OpenAPI spec doesn't reflect CSRF requirements for mutation endpoints
- Risk of auth bypass if precedence is not enforced at middleware level

**Strategic Context:**
- Part of Security Hardening Sprint (Q1 2026)
- Critical for LGPD compliance (explicit session management)
- Blocks: OAuth2 integration, Mobile app tokens

**Previous Work:**
- Migration 0041: RBAC system implemented
- Cookie refresh rotation: implemented with secure flags
- CSRF middleware: exists but not formally integrated in auth chain

---

## 2. SSOT (OBRIGATÓRIO) — SINGLE SOURCE OF TRUTH

### 2.1 SSOT_STRUCTURAL
- **Primary:** `app/core/context.py`
- **Function:** `get_current_context`
- **Authority:** `AUTH_RESOLUTION_ORDER` = `COOKIE > BEARER`
- **Stability:** Runtime deterministic; changes via versioned commits only.

### 2.2 CSRF_MECHANISM
- **Type:** Middleware Enforcement
- **Enforcement Point:** `app/middleware/csrf.py` (ensure implementation or create if missing)
- **Constraint:** `CSRF_CHECK_REQUIRED` if `AUTH_METHOD == COOKIE` AND `METHOD in [POST, PUT, PATCH, DELETE]`.

### 2.3 SSOT_SECONDARY (derivados)
- `docs/_generated/openapi.json` — Generated Contract (via `inv.ps1 refresh`).
- `app/api/v1/routers/auth.py` — Login/Logout endpoints.

---

## 3. OPENAPI ARTIFACT (CAMINHO ÚNICO)

**OPENAPI_ARTIFACT_PATH:** `docs/_generated/openapi.json`

**Validation (Strict):**
- **Security Schemes:**
  - `cookieAuth`: `type=apiKey`, `in=cookie`, `name=hb_access_token`
  - `csrfToken`: `type=apiKey`, `in=header`, `name=X-CSRF-Token`
- **Mutation Security:** `PATHS_MUTATION_LIST` endpoints must require **BOTH**:
  - `security: [{"cookieAuth": [], "csrfToken": []}]` (Propriedade `AND` no OpenAPI).

---

## 4. MUST OBJECTIVES (5)

**MUST-01: Enforce Auth Precedence (COOKIE > BEARER)**
- **Cookie Invalid Policy:** `FALLBACK_TO_BEARER` (if cookie invalid/expired, try Bearer)
- **CSRF Cookie Detection:** `REQUIRE_VALID_COOKIE` (CSRF check only when cookie is valid)
- Modify `get_current_context` in `app/core/context.py`:
  1. Check `request.cookies.get("hb_access_token")`.
  2. If found AND valid -> Set `AUTH_METHOD = COOKIE`.
  3. If found BUT invalid -> Try Bearer (fallback).
  4. If not found -> Check `Authorization` header (Bearer).
  5. If Bearer found AND valid -> Set `AUTH_METHOD = BEARER`.
  6. If neither valid -> 401 Unauthorized.

**MUST-02: Strict CSRF for Cookie Mutations**
- Middleware must validate `X-CSRF-Token` if:
  - `AUTH_METHOD == COOKIE`
  - HTTP Method is unsafe (`POST`, `PUT`, `PATCH`, `DELETE`)
- Failure -> 403 Forbidden.

**MUST-03: Deprecate Bearer for Specified Mutations**
- **Policy:** `MUTATION_BEARER_POLICY`
  - `allow_bearer`: `true` (soft deprecation)
  - `openapi_includes_bearer`: `false` (contract enforces Cookie+CSRF only)
  - `warning_code`: `BEARER_MUTATION_DEPRECATED`
  - `enforcement_date`: `2026-06-01` (hard block after 3 releases)
- **Action:** If `AUTH_METHOD == BEARER` and endpoint is in `PATHS_MUTATION_LIST`:
  - **Logic:** ALLOW execution but LOG WARNING.
  - **Log:** `logger.warning("Bearer token used for mutation. Deprecated. Hard block on 2026-06-01.", extra={"path": request.url.path, "code": "BEARER_MUTATION_DEPRECATED"})`

**MUST-04: Update OpenAPI Contract**
- **OpenAPI Scheme Binding:**
  - `implementation_file`: `app/core/context.py` (or `app/api/v1/deps/auth.py` if refactored)
  - `cookie_scheme_name`: `cookieAuth`
  - `csrf_scheme_name`: `csrfToken`
  - `scheme_definition_mechanism`: FastAPI `APIKeyCookie(name="hb_access_token", scheme_name="cookieAuth")` + `APIKeyHeader(name="X-CSRF-Token", scheme_name="csrfToken")`
- Implement strict security definition in `docs/_generated/openapi.json`.
- `security: [{"cookieAuth": [], "csrfToken": []}]`.

**MUST-05: Contract & Invariant Testing**
- **Test Files (Canonical):**
  - `tests/invariants/test_inv_auth_001_cookie_precedence.py`
  - `tests/invariants/test_inv_auth_002_csrf_required_mutations.py`
  - `tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py`
  - `tests/integration/test_openapi_contract.py`
- Validate Precedence (Cookie wins over Header).
- Validate CSRF requirement (403 if missing on Cookie auth).
- Validate Warning emission on Bearer mutation.

---

## 5. SCOPE (ALLOWLISTS + FORBIDDEN PATHS)

### 5.1 READ_ALLOWLIST
- `app/core/context.py`
- `app/api/v1/routers/*.py` (ReadOnly for reference)
- `tests/invariants/*.py`
- `docs/_generated/openapi.json`
- `app/middleware/*.py`

### 5.2 WRITE_ALLOWLIST
- `app/core/context.py`
- `app/middleware/csrf.py`
- `tests/invariants/test_inv_auth_*.py` (New files)
- `tests/integration/test_openapi_contract.py` (Update/Create)
- `docs/_generated/openapi.json` (Via script only)

### 5.3 FORBIDDEN_PATHS
- `alembic/**`
- `app/models/**`
- `app/schemas/**`
- `.hb_guard/**`

---

## 6. PATHS_MUTATION_LIST (ESCOPO FECHADO)

```python
PATHS_MUTATION_LIST = [
    "/api/v1/training_sessions",       # POST
    "/api/v1/training_sessions/{id}",  # PUT/PATCH/DELETE
    "/api/v1/seasons",                 # POST
    "/api/v1/seasons/{id}",            # PUT/PATCH/DELETE
    "/api/v1/users",                   # POST
    "/api/v1/users/{id}",              # PUT/PATCH/DELETE
]
```

**Verification:**
- `PATHS_MUTATION_LIST_VERIFIED`: `true`
- `VERIFICATION_ANCHOR`: `docs/_generated/openapi.json`
- JSON Pointers to validate:
  - `/paths/~1api~1v1~1training_sessions`
  - `/paths/~1api~1v1~1training_sessions~1{id}`
  - `/paths/~1api~1v1~1seasons`
  - `/paths/~1api~1v1~1seasons~1{id}`
  - `/paths/~1api~1v1~1users`
  - `/paths/~1api~1v1~1users~1{id}`

Note: Contract test validates all paths exist in OpenAPI spec before modifying security requirements.

---

## 7. COMMANDS (STRICT ALLOWLIST)

**CMD_01:** Pre-flight status
```powershell
git status --porcelain
# Exit Code: 0 (Output must be empty)
```

**CMD_02:** SSOT Refresh
```powershell
.\scripts\inv.ps1 refresh
# Exit Code: 0
```

**CMD_03:** Run Invariant Tests
```powershell
.\venv\Scripts\pytest tests/invariants/test_inv_auth_*.py -x --tb=short --disable-warnings
# Exit Code: 0
```

**CMD_04:** Run Contract Tests
```powershell
.\venv\Scripts\pytest tests/integration/test_openapi_contract.py -x --tb=short
# Exit Code: 0
```

**CMD_05:** Capture Warnings (Bearer Deprecation)
```powershell
.\venv\Scripts\pytest tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py --log-cli-level=WARNING
# Exit Code: 0 (Check output for specific log message)
```

**CMD_06:** Inspect OpenAPI Diff
```powershell
git diff docs/_generated/openapi.json
# Exit Code: 0
```

**CMD_07:** Verify Final Status
```powershell
git status --porcelain
# Exit Code: 0 (Show modified files only)
```

**CMD_08 (Optional):** Stage Changes (Manual approval required)
```powershell
git add app/core/context.py app/middleware/csrf.py tests/invariants/test_inv_auth_001_cookie_precedence.py tests/invariants/test_inv_auth_002_csrf_required_mutations.py tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py tests/integration/test_openapi_contract.py docs/_generated/openapi.json
# Exit Code: 0
```

**CMD_09 (Optional):** Commit Changes (Manual approval required)
```powershell
git commit -m "feat(auth): implement Cookie/CSRF precedence over JWT Bearer

- Add explicit precedence logic in app/core/context.py
- Update contract test to validate OpenAPI security schemes
- Add 3 invariant tests for auth precedence
- Regenerate OpenAPI spec with cookieAuth + csrfToken requirements

Closes: AUTH-CONTEXT-SSOT-002"
# Exit Code: 0
```

---

## 8. GATES DE ACEITAÇÃO (100% BINÁRIO)

**AC-A1: Precedence Logic**
- Logic in `get_current_context` explicitly checks Cookies BEFORE Authorization Header.
- **Fail Check:** If Header overrides available Cookie -> FAIL.

**AC-A2: CSRF Enforcement**
- Test `POST /api/v1/training_sessions` with **Cookie Auth** AND **No CSRF Token**.
- **Result:** Status `403 Forbidden`.
- Test `POST /api/v1/training_sessions` with **Cookie Auth** AND **CSRF Token**.
- **Result:** Status `200/201` (or business logic error, not 403).

**AC-A3: Bearer Warning**
- Test `POST /api/v1/training_sessions` with **Bearer Auth** ONLY.
- **Result:** Status `200/201`.
- **Log Requirement:** Contains "BEARER_MUTATION_DEPRECATED".

**AC-A4: OpenAPI Structure**
- `docs/_generated/openapi.json` validation:
- Path `/api/v1/training_sessions` (POST) must have `security: [{"cookieAuth": [], "csrfToken": []}]`.
- `components.securitySchemes` must contain `cookieAuth` AND `csrfToken`.

**AC-A5: Automation**
- All 3 new invariant tests PASS (Exit 0).
- `inv.ps1 refresh` runs without error (Exit 0).

---

## 9. STOP CONDITIONS + ROLLBACK

### 9.1 STOP CONDITIONS
- **STOP_01:** `git status --porcelain` is not empty at start.
- **STOP_02:** `inv.ps1 refresh` returns non-zero exit code.
- **STOP_03:** Pytest failures (Exit 1).
- **STOP_04:** `test_openapi_contract.py` fails to validate JSON structure.

### 9.2 ROLLBACK PLAN

**Strategy:** `NO_UNTRACKED_FILES` (Create placeholders first, then rollback = git restore only)

**Preparation (Before Implementation):**
```powershell
# PREP_01: Create empty test placeholders
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_001_cookie_precedence.py" -Force
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_002_csrf_required_mutations.py" -Force
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py" -Force

# PREP_02: Stage placeholders
git add tests/invariants/test_inv_auth_001_cookie_precedence.py tests/invariants/test_inv_auth_002_csrf_required_mutations.py tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py

# PREP_03: Commit placeholders
git commit -m "chore: placeholder test files for AUTH-CONTEXT-SSOT-002"
```

**Rollback Execution (After Implementation Failure):**
```powershell
# ROLLBACK_01: Restore all tracked files (includes placeholders)
git restore app/core/context.py app/middleware/csrf.py tests/invariants/test_inv_auth_001_cookie_precedence.py tests/invariants/test_inv_auth_002_csrf_required_mutations.py tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py tests/integration/test_openapi_contract.py docs/_generated/openapi.json

# ROLLBACK_02: Verify clean state
git status --porcelain
# Expected: Empty (all changes reverted)
```

---

## 10. COMMAND_BUDGET

- **MAX_COMMANDS:** 18 (includes PREP + ROLLBACK)
- **MAX_TIME:** 50 Minutes

---

## 11. EVIDENCE PACK (≥4 PROVAS OBJETIVAS)

1. **`invariants_result.txt`:** Output of pytest execution (3 passed).
2. **`contract_result.txt`:** Output of contract test (schemas validated).
3. **`deprecation.log`:** Log snippet proving Bearer usage triggers warning.
4. **`openapi_diff.diff`:** Git diff showing added security requirements.
5. **`final_status.txt`:** Output of `git status` proving clean state (or staged files).

---

## 12. DEPENDENCIES & RISKS

### 12.1 Dependencies
- Cookie refresh rotation implementada (migration 0fb0f76b48a7)
- CSRF middleware existente (`app/middleware/csrf.py`)
- RBAC system implementado (migration 0041)

### 12.2 Risks
- **R1 (MED):** Quebra de clientes mobile que ainda usam JWT Bearer para mutations
  - Mitigation: Implementar deprecation warning antes de hard enforcement (3 releases)
- **R2 (LOW):** OpenAPI spec inconsistente após refactor
  - Mitigation: Contract test valida conformidade antes de merge
- **R3 (LOW):** Performance overhead de precedência check
  - Mitigation: Precedência implementada com early return (O(1))

---

## 13. DEFINITION OF DONE (DoD)

**DoD-01: Code Implementation**
- ✅ `app/core/context.py` contém lógica de precedência explícita
- ✅ Docstring documenta ordem
- ✅ Log DEBUG emitido para cada request

**DoD-02: Tests**
- ✅ 3 testes de invariantes criados e passando (exit 0)
- ✅ 1 contract test atualizado e passando (exit 0)
- ✅ Deprecation warning capturado em teste

**DoD-03: Contract**
- ✅ `docs/_generated/openapi.json` atualizado via `inv.ps1 refresh`
- ✅ Todos os 6 paths mutáveis (6 endpoints × múltiplos métodos) têm `security: [{"cookieAuth": [], "csrfToken": []}]`

**DoD-04: Evidence**
- ✅ 6 provas objetivas geradas (pytest outputs, git diff, logs)

**DoD-05: Rollback Tested**
- ✅ ROLLBACK executado em dry-run (simulated)
- ✅ `git status --porcelain` vazio após rollback

**DoD-06: Documentation**
- ✅ Docstrings atualizadas em `app/core/context.py` e `app/api/v1/deps/auth.py`
- ✅ Inline comments explicando precedência

---

## 14. EXECUTION WORKFLOW (DETERMINISTIC)

```powershell
# STEP 0: Preparation (Create Placeholders)
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_001_cookie_precedence.py" -Force
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_002_csrf_required_mutations.py" -Force
New-Item -ItemType File -Path "tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py" -Force
git add tests/invariants/test_inv_auth_*.py
git commit -m "chore: placeholder test files for AUTH-CONTEXT-SSOT-002"

# STEP 1: Pre-flight
git status --porcelain  # Deve retornar vazio

# STEP 2: SSOT Refresh (WRITE — requer aprovação)
.\scripts\inv.ps1 refresh  # Exit 0 esperado

# STEP 3: Implementação (WRITE — agente aplica mudanças)
# - Editar app/core/context.py (adicionar lógica de precedência)
# - Editar app/middleware/csrf.py (ajustar validação se necessário)
# - Editar tests/invariants/test_inv_auth_001_cookie_precedence.py
# - Editar tests/invariants/test_inv_auth_002_csrf_required_mutations.py
# - Editar tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py
# - Atualizar tests/integration/test_openapi_contract.py

# STEP 4: Testing Gate
.\venv\Scripts\pytest tests/invariants/test_inv_auth_*.py -x --tb=short --disable-warnings > pytest_output_invariants.txt
$ec1 = $LASTEXITCODE
if ($ec1 -ne 0) { Write-Host "[ABORT] Invariants failed"; exit $ec1 }

.\venv\Scripts\pytest tests/integration/test_openapi_contract.py -x --tb=short --disable-warnings > pytest_output_contract.txt
$ec2 = $LASTEXITCODE
if ($ec2 -ne 0) { Write-Host "[ABORT] Contract test failed"; exit $ec2 }

# STEP 5: Capture Warnings
.\venv\Scripts\pytest tests/invariants/test_inv_auth_*.py -x --tb=short --log-cli-level=WARNING > deprecated_auth_logs.txt

# STEP 6: SSOT Regeneration (WRITE — requer aprovação)
.\scripts\inv.ps1 refresh > inv_refresh_output.txt
$ec3 = $LASTEXITCODE
if ($ec3 -ne 0) { Write-Host "[ABORT] inv.ps1 refresh failed"; exit $ec3 }

# STEP 7: Validation
git --no-pager diff docs/_generated/openapi.json > git_diff_openapi.txt
git status --porcelain > git_status_final.txt

# STEP 8: Commit (WRITE — requer aprovação; usar CMD_08 e CMD_09)
# Se tudo OK, executar CMD_08 e CMD_09

# Se algo falhou: ROLLBACK (usar ROLLBACK_01 e ROLLBACK_02)
```

---

## 15. CHANGELOG ENTRY (Template para merge)

```markdown
### AUTH-CONTEXT-SSOT-002 — Auth Precedence: Cookie/CSRF > JWT Bearer

**Date:** 2026-02-14  
**Type:** FEATURE  
**Impact:** HIGH (Security hardening)

**Changes:**
- Implemented explicit auth precedence in `app/core/context.py`: Cookie > Bearer (fallback on invalid cookie)
- Updated OpenAPI contract to require `cookieAuth + csrfToken` for 6 mutation paths
- Added 3 invariant tests: `test_inv_auth_001_cookie_precedence`, `test_inv_auth_002_csrf_required_mutations`, `test_inv_auth_003_bearer_mutation_deprecation`
- Updated contract test to validate security schemes in OpenAPI spec
- Added deprecation warning for JWT Bearer usage in mutation endpoints (enforcement date: 2026-06-01)

**Files Modified:**
- `app/core/context.py` (precedence logic with fallback policy)
- `app/middleware/csrf.py` (validation refinement)
- `tests/invariants/test_inv_auth_001_cookie_precedence.py` (new)
- `tests/invariants/test_inv_auth_002_csrf_required_mutations.py` (new)
- `tests/invariants/test_inv_auth_003_bearer_mutation_deprecation.py` (new)
- `tests/integration/test_openapi_contract.py` (security validation)
- `docs/_generated/openapi.json` (regenerated via inv.ps1 refresh)

**Evidence:**
- `pytest_output_invariants.txt` (3 passed)
- `pytest_output_contract.txt` (1 passed)
- `git_diff_openapi.txt` (6 paths updated)
- `deprecated_auth_logs.txt` (warnings captured)

**Validation:** All acceptance criteria met (AC-A1 to AC-A5)
```

---

## 16. METADATA

**Protocol Compliance:**
- ✅ 9-point determinism refinement applied
- ✅ SSOT_STRUCTURAL defined (single source)
- ✅ OPENAPI_ARTIFACT_PATH fixed (1 canonical path)
- ✅ Commands aligned to 08_APPROVED_COMMANDS.md
- ✅ SCOPE allowlists formalized (READ/WRITE/FORBIDDEN)
- ✅ Acceptance criteria 100% binário (no manual review)
- ✅ PATHS_MUTATION_LIST closed scope (12 endpoints)
- ✅ STOP conditions + ROLLBACK executable
- ✅ COMMAND_BUDGET defined (12 commands, 45min max)
- ✅ Evidence Pack ≥4 proofs (6 provided)

**Estimated Effort:** 3-4 hours  
**Command Count:** 8-12 commands  
**Risk Level:** MEDIUM (security-critical but well-tested)

---

**Approved by:** [Pending]  
**Executor:** AI Agent (following AI_ARCH_EXEC_PROTOCOL v1.0.0)  
**Review Required:** YES (Security Lead + Tech Lead)

---

**End of ARCH_REQUEST AUTH-CONTEXT-SSOT-002**

# ARCH_REQUEST: AR-2026-02-17-SCRIPTS-REFACTOR-SEED-PERMISSIONS

**ID:** AR-2026-02-17-SCRIPTS-REFACTOR-SEED-PERMISSIONS  
**Canonical ID:** ARCH-SCRIPTS-REFACTOR-004  
**Status:** IN_PROGRESS  
**Created:** 2026-02-13  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0

---

## 1. CONTEXT & MOTIVATION

**Current State:**
- File: `Hb Track - Backend/db/seeds/_archived/006_seed_permissions.py` (150 lines)
- Classification: `DIVIDA_TECNICA`
- **Current idempotency**: Basic COUNT check (`if count > 0: return`)
- **Issue**: No unified tracking across script executions
- Missing: CLI interface, JSON logging, --dry-run, --force, explicit exit codes

**Strategic Context:**
- Part of P2_REFACTORING roadmap (AR-001 ✅, AR-002 ✅, AR-003 ✅, AR-004 in progress)
- Template Source: AR-003 (idempotency_keys pattern)
- Complexity: MEDIUM (simpler than AR-003, single entity type)
- High usage in development workflows (permissions are foundational)

**Previous Work:**
- AR-001 (fix_superadmin.py): State checking via bcrypt.checkpw()
- AR-002 (compact_exec_logs.py): State checking via file content comparison
- **AR-003 (seed_v1_2_initial.py)**: Database-based tracking via idempotency_keys table
- **AR-004 NEW**: Apply idempotency_keys pattern to permissions seeding (SQLAlchemy adapter)

---

## 2. MUST OBJECTIVES (5)

**MUST-01: Implement Unified Idempotency via idempotency_keys Table**
- Create/check `idempotency_keys` table (same as AR-003)
- Key format: `"seed_permissions:YYYY-MM-DD"`
- Logic:
  - 1st run today: Insert 65 permissions → Save key → Exit 1 (seeded)
  - 2nd run today: Detect key exists → Skip seeding → Exit 0 (noop)
  - --force: Ignore key, re-seed → Exit 1
- Replaces COUNT-based check with unified script tracking

**MUST-02: Add JSON Structured Logging**
- Implement `json_log()` helper (conformant with SCRIPTS_GUIDE.md sec 3)
- Log operations:
  - Idempotency key lookup
  - Seeding decision (skip vs execute)
  - Permission insert results
  - Final summary
- Fields: timestamp, script, operation, status, details, dry_run

**MUST-03: Implement CLI Interface**
- Add argparse with:
  - `--dry-run`: Preview without DB writes
  - `--force`: Bypass idempotency check
  - `--output json|text`: Output format (default: json)
  - `--help`: Usage information
- Backward compatible: no args = apply mode

**MUST-04: Smoke Test Validation**
- Test 1: `--help` shows usage
- Test 2: 1st run → exit 1 (seeded)
- Test 3: 2nd run same day → exit 0 (noop, idempotent) ✅ CRITICAL
- Test 4: `--force` → bypass idempotency, exit 1 (re-seeded)
- Test 5: `--dry-run` → preview, no DB writes, exit 0
- Test 6: JSON output parseable

**MUST-05: Update Documentation**
- Add `seed_permissions.py` to SCRIPTS_GUIDE.md section 7
- Update section 8 classification: DIVIDA_TECNICA → INCORPORAR
- Create VALIDATION_MUST_REPORT_AR-2026-02-17.md

---

## 3. SSOT REFERENCES

**Authoritative Sources:**
- `Hb Track - Backend/db/seeds/_archived/006_seed_permissions.py` (current implementation)
- `Hb Track - Backend/docs/_generated/schema.sql` (idempotency_keys table + permissions table)
- `docs/_canon/SCRIPTS_GUIDE.md` (enterprise contract)
- `docs/_canon/_arch_requests/AR-2026-02-16-*.md` (methodology reference)

**Key Table Schemas:**
```sql
-- permissions table (target of seeding)
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY,
    code VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
);

-- idempotency_keys table (reused from AR-003)
CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    endpoint VARCHAR(255),
    request_hash VARCHAR(255),
    -- ... other columns
);
```

---

## 4. SCOPE & DELTA

**In Scope:**
- ✅ `seed_permissions.py` refactoring
- ✅ idempotency_keys table integration
- ✅ SCRIPTS_GUIDE.md update
- ✅ VALIDATION_MUST_REPORT creation
- ✅ Smoke tests execution
- ✅ Governance registration

**Out of Scope:**
- ❌ Changes to permission definitions (values stay same: 65 permissions)
- ❌ Changes to permissions table schema
- ❌ Migration to Alembic seeds
- ❌ Other seed scripts refactoring

**Estimated Delta:**
- seed_permissions.py: +120-150 lines (150 → ~270-300)
- Total: ~120-150 lines added

---

## 5. EXECUTION PLAN

**Phase 1: Analysis (COMPLETE)** ✅
- ✅ Read current script (150 lines)
- ✅ Identify state: basic idempotency, no CLI, no JSON logging
- ✅ Plan approach: apply AR-003 template with SQLAlchemy adapter

**Phase 2: Implementation**
- Step 2.1: Move file from `_archived/` to `scripts/` (if needed)
- Step 2.2: Add idempotency_keys table check/creation
- Step 2.3: Implement `check_idempotency()` and `save_idempotency_key()`
- Step 2.4: Wrap seeding logic with idempotency check
- Step 2.5: Add argparse CLI interface
- Step 2.6: Add `json_log()` helper
- Step 2.7: Implement --dry-run mode (no DB writes)
- Step 2.8: Explicit exit codes (0=noop, 1=seeded, 3=error)
- Estimated: 60-90 min

**Phase 3: Smoke Tests**
- Test 1: `--help`
- Test 2: 1st run → exit 1
- Test 3: 2nd run → exit 0 (idempotency)
- Test 4: `--force` → exit 1
- Test 5: `--dry-run` → exit 0, no writes
- Test 6: JSON output validation
- Estimated: 20-30 min

**Phase 4: Documentation**
- Update SCRIPTS_GUIDE.md
- Create VALIDATION_MUST_REPORT
- Estimated: 20-30 min

**Phase 5: Commit**
- Git add + commit with canonical message
- Estimated: 10 min

**Phase 6: Governance**
- Create event.json artifact
- Update CHANGELOG + EXECUTIONLOG
- Governance commit
- Estimated: 10 min

**Total Estimated:** 120-180 min (vs 240 min for AR-003, simpler scope)

---

## 6. GATES (5)

**GATE-A: Idempotency Validation**
- **Method:** Execute script 2x same day
- **Expected:** 1st run → exit 1 (seeded), 2nd run → exit 0 (noop)
- **Validation:** Check idempotency_keys table for key existence
- **Critical:** YES

**GATE-B: Force Bypass**
- **Method:** 2nd run with `--force` flag
- **Expected:** Bypasses idempotency check, re-seeds → exit 1
- **Validation:** idempotency_keys updated with new timestamp

**GATE-C: Dry-Run No Mutations**
- **Method:** Run with `--dry-run`, verify no DB writes
- **Expected:** Preview shown, no INSERT executed, exit 0
- **Validation:** permissions table row count unchanged

**GATE-D: JSON Output Parseable**
- **Method:** Parse output with `ConvertFrom-Json`
- **Expected:** Valid JSON structure
- **Compliance:** SCRIPTS_GUIDE.md section 3

**GATE-E: Documentation Updated**
- **Method:** Git diff SCRIPTS_GUIDE.md
- **Expected:** Section 7 includes seed_permissions.py, section 8 updated
- **Classification:** DIVIDA_TECNICA → INCORPORAR

---

## 7. ACCEPTANCE CRITERIA

1. ✅ Script runs 2x same day → 1st=exit 1 (seeded), 2nd=exit 0 (noop)
2. ✅ `--force` bypasses idempotency → exit 1 (re-seeded)
3. ✅ `--dry-run` shows preview without DB writes
4. ✅ `--help` displays correct usage + examples
5. ✅ JSON output parseable via `ConvertFrom-Json`
6. ✅ SCRIPTS_GUIDE.md updated (classification INCORPORAR)
7. ✅ Backward compatibility preserved (no args = apply mode)
8. ✅ Exit codes: 0=noop, 1=seeded, 3=error
9. ✅ All 65 permissions inserted correctly (verify count)

---

## 8. STOP CONDITIONS

**ABORT if:**
1. idempotency_keys table creation fails
2. Smoke test GATE-A fails (2nd run ≠ noop)
3. --force bypass not functional
4. Permission seeding breaks (count != 65)
5. Budget exceeded (>30 commands or >180 min)

**Rollback Plan:**
- `git revert <commit_hash>` (single file refactor)
- idempotency_keys table persist (harmless)
- No data corruption risk (test data only)

---

## 9. TEST PLAN

**Smoke Tests:**
```powershell
# SMOKE-1: CLI Help
python seed_permissions.py --help
# Expected: Usage displayed, exit 0

# SMOKE-2: First run (seeding)
python seed_permissions.py
# Expected: 65 permissions inserted, idempotency key saved, exit 1

# SMOKE-3: Second run (idempotency) [CRITICAL]
python seed_permissions.py
# Expected: Key detected, skip seeding, exit 0

# SMOKE-4: Force bypass
python seed_permissions.py --force
# Expected: Re-seed, exit 1

# SMOKE-5: Dry-run preview
python seed_permissions.py --dry-run
# Expected: Preview shown, no DB writes, exit 0

# SMOKE-6: JSON output validation
python seed_permissions.py --output json | ConvertFrom-Json
# Expected: Parseable JSON
```

---

## 10. RISK ASSESSMENT

**Risk Level:** LOW (lower than AR-003)

**Risk Factors:**
- DB Operations: INSERT (simpler than AR-003's 10 seed functions)
- Scope: Permissions only (single entity type)
- Template: Direct AR-003 reuse (proven pattern)
- Rollback: Simple (single file)

**Mitigation:**
- Template-based (AR-003 reduces unknowns)
- Test data scope (non-production)
- Comprehensive smoke tests (6 scenarios)
- Dry-run mode (preview before apply)

---

## 11. DETERMINISM SCORE

**Target:** 5/5

**Criteria:**
1. ✅ Input deterministic (65 hardcoded permissions)
2. ✅ State deterministic (idempotency_keys table)
3. ✅ Output deterministic (same permissions each run)
4. ✅ Idempotency testable (2x execution verifiable)
5. ✅ Escape hatch (--force flag)

---

## 12. BUDGET & CONSTRAINTS

**Budget:**
- Max Commands: 30
- Max Time: 120 min (more efficient than AR-003)
- Estimated Usage: 20-25 commands (~60-90 min)
- Target Efficiency: 75-85%

**Constraints:**
- Backward compatibility: MANDATORY
- Determinism score: ≥4/5 (target 5/5)
- Protocol compliance: 100% (AI_ARCH_EXEC_PROTOCOL)
- Stop on failure: ENABLED

---

## AUTHORIZATION

**Approved By:** AI Architect  
**Date:** 2026-02-13  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0  
**Status:** READY FOR PHASE 2 EXECUTION

---

END OF ARCH_REQUEST

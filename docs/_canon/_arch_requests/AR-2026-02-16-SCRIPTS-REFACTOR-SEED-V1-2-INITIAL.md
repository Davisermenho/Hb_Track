# ARCH_REQUEST: AR-2026-02-16-SCRIPTS-REFACTOR-SEED-V1-2-INITIAL

**ID:** AR-2026-02-16-SCRIPTS-REFACTOR-SEED-V1-2-INITIAL  
**Canonical ID:** ARCH-SCRIPTS-REFACTOR-003  
**Status:** IN_PROGRESS  
**Created:** 2026-02-16  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0

---

## 1. CONTEXT & MOTIVATION

**Current State:**
- `Hb Track - Backend/scripts/seed_v1_2_initial.py` (374 lines)
- Classification: `DIVIDA_TECNICA`
- **Partial idempotency**: Each function uses `ON CONFLICT DO NOTHING`, but no unified tracking
- **Issue**: Script always connects DB and attempts INSERT, even if already seeded
- **Issue**: No way to check "was this script run successfully today?"
- Missing: CLI interface, JSON logging, --dry-run, --force, explicit exit codes

**Strategic Context:**
- Part of P2_REFACTORING roadmap (AR-001 ✅, AR-002 ✅, AR-003 in progress)
- Complexity progression: LOW → LOW → **MEDIUM-HIGH**
- Foundation script (seeds essential data for dev/test environments)
- High usage in development workflow

**Previous Work:**
- AR-001 (fix_superadmin.py): State checking via bcrypt.checkpw()
- AR-002 (compact_exec_logs.py): State checking via file content comparison
- **AR-003 NEW**: State checking via database idempotency_keys table

---

## 2. MUST OBJECTIVES (5)

**MUST-01: Implement Unified Idempotency via idempotency_keys Table**
- Create/check `idempotency_keys` table
- Key format: `"seed_v1_2_initial:YYYY-MM-DD"`
- Logic:
  - 1st run today: Execute seeding → Save key → Exit 1 (seeded)
  - 2nd run today: Detect key exists → Skip seeding → Exit 0 (noop)
  - --force: Ignore key, re-seed → Exit 1
- Eliminates unnecessary DB operations when already seeded

**MUST-02: Add JSON Structured Logging**
- Implement `json_log()` helper (conformant with SCRIPTS_GUIDE.md sec 3)
- Log key operations:
  - Pre-flight check (idempotency key lookup)
  - Seeding decision (skip vs execute)
  - Per-function seeding results
  - Final summary
- Fields: timestamp, script, operation, status, details, dry_run

**MUST-03: Implement CLI Interface**
- Add argparse with:
  - `--dry-run`: Preview without DB writes
  - `--force`: Bypass idempotency check (re-seed)
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
- Add `seed_v1_2_initial.py` to SCRIPTS_GUIDE.md section 7 (critical scripts)
- Update section 8 classification: DIVIDA_TECNICA → INCORPORAR
- Create VALIDATION_MUST_REPORT_AR-2026-02-16.md

---

## 3. SSOT REFERENCES

**Authoritative Sources:**
- `Hb Track - Backend/scripts/seed_v1_2_initial.py` (current implementation)
- `Hb Track - Backend/docs/_generated/schema.sql` (idempotency_keys table schema)
- `docs/_canon/SCRIPTS_GUIDE.md` (enterprise contract)
- `docs/_canon/_arch_requests/AR-2026-02-14-*.md` (methodology reference)
- `docs/_canon/_arch_requests/AR-2026-02-15-*.md` (methodology reference)

**Database Schema (idempotency_keys):**
```sql
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    script_name VARCHAR(255) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);
```

---

## 4. SCOPE & DELTA

**In Scope:**
- ✅ `seed_v1_2_initial.py` refactoring
- ✅ idempotency_keys table logic
- ✅ SCRIPTS_GUIDE.md update
- ✅ VALIDATION_MUST_REPORT creation
- ✅ Smoke tests execution
- ✅ Governance registration

**Out of Scope:**
- ❌ Changes to seeded data values
- ❌ Changes to table schemas (roles, categories, etc)
- ❌ Migration of seed logic to Alembic
- ❌ Other seed scripts refactoring

**Estimated Delta:**
- seed_v1_2_initial.py: +150-200 lines (374 → ~550-575)
- Total: ~200 lines added

---

## 5. EXECUTION PLAN

**Phase 1: Analysis (COMPLETE)**
- ✅ Read current script (374 lines)
- ✅ Identify state: partial idempotency, no CLI, no JSON logging
- ✅ Plan approach: idempotency_keys table + CLI + JSON logging

**Phase 2: Implementation**
- Step 2.1: Add idempotency_keys table creation/check
- Step 2.2: Implement `check_idempotency()` and `save_idempotency_key()`
- Step 2.3: Wrap main() with idempotency logic
- Step 2.4: Add argparse CLI interface
- Step 2.5: Add `json_log()` helper and logging throughout
- Step 2.6: Implement --dry-run mode (skip DB writes)
- Step 2.7: Explicit exit codes (0=noop, 1=seeded, 3=error)
- Estimated: 120-150 min

**Phase 3: Smoke Tests**
- Test 1: `--help`
- Test 2: 1st run → exit 1
- Test 3: 2nd run → exit 0 (idempotency)
- Test 4: `--force` → exit 1 (bypass)
- Test 5: `--dry-run` → exit 0, no writes
- Test 6: JSON output validation
- Estimated: 30-40 min

**Phase 4: Documentation**
- Create AR-2026-02-16 document ✅
- Update SCRIPTS_GUIDE.md
- Create VALIDATION_MUST_REPORT
- Estimated: 30 min

**Phase 5: Commit**
- Git add changes
- Canonical commit message
- Verify workspace clean
- Estimated: 10 min

**Phase 6: Governance**
- Create event.json artifact
- Update CHANGELOG + EXECUTIONLOG
- Governance commit
- Estimated: 10 min

**Total Estimated:** 200-240 min (under 240 min extended budget)

---

## 6. GATES (5)

**GATE-A: Idempotency Validation**
- **Method:** Execute script 2x same day
- **Expected:** 1st run → exit 1 (seeded), 2nd run → exit 0 (noop)
- **Validation:** Check idempotency_keys table for key existence
- **Critical:** YES (core requirement for INCORPORAR classification)

**GATE-B: Force Bypass**
- **Method:** 2nd run with `--force` flag
- **Expected:** Bypasses idempotency check, re-seeds → exit 1
- **Validation:** idempotency_keys updated with new timestamp

**GATE-C: Dry-Run No Mutations**
- **Method:** Run with `--dry-run`, verify no DB writes
- **Expected:** Preview shown, no INSERT executed, exit 0
- **Validation:** idempotency_keys table unchanged, manual

 DB inspection

**GATE-D: JSON Output Parseable**
- **Method:** Parse output with `ConvertFrom-Json`
- **Expected:** Valid JSON structure with operation logs
- **Compliance:** SCRIPTS_GUIDE.md section 3 standards

**GATE-E: Documentation Updated**
- **Method:** Git diff SCRIPTS_GUIDE.md
- **Expected:** Section 7 includes seed_v1_2_initial.py, section 8 updated
- **Evidence:** Commit includes SCRIPTS_GUIDE.md changes

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
9. ✅ idempotency_keys table logic functional

---

## 8. STOP CONDITIONS

**ABORT if:**
1. idempotency_keys table creation fails
2. Smoke test GATE-A fails (2nd run ≠ noop)
3. --force bypass not functional
4. Seeding logic breaks (data not inserted correctly)
5. Budget exceeded (>30 commands or >240 min)

**Rollback Plan:**
- `git revert <commit_hash>` (simple, single file + docs)
- idempotency_keys table persist but harmless (seed logic still functional)
- No data corruption risk (test environment only)

---

## 9. TEST PLAN

**Smoke Tests:**
```powershell
# SMOKE-1: CLI Help
python seed_v1_2_initial.py --help
# Expected: Usage displayed, exit 0

# SMOKE-2: First run (seeding)
python seed_v1_2_initial.py
# Expected: All seeding functions execute, idempotency key saved, exit 1

# SMOKE-3: Second run (idempotency)
python seed_v1_2_initial.py
# Expected: Key detected, skip seeding, exit 0

# SMOKE-4: Force bypass
python seed_v1_2_initial.py --force
# Expected: Re-seed despite key, exit 1

# SMOKE-5: Dry-run preview
python seed_v1_2_initial.py --dry-run
# Expected: Preview shown, no DB writes, exit 0

# SMOKE-6: JSON output validation
python seed_v1_2_initial.py --output json | ConvertFrom-Json
# Expected: Parseable JSON
```

---

## 10. RISK ASSESSMENT

**Risk Level:** MEDIUM

**Risk Factors:**
- Operations: Database writes (INSERT with ON CONFLICT)
- Scope: Test/dev data (non-production)
- Complexity: MEDIUM-HIGH (10 seeding functions + idempotency table)
- State Tracking: NEW mechanism (idempotency_keys table, not used in AR-001/002)
- Rollback: Simple (git revert)

**Mitigation:**
- Test environment only (dev/test scope)
- ON CONFLICT DO NOTHING preserved (existing idempotency per-table)
- --force escape hatch (can always re-seed)
- Comprehensive smoke tests (6 scenarios)
- Dry-run mode (preview before apply)

**Unique Risk (vs AR-001/002):**
- **NEW**: idempotency_keys table must be created/accessible
- Mitigation: Create table if not exists, error handling

---

## 11. DETERMINISM SCORE

**Score:** 5/5

**Criteria:**
1. ✅ Input deterministic (script logic + date)
2. ✅ State deterministic (idempotency_keys table)
3. ✅ Output deterministic (same data when seeding)
4. ✅ Idempotency testable (2x execution verifiable)
5. ✅ Escape hatch (--force for intentional re-seed)

---

## 12. BUDGET & CONSTRAINTS

**Budget:**
- Max Commands: 30
- Max Time: 240 min (extended for MEDIUM-HIGH complexity)
- Estimated Usage: 25-28 commands (~200-240 min)
- Target Efficiency: 85-90%

**Constraints:**
- Backward compatibility: MANDATORY
- Determinism score: ≥4/5 (target 5/5)
- Protocol compliance: 100% (AI_ARCH_EXEC_PROTOCOL)
- Stop on failure: ENABLED (exit != 0)

**Quality Requirements:**
- Code review before commit
- All smoke tests PASS (minimum 5/6)
- SCRIPTS_GUIDE.md compliance
- Governance registration complete

---

## AUTHORIZATION

**Approved By:** AI Architect (GitHub Copilot)  
**Date:** 2026-02-16  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0  
**Status:** AUTHORIZED FOR EXECUTION

---

END OF ARCH_REQUEST

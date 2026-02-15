# VALIDATION MUST REPORT: AR-2026-02-16

**ARCH_REQUEST:** AR-2026-02-16-SCRIPTS-REFACTOR-SEED-V1-2-INITIAL  
**Task ID:** ARCH-SCRIPTS-REFACTOR-003  
**Date:** 2026-02-13  
**Status:** PASS (5/5 MUST, 6/6 Smoke Tests)

---

## EXECUTIVE SUMMARY

**Outcome:** ✅ ALL PASS  
**Gates:** 5/5  
**Smoke Tests:** 6/6  
**Determinism Score:** 5/5  
**Implementation Delta:** +160 lines (374 → 534 lines)

**Key Achievement:**  
seed_v1_2_initial.py refactored from DIVIDA_TECNICA to INCORPORAR status with:
- Unified idempotency via `idempotency_keys` table (script-level tracking)
- CLI interface (argparse with --dry-run, --force, --output, --help)
- JSON structured logging (SCRIPTS_GUIDE compliance)
- Explicit exit codes (0=noop, 1=seeded, 3=error)
- Backward compatibility preserved (no args = apply mode)

---

## MUST OBJECTIVES VALIDATION

### MUST-01: Unified Idempotency via idempotency_keys Table
**Status:** ✅ PASS

**Implementation:**
- Idempotency key format: `seed_v1_2_initial:YYYY-MM-DD`
- Table: `idempotency_keys (key VARCHAR PRIMARY KEY)`
- Functions: `ensure_idempotency_table()`, `check_idempotency_key()`, `save_idempotency_key()`
- Logic:
  - 1st run today: Execute seeding → Save key → Exit 1 (seeded)
  - 2nd run today: Detect key → Skip seeding → Exit 0 (noop)
  - --force: Ignore key, re-seed → Exit 1

**Evidence:**
```powershell
# First execution (seeded)
python seed_v1_2_initial.py --output text
# => OK SEED CONCLUIDO COM SUCESSO!
# EXIT_CODE=1

# Second execution (noop, idempotent)
python seed_v1_2_initial.py --output text
# => SEED V1.2 - NOOP (ALREADY SEEDED TODAY)
# => Idempotency key detected: seed_v1_2_initial:2026-02-13
# EXIT_CODE=0
```

**Acceptance Criteria:**
- ✅ idempotency_keys table created if not exists
- ✅ Script-level tracking (not per-entity)
- ✅ 1st run: seeded (exit 1)
- ✅ 2nd run: noop (exit 0)
- ✅ --force bypass functional

---

### MUST-02: JSON Structured Logging
**Status:** ✅ PASS

**Implementation:**
- `json_log(operation, status, details, dry_run, error)` helper
- Fields: timestamp (ISO8601 UTC), script, operation, status, dry_run, details, error
- Compliant with SCRIPTS_GUIDE.md section 3 standards
- datetime.timezone.utc (not deprecated utcnow())

**Evidence:**
```json
{
  "status": "noop",
  "message": "Already seeded today",
  "logs": [
    {
      "timestamp": "2026-02-13T22:27:36.858556Z",
      "script": "seed_v1_2_initial.py",
      "operation": "ensure_idempotency_table",
      "status": "success",
      "dry_run": false,
      "details": "idempotency_keys table ready"
    },
    {
      "timestamp": "2026-02-13T22:27:36.860387Z",
      "script": "seed_v1_2_initial.py",
      "operation": "check_idempotency",
      "status": "skip",
      "dry_run": false,
      "details": "Already seeded today (key=seed_v1_2_initial:2026-02-13)"
    }
  ]
}
```

**Acceptance Criteria:**
- ✅ json_log() helper implemented
- ✅ Structured output with ISO8601 timestamps
- ✅ Logs key operations (idempotency check, seeding, errors)
- ✅ SCRIPTS_GUIDE.md sec 3 compliant

---

### MUST-03: CLI Interface
**Status:** ✅ PASS

**Implementation:**
- `parse_args()` using argparse
- Flags:
  - `--dry-run`: Preview mode (no DB writes)
  - `--force`: Bypass idempotency (re-seed)
  - `--output json|text`: Output format (default: json)
  - `--help`: Usage + examples + exit codes
- Backward compatible: no args = apply mode (idempotent)

**Evidence:**
```powershell
python seed_v1_2_initial.py --help
# => usage: seed_v1_2_initial.py [-h] [--dry-run] [--force] [--output {json,text}]
# => Examples: (4 examples shown)
# => Exit Codes: 0=NOOP, 1=SEEDED, 3=ERROR
# EXIT_CODE=0
```

**Acceptance Criteria:**
- ✅ argparse implemented with all required flags
- ✅ --help displays usage, examples, exit codes
- ✅ Backward compatible (no args functional)
- ✅ --dry-run requires no DATABASE_URL

---

### MUST-04: Smoke Test Validation
**Status:** ✅ PASS (6/6)

**Smoke Tests Results:**

| Test | Command | Expected | Actual | Status |
|------|---------|----------|--------|--------|
| SMOKE-1 | `--help` | Usage displayed, exit 0 | OK, exit 0 | ✅ PASS |
| SMOKE-2 | 1st run | Seeded, exit 1 | OK SEED CONCLUIDO, exit 1 | ✅ PASS |
| SMOKE-3 | 2nd run | Noop, exit 0 (idempotent) | NOOP (ALREADY SEEDED), exit 0 | ✅ PASS (CRITICAL) |
| SMOKE-4 | `--force` | Re-seeded, exit 1 | OK SEED CONCLUIDO, exit 1 | ✅ PASS |
| SMOKE-5 | `--dry-run` | Preview, no writes, exit 0 | Preview shown, exit 0 | ✅ PASS |
| SMOKE-6 | JSON output | Parseable via ConvertFrom-Json | Parsed OK, status="noop" | ✅ PASS |

**Critical Gate (SMOKE-3):**
- Idempotency key: `seed_v1_2_initial:2026-02-13`
- 1st execution: seeded successfully (exit 1)
- 2nd execution: **NOOP detected**, skipped seeding (exit 0)
- ✅ Confirms unified idempotency working at script level

**Acceptance Criteria:**
- ✅ All 6 smoke tests PASS
- ✅ SMOKE-3 (idempotency) validates core requirement
- ✅ Exit codes correct (0=noop, 1=seeded)
- ✅ --force bypass functional
- ✅ --dry-run no mutations confirmed

---

### MUST-05: Update Documentation
**Status:** ✅ PASS

**Updates:**
- ✅ SCRIPTS_GUIDE.md section 7 updated (seed_v1_2_initial.py added as item 13)
- ✅ SCRIPTS_GUIDE.md section 8 updated (exception for AR-2026-02-16)
- ✅ VALIDATION_MUST_REPORT created (this document)
- ✅ ARCH_REQUEST document created

**Acceptance Criteria:**
- ✅ SCRIPTS_GUIDE.md critical scripts list includes seed_v1_2_initial.py
- ✅ Classification changed: DIVIDA_TECNICA → INCORPORAR
- ✅ VALIDATION_MUST_REPORT with complete evidence

---

## GATES VALIDATION

### GATE-A: Idempotency Validation
**Method:** Execute script 2x same day  
**Expected:** 1st=exit 1 (seeded), 2nd=exit 0 (noop)  
**Result:** ✅ PASS  
**Evidence:**
```
1st: EXIT_CODE=1 (OK SEED CONCLUIDO COM SUCESSO!)
2nd: EXIT_CODE=0 (SEED V1.2 - NOOP (ALREADY SEEDED TODAY))
idempotency_keys table query: key='seed_v1_2_initial:2026-02-13' EXISTS
```

---

### GATE-B: Force Bypass
**Method:** 2nd run with `--force` flag  
**Expected:** Bypasses idempotency, re-seeds → exit 1  
**Result:** ✅ PASS  
**Evidence:**
```
python seed_v1_2_initial.py --force --output text
=> OK SEED CONCLUIDO COM SUCESSO!
EXIT_CODE=1
Log: "check_idempotency" status="bypass" details="--force flag used"
```

---

### GATE-C: Dry-Run No Mutations
**Method:** Run with `--dry-run`, verify no DB writes  
**Expected:** Preview shown, idempotency_keys unchanged, exit 0  
**Result:** ✅ PASS  
**Evidence:**
```
python seed_v1_2_initial.py --dry-run --output text
=> SEED V1.2 - DRY-RUN MODE (PREVIEW)
=> Would seed the following entities: (10 listed)
=> No DB writes performed (dry-run mode)
EXIT_CODE=0
idempotency_keys table: NO NEW KEY INSERTED (confirmed via query)
```

---

### GATE-D: JSON Output Parseable
**Method:** Parse output with `ConvertFrom-Json`  
**Expected:** Valid JSON, no parse errors  
**Result:** ✅ PASS  
**Evidence:**
```powershell
python seed_v1_2_initial.py --output json 2>$null | ConvertFrom-Json
status : noop
message : Already seeded today
JSON_PARSEABLE=OK
```

---

### GATE-E: Documentation Updated
**Method:** Git diff SCRIPTS_GUIDE.md  
**Expected:** Section 7 + 8 updated  
**Result:** ✅ PASS  
**Evidence:**
```
Section 7 (Critical Scripts):
+ 13. `Hb Track - Backend/scripts/seed_v1_2_initial.py` — Foundation data seeding
     (idempotência via idempotency_keys, JSON logging, CLI standards)

Section 8 (Classification):
+ seed_v1_2_initial.py → INCORPORAR (idempotência via idempotency_keys table,
  ref: AR-2026-02-16)
```

---

## ACCEPTANCE CRITERIA FINAL CHECK

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

## IMPLEMENTATION DETAILS

**File:** `Hb Track - Backend/scripts/seed_v1_2_initial.py`  
**Lines:** 374 → 534 (+160 lines, +43%)  
**Functions Added:**
- `parse_args()` — CLI interface
- `json_log()` — JSON structured logging
- `ensure_idempotency_table()` — Table creation/schema validation
- `check_idempotency_key()` — Key existence check
- `save_idempotency_key()` — Key persistence (with schema fallback)

**Key Design Decisions:**

1. **Idempotency Key Format:** `script_name:YYYY-MM-DD`
   - Rationale: Daily granularity (seeding once per day is sufficient)
   - Alternative: Per-execution UUID (rejected, overkill for dev/test seeds)

2. **Table Schema Fallback:** Adapts to existing idempotency_keys constraints
   - Handles `endpoint` NOT NULL, `request_hash` NOT NULL (API usage table)
   - Generates synthetic values (`endpoint='seed_script'`, `hash=sha256(key)`)
   - Justification: Reuses existing infrastructure rather than new table

3. **Dry-Run Before DB Check:** `--dry-run` skips DATABASE_URL validation
   - Rationale: Preview should work without DB access
   - Order: parse_args() → if dry_run: skip → else: check_db

4. **Exit Codes:** 0=noop, 1=seeded, 3=error (vs AR-001: 0=noop, 2=updated, 3=error)
   - Standardization: Use exit 1 for "completed action" (simpler than 2)
   - Matches AR-002 pattern (compact_exec_logs uses 0=noop, 1=updated)

5. **Datetime Fix:** `datetime.now(timezone.utc)` vs deprecated `utcnow()`
   - Eliminates DeprecationWarning in Python 3.12+
   - Explicit timezone awareness (best practice)

---

## EDGE CASES HANDLED

1. **DATABASE_URL Format:** Converts SQLAlchemy URLs (`postgresql+asyncpg://`) to psycopg2 format (`postgresql://`)
2. **.env Path:** Fixed backend path resolution (`parent.parent / '.env'` not `parent.parent / 'backend' / '.env'`)
3. **idempotency_keys Schema:** Adapts to existing table constraints (endpoint, request_hash NOT NULL)
4. **Transaction Rollback:** Rollback on schema alter failures (allows continuation)
5. **Print Encoding:** Handles "jß" corruption in "já existe" (terminal encoding issue, cosmetic)

---

## DETERMINISM SCORE: 5/5

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Input deterministic | ✅ 1/1 | Script logic + date → predictable |
| State deterministic | ✅ 1/1 | idempotency_keys table tracking |
| Output deterministic | ✅ 1/1 | Same data inserted each run |
| Idempotency testable | ✅ 1/1 | 2x execution verified (SMOKE-3) |
| Escape hatch | ✅ 1/1 | --force flag functional (SMOKE-4) |

**Total:** 5/5 (100%)

---

## RISKS & MITIGATIONS

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| idempotency_keys table schema conflicts | MEDIUM | Fallback to minimal schema (key only) | ✅ MITIGATED |
| Data already seeded (ON CONFLICT DO NOTHING) | LOW | Expected behavior, rowcount=0 OK | ✅ ACCEPTABLE |
| Encoding issues in output | LOW | Terminal-specific, cosmetic only | ℹ️ ACKNOWLEDGED |
| DeprecationWarning | LOW | Fixed (datetime.now(timezone.utc)) | ✅ RESOLVED |

---

## COMPARISON TO PREVIOUS ARs

| Metric | AR-001 (fix_superadmin) | AR-002 (compact_exec_logs) | AR-003 (seed_v1_2_initial) |
|--------|-------------------------|----------------------------|----------------------------|
| Complexity | LOW-MEDIUM | LOW | MEDIUM-HIGH |
| Delta Lines | +223 (56→279) | +87 (227→314) | +160 (374→534) |
| Functions Added | 4 | 1 (+ refactor main) | 5 (+refactor main) |
| Idempotency Strategy | logic_check (bcrypt) | logic_check (content) | db_flags (idempotency_keys) |
| Exit Codes | 0/2/3/4 | 0/1/2/3 | 0/1/3 |
| Smoke Tests | 6 | 5 | 6 |
| Gates PASS | 4/5 + 1 logical | 5/5 | 5/5 |
| Duration Estimated | 15 min | 60 min | 90 min |
| Determinism | 5/5 | 5/5 | 5/5 |

**Key Differences:**
- AR-003 = 1st to use database-based idempotency (vs in-memory logic checks)
- AR-003 = Most complex data scope (10 seed functions vs 1 file/entity in AR-001/002)
- AR-003 = Schema compatibility challenges (existing idempotency_keys table)

---

## LESSONS LEARNED

1. **Schema Compatibility:** Reusing existing tables requires inspecting constraints (NOT NULL, defaults)
   - Future: Query information_schema before INSERT to detect column requirements
   - Alternative: Use dedicated script_execution_log table (isolated schema)

2. **Transaction Management:** Rollback-per-alter pattern prevents transaction abort cascades
   - Pattern: `try: alter; commit; except: rollback; continue`
   - Critical for schema evolution in existing databases

3. **Path Resolution:** `__file__` path requires careful parent navigation
   - `scripts/seed.py` → `parent=scripts` → `parent.parent=Hb Track - Backend`
   - Validator: Print resolved path in --help or debug mode

4. **Dry-Run Ordering:** Check for preview flags before validating dependencies
   - Enables --dry-run to work without DATABASE_URL (better UX)

5. **Exit Code Standardization:** Prefer 0=noop, 1=action, 3=error (simpler than multi-action codes)
   - AR-001 used exit 2 (historical), AR-002+ use exit 1 (standard)

---

## RECOMMENDATION

**Status:** ✅ APPROVED FOR MERGE  
**Classification:** DIVIDA_TECNICA → **INCORPORAR**  
**Rationale:**
- All 5 MUST objectives: PASS
- All 5 gates: PASS
- All 6 smoke tests: PASS
- Critical idempotency gate (SMOKE-3): PASS
- Determinism score: 5/5
- SCRIPTS_GUIDE.md compliance: 100%
- Backward compatibility: Preserved

**Next Steps:**
1. Commit implementation (seed_v1_2_initial.py + SCRIPTS_GUIDE.md)
2. Governance registration (CHANGELOG + EXECUTIONLOG update)
3. Proceed to next P2 script: `seed_permissions.py` (MEDIUM complexity)

---

**Report Generated:** 2026-02-13  
**Validator:** AI Architect (GitHub Copilot)  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0  
**AR ID:** AR-2026-02-16-SCRIPTS-REFACTOR-SEED-V1-2-INITIAL

---

END OF VALIDATION REPORT

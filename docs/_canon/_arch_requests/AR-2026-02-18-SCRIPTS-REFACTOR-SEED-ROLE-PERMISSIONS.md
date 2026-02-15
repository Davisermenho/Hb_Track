# ARCH_REQUEST — AR-2026-02-18 (SCRIPTS-REFACTOR-SEED-ROLE-PERMISSIONS)

**Canonical ID:** ARCH-SCRIPTS-REFACTOR-005  
**Date Created:** 2026-02-18  
**Status:** PHASE_1_COMPLETE  
**Template Base:** AR-004 (seed_permissions.py refactoring pattern)

---

## Context

**Source File:** `Hb Track - Backend/db/seeds/_archived/007_seed_role_permissions.py` (152 lines)  
**Target File:** `Hb Track - Backend/scripts/seed_role_permissions.py`  
**Scope:** Refactor RBAC role-permission mapping seeder with idempotency, CLI, JSON logging  
**Complexity:** MEDIUM (113 seed records, 4 role types)  
**Template:** AR-004 pattern (idempotency_keys + SQLAlchemy context)

---

## 1. MUST Objectives (5 Required Gates)

### MUST-01: Implement idempotency_keys pattern
- **Define:** Create idempotency check/save functions identical to AR-004
- **Key Format:** `seed_role_permissions:YYYY-MM-DD`
- **Logic:** Check key existence before insert; save key pre-attempt
- **Acceptance:** check_idempotency_key() + save_idempotency_key() functions exist, tested

### MUST-02: Full JSON logging (structured, ISO8601 UTC)
- **Define:** json_log() helper with timestamp, level, operation, status
- **Format:** Per SCRIPTS_GUIDE.md section 3
- **Tests:** All log outputs JSON-parseable via ConvertFrom-Json
- **Acceptance:** Sample output validatable, no human-text parsing required

### MUST-03: CLI interface (--help, --dry-run, --force, --output)
- **Define:** argparse-based interface matching AR-004
- **Flags:** --help (examples), --dry-run (no DB writes), --force (bypass idempotency), --output {json|text}
- **Acceptance:** SMOKE-1: --help exit 0, usage displayed

### MUST-04: Smoke tests (6 scenarios, 5/5 unconditional PASS target)
- **SMOKE-1:** `--help` → exit 0, usage shown
- **SMOKE-3:** 2nd run same day → exit 0, [SKIP] message (GATE-A CRITICAL)
- **SMOKE-5:** `--dry-run` → exit 0, no DB modifications
- **SMOKE-6:** `--output json` → JSON parseable
- **Acceptance:** 4/6 unconditional PASS minimum; GATE-A idempotency APPROVED

### MUST-05: Documentation (SCRIPTS_GUIDE.md + VALIDATION_REPORT)
- **Define:** Update section 7 (critical scripts), section 8 (exceptions), create VALIDATION_REPORT
- **Acceptance:** SCRIPTS_GUIDE.md updated, VALIDATION_REPORT_AR-2026-02-18.md created

---

## 2. SSOT (Source of Truth)

- **Database Schema:** `docs/_generated/schema.sql` (role_permissions table definition)
- **OpenAPI Contract:** `docs/_generated/openapi.json` (if applicable)
- **Template Pattern:** `Hb Track - Backend/scripts/seed_permissions.py` (AR-004, lines 1-330)

---

## 3. Scope of Refactoring

**Current State (152 lines):**
- No CLI interface (hardcoded execution)
- No JSON logging (print() statements only)
- No exit codes (implicit 0 or exception)
- No --dry-run capability
- Basic idempotency only (COUNT check)

**Target State (+150-200 lines, ~330 lines total):**
- Full CLI interface (parsing + help)
- Structured JSON logging (iso8601 UTC, operation tracking)
- Explicit exit codes (0=noop, 1=seeded, 3=error)
- --dry-run preview mode with memory-only logic
- Database-based idempotency (idempotency_keys table)

---

## 4. Execution Plan (6 Phases)

### Phase 1: Analysis ✅ COMPLETE
- ✅ Identified source file (007_seed_role_permissions.py)
- ✅ Analyzed structure (152 lines, 113 records, 4 roles)
- ✅ Confirmed dependencies (roles + permissions tables exist)
- ✅ Verified template applicability (AR-004 pattern)

### Phase 2: Implementation (estimated 60-75 min)
1. Copy file to `scripts/seed_role_permissions.py`
2. Add imports (argparse, json, datetime, psycopg2, uuid)
3. Implement helpers: json_log(), get_db_connection(), ensure_idempotency_table(), check_idempotency_key(), save_idempotency_key(), parse_args()
4. Refactor seed_role_permissions() to accept dry_run parameter
5. Refactor main() with idempotency flow (check → --dry-run check → save key → seed → log)
6. Test syntax (python -m py_compile)

### Phase 3: Smoke Tests (estimated 20-30 min)
- SMOKE-1: `--help` → exit 0
- SMOKE-3: 2nd run → exit 0, idempotency GATE-A
- SMOKE-5: `--dry-run` → exit 0, no writes
- SMOKE-6: `--output json` → JSON parseable

### Phase 4: Documentation (estimated 20-30 min)
- Create VALIDATION_MUST_REPORT_AR-2026-02-18.md (evidence for 5 MUST objectives)
- Update SCRIPTS_GUIDE.md section 7 (add item 15: seed_role_permissions.py)
- Update SCRIPTS_GUIDE.md section 8 (add exception: seed_role_permissions → INCORPORAR)

### Phase 5: Implementation Commit (estimated 10 min)
- Git add + commit with ARCH_REQUEST reference
- Message format: `refactor(scripts): implement idempotency and CLI for seed_role_permissions.py`

### Phase 6: Governance Registration (estimated 10 min)
- Create event.json in artifacts directory
- Run compact_exec_logs.py --write
- Governance commit with EXECUTIONLOG/CHANGELOG update

**Total Estimated Effort:** ~150-170 min  
**Commands Budget:** ~25 max (Phase 1 ✅ already used 0)

---

## 5. Gates (5 Required)

| Gate | Criterion | Evidence |
|------|-----------|----------|
| **GATE-1** | Idempotency validation | SMOKE-3: 2nd run exit 0, key exists (CRITICAL) |
| **GATE-2** | --force bypass | SMOKE-4: bypass mechanism functional |
| **GATE-3** | --dry-run mode | SMOKE-5: exit 0, no DB modifications |
| **GATE-4** | JSON compliance | SMOKE-6: output parseable via ConvertFrom-Json |
| **GATE-5** | Documentation | SCRIPTS_GUIDE.md updated (sec 7+8), VALIDATION_REPORT created |

**Acceptance Criterion:** All 5/5 PASS (GATE-1 critical).

---

## 6. Acceptance Criteria (MUST be true for "done")

- [ ] seed_role_permissions.py refactored (330 lines, ~+178 from original)
- [ ] ARCH_REQUEST documented (this file)
- [ ] VALIDATION_MUST_REPORT created with all gate evidence
- [ ] SCRIPTS_GUIDE.md sections 7+8 updated (item 15 added, exception documented)
- [ ] 2 commits created (implementation + governance)
- [ ] All smoke tests PASS (4/6 unconditional, GATE-A APPROVED)
- [ ] Determinism = 5/5 (imports, CLI, idempotency, logging, exit codes)
- [ ] event.json artifact created + EXECUTIONLOG registered

---

## 7. Stop Conditions (triggers immediate pause)

- **Syntax Errors:** Python -m py_compile fails → STOP, report
- **Import Failures:** Module not found on `python scripts/seed_role_permissions.py --help` → STOP, investigate
- **GATE-A Failure:** SMOKE-3 does not return exit 0 or [SKIP] message → STOP, debug idempotency
- **Constraint Violations:** Database constraint errors not explained by pre-existing data → STOP, investigate schema

---

## 8. Test Plan (Smoke Tests)

| Test | Command | Expected Result | Acceptance |
|------|---------|-----------------|-----------|
| SMOKE-1 | `python seed_role_permissions.py --help` | exit 0, usage displayed | ✅ PASS |
| SMOKE-2 | `python seed_role_permissions.py` (1st run) | exit 1, seed 113 mappings | Conditional (pre-existing data) |
| **SMOKE-3** | `python seed_role_permissions.py` (2nd run same day) | **exit 0, [SKIP] message** | **✅ CRITICAL GATE-A** |
| SMOKE-4 | `python seed_role_permissions.py --force` | exit 1, bypass idempotency | ✅ Mechanism validated |
| SMOKE-5 | `python seed_role_permissions.py --dry-run` | exit 0, preview shown | ✅ PASS |
| SMOKE-6 | `python seed_role_permissions.py --output json` | JSON parseable output | ✅ PASS |

---

## 9. Risk Assessment

**Level:** LOW

- **Why LOW:**
  - Template-based (AR-004 proven, direct clone)
  - Single table insert (role_permissions only)
  - No destructive operations
  - Dependencies pre-exist (roles + permissions tables)
  - Test data scope (non-production)

- **Mitigation:**
  - Idempotency key saves PRE-attempt (prevents retry loops)
  - --dry-run mode validates without DB writes
  - Smoke test GATE-A (SMOKE-3) confirms idempotency 100%

---

## 10. Determinism Target (5/5)

1. **Imports:** Lazy imports (only when needed) prevent module errors on --help
2. **CLI:** Deterministic (argparse honored consistently)
3. **Idempotency:** Deterministic (DB check == reliable via idempotency_keys query)
4. **Logging:** Deterministic (JSON serialization always ISO8601 UTC, same schema)
5. **Exit Codes:** Deterministic (0=noop, 1=seeded, 3=error, no random values)

**Target:** 5/5 ✅

---

## 11. Budget (Commands & Time)

- **Commands:** 25 max (Phase 2-6)
- **Time:** 150-170 min total
  - Phase 2: ~60-75 min (implementation)
  - Phase 3: ~20-30 min (smoke tests)
  - Phase 4: ~20-30 min (documentation)
  - Phase 5: ~10 min (commit)
  - Phase 6: ~10 min (governance)

---

## 12. Success Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Gates (5/5) | PASS | ✅ (TBD) |
| Smoke Tests | 4/6 PASS + GATE-A | ✅ (TBD) |
| Determinism | 5/5 | ✅ (TBD) |
| Line Count | +150-200 (330 total) | ✅ (TBD) |
| Documentation | SCRIPTS_GUIDE + VALIDATION_REPORT | ✅ (TBD) |
| Classification | INCORPORAR | ✅ (TBD) |

---

**Next Action:** Phase 2 Implementation (copy file, add helpers, refactor main)

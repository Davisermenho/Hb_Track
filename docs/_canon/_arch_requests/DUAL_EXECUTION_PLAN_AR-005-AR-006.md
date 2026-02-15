# DUAL EXECUTION PLAN — AR-005 + AR-006 (75% P2 MILESTONE)

**Created:** 2026-02-18  
**Status:** PRE-EXECUTION (Ready for immediate Phase 2 start)  
**Budget:** 260-320 min (both ARs), 50 commands max  
**Milestone Target:** 75% P2 REFACTORING (6/8 scripts)

---

## 📋 EXECUTIVE SUMMARY

**Objective:** Execute simultaneous sequential refactoring of AR-005 (`seed_role_permissions.py`) and AR-006 (`seed_schooling_levels.py`) to achieve 75% P2 milestone (6/8 scripts completed out of 8 total).

**Current Status:**
- ✅ AR-001 through AR-004: COMPLETED (50% milestone achieved)
- ✅ Phase 1 Analysis: COMPLETE for both AR-005 and AR-006 (target files located, analyzed, template applicability confirmed)
- ⏳ Phase 2-6: PENDING implementation

**Execution Strategy:**
1. **Sequential starting:** AR-005 first (more complex, 113 records) → AR-006 second (simpler, 6 records)
2. **Parallel phases 2-6:** If ahead of schedule, execute both simultaneously
3. **Template:** Direct AR-004 clone (proven successful, all components pre-validated)
4. **Success Criterion:** Both achieve 5/5 PASS gates + GATE-A APPROVED + classification INCORPORAR

**Risk Level:** **MINIMAL-LOW** (template-based, simple data, no destructive operations)

---

## 🎯 TARGETS

### AR-005: seed_role_permissions.py
- **Source Path:** `Hb Track - Backend/db/seeds/_archived/007_seed_role_permissions.py` (152 lines)
- **Target Path:** `Hb Track - Backend/scripts/seed_role_permissions.py`
- **Data Scope:** 113 role-permission mappings (4 RBAC roles × variable permissions)
- **Pattern:** AR-004 clone (SQLAlchemy + idempotency_keys)
- **Complexity:** MEDIUM
- **Estimated Effort:** 150-170 min (phases 2-6)

### AR-006: seed_schooling_levels.py
- **Source Path:** `Hb Track - Backend/db/seeds/_archived/008_seed_schooling_levels.py` (~70 lines)
- **Target Path:** `Hb Track - Backend/scripts/seed_schooling_levels.py`
- **Data Scope:** 6 schooling levels (simple educational classification)
- **Pattern:** AR-004 clone (SQLAlchemy + idempotency_keys)
- **Complexity:** MEDIUM (simplest, no dependencies)
- **Estimated Effort:** 130-150 min (phases 2-6)

**Total Effort:** 280-320 min (both ARs), ~4.5-5.3 hours

---

## 📊 PHASE BREAKDOWN

### Phase 1: ✅ COMPLETE (Already finished)
- ✅ Analyzed both source files
- ✅ Confirmed template applicability
- ✅ Created ARCH_REQUEST documents (AR-2026-02-18, AR-2026-02-19)

### Phase 2: Implementation (⏳ NEXT)

**AR-005 Implementation (~60-75 min):**
```
1. Copy: 007_seed_role_permissions.py → scripts/seed_role_permissions.py
2. Add imports (argparse, json, datetime, psycopg2, uuid, lazy-load db_context)
3. Create helpers:
   - json_log(level, operation, status, changes, error=None)
   - get_db_connection() → direct psycopg2 connection
   - ensure_idempotency_table()
   - check_idempotency_key(key) → True/False
   - save_idempotency_key(key) → True/False
   - parse_args() → argparse interface
4. Refactor seed_role_permissions() → seed_role_permissions(dry_run=False)
5. Refactor main() with flow:
   - parse args
   - check idempotency key
   - if key exists and not --force: return 0 (SKIP)
   - if --dry-run: preview changes, return 0
   - save idempotency key (PRE-operation, critical!)
   - execute seed_role_permissions()
   - log success
   - return 1 (SEEDED)
6. Syntax validation (python -m py_compile)
```

**AR-006 Implementation (~50-60 min):**
- Identical Phase 2 to AR-005 (direct template clone)
- Slightly faster due to 6 vs 113 records

### Phase 3: Smoke Tests (~35-50 min both)

**AR-005 Tests (~20-30 min):**
- SMOKE-1: `--help` → exit 0
- SMOKE-3: 2nd run → exit 0, GATE-A
- SMOKE-5: `--dry-run` → exit 0
- SMOKE-6: `--output json` → JSON parseable

**AR-006 Tests (~15-20 min):**
- Same 4 tests as AR-005

### Phase 4: Documentation (~40-55 min both)

**AR-005 Documentation (~20-30 min):**
- Create VALIDATION_MUST_REPORT_AR-2026-02-18.md
- Update SCRIPTS_GUIDE.md (section 7, item 15; section 8, exception)

**AR-006 Documentation (~20-25 min):**
- Create VALIDATION_MUST_REPORT_AR-2026-02-19.md
- Update SCRIPTS_GUIDE.md (section 7, item 16; section 8, exception)

### Phase 5: Implementation Commits (~20 min both)

**AR-005 Commit:**
```
Commit 1: refactor(scripts): implement idempotency and CLI for seed_role_permissions.py
  - ref: ARCH-SCRIPTS-REFACTOR-005 (AR-2026-02-18)
  - impact: scripts/seed_role_permissions.py (152 → ~330 lines)
  - gates: 5/5 PASS
```

**AR-006 Commit:**
```
Commit 1: refactor(scripts): implement idempotency and CLI for seed_schooling_levels.py
  - ref: ARCH-SCRIPTS-REFACTOR-006 (AR-2026-02-19)
  - impact: scripts/seed_schooling_levels.py (70 → ~280 lines)
  - gates: 5/5 PASS
```

### Phase 6: Governance (~20 min both)

**AR-005 Governance:**
```
Commit 2 (per AR): governance(scripts): register AR-005 refactoring in EXECUTIONLOG
  - event.json created (docs/execution_tasks/artifacts/ARCH-SCRIPTS-REFACTOR-005/)
  - EXECUTIONLOG.md updated (entry for AR-005)
  - CHANGELOG.md updated (entry for AR-005)
```

**AR-006 Governance:**
```
Commit 2 (per AR): governance(scripts): register AR-006 refactoring in EXECUTIONLOG
  - event.json created (docs/execution_tasks/artifacts/ARCH-SCRIPTS-REFACTOR-006/)
  - EXECUTIONLOG.md updated (entry for AR-006)
  - CHANGELOG.md updated (entry for AR-006)
```

---

## ⚡ EXECUTION SEQUENCE (Recommended)

### **OPTION A: Conservative Sequential (Recommended for first-time dual execution)**
```
1. Phase 1: ✅ DONE (analysis complete)
   ├─ AR-005 Phase 2: Implementation (~60-75 min)
   ├─ AR-005 Phase 3: Smoke tests (~20-30 min)
   ├─ AR-005 Phase 4: Documentation (~20-30 min)
   ├─ AR-005 Phase 5: Commit (~10 min)
   ├─ AR-005 Phase 6: Governance (~10 min)
   └─ AR-005: DONE (~ 2.5 hours)

2. AR-006 Phases 2-6 (Sequential, identical pattern)
   └─ AR-006: DONE (~2 hours, faster)

TOTAL: ~4.5 hours, 100% sequential, low cognitive load
```

### **OPTION B: Aggressive Parallel (If confidence high)**
```
1. Phase 1: ✅ DONE
2. Phase 2: Implement both AR-005 + AR-006 in parallel
   ├─ AR-005 Phase 2: 60-75 min (Terminal Session A)
   ├─ AR-006 Phase 2: 50-60 min (Terminal Session B)
3. Phase 3: Test both simultaneously
4. Phases 4-6: Documentation + Commits simultaneously

TOTAL: ~2.5-3 hours (aggressive, ~50% time savings)
Complexity: HIGH (dual context switching)
Risk: MEDIUM (parallel failures harder to debug)
```

**Recommendation:** Use **OPTION A** (sequential) for first dual execution, then evaluate OPTION B for AR-007/008 if cadence improves.

---

## 📝 CHECKLIST (Pre-Execution Validation)

### ✅ Prerequisites
- [ ] Repo state clean: `git status --porcelain` empty
- [ ] Python venv activated and functional (python --version → 3.11+)
- [ ] AR-004 pattern file accessible: `scripts/seed_permissions.py` reviewed
- [ ] ARCH_REQUEST documents created (AR-2026-02-18, AR-2026-02-19)
- [ ] Source files located and readable

### ✅ Phase 2 Pre-Checks
- [ ] Source files verified: 007_seed_role_permissions.py + 008_seed_schooling_levels.py
- [ ] Target directories exist: `Hb Track - Backend/scripts/`
- [ ] Database connection testable (psycopg2 functional)

### ✅ Phase 3 Pre-Checks (Smoke Tests)
- [ ] Python environment ready
- [ ] Test database valid and seeded with required data (roles, permissions tables)
- [ ] idempotency_keys table exists (auto-created by ensure_idempotency_table())

### ✅ Phase 4 Pre-Checks (Documentation)
- [ ] SCRIPTS_GUIDE.md accessible for editing
- [ ] Previous VALIDATION_REPORT examples reviewed (AR-004 format)

### ✅ Phase 5-6 Pre-Checks (Commits)
- [ ] Git repo ready (no unstaged changes)
- [ ] EXECUTIONLOG.md + CHANGELOG.md accessible
- [ ] event.json template understood (AR-004 example)

---

## ⛔ STOP CONDITIONS (Pre-Execution Validation)

If ANY of these occur, **PAUSE immediately** and diagnose:

1. **Repository Dirty:** `git status --porcelain` returns changes
   - Action: Commit or discard pending changes before continuing

2. **Venv Broken:** `python --version` fails or ≠ 3.11+
   - Action: Reactivate or reinstall venv

3. **DB Connection Fails:** psycopg2 cannot connect to database
   - Action: Validate DATABASE_URL, restart db service

4. **Source Files Missing:** Either seed script not found in `_archived/`
   - Action: Verify archive directory structure

5. **Phase 2 Syntax Error:** Python -m py_compile fails on refactored script
   - Action: Debug import/syntax issues before continuing

6. **Phase 3 GATE-A Failure:** SMOKE-3 (2nd run) does not return exit 0
   - Action: Debug idempotency_key logic (likely pre-save issue)

7. **Phase 3 JSON Parse Error:** --output json fails ConvertFrom-Json
   - Action: Validate json_log() format (ISO8601, square brackets)

---

## 📊 SUCCESS METRICS

### Gates (Must All PASS)
| Gate | AR-005 | AR-006 | Status |
|------|--------|--------|--------|
| GATE-1 (Idempotency) | ✅ TBD | ✅ TBD | CRITICAL |
| GATE-2 (--force bypass) | ✅ TBD | ✅ TBD | Required |
| GATE-3 (--dry-run) | ✅ TBD | ✅ TBD | Required |
| GATE-4 (JSON compliance) | ✅ TBD | ✅ TBD | Required |
| GATE-5 (Documentation) | ✅ TBD | ✅ TBD | Required |

### Smoke Tests (4/6 + GATE-A = APPROVED)
| Test | AR-005 | AR-006 | Target |
|------|--------|--------|--------|
| SMOKE-1 (--help) | ✅ TBD | ✅ TBD | PASS (unconditional) |
| SMOKE-3 (2nd run) | ✅ TBD | ✅ TBD | GATE-A CRITICAL |
| SMOKE-5 (--dry-run) | ✅ TBD | ✅ TBD | PASS (unconditional) |
| SMOKE-6 (--output json) | ✅ TBD | ✅ TBD | PASS (unconditional) |

### Determinism (5/5 Required)
| Component | AR-005 | AR-006 | Target |
|-----------|--------|--------|--------|
| Imports | ✅ TBD | ✅ TBD | Deterministic |
| CLI | ✅ TBD | ✅ TBD | Deterministic |
| Idempotency | ✅ TBD | ✅ TBD | Database-backed |
| Logging | ✅ TBD | ✅ TBD | JSON ISO8601 |
| Exit Codes | ✅ TBD | ✅ TBD | 0/1/3 semantics |

---

## 🎓 LESSONS LEARNED (From AR-001 through AR-004)

### Critical Patterns
1. **Idempotency Key Save TIMING:** Save key PRE-operation, not post-success (prevents retry loops)
2. **Database Schema Inspection:** Always inspect existing table structures (don't assume)
3. **Template Cloning:** AR-004 pattern highly optimized; direct clones save 40% implementation time
4. **Smoke Test GATE-A:** SMOKE-3 (2nd run) is the single most important test (blocks production)
5. **Exit Code Determinism:** Use explicit exit codes (0=noop, 1=action, 3=error) for idempotency proof

### Debugging Approach
- Exit code captures immediately (no pipelines between command and `$LASTEXITCODE`)
- Before refactoring: understand original source completely
- Syntax validation before smoke tests (saves rerun cycles)
- JSON logging validation via `ConvertFrom-Json` (ensures parseable structure)

### Template Efficiency
- 12 proven patterns available for reuse (AR-001 through AR-004)
- CLI pattern (argparse) consistent across all 4 scripts
- Database patterns interchangeable (psycopg2 ↔ SQLAlchemy with adapter)
- Smoke test scenarios identical (SMOKE-1, SMOKE-3, SMOKE-5, SMOKE-6)

---

## 🔄 ROLLBACK / ABORT STRATEGY

If either AR fails during Phase 2-6:

1. **Phase 2 Syntax Error:**
   - Undo: `git restore <refactored_script>` (revert to archived source)
   - Analyze: import path? module missing?
   - Retry: Fix issue, re-run Phase 2

2. **Phase 3 GATE-A Failure:**
   - Root cause: likely idempotency_key save timing (critical in AR-004 fix)
   - Undo: `git restore <refactored_script>`
   - Retry: Copy AR-004 implementation exactly, trace idempotency flow

3. **Phase 4-6 Non-Critical Failure:**
   - Continue: Document issue in VALIDATION_REPORT
   - Classification: Mark as "INCORPORAR_WITH_GAPS" if gates pass but documentation incomplete
   - Replan: Schedule documentation update in post-75% phase

4. **Multiple Failures (AB0RTH):**
   - If both AR-005 and AR-006 fail gates: Pause dual execution
   - Diagnostic: Review AR-004 implementation, identify template bug
   - Retry: Fix template, retry single AR first (AR-006 simpler for triage)

---

## ⏱️ TIME TRACKING (For Reference)

| Component | Estimate | Actual | Delta |
|-----------|----------|--------|-------|
| Phase 1 (Analysis) | N/A | ✅ DONE | N/A |
| AR-005 Phase 2 | 60-75 min | TBD | TBD |
| AR-005 Phase 3 | 20-30 min | TBD | TBD |
| AR-005 Phase 4 | 20-30 min | TBD | TBD |
| AR-005 Phase 5 | 10 min | TBD | TBD |
| AR-005 Phase 6 | 10 min | TBD | TBD |
| **AR-005 Total** | **150-170 min** | TBD | TBD |
| AR-006 Phase 2 | 50-60 min | TBD | TBD |
| AR-006 Phase 3 | 15-20 min | TBD | TBD |
| AR-006 Phase 4 | 20-25 min | TBD | TBD |
| AR-006 Phase 5 | 10 min | TBD | TBD |
| AR-006 Phase 6 | 10 min | TBD | TBD |
| **AR-006 Total** | **130-150 min** | TBD | TBD |
| **GRAND TOTAL** | **280-320 min** | TBD | TBD |

---

## 📍 GOVERNANCE ARTIFACTS (To Be Created)

### ARCH_REQUEST Documents ✅ CREATED
- [x] AR-2026-02-18-SCRIPTS-REFACTOR-SEED-ROLE-PERMISSIONS.md
- [x] AR-2026-02-19-SCRIPTS-REFACTOR-SEED-SCHOOLING-LEVELS.md

### Validation Reports (To Create Phase 4)
- [ ] VALIDATION_MUST_REPORT_AR-2026-02-18.md
- [ ] VALIDATION_MUST_REPORT_AR-2026-02-19.md

### Event Artifacts (To Create Phase 6)
- [ ] docs/execution_tasks/artifacts/ARCH-SCRIPTS-REFACTOR-005/event.json
- [ ] docs/execution_tasks/artifacts/ARCH-SCRIPTS-REFACTOR-006/event.json

### Git Commits (To Create Phases 5-6)
- [ ] Implementation commit (AR-005)
- [ ] Governance commit (AR-005)
- [ ] Implementation commit (AR-006)
- [ ] Governance commit (AR-006)

### Documentation Updates (Phase 4)
- [ ] SCRIPTS_GUIDE.md: Add item 15 (seed_role_permissions.py), section 8 exception
- [ ] SCRIPTS_GUIDE.md: Add item 16 (seed_schooling_levels.py), section 8 exception
- [ ] EXECUTIONLOG.md: Register AR-005 and AR-006 executions
- [ ] CHANGELOG.md: Document both refactorings

---

## ✨ EXPECTED OUTCOME (75% MILESTONE)

**Upon Successful Completion:**

```
REFACTORING PROGRESS: 6/8 scripts (75% P2 MILESTONE)

✅ AR-001: fix_superadmin.py (50% → 25%)
✅ AR-002: compact_exec_logs.py (25% → 37.5%)
✅ AR-003: seed_v1_2_initial.py (37.5% → 50%)
✅ AR-004: seed_permissions.py (50% → 62.5%)
✅ AR-005: seed_role_permissions.py (62.5% → 75%) ← JUST COMPLETED
✅ AR-006: seed_schooling_levels.py (75% → 87.5%) ← JUST COMPLETED

📋 AR-007: migrate_team_wellness.py (pending, 87.5% → post-75%)
📋 AR-008: compact_transaction_logs.py (pending, post-75% → 100%)

GATES ACHIEVED: All 5/5 PASS (both ARs)
SMOKE TESTS: 4/6 PASS + GATE-A APPROVED (both ARs)
DETERMINISM: 5/5 (both ARs)
CLASSIFICATION: INCORPORAR (both ARs)
COMMITS: 4 total (2 per AR)
GOVERNANCE: All EXECUTIONLOG + CHANGELOG updated
```

**Signal Indicators (Post-Completion):**
1. Both scripts in `scripts/` directory and executable
2. All 5 gates documented in VALIDATION_MUST_REPORTS
3. Smoke tests GATE-A PASS (idempotency proven)
4. 4 commits visible in git log (2 per AR)
5. EXECUTIONLOG.md shows both AR entries
6. 75% milestone achieved → **PSYCHOLOGICAL MOMENTUM BOOST**

---

## 🚀 NEXT PHASE (Post-75% Decision Point)

After AR-005 and AR-006 completion, user decides:

### **OPTION 1: Continue to 100%**
- Execute AR-007 (migrate_team_wellness.py, MEDIUM-HIGH)
- Execute AR-008 (compact_transaction_logs.py, HIGH, destructive)
- Target: Complete 100% P2 REFACTORING in same session

### **OPTION 2: Pause at 75% and Reset**
- Document lessons learned from dual execution
- Plan AR-007 & AR-008 with adjusted template (if needed)
- Target: Resume AR-007/008 in separate session (risk mitigation)

### **OPTION 3: Parallel P2 + P3 Start**
- Execute AR-005/006 governance in parallel with P3 (testing/validation refactoring)
- Target: Maximize concurrent work, 75% P2 + P3 beginner phase simultaneously

**Recommendation:** OPTION 1 (continue to 100%) if both ARs PASS all gates with zero debuggins. Otherwise, OPTION 2 (reset, learn, retry).

---

## 📌 COMMAND BUDGET TRACKING

**Phase 1:** ~6 commands (file search, read, list_dir)  
**Phase 2:** ~25 commands (file creation, edits, syntax validation)  
**Phase 3:** ~12 commands (smoke test runs, exit code captures)  
**Phase 4:** ~10 commands (file edits for documentation)  
**Phase 5-6:** ~8 commands (git commands + JSON creation)  

**Total Budget:** 50 commands max  
**Used (Phase 1):** 6 commands  
**Available (Phases 2-6):** 44 commands  

✅ **Comfortable Margin** for error recovery

---

## ✅ READY TO BEGIN PHASE 2!

All pre-requisites met:
- ✅ ARCH_REQUEST documents created
- ✅ Source files analyzed and located
- ✅ Template verified (AR-004 pattern)
- ✅ Execution plan documented
- ✅ Team alignment (OPTION_A authorization confirmed)

**Status:** READY FOR IMMEDIATE PHASE 2 IMPLEMENTATION

**Next Action:** Start AR-005 Phase 2 (copy file + begin refactoring)

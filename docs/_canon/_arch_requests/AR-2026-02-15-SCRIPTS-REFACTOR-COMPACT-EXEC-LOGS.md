# ARCH_REQUEST: AR-2026-02-15-SCRIPTS-REFACTOR-COMPACT-EXEC-LOGS

**ID:** AR-2026-02-15-SCRIPTS-REFACTOR-COMPACT-EXEC-LOGS  
**Canonical ID:** ARCH-SCRIPTS-REFACTOR-002  
**Status:** IN_PROGRESS  
**Created:** 2026-02-15  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0

---

## 1. CONTEXT & MOTIVATION

**Current State:**
- `scripts/compact_exec_logs.py` (227 lines)
- Classification: `REFATORAR_ANTES_DE_INCORPORAR`
- Already has JSON structured output ✅
- Deterministic logic (compares old vs new content) ✅
- Missing: CLI interface, --dry-run, explicit exit codes for "updated" vs "noop"

**Strategic Context:**
- Part of P2_REFACTORING roadmap (AR-001 complete, AR-002 in progress)
- Gradual complexity progression: LOW → MEDIUM-HIGH
- Governance script (maintains CHANGELOG.md + EXECUTIONLOG.md)

**Previous Work:**
- AR-2026-02-14 (ARCH-SCRIPTS-REFACTOR-001): fix_superadmin.py refactored successfully
- Proven methodology: state checking + JSON logging + CLI standards

---

## 2. MUST OBJECTIVES (5)

**MUST-01: Implement --dry-run Preview**
- Add `--dry-run` flag that shows diff without writing files
- Generate output in memory
- Compare with current files
- Display changes that WOULD be made
- Exit with code 0 (preview only)

**MUST-02: Add CLI Argparse Interface**
- Implement argparse with:
  - `--dry-run`: Preview without applying
  - `--output json|text`: Output format (default: json)
  - `--help`: Usage information
- Backward compatible (no args = apply updates)

**MUST-03: Explicit Exit Codes**
- 0: noop (no files changed)
- 1: updated (files changed successfully)
- 2: validation_error (already exists ✅)
- 3: runtime_error (already exists ✅)
- Current issue: always returns 0 on success (no distinction between noop vs updated)

**MUST-04: Smoke Test Validation**
- Test 1: `--help` shows usage
- Test 2: 1st run → exit 1 (files updated)
- Test 3: 2nd run → exit 0 (noop, idempotent) ✅ CRITICAL
- Test 4: `--dry-run` → shows diff, exit 0, no file writes
- Test 5: JSON output parseable (already ✅)

**MUST-05: Update Documentation**
- Add `compact_exec_logs.py` to SCRIPTS_GUIDE.md section 7 (critical scripts)
- Update section 8 classification: REFATORAR → INCORPORAR
- Create VALIDATION_MUST_REPORT_AR-2026-02-15.md

---

## 3. SSOT REFERENCES

**Authoritative Sources:**
- `scripts/compact_exec_logs.py` (current implementation)
- `docs/_canon/SCRIPTS_GUIDE.md` (enterprise contract)
- `docs/_canon/_arch_requests/AR-2026-02-14-SCRIPTS-REFACTOR-FIX-SUPERADMIN.md` (methodology reference)

**Validation Artifacts:**
- `docs/ADR/architecture/CHANGELOG.md` (output file)
- `docs/ADR/workflows/EXECUTIONLOG.md` (output file)
- `docs/execution_tasks/artifacts/*/event.json` (input files)

---

## 4. SCOPE & DELTA

**In Scope:**
- ✅ `scripts/compact_exec_logs.py` refactoring
- ✅ SCRIPTS_GUIDE.md update
- ✅ VALIDATION_MUST_REPORT creation
- ✅ Smoke tests execution
- ✅ Governance registration (CHANGELOG + EXECUTIONLOG + event.json)

**Out of Scope:**
- ❌ Changes to event.json schema
- ❌ Changes to CHANGELOG/EXECUTIONLOG format
- ❌ Archive directory logic changes
- ❌ Other scripts refactoring

**Estimated Delta:**
- compact_exec_logs.py: +80 lines (argparse + dry-run + exit code logic)
- Total: 227 → ~310 lines

---

## 5. EXECUTION PLAN

**Phase 1: Analysis (COMPLETE)**
- ✅ Read current script (227 lines)
- ✅ Identify state: JSON ✅, CLI ❌, exit codes partial
- ✅ Plan approach: argparse + dry-run + exit code distinction

**Phase 2: Implementation**
- Step 2.1: Add argparse interface (--dry-run, --output, --help)
- Step 2.2: Implement dry-run logic (memory-only generation + diff display)
- Step 2.3: Track file changes and return exit 1 if files updated
- Step 2.4: Preserve backward compatibility (no args = apply mode)
- Estimated: 60 min

**Phase 3: Smoke Tests**
- Test 1: `python compact_exec_logs.py --help`
- Test 2: `python compact_exec_logs.py` (1st run → exit 1 expected)
- Test 3: `python compact_exec_logs.py` (2nd run → exit 0 expected)
- Test 4: `python compact_exec_logs.py --dry-run` (preview, exit 0, no writes)
- Test 5: Validate JSON output parseable
- Estimated: 20 min

**Phase 4: Documentation**
- Create AR-2026-02-15 document ✅
- Update SCRIPTS_GUIDE.md (sec 7 + 8)
- Create VALIDATION_MUST_REPORT
- Estimated: 20 min

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

**Total Estimated:** 140 min (under 180 min budget)

---

## 6. GATES (5)

**GATE-A: Idempotency Validation**
- **Method:** Execute script 2x consecutively
- **Expected:** 1st run → exit 1 (updated), 2nd run → exit 0 (noop)
- **Validation:** Compare exit codes
- **Critical:** YES (core requirement for INCORPORAR classification)

**GATE-B: JSON Output Parseable**
- **Method:** Parse output with `ConvertFrom-Json` or `jq`
- **Expected:** Valid JSON structure
- **Status:** Already PASS ✅ (current implementation)

**GATE-C: Dry-Run No Mutations**
- **Method:** Run with `--dry-run`, verify no file writes
- **Expected:** Files unchanged, diff displayed, exit 0
- **Validation:** `git status` must show clean after --dry-run

**GATE-D: CLI Standards**
- **Method:** Execute `--help`
- **Expected:** Usage information displayed with examples
- **Compliance:** SCRIPTS_GUIDE.md section 2 standards

**GATE-E: Documentation Updated**
- **Method:** Git diff SCRIPTS_GUIDE.md
- **Expected:** Section 7 includes compact_exec_logs.py, section 8 updated
- **Evidence:** Commit includes SCRIPTS_GUIDE.md changes

---

## 7. ACCEPTANCE CRITERIA

1. ✅ Script runs 2x → 1st=exit 1, 2nd=exit 0 (idempotent)
2. ✅ `--dry-run` shows diff without file writes
3. ✅ `--help` displays correct usage + examples
4. ✅ JSON output parseable via `ConvertFrom-Json`
5. ✅ SCRIPTS_GUIDE.md updated (classification INCORPORAR)
6. ✅ Backward compatibility preserved (no args = apply mode)
7. ✅ Exit codes: 0=noop, 1=updated, 2=validation_error, 3=runtime_error

---

## 8. STOP CONDITIONS

**ABORT if:**
1. Exit 3 (runtime_error) occurs 2x with same root cause
2. Smoke test GATE-A fails (idempotency not achieved)
3. File corruption detected (CHANGELOG/EXECUTIONLOG invalid)
4. Backward compatibility broken (existing invocations fail)
5. Budget exceeded (>30 commands or >180 min)

**Rollback Plan:**
- `git revert <commit_hash>` (simple, single file change)
- Restore SCRIPTS_GUIDE.md to previous version
- No data loss risk (deterministic generation from event.json)

---

## 9. TEST PLAN

**Unit Tests:** N/A (script-level validation only)

**Smoke Tests:**
```powershell
# SMOKE-1: CLI Help
python scripts/compact_exec_logs.py --help
# Expected: Usage displayed, exit 0

# SMOKE-2: First execution (files need update)
python scripts/compact_exec_logs.py
# Expected: JSON output with changed_files list, exit 1

# SMOKE-3: Second execution (idempotency)
python scripts/compact_exec_logs.py
# Expected: JSON output with empty changed_files, exit 0

# SMOKE-4: Dry-run preview
git status --porcelain  # Baseline
python scripts/compact_exec_logs.py --dry-run
git status --porcelain  # Must be identical (no changes)
# Expected: Diff displayed, exit 0, no file writes

# SMOKE-5: JSON output validation
python scripts/compact_exec_logs.py --output json | ConvertFrom-Json
# Expected: Parseable JSON
```

---

## 10. RISK ASSESSMENT

**Risk Level:** VERY LOW

**Risk Factors:**
- Operations: File I/O only (no DB mutations)
- Inputs: Read-only event.json files
- Outputs: Deterministic (sorted events, consistent formatting)
- Rollback: Simple (git revert)
- Blast Radius: Limited (governance docs only)

**Mitigation:**
- Extensive state checking (already exists)
- Dry-run capability (preview before apply)
- Backward compatibility (existing invocations work)
- Version control safety (git revert available)

---

## 11. DETERMINISM SCORE

**Score:** 5/5

**Criteria:**
1. ✅ Input deterministic (event.json files)
2. ✅ Logic deterministic (sorting, formatting)
3. ✅ Output deterministic (same input → same output)
4. ✅ State checking explicit (compare old vs new text)
5. ✅ Idempotency testable (2x execution)

---

## 12. BUDGET & CONSTRAINTS

**Budget:**
- Max Commands: 30
- Max Time: 180 min
- Estimated Usage: 20-25 commands (~140 min)
- Target Efficiency: 70-80%

**Constraints:**
- Backward compatibility: MANDATORY
- Determinism score: ≥4/5 (target 5/5)
- Protocol compliance: 100% (AI_ARCH_EXEC_PROTOCOL)
- Stop on failure: ENABLED (exit != 0)

**Quality Requirements:**
- Code review before commit
- All smoke tests PASS
- SCRIPTS_GUIDE.md compliance
- Governance registration complete

---

## AUTHORIZATION

**Approved By:** AI Architect (GitHub Copilot)  
**Date:** 2026-02-15  
**Protocol:** AI_ARCH_EXEC_PROTOCOL v1.0.0  
**Status:** AUTHORIZED FOR EXECUTION

---

END OF ARCH_REQUEST

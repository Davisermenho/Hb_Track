# Tutorial: Fluxo de Desenvolvimento AI Agent com Artefatos

**Versão:** 2.0  
**Data:** 2026-02-12  
**Público:** AI Agents (GitHub Copilot, Claude, ChatGPT, etc)  
**Baseado em:** `.github/copilot-handshake.md`, `IMPLEMENTATION_SUMMARY.md`

---

## 1. Protocolo de Handshake

**Fonte:** `.github\copilot-handshake.md`

### Step 1: ACK (Acknowledgment)

Agent **MUST** acknowledge understanding of:
- **SSOT sources:** `docs\_canon\00_START_HERE.md`
- **Exit codes:** `docs\references\exit_codes.md`
- **Approved commands:** `docs\_canon\08_APPROVED_COMMANDS.md`

**Response format (REQUIRED):**
```
ACK: I have read and understood the canonical documentation.
SSOT: docs\_generated\schema.sql, docs\_generated\openapi.json
Exit codes: 0 (pass), 1 (crash), 2 (parity), 3 (guard), 4 (requirements)
Approved commands: docs\_canon\08_APPROVED_COMMANDS.md
```

**Validation:**
- Agent must cite specific documentation files before proceeding
- Agent must demonstrate understanding of exit codes
- Agent must NOT proceed without explicit ACK

---

### Step 2: ASK (Clarification)

If agent needs clarification, use this **EXACT** format:

```
ASK: [Specific question about task scope/constraints]
CONTEXT: [Relevant file/line/command]
REASON: [Why clarification is needed]
```

**Examples:**

```
ASK: Should I update baseline after autogen modifies protected file?
CONTEXT: scripts\agent_guard.py, app\routes\teams.py (protected)
REASON: Autogen changed teams.py which is in baseline.json
```

```
ASK: Which profile to use for FK circular reference?
CONTEXT: models_autogen_gate.ps1 -Profile <strict|fk>
REASON: teams ↔ seasons have circular FK dependency
```

---

### Step 3: EXECUTE (Proceed)

**ONLY proceed after:**
1. ✅ ACK confirmed by user/system
2. ✅ All ASK questions resolved
3. ✅ CWD validated (see Section 2.2)

**Validation before EXECUTE:**
```powershell
# Mandatory pre-flight check
git status --porcelain  # Must be empty or only intentional changes
Get-Location            # Must match expected CWD
```

---

## 2. Escopo Permitido

**Fonte:** `docs\_ai\_context\approved-commands.yml`

### 2.1 Comandos Whitelisted

Agent pode executar **SOMENTE** comandos listados em `approved-commands.yml`:

#### Categoria: Git Operations (Read-Only)
```powershell
git status --porcelain
git diff <file>
git log --oneline -n <N>
git show <commit>
```

#### Categoria: Model Validation
```powershell
.\scripts\models_autogen_gate.ps1 -Table "<TABLE>" -Profile strict
.\scripts\parity_scan.ps1 -Table "<TABLE>"
```

#### Categoria: Requirements
```powershell
python scripts\model_requirements.py --table <TABLE> --profile strict
```

#### Categoria: SSOT Refresh
```powershell
.\scripts\inv.ps1 refresh
```

#### Categoria: Guard & Baseline
```powershell
python scripts\agent_guard.py check baseline
python scripts\agent_guard.py snapshot baseline  # REQUIRES APPROVAL
```

---

### 2.2 Comandos Proibidos

Agent **NÃO** pode executar:

❌ **Destructive Git Operations:**
```powershell
git reset --hard
git clean -f
git push --force
```

❌ **Destructive File Operations:**
```powershell
Remove-Item -Recurse -Force <path>
```

❌ **Code Injection Risks:**
```powershell
Invoke-Expression <string>
iex <string>
```

❌ **Unauthorized Commands:**
- Any command NOT listed in `docs\_ai\_context\approved-commands.yml`

**Enforcement:**
- Run `python scripts\_ia\validators\validate-approved-commands.py` before executing
- Exit code 0 = all approved
- Exit code 1 = violations found (ABORT)

---

### 2.3 CWD (Current Working Directory) Requirements

**CRITICAL:** Different commands require different CWDs

| Command Type | Required CWD | Validation |
|-------------|-------------|------------|
| `scripts\_ia\**\*.py` | **Repo root** (`C:\HB TRACK`) | `Test-Path "scripts\_ia"` |
| `scripts\models_autogen_gate.ps1` | **Backend root** (`...\Hb Track - Backend`) | `$PWD -match "Hb Track - Backend"` |
| `scripts\inv.ps1` | **Repo root** | `Test-Path "scripts\inv.ps1"` |

**Pre-execution check (MANDATORY):**
```powershell
# For AI artifact scripts
if (-not (Test-Path "scripts\_ia")) {
    Write-Host "[ERROR] Wrong CWD. Expected: repo root" -ForegroundColor Red
    exit 1
}

# For backend scripts
$expectedPath = "Hb Track - Backend"
if ((Get-Location).Path -notmatch [regex]::Escape($expectedPath)) {
    Write-Host "[ERROR] Wrong CWD. Expected: *\$expectedPath" -ForegroundColor Red
    exit 1
}
```

---

## 3. Formato de Task (Structured Prompts)

**Fonte:** `docs\_ai\_specs\invocation-examples.yml`

### 3.1 Exemplo: Validar Model

**Task structure:**
```yaml
task: models_validation
command: python scripts\model_requirements.py --table <TABLE> --profile strict
context:
  - table: athletes
  - profile: strict
  - expected_exit: 0 (pass) or 4 (violations)
```

**Execution:**
```powershell
# 1. Validate CWD
Set-Location "C:\HB TRACK\Hb Track - Backend"

# 2. Execute
python scripts\model_requirements.py --table athletes --profile strict

# 3. Capture exit code IMMEDIATELY
$exitCode = $LASTEXITCODE

# 4. Handle result
if ($exitCode -eq 0) {
    Write-Host "✅ Model validation passed"
} elseif ($exitCode -eq 4) {
    Write-Host "❌ Requirements violations found (see output)"
    # Parse violations and suggest fixes
} else {
    Write-Host "💥 Unexpected exit code: $exitCode"
}
```

---

### 3.2 Exemplo: Gate Completo (Guard → Parity → Requirements)

**Task structure:**
```yaml
task: models_gate_full
command: .\scripts\models_autogen_gate.ps1 -Table <TABLE> -Profile strict
context:
  - table: athletes
  - profile: strict
  - allow_cycle_warning: false
  - expected_exits: [0, 2, 3, 4]
```

**Execution:**
```powershell
# 1. Pre-check: repo must be clean
$dirty = git status --porcelain
if ($dirty) {
    Write-Host "[ABORT] Repository has uncommitted changes" -ForegroundColor Red
    exit 3  # Guard violation
}

# 2. Execute gate
.\scripts\models_autogen_gate.ps1 -Table "athletes" -Profile strict
$exitCode = $LASTEXITCODE

# 3. Handle exit codes
switch ($exitCode) {
    0 { Write-Host "✅ Gate passed (model perfect)" }
    2 { Write-Host "❌ Parity fail (see parity_report.json)" }
    3 { Write-Host "❌ Guard fail (baseline violation)" }
    4 { Write-Host "❌ Requirements fail (see output)" }
    default { Write-Host "💥 Crash (exit=$exitCode)" }
}
```

---

### 3.3 Exemplo: Regenerar Artefatos AI

**Task structure:**
```yaml
task: regenerate_ai_artifacts
commands:
  - python scripts\_ia\extractors\extract-approved-commands.py
  - python scripts\_ia\extractors\extract-troubleshooting.py
  - python scripts\_ia\generators\generate-handshake-template.py
  - python scripts\_ia\generators\generate-invocation-examples.py
  - python scripts\_ia\generators\generate-checklist-yml.py
expected_exit: 0 (all)
```

**Execution:**
```powershell
# 1. Validate CWD (repo root required)
Set-Location "C:\HB TRACK"
if (-not (Test-Path "scripts\_ia")) {
    Write-Host "[ERROR] Wrong CWD" -ForegroundColor Red
    exit 1
}

# 2. Execute in order (fail-fast)
$scripts = @(
    "scripts\_ia\extractors\extract-approved-commands.py",
    "scripts\_ia\extractors\extract-troubleshooting.py",
    "scripts\_ia\generators\generate-handshake-template.py",
    "scripts\_ia\generators\generate-invocation-examples.py",
    "scripts\_ia\generators\generate-checklist-yml.py"
)

foreach ($script in $scripts) {
    Write-Host "`n=== Running: $script ===" -ForegroundColor Cyan
    python $script
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ABORT] Script failed with exit $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`n✅ All AI artifacts regenerated successfully" -ForegroundColor Green
```

---

## 4. Exit Code Contract

**Fonte:** `docs\_ai\_maps\troubleshooting-map.json`, `docs\references\exit_codes.md`

### 4.1 Exit Code Handling Matrix

| Code | Meaning | Agent Action | Example |
|------|---------|--------------|---------|
| **0** | Success | Proceed to next step | `✅ Gate passed` |
| **1** | Crash | Stop, report error, request human intervention | `💥 FileNotFoundError: schema.sql` |
| **2** | Parity fail | Parse `parity_report.json`, suggest migration | `❌ Column 'email' missing in DB` |
| **3** | Guard fail | Check baseline, ask if change is intentional | `❌ teams.py modified (protected)` |
| **4** | Requirements fail | Parse violations, suggest model fixes | `❌ expected=Integer got=String` |

---

### 4.2 Exit Code 0: Success

**Action:** Proceed to next step

**Example:**
```powershell
python scripts\model_requirements.py --table athletes --profile strict
# Exit: 0
# ✅ All requirements satisfied
```

---

### 4.3 Exit Code 1: Crash

**Symptoms:**
- Python traceback
- `FileNotFoundError`
- `ModuleNotFoundError`
- Unexpected exception

**Agent action:**
1. Stop execution immediately
2. Capture full error output
3. Report to user with diagnostics:
   ```
   [CRASH] Exit code 1
   Error: FileNotFoundError: docs\_generated\schema.sql
   
   Diagnostics:
   - CWD: <current path>
   - Command: <full command>
   - Suggestion: Run `.\scripts\inv.ps1 refresh` to regenerate SSOT
   ```

**Do NOT:**
- Attempt automatic recovery
- Continue to next step
- Modify files to "fix" the crash

---

### 4.4 Exit Code 2: Parity Fail

**Symptoms:**
- `[PARITY] Structural differences detected`
- Diff output showing column/constraint/index mismatches

**Agent action:**
1. Parse `docs\_generated\parity_report.json`
2. Identify specific differences:
   ```json
   {
     "table": "athletes",
     "differences": [
       {"type": "add_column", "column": "email", "status": "missing_in_db"},
       {"type": "modify_nullable", "column": "birth_date", "db": "NOT NULL", "model": "nullable"}
     ]
   }
   ```
3. Suggest remediation:
   ```
   [PARITY FAIL] athletes table has 2 differences:
   
   1. Column 'email' exists in model but not in DB
      → Suggestion: Run migration or add column manually
   
   2. birth_date nullable mismatch
      → DB: NOT NULL
      → Model: nullable=True
      → Suggestion: Align model with DB (set nullable=False)
   ```

**Consult:** `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md`

---

### 4.5 Exit Code 3: Guard Fail

**Symptoms:**
- `[GUARD] Baseline violation detected`
- Protected file was modified

**Agent action:**
1. Identify modified file
2. Ask user for clarification:
   ```
   ASK: File 'app\routes\teams.py' is protected but was modified. Is this intentional?
   CONTEXT: Baseline: .hb_guard\baseline.json, Modified: app\routes\teams.py
   REASON: Need to decide if baseline should be updated or change reverted
   ```
3. Based on response:
   - **If intentional:** Update baseline (requires approval)
     ```powershell
     python scripts\agent_guard.py snapshot baseline
     ```
   - **If accidental:** Revert change
     ```powershell
     git restore -- app\routes\teams.py
     ```

**Consult:** `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md`

---

### 4.6 Exit Code 4: Requirements Fail

**Symptoms:**
- `[REQUIREMENTS] Violations detected`
- Type mismatch
- Nullable mismatch
- Missing server_default
- FK constraint issues

**Agent action:**
1. Parse violations from output
2. Categorize by type:
   ```
   [REQUIREMENTS FAIL] athletes model has 3 violations:
   
   TYPE MISMATCH:
   - Column 'age': expected=Integer got=String
     → Fix: mapped_column(Integer, ...)
   
   NULLABLE MISMATCH:
   - Column 'email': expected=NOT NULL got=nullable=True
     → Fix: mapped_column(String, nullable=False, ...)
   
   SERVER_DEFAULT MISSING:
   - Column 'is_active': expected=default_literal:false
     → Fix: mapped_column(Boolean, server_default=text("false"), ...)
   ```
3. Generate suggested code fixes
4. **Do NOT** apply fixes automatically (suggest only)

**Consult:** `docs\references\model_requirements_guide.md`

---

## 5. Guardrails (Policy Enforcement)

**Fonte:** `docs\_ai\_guardrails\GUARDRAIL_POLICY_*.md`

### 5.1 Parity Guardrail

**Policy:** Model MUST match DB schema exactly

**Enforcement:**
- Run `scripts\parity_gate.ps1` before committing model changes
- Exit code 2 = parity violation (BLOCK commit)

**Agent behavior:**
- Always run parity check after model modifications
- Do NOT commit if parity fails without user approval

---

### 5.2 Baseline Guardrail

**Policy:** Protected files CANNOT be modified without approval

**Protected files:**
- `app\routes\teams.py`
- `app\routes\seasons.py`
- (See `.hb_guard\baseline.json` for full list)

**Enforcement:**
- Run `python scripts\agent_guard.py check baseline` before operations
- Exit code 3 = baseline violation (ASK user)

**Agent behavior:**
- NEVER update baseline without explicit user approval
- Always ASK when protected file is modified

---

### 5.3 Requirements Guardrail

**Policy:** Models MUST satisfy all structural requirements

**Requirements:**
- Correct SQLAlchemy types (Integer, String, Boolean, etc)
- Nullable consistency with DB schema
- FK constraints properly defined
- server_default when DB has defaults

**Enforcement:**
- Run `python scripts\model_requirements.py` after model changes
- Exit code 4 = requirements violation (FIX before commit)

**Agent behavior:**
- Suggest fixes, do NOT auto-apply
- Cite specific requirement violated
- Provide code example of correct implementation

---

## 6. Validation Workflow

**Fonte:** `docs\_ai\_specs\checklist-models.yml`

### Standard Validation Sequence

**For ANY model change, execute in this order:**

```yaml
STEP_0: Validate repo is clean
  command: git status --porcelain
  expected: empty or only intentional changes
  on_fail: ABORT

STEP_1: Guard check (baseline)
  command: python scripts\agent_guard.py check baseline
  expected: exit 0
  on_fail: ASK user if change is intentional

STEP_2: Parity pre-check
  command: .\scripts\parity_gate.ps1 -Table <TABLE>
  expected: exit 0
  on_fail: Fix parity issues before proceeding

STEP_3: Requirements check
  command: python scripts\model_requirements.py --table <TABLE> --profile strict
  expected: exit 0
  on_fail: Fix requirements violations

STEP_4: Full gate (if all above pass)
  command: .\scripts\models_autogen_gate.ps1 -Table <TABLE> -Profile strict
  expected: exit 0
  on_success: Model is compliant
```

**Fail-fast:** Stop at first failure, report to user

---

## 7. Recovery Paths

**Fonte:** `docs\_ai\_maps\troubleshooting-map.json`

### Recovery Matrix

| Exit Code | Automatic Recovery | Manual Recovery Required |
|-----------|-------------------|-------------------------|
| **0** | N/A (success) | N/A |
| **1** | ❌ No (crash) | ✅ User must fix environment/code |
| **2** | ⚠️ Suggest migration | ✅ User must apply migration |
| **3** | ❌ No (requires approval) | ✅ User must approve baseline update or revert |
| **4** | ⚠️ Suggest code fix | ✅ User must approve fix before applying |

**Agent recovery capabilities:**
- **Diagnostic:** Always (parse errors, suggest solutions)
- **Auto-fix:** NEVER (all changes require user approval)
- **Suggest fix:** Always (provide code examples, commands)

---

## 8. Quality Gates

**Fonte:** `docs\_ai\_specs\quality-gates.yml` (PENDENTE: validar se existe)

### Pre-defined Quality Metrics

**Complexity:**
- Max cyclomatic complexity: 10
- Enforcement: `python scripts\_ia\validators\validate-quality-gates.py`

**Type coverage:**
- 100% type hints in models
- Enforcement: Manual review (TODO: automated checker)

**Documentation:**
- Docstrings in all public functions
- Enforcement: Manual review (TODO: automated checker)

### Validation Before Commit

```powershell
# 1. Validate approved commands
python scripts\_ia\validators\validate-approved-commands.py
if ($LASTEXITCODE -ne 0) { exit 1 }

# 2. Validate quality gates (if file exists)
if (Test-Path "docs\_ai\_specs\quality-gates.yml") {
    python scripts\_ia\validators\validate-quality-gates.py "Hb Track - Backend\app"
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
```

---

## 9. Agent Constraints (DO/DON'T)

### ✅ DO

1. **Always ACK** before executing tasks
2. **Always validate CWD** before running commands
3. **Always capture `$LASTEXITCODE` immediately** (no pipeline before capture)
4. **Always stop on first failure** (fail-fast)
5. **Always cite documentation** when making decisions
6. **Always ASK** when uncertain (don't guess)
7. **Always suggest fixes** (never auto-apply without approval)

### ❌ DON'T

1. **NEVER execute commands** not in approved-commands.yml
2. **NEVER update baseline** without explicit user approval
3. **NEVER auto-commit** changes without user review
4. **NEVER guess** exit code meanings (consult troubleshooting-map.json)
5. **NEVER skip validation steps** (always follow checklist)
6. **NEVER modify protected files** without ASK
7. **NEVER use pipeline before `$LASTEXITCODE`** (use `2>&1 | Tee-Object` AFTER capture)

---

## 10. Artifact Consumption Guide

### 10.1 approved-commands.yml

**Purpose:** Whitelist of safe commands

**Usage:**
```powershell
# Load whitelist
$whitelist = Get-Content "docs\_ai\_context\approved-commands.yml" | ConvertFrom-Yaml

# Check if command is approved
if ($whitelist.categories -contains $commandCategory) {
    # Execute
} else {
    # BLOCK and ASK user
}
```

---

### 10.2 troubleshooting-map.json

**Purpose:** Exit code diagnostics

**Usage:**
```powershell
# Load troubleshooting map
$map = Get-Content "docs\_ai\_maps\troubleshooting-map.json" | ConvertFrom-Json

# Get diagnostics for exit code
$exitCode = 2
$diagnostic = $map.exit_codes.$exitCode
Write-Host "Description: $($diagnostic.description)"
Write-Host "Causes: $($diagnostic.causes -join ', ')"
Write-Host "Solutions: $($diagnostic.solutions -join ', ')"
```

---

### 10.3 invocation-examples.yml

**Purpose:** Task execution templates

**Usage:**
```yaml
# Example task template
task: models_validation
command: python scripts\model_requirements.py --table athletes --profile strict
exit_codes:
  '0': pass
  '4': requirements_violation

# Agent uses template to execute task consistently
```

---

### 10.4 checklist-models.yml

**Purpose:** Workflow steps for model validation

**Usage:**
```yaml
# Step-by-step execution
steps:
  - id: STEP_0
    name: Definir Schema (DDL)
    required: true
  - id: STEP_1
    name: Agent Guard (Baseline)
    required: true
  - id: STEP_2
    name: Parity Pre-Check
    required: true

# Agent follows checklist to ensure all steps are completed
```

---

## 11. Summary: Quick Reference

**Before ANY task:**
1. ACK documentation understanding
2. Validate CWD
3. Check repo is clean (`git status --porcelain`)

**During task execution:**
1. Use ONLY approved commands
2. Capture `$LASTEXITCODE` immediately
3. Stop on first error (fail-fast)
4. ASK when uncertain

**After task completion:**
1. Verify exit code (0 = success)
2. Review changes (`git diff`)
3. Run validators before suggesting commit

**In case of error:**
1. Parse exit code (0/1/2/3/4)
2. Consult troubleshooting-map.json
3. Suggest solution (never auto-fix)
4. ASK user if unclear

---

**Última atualização:** 2026-02-12  
**Autor:** GitHub Copilot Agent  
**Baseado em:** `.github/copilot-handshake.md`, `IMPLEMENTATION_SUMMARY.md`, artefatos AI em `docs/_ai/`

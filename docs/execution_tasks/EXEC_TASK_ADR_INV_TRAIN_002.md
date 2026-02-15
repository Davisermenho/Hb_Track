# TASK: Implementação do Sistema de Gates para Invariantes

**ID**: TASK-INV-GATE-001  
**Prioridade**: ALTA  
**Esforço Estimado**: 6-8 horas (Fase 1)  
**Assignee**: AI Agent (Claude Opus em VS Code)  
**Reviewer**: Davi  
**Baseado em**: ADR-INV-TRAIN-002  
**Data de Criação**: 2026-02-08

---

## 📋 CONTEXTO

Implementar o Sistema de Gates em 4 camadas para validação determinística de invariantes, conforme especificado na ADR-INV-TRAIN-002. Este sistema elevará a cobertura de validação de 90% para 96%, eliminando gaps críticos de rastreabilidade e qualidade.

**Decisão Arquitetural**: [ADR-INV-TRAIN-002.md](./ADR-INV-TRAIN-002.md)

---

## 🎯 OBJETIVO DA FASE 1 (Quick Wins)

Implementar **Gate 2 (Anchor Validation)** e o **Orquestrador Master**, permitindo validação automática de que anchors em `INVARIANTS_TRAINING.md` apontam para entidades reais no `schema.sql`.

**Entregáveis**:
1. ✅ `scripts/validate_invariant_anchors.py` (Gate 2 completo)
2. ✅ `scripts/invariants_full_gate.ps1` (Orquestrador básico)
3. ✅ Smoke test em INV-TRAIN-033 (wellness_pre_sleep_hours)
4. ✅ Documentação de troubleshooting

---

## 📐 ARQUITETURA DE REFERÊNCIA

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: INVARIANTS_TRAINING.md                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ ## INV-TRAIN-033                                    │    │
│  │ **Regra**: sleep_hours must be between 0 and 24   │    │
│  │                                                     │    │
│  │ ### SPEC                                           │    │
│  │ ```yaml                                            │    │
│  │ class: A                                           │    │
│  │ unit:                                              │    │
│  │   required: true                                   │    │
│  │   test_node: TestInvTrain033WellnessPreSleepHours │    │
│  │   anchors:                                         │    │
│  │     db.table: wellness_pre                         │    │
│  │     db.constraint: ck_wellness_pre_sleep_hours    │    │
│  │ ```                                                │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  GATE 2: validate_invariant_anchors.py                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Parse SPEC block (YAML in markdown)             │    │
│  │ 2. Extract anchors: {db.table, db.constraint}      │    │
│  │ 3. Load schema.sql                                 │    │
│  │ 4. Validate:                                       │    │
│  │    - V1: table exists                              │    │
│  │    - V2: constraint exists in table                │    │
│  │    - V3: constraint type matches class             │    │
│  │ 5. Report violations (VS Code format)              │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: Exit code + violations report                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ [OK] All anchors valid for INV-TRAIN-033           │    │
│  │   ✓ db.table 'wellness_pre' exists                │    │
│  │   ✓ db.constraint 'ck_wellness_pre_sleep_hours'   │    │
│  │   ✓ constraint type 'CHECK' matches class 'A'     │    │
│  │                                                     │    │
│  │ Exit code: 0                                       │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ ESPECIFICAÇÃO TÉCNICA

### DELIVERABLE 1: `scripts/validate_invariant_anchors.py`

#### **Estrutura do Arquivo**

```python
#!/usr/bin/env python3
"""
Invariant Anchors Validator - GATE 2

Validates that anchors in INVARIANTS_TRAINING.md point to real entities
in schema.sql, openapi.json, and codebase.

USAGE:
    python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033
    python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033 --level strict
    python scripts/validate_invariant_anchors.py --all --level standard

EXIT CODES:
    0: PASS (all anchors valid)
    1: EXECUTION ERROR (file not found, parse failed)
    2: FAIL (ERROR violations found)

OUTPUT FORMAT (VS Code problemMatcher compatible):
    path:line:col: LEVEL [CODE]: message — action
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Violation:
    """Validation violation."""
    inv_id: str
    file: str
    line: int
    col: int
    level: str  # ERROR | WARNING | INFO
    code: str
    message: str
    action: str

@dataclass
class Anchors:
    """Parsed anchors from SPEC block."""
    db: Dict[str, str] = field(default_factory=dict)
    api: Dict[str, str] = field(default_factory=dict)
    code: Dict[str, str] = field(default_factory=dict)

@dataclass
class Invariant:
    """Parsed invariant from INVARIANTS_TRAINING.md."""
    id: str
    title: str
    class_type: str  # A, B, C1, C2, D, E1, F
    anchors: Anchors
    line_number: int

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_invariants_md(md_path: Path) -> List[Invariant]:
    """
    Parse INVARIANTS_TRAINING.md and extract all invariants with SPEC blocks.
    
    Returns list of Invariant objects with parsed anchors.
    """
    # TODO: Implement markdown parsing
    # - Scan for ## INV-TRAIN-XXX headers
    # - Extract SPEC YAML blocks
    # - Parse anchors (db.*, api.*, code.*)
    # - Track line numbers for violation reporting
    pass

def extract_table_from_schema(schema_text: str, table_name: str) -> Optional[str]:
    """
    Extract CREATE TABLE block for given table name.
    
    Returns the full CREATE TABLE ... ; block or None if not found.
    """
    # TODO: Implement
    # - Regex: CREATE TABLE public.{table_name} \(
    # - Extract until matching );
    pass

def detect_constraint_type(schema_text: str, constraint_name: str) -> Optional[str]:
    """
    Detect constraint type from schema.sql.
    
    Returns: "CHECK" | "UNIQUE" | "FOREIGN KEY" | "NOT NULL" | None
    """
    # TODO: Implement
    # - Search for CONSTRAINT {constraint_name}
    # - Parse following token (CHECK | UNIQUE | FOREIGN KEY)
    pass

# ============================================================================
# VALIDATION FUNCTIONS (Core Logic)
# ============================================================================

def validate_db_table_exists(
    inv: Invariant,
    schema_text: str
) -> List[Violation]:
    """
    V1: Validate that db.table anchor points to existing table.
    
    Violation Code: ANCHOR_TABLE_NOT_FOUND
    """
    violations = []
    
    table_name = inv.anchors.db.get('table')
    if not table_name:
        return violations  # No validation needed if anchor not present
    
    # Check: CREATE TABLE public.{table_name}
    if f"CREATE TABLE public.{table_name}" not in schema_text:
        violations.append(Violation(
            inv_id=inv.id,
            file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
            line=inv.line_number,
            col=5,
            level='ERROR',
            code='ANCHOR_TABLE_NOT_FOUND',
            message=f"Anchor db.table='{table_name}' not found in schema.sql",
            action=f"Verify table name or check docs/_generated/schema.sql"
        ))
    
    return violations

def validate_db_constraint_exists(
    inv: Invariant,
    schema_text: str
) -> List[Violation]:
    """
    V2: Validate that db.constraint anchor points to existing constraint
    in the correct table.
    
    Violation Codes: 
    - ANCHOR_CONSTRAINT_NOT_FOUND
    - CONSTRAINT_TABLE_MISMATCH
    """
    violations = []
    
    constraint_name = inv.anchors.db.get('constraint')
    table_name = inv.anchors.db.get('table')
    
    if not constraint_name:
        return violations
    
    # Check 1: Constraint exists anywhere in schema
    constraint_pattern = rf"CONSTRAINT\s+{re.escape(constraint_name)}\s+(CHECK|UNIQUE|FOREIGN KEY)"
    if not re.search(constraint_pattern, schema_text, re.IGNORECASE):
        violations.append(Violation(
            inv_id=inv.id,
            file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
            line=inv.line_number,
            col=5,
            level='ERROR',
            code='ANCHOR_CONSTRAINT_NOT_FOUND',
            message=f"Anchor db.constraint='{constraint_name}' not found in schema.sql",
            action=f"Verify constraint name or check schema.sql"
        ))
        return violations
    
    # Check 2: Constraint belongs to declared table
    if table_name:
        table_block = extract_table_from_schema(schema_text, table_name)
        if table_block:
            # Check if constraint is in CREATE TABLE block
            in_create_table = constraint_name in table_block
            
            # Check if constraint is in ALTER TABLE
            alter_pattern = rf"ALTER TABLE ONLY public\.{re.escape(table_name)}\s+ADD CONSTRAINT\s+{re.escape(constraint_name)}"
            in_alter_table = re.search(alter_pattern, schema_text, re.IGNORECASE)
            
            if not (in_create_table or in_alter_table):
                violations.append(Violation(
                    inv_id=inv.id,
                    file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
                    line=inv.line_number,
                    col=5,
                    level='ERROR',
                    code='CONSTRAINT_TABLE_MISMATCH',
                    message=f"Constraint '{constraint_name}' exists but not in table '{table_name}'",
                    action=f"Verify table name or constraint belongs to different table"
                ))
    
    return violations

def validate_constraint_type_matches_class(
    inv: Invariant,
    schema_text: str,
    level: str
) -> List[Violation]:
    """
    V3: Validate that constraint type matches invariant class.
    
    Class A expects: CHECK | UNIQUE | FOREIGN KEY
    Class B expects: N/A (trigger-based)
    
    Violation Code: ANCHOR_CONSTRAINT_TYPE_MISMATCH
    
    Only enforced in levels: standard, strict
    """
    violations = []
    
    if level not in ['standard', 'strict']:
        return violations
    
    constraint_name = inv.anchors.db.get('constraint')
    if not constraint_name:
        return violations
    
    constraint_type = detect_constraint_type(schema_text, constraint_name)
    if not constraint_type:
        return violations  # Already caught by V2
    
    # Class A should have DB constraints (CHECK, UNIQUE, FK)
    if inv.class_type == 'A':
        if constraint_type not in ['CHECK', 'UNIQUE', 'FOREIGN KEY']:
            violations.append(Violation(
                inv_id=inv.id,
                file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
                line=inv.line_number,
                col=5,
                level='ERROR',
                code='ANCHOR_CONSTRAINT_TYPE_MISMATCH',
                message=f"Class A expects CHECK/UNIQUE/FK but constraint '{constraint_name}' is '{constraint_type}'",
                action=f"Change class to B (trigger) or verify constraint type"
            ))
    
    return violations

def validate_db_trigger_exists(
    inv: Invariant,
    schema_text: str
) -> List[Violation]:
    """
    V4: Validate that db.trigger anchor points to existing trigger
    and binds to correct table.
    
    Violation Codes:
    - ANCHOR_TRIGGER_NOT_FOUND
    - TRIGGER_TABLE_MISMATCH
    """
    violations = []
    
    trigger_name = inv.anchors.db.get('trigger')
    table_name = inv.anchors.db.get('table')
    
    if not trigger_name:
        return violations
    
    # Check 1: Trigger exists
    trigger_pattern = rf"CREATE\s+TRIGGER\s+{re.escape(trigger_name)}"
    if not re.search(trigger_pattern, schema_text, re.IGNORECASE):
        violations.append(Violation(
            inv_id=inv.id,
            file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
            line=inv.line_number,
            col=5,
            level='ERROR',
            code='ANCHOR_TRIGGER_NOT_FOUND',
            message=f"Anchor db.trigger='{trigger_name}' not found in schema.sql",
            action=f"Verify trigger name or check schema.sql"
        ))
        return violations
    
    # Check 2: Trigger binds to correct table
    if table_name:
        binding_pattern = rf"CREATE\s+TRIGGER\s+{re.escape(trigger_name)}\s+.*?\s+ON\s+public\.{re.escape(table_name)}"
        if not re.search(binding_pattern, schema_text, re.IGNORECASE | re.DOTALL):
            violations.append(Violation(
                inv_id=inv.id,
                file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
                line=inv.line_number,
                col=5,
                level='ERROR',
                code='TRIGGER_TABLE_MISMATCH',
                message=f"Trigger '{trigger_name}' exists but not bound to table '{table_name}'",
                action=f"Verify table name or trigger binds to different table"
            ))
    
    return violations

def validate_db_function_exists(
    inv: Invariant,
    schema_text: str
) -> List[Violation]:
    """
    V5: Validate that db.function anchor points to existing function.
    
    Violation Code: ANCHOR_FUNCTION_NOT_FOUND
    """
    violations = []
    
    function_name = inv.anchors.db.get('function')
    if not function_name:
        return violations
    
    # Check: CREATE FUNCTION {function_name}
    function_pattern = rf"CREATE\s+FUNCTION\s+(public\.)?{re.escape(function_name)}"
    if not re.search(function_pattern, schema_text, re.IGNORECASE):
        violations.append(Violation(
            inv_id=inv.id,
            file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
            line=inv.line_number,
            col=5,
            level='ERROR',
            code='ANCHOR_FUNCTION_NOT_FOUND',
            message=f"Anchor db.function='{function_name}' not found in schema.sql",
            action=f"Verify function name or check schema.sql"
        ))
    
    return violations

def validate_api_operation_exists(
    inv: Invariant,
    openapi_spec: dict
) -> List[Violation]:
    """
    V6: Validate that api.operation anchor points to existing operationId.
    
    Violation Code: ANCHOR_OPERATION_NOT_FOUND
    """
    violations = []
    
    operation_id = inv.anchors.api.get('operation')
    if not operation_id:
        return violations
    
    # Extract all operationIds from openapi.json
    all_operation_ids = set()
    paths = openapi_spec.get('paths', {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict) and 'operationId' in details:
                all_operation_ids.add(details['operationId'])
    
    if operation_id not in all_operation_ids:
        violations.append(Violation(
            inv_id=inv.id,
            file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
            line=inv.line_number,
            col=5,
            level='ERROR',
            code='ANCHOR_OPERATION_NOT_FOUND',
            message=f"Anchor api.operation='{operation_id}' not found in openapi.json",
            action=f"Verify operationId or check docs/_generated/openapi.json"
        ))
    
    return violations

# ============================================================================
# MAIN LOGIC
# ============================================================================

def validate_invariant(
    inv: Invariant,
    schema_text: str,
    openapi_spec: dict,
    level: str
) -> List[Violation]:
    """
    Run all validations for a single invariant.
    
    Returns list of violations (empty if all pass).
    """
    violations = []
    
    # DB validations
    violations.extend(validate_db_table_exists(inv, schema_text))
    violations.extend(validate_db_constraint_exists(inv, schema_text))
    violations.extend(validate_constraint_type_matches_class(inv, schema_text, level))
    violations.extend(validate_db_trigger_exists(inv, schema_text))
    violations.extend(validate_db_function_exists(inv, schema_text))
    
    # API validations
    violations.extend(validate_api_operation_exists(inv, openapi_spec))
    
    return violations

def print_violations(violations: List[Violation], verbose: bool = False) -> None:
    """
    Print violations in VS Code problemMatcher format.
    
    Format: path:line:col: LEVEL [CODE]: message — action
    """
    if not violations:
        return
    
    print("[FAIL] Anchor validation violations:")
    for v in violations:
        # VS Code format
        print(f"{v.file}:{v.line}:{v.col}: {v.level} [{v.code}]: {v.message} — {v.action}")
        
        if verbose:
            print(f"       Invariant: {v.inv_id}")

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point.
    
    Returns:
        0: PASS
        1: EXECUTION ERROR
        2: FAIL (violations found)
    """
    ap = argparse.ArgumentParser(
        prog='validate_invariant_anchors',
        description='Validate anchors in INVARIANTS_TRAINING.md (GATE 2)'
    )
    ap.add_argument('--inv-id', type=str, help='Specific invariant ID to validate (ex: INV-TRAIN-033)')
    ap.add_argument('--all', action='store_true', help='Validate all invariants')
    ap.add_argument('--invariants-md', type=str, default='docs/02-modulos/training/INVARIANTS_TRAINING.md')
    ap.add_argument('--schema', type=str, default='docs/_generated/schema.sql')
    ap.add_argument('--openapi', type=str, default='docs/_generated/openapi.json')
    ap.add_argument('--level', choices=['basic', 'standard', 'strict'], default='standard')
    ap.add_argument('--verbose', action='store_true')
    
    args = ap.parse_args(argv)
    
    # Validate inputs
    invariants_path = Path(args.invariants_md)
    schema_path = Path(args.schema)
    openapi_path = Path(args.openapi)
    
    if not invariants_path.exists():
        print(f"[ERROR] INVARIANTS_TRAINING.md not found: {invariants_path}")
        return 1
    
    if not schema_path.exists():
        print(f"[ERROR] schema.sql not found: {schema_path}")
        return 1
    
    if not openapi_path.exists():
        print(f"[WARN] openapi.json not found: {openapi_path} (API validations skipped)")
        openapi_spec = {}
    else:
        openapi_spec = json.loads(openapi_path.read_text(encoding='utf-8'))
    
    try:
        # Parse inputs
        schema_text = schema_path.read_text(encoding='utf-8')
        invariants = parse_invariants_md(invariants_path)
        
        # Filter to target invariant(s)
        if args.inv_id:
            invariants = [inv for inv in invariants if inv.id == args.inv_id]
            if not invariants:
                print(f"[ERROR] Invariant {args.inv_id} not found in {invariants_path}")
                return 1
        elif not args.all:
            print("[ERROR] Must specify --inv-id or --all")
            return 1
        
        if args.verbose:
            print(f"[INFO] Validating {len(invariants)} invariant(s)")
            print(f"[INFO] Level: {args.level}")
        
        # Run validations
        all_violations = []
        for inv in invariants:
            if args.verbose:
                print(f"[INFO] Validating {inv.id}...")
            
            violations = validate_invariant(inv, schema_text, openapi_spec, args.level)
            all_violations.extend(violations)
            
            if args.verbose and not violations:
                print(f"  ✓ {inv.id}: All anchors valid")
        
        # Report results
        if all_violations:
            print_violations(all_violations, args.verbose)
            return 2
        
        print(f"[OK] All anchors valid ({len(invariants)} invariant(s) checked)")
        return 0
    
    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

#### **Checklist de Implementação**

- [ ] Criar arquivo `scripts/validate_invariant_anchors.py`
- [ ] Implementar `parse_invariants_md()` (parsing de markdown + YAML)
- [ ] Implementar `extract_table_from_schema()` (regex CREATE TABLE)
- [ ] Implementar `detect_constraint_type()` (parse CONSTRAINT token)
- [ ] Implementar V1: `validate_db_table_exists()`
- [ ] Implementar V2: `validate_db_constraint_exists()`
- [ ] Implementar V3: `validate_constraint_type_matches_class()`
- [ ] Implementar V4: `validate_db_trigger_exists()`
- [ ] Implementar V5: `validate_db_function_exists()`
- [ ] Implementar V6: `validate_api_operation_exists()`
- [ ] Implementar `main()` com argparse
- [ ] Implementar output em formato VS Code problemMatcher

---

### DELIVERABLE 2: `scripts/invariants_full_gate.ps1`

#### **Estrutura do Arquivo**

```powershell
<#
.SYNOPSIS
    Executa validação completa de invariante em 4 gates progressivos.

.DESCRIPTION
    Orquestra a execução de:
    - GATE 1: Model Structure (schema.sql → models)
    - GATE 2: Anchor Validation (INVARIANTS.md → schema.sql)
    - GATE 3: Test Quality (tests → CANON)
    - GATE 4: Runtime Execution (pytest → DB)

.PARAMETER InvId
    ID da invariante a validar (ex: INV-TRAIN-033)

.PARAMETER Profile
    Profile do model validation (fk | strict). Default: strict

.PARAMETER TestLevel
    Level do test validation (basic | standard | strict). Default: standard

.PARAMETER SkipGate
    Gates a pular (1,2,3,4). Ex: -SkipGate 1,4

.PARAMETER Verbose
    Habilita output detalhado

.EXAMPLE
    .\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033"
    # Executa todos os 4 gates com profiles padrão

.EXAMPLE
    .\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033" -Profile "strict" -TestLevel "strict"
    # Validação máxima (CI/CD)

.EXAMPLE
    .\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033" -SkipGate 1,4
    # Pula Gate 1 (model) e Gate 4 (runtime)

.NOTES
    Exit codes:
    - 0: Todos os gates passaram
    - 1: Gate 1 falhou (model structure)
    - 2: Gate 2 falhou (anchors)
    - 3: Gate 3 falhou (test quality)
    - 4: Gate 4 falhou (runtime)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$InvId,
    
    [ValidateSet("fk","strict")]
    [string]$Profile = "strict",
    
    [ValidateSet("basic","standard","strict")]
    [string]$TestLevel = "standard",
    
    [int[]]$SkipGate = @(),
    
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# ============================================================================
# SETUP
# ============================================================================

# Detect Python
if (Test-Path ".\venv\Scripts\python.exe") { 
    $py = ".\venv\Scripts\python.exe" 
} else { 
    $py = "python" 
}

# Detect pytest
if (Test-Path ".\venv\Scripts\pytest.exe") { 
    $pytest = ".\venv\Scripts\pytest.exe" 
} else { 
    $pytest = "pytest" 
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INVARIANTS FULL GATE: $InvId" -ForegroundColor Cyan
Write-Host "Profile: $Profile | TestLevel: $TestLevel" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ============================================================================
# GATE 1: Model Structure Validation
# ============================================================================

if (1 -notin $SkipGate) {
    Write-Host "`n[GATE 1/4] Validating model structure..." -ForegroundColor Yellow
    
    # Detect table from SPEC block in INVARIANTS_TRAINING.md
    $detectTableScript = @"
import re
from pathlib import Path

md_path = Path('docs/02-modulos/training/INVARIANTS_TRAINING.md')
if not md_path.exists():
    print('')
    exit(0)

md_text = md_path.read_text(encoding='utf-8')

# Find INV section
inv_pattern = r'## $InvId(.*?)(?=## INV-|$)'
inv_match = re.search(inv_pattern, md_text, re.DOTALL)
if not inv_match:
    print('')
    exit(0)

inv_section = inv_match.group(1)

# Extract SPEC block
spec_pattern = r'### SPEC.*?```yaml(.*?)```'
spec_match = re.search(spec_pattern, inv_section, re.DOTALL)
if not spec_match:
    print('')
    exit(0)

spec_yaml = spec_match.group(1)

# Extract db.table
table_pattern = r'db\.table:\s*(\w+)'
table_match = re.search(table_pattern, spec_yaml)
if table_match:
    print(table_match.group(1))
else:
    print('')
"@
    
    $table = & $py -c $detectTableScript
    
    if (-not $table) {
        Write-Host "[WARN] Could not detect table from SPEC, skipping Gate 1" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Detected table: $table" -ForegroundColor Gray
        
        $gate1Args = @("scripts\model_requirements.py", "--table", $table, "--profile", $Profile)
        if ($Verbose) { $gate1Args += "--verbose" }
        
        & $py $gate1Args
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] Gate 1 failed (model structure)" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "[OK] Gate 1 passed" -ForegroundColor Green
    }
} else {
    Write-Host "`n[GATE 1/4] SKIPPED" -ForegroundColor Gray
}

# ============================================================================
# GATE 2: Anchor Validation
# ============================================================================

if (2 -notin $SkipGate) {
    Write-Host "`n[GATE 2/4] Validating anchors..." -ForegroundColor Yellow
    
    $gate2Args = @(
        "scripts\validate_invariant_anchors.py",
        "--inv-id", $InvId,
        "--level", $TestLevel
    )
    if ($Verbose) { $gate2Args += "--verbose" }
    
    & $py $gate2Args
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Gate 2 failed (anchors)" -ForegroundColor Red
        exit 2
    }
    
    Write-Host "[OK] Gate 2 passed" -ForegroundColor Green
} else {
    Write-Host "`n[GATE 2/4] SKIPPED" -ForegroundColor Gray
}

# ============================================================================
# GATE 3: Test Quality Validation
# ============================================================================

if (3 -notin $SkipGate) {
    Write-Host "`n[GATE 3/4] Validating test quality..." -ForegroundColor Yellow
    
    $gate3Args = @(
        "scripts\verify_invariants_tests.py",
        "--inv", $InvId,
        "--level", $TestLevel
    )
    if ($Verbose) { $gate3Args += "--verbose" }
    
    & $py $gate3Args
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Gate 3 failed (test quality)" -ForegroundColor Red
        exit 3
    }
    
    Write-Host "[OK] Gate 3 passed" -ForegroundColor Green
} else {
    Write-Host "`n[GATE 3/4] SKIPPED" -ForegroundColor Gray
}

# ============================================================================
# GATE 4: Runtime Execution
# ============================================================================

if (4 -notin $SkipGate) {
    Write-Host "`n[GATE 4/4] Running tests..." -ForegroundColor Yellow
    
    # Convert INV-TRAIN-033 → test_inv_train_033
    $testPattern = $InvId.ToLower().Replace("-", "_")
    
    $gate4Args = @(
        "tests\invariants",
        "-k", $testPattern,
        "-v",
        "--tb=short",
        "--strict-markers"
    )
    if ($Verbose) { $gate4Args += "-vv" }
    
    & $pytest $gate4Args
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Gate 4 failed (runtime)" -ForegroundColor Red
        exit 4
    }
    
    Write-Host "[OK] Gate 4 passed" -ForegroundColor Green
} else {
    Write-Host "`n[GATE 4/4] SKIPPED" -ForegroundColor Gray
}

# ============================================================================
# SUCCESS
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "ALL GATES PASSED: $InvId" -ForegroundColor Green
Write-Host "  ✓ Gate 1: Model structure correct" -ForegroundColor Green
Write-Host "  ✓ Gate 2: Anchors valid" -ForegroundColor Green
Write-Host "  ✓ Gate 3: Test quality approved" -ForegroundColor Green
Write-Host "  ✓ Gate 4: Tests passing on DB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

exit 0
```

#### **Checklist de Implementação**

- [ ] Criar arquivo `scripts/invariants_full_gate.ps1`
- [ ] Implementar detecção automática de tabela via SPEC
- [ ] Implementar chamada para Gate 1 (model_requirements.py)
- [ ] Implementar chamada para Gate 2 (validate_invariant_anchors.py)
- [ ] Implementar chamada para Gate 3 (verify_invariants_tests.py)
- [ ] Implementar chamada para Gate 4 (pytest)
- [ ] Implementar tratamento de exit codes (fail-fast)
- [ ] Implementar --SkipGate para debugging
- [ ] Implementar --Verbose para output detalhado

---

### DELIVERABLE 3: Smoke Test em INV-TRAIN-033

#### **Comandos de Teste**

```powershell
# Test 1: Validar apenas Gate 2 (anchor validation)
.\scripts\validate_invariant_anchors.py --inv-id INV-TRAIN-033 --verbose

# Expected output:
# [INFO] Validating INV-TRAIN-033...
# [INFO] Anchors: db.table=wellness_pre, db.constraint=ck_wellness_pre_sleep_hours
#   ✓ db.table 'wellness_pre' exists in schema.sql
#   ✓ db.constraint 'ck_wellness_pre_sleep_hours' exists in table 'wellness_pre'
#   ✓ constraint type 'CHECK' matches class 'A'
# [OK] All anchors valid (1 invariant checked)

# Test 2: Validar todos os 4 gates juntos
.\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033" -Verbose

# Expected output:
# ========================================
# INVARIANTS FULL GATE: INV-TRAIN-033
# Profile: strict | TestLevel: standard
# ========================================
# 
# [GATE 1/4] Validating model structure...
# [INFO] Detected table: wellness_pre
# [OK] model satisfies DB requirements (per schema.sql)
# [OK] Gate 1 passed
# 
# [GATE 2/4] Validating anchors...
# [OK] All anchors valid
# [OK] Gate 2 passed
# 
# [GATE 3/4] Validating test quality...
# [OK] test_inv_train_033 satisfies CANON (0 violations)
# [OK] Gate 3 passed
# 
# [GATE 4/4] Running tests...
# ============================== 3 passed in 2.34s ===============================
# [OK] Gate 4 passed
# 
# ========================================
# ALL GATES PASSED: INV-TRAIN-033
#   ✓ Gate 1: Model structure correct
#   ✓ Gate 2: Anchors valid
#   ✓ Gate 3: Test quality approved
#   ✓ Gate 4: Tests passing on DB
# ========================================

# Test 3: Teste negativo (invariante inexistente)
.\scripts\validate_invariant_anchors.py --inv-id INV-TRAIN-999 --verbose

# Expected output:
# [ERROR] Invariant INV-TRAIN-999 not found in docs/02-modulos/training/INVARIANTS_TRAINING.md

# Test 4: Teste negativo (anchor inválido)
# Primeiro, edite temporariamente INVARIANTS_TRAINING.md:
# Altere db.constraint: ck_wellness_pre_sleep_hours
# Para:   db.constraint: ck_wellness_INVALID_NAME

.\scripts\validate_invariant_anchors.py --inv-id INV-TRAIN-033 --verbose

# Expected output:
# docs/02-modulos/training/INVARIANTS_TRAINING.md:XXX:5: ERROR [ANCHOR_CONSTRAINT_NOT_FOUND]: Anchor db.constraint='ck_wellness_INVALID_NAME' not found in schema.sql — verify constraint name or check docs/_generated/schema.sql
# [FAIL] Anchor validation violations:

# Reverter alteração temporária
```

#### **Checklist de Testes**

- [ ] Teste 1: Gate 2 standalone (INV-TRAIN-033) → PASS
- [ ] Teste 2: Full gate (4 gates) → PASS
- [ ] Teste 3: Invariante inexistente → ERROR exit 1
- [ ] Teste 4: Anchor inválido → FAIL exit 2
- [ ] Teste 5: --SkipGate 1,4 (pular model e runtime) → PASS apenas 2,3
- [ ] Teste 6: --Verbose (output detalhado) → verbosity adequada

---

### DELIVERABLE 4: Documentação de Troubleshooting

#### **Arquivo**: `docs/troubleshooting/INVARIANTS_GATE_FAQ.md`

```markdown
# Invariants Gate System - FAQ e Troubleshooting

## Erros Comuns e Soluções

### ERROR: ANCHOR_TABLE_NOT_FOUND

**Mensagem**:
```
docs/02-modulos/training/INVARIANTS_TRAINING.md:123:5: ERROR [ANCHOR_TABLE_NOT_FOUND]: Anchor db.table='wellness_pre' not found in schema.sql — verify table name or check docs/_generated/schema.sql
```

**Causa**: Tabela referenciada no anchor não existe no schema.sql.

**Soluções**:
1. Verificar typo no nome da tabela em INVARIANTS_TRAINING.md
2. Verificar se migration foi aplicada: `alembic upgrade head`
3. Regenerar schema.sql: `.\scripts\dump_schema.ps1`
4. Se tabela realmente não existe, remover ou corrigir anchor

---

### ERROR: ANCHOR_CONSTRAINT_NOT_FOUND

**Mensagem**:
```
ERROR [ANCHOR_CONSTRAINT_NOT_FOUND]: Anchor db.constraint='ck_wellness_pre_sleep_hours' not found in schema.sql
```

**Causa**: Constraint referenciado não existe no schema.sql.

**Soluções**:
1. Verificar typo no nome do constraint
2. Verificar se constraint está na tabela correta
3. Regenerar schema.sql: `.\scripts\dump_schema.ps1`
4. Se constraint foi removido, atualizar INVARIANTS_TRAINING.md

**Verificação manual**:
```sql
-- No schema.sql, procurar por:
CONSTRAINT ck_wellness_pre_sleep_hours CHECK (...)
```

---

### ERROR: CONSTRAINT_TABLE_MISMATCH

**Mensagem**:
```
ERROR [CONSTRAINT_TABLE_MISMATCH]: Constraint 'ck_wellness_pre_sleep_hours' exists but not in table 'wellness_pre'
```

**Causa**: Constraint existe mas pertence a outra tabela.

**Soluções**:
1. Corrigir `db.table` para a tabela correta
2. Ou corrigir `db.constraint` se o nome está errado

---

### ERROR: ANCHOR_CONSTRAINT_TYPE_MISMATCH

**Mensagem**:
```
ERROR [ANCHOR_CONSTRAINT_TYPE_MISMATCH]: Class A expects CHECK/UNIQUE/FK but constraint 'tr_update_wellness_post_response' is 'TRIGGER'
```

**Causa**: Constraint type não bate com a classe da invariante.

**Soluções**:
1. Se é um trigger: mudar classe para B
2. Se é CHECK/UNIQUE: classe A está correta, verificar nome do constraint
3. Verificar se anchor aponta para o elemento correto (constraint vs trigger)

---

## Workflow de Debugging

### Passo 1: Rodar Gate 2 standalone
```powershell
python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033 --verbose
```

Se falhar, corrigir anchors antes de prosseguir.

### Passo 2: Verificar schema.sql manualmente
```powershell
# Procurar pela tabela
Select-String -Path docs/_generated/schema.sql -Pattern "CREATE TABLE public.wellness_pre"

# Procurar pelo constraint
Select-String -Path docs/_generated/schema.sql -Pattern "ck_wellness_pre_sleep_hours"
```

### Passo 3: Verificar SPEC block syntax
```yaml
# CORRETO:
anchors:
  db.table: wellness_pre
  db.constraint: ck_wellness_pre_sleep_hours

# ERRADO (sintaxe inválida):
anchors:
  db.table wellness_pre  # faltou ":"
  db.constraint: "ck_wellness_pre_sleep_hours"  # quotes desnecessárias
```

### Passo 4: Rodar full gate com --SkipGate
```powershell
# Pular Gate 1 e 4 (focar em anchors e test quality)
.\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033" -SkipGate 1,4 -Verbose
```

## Referências

- ADR-INV-TRAIN-002: Especificação completa do sistema de gates
- INVARIANTS_TESTING_CANON.md: Protocolo canônico (DoD-0 a DoD-9)
```

#### **Checklist de Documentação**

- [ ] Criar `docs/troubleshooting/INVARIANTS_GATE_FAQ.md`
- [ ] Documentar todos os códigos de violação (V1-V6)
- [ ] Incluir exemplos de mensagens de erro reais
- [ ] Incluir workflow de debugging passo-a-passo
- [ ] Incluir verificações manuais (regex, SQL)

---

## 🎯 CRITÉRIOS DE ACEITAÇÃO

### Funcional

- [ ] **F1**: `validate_invariant_anchors.py --inv-id INV-TRAIN-033` retorna exit 0
- [ ] **F2**: `validate_invariant_anchors.py --inv-id INVALID` retorna exit 1 (not found)
- [ ] **F3**: Anchor inválido retorna exit 2 com violation em formato VS Code
- [ ] **F4**: `invariants_full_gate.ps1 -InvId INV-TRAIN-033` executa 4 gates em ordem
- [ ] **F5**: Gate 2 detecta tabela inexistente (ANCHOR_TABLE_NOT_FOUND)
- [ ] **F6**: Gate 2 detecta constraint inexistente (ANCHOR_CONSTRAINT_NOT_FOUND)
- [ ] **F7**: Gate 2 detecta constraint type mismatch (class A com trigger)
- [ ] **F8**: `--SkipGate 1,4` pula apenas gates especificados
- [ ] **F9**: `--Verbose` aumenta verbosity adequadamente

### Performance

- [ ] **P1**: Gate 2 executa em <5s para 1 invariante
- [ ] **P2**: Gate 2 executa em <30s para --all (46 invariantes)
- [ ] **P3**: Full gate executa em <40s para 1 invariante (incluindo pytest)

### Qualidade de Código

- [ ] **Q1**: Type hints completos (Python 3.10+)
- [ ] **Q2**: Docstrings em todas as funções públicas
- [ ] **Q3**: Error handling robusto (try/except com mensagens claras)
- [ ] **Q4**: Regex testado contra casos edge (nomes com underscores, parênteses)
- [ ] **Q5**: Output colorido no PowerShell (Green/Yellow/Red)

### Documentação

- [ ] **D1**: Docstrings explicam cada validação (V1-V6)
- [ ] **D2**: FAQ cobre todos os códigos de violação
- [ ] **D3**: Exemplos de output (success e failure) documentados
- [ ] **D4**: Workflow de debugging step-by-step

---

## 🔍 CASOS DE TESTE OBRIGATÓRIOS

### Test Case 1: Happy Path (INV-TRAIN-033)

**Setup**: INV-TRAIN-033 já existe com anchors corretos

**Comando**:
```powershell
python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033 --verbose
```

**Expected Output**:
```
[INFO] Validating 1 invariant(s)
[INFO] Level: standard
[INFO] Validating INV-TRAIN-033...
  ✓ INV-TRAIN-033: All anchors valid
[OK] All anchors valid (1 invariant(s) checked)
```

**Exit Code**: 0

---

### Test Case 2: Table Not Found

**Setup**: Temporariamente editar INVARIANTS_TRAINING.md:
```yaml
# Alterar:
db.table: wellness_pre_INVALID
```

**Comando**:
```powershell
python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033 --verbose
```

**Expected Output**:
```
[INFO] Validating INV-TRAIN-033...
[FAIL] Anchor validation violations:
docs/02-modulos/training/INVARIANTS_TRAINING.md:XXX:5: ERROR [ANCHOR_TABLE_NOT_FOUND]: Anchor db.table='wellness_pre_INVALID' not found in schema.sql — verify table name or check docs/_generated/schema.sql
       Invariant: INV-TRAIN-033
```

**Exit Code**: 2

**Teardown**: Reverter alteração

---

### Test Case 3: Constraint Not Found

**Setup**: Temporariamente editar INVARIANTS_TRAINING.md:
```yaml
# Alterar:
db.constraint: ck_INVALID_NAME
```

**Comando**:
```powershell
python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-033
```

**Expected Output**:
```
[FAIL] Anchor validation violations:
docs/02-modulos/training/INVARIANTS_TRAINING.md:XXX:5: ERROR [ANCHOR_CONSTRAINT_NOT_FOUND]: Anchor db.constraint='ck_INVALID_NAME' not found in schema.sql — verify constraint name or check schema.sql
```

**Exit Code**: 2

**Teardown**: Reverter alteração

---

### Test Case 4: Constraint Type Mismatch (Level: strict)

**Setup**: Invariante Classe A com anchor apontando para trigger

**Comando**:
```powershell
python scripts/validate_invariant_anchors.py --inv-id INV-TRAIN-046 --level strict
```

**Expected**: Se INV-TRAIN-046 é Classe A mas aponta para trigger:
```
ERROR [ANCHOR_CONSTRAINT_TYPE_MISMATCH]: Class A expects CHECK/UNIQUE/FK but constraint 'tr_update_wellness_post_response' is 'TRIGGER'
```

**Exit Code**: 2

---

### Test Case 5: Full Gate Success

**Setup**: INV-TRAIN-033 com tudo correto

**Comando**:
```powershell
.\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033" -Verbose
```

**Expected Output**: 4 gates passam sequencialmente

**Exit Code**: 0

---

### Test Case 6: Full Gate Failure on Gate 2

**Setup**: Anchor inválido em INV-TRAIN-033

**Comando**:
```powershell
.\scripts\invariants_full_gate.ps1 -InvId "INV-TRAIN-033"
```

**Expected**: Gate 2 falha, gates 3 e 4 não executam (fail-fast)

**Exit Code**: 2

---

## 📦 ESTRUTURA DE COMMITS

### Commit 1: Scaffold Gate 2
```
feat(gates): add validate_invariant_anchors.py scaffold

- Create script structure with argparse
- Implement data structures (Violation, Anchors, Invariant)
- Add placeholder validation functions (V1-V6)
- Add main() with file existence checks

Related: ADR-INV-TRAIN-002 Gate 2
```

### Commit 2: Implement Parsing
```
feat(gates): implement INVARIANTS.md and schema.sql parsing

- parse_invariants_md(): extract SPEC blocks with YAML
- extract_table_from_schema(): regex CREATE TABLE
- detect_constraint_type(): parse CONSTRAINT token

Tested with INV-TRAIN-033

Related: ADR-INV-TRAIN-002 Gate 2
```

### Commit 3: Implement Validations V1-V3
```
feat(gates): implement db.table and db.constraint validations

- V1: validate_db_table_exists()
- V2: validate_db_constraint_exists()
- V3: validate_constraint_type_matches_class()

Covers 80% of DB anchor cases

Related: ADR-INV-TRAIN-002 Gate 2
```

### Commit 4: Implement Validations V4-V6
```
feat(gates): implement trigger, function, and API validations

- V4: validate_db_trigger_exists()
- V5: validate_db_function_exists()
- V6: validate_api_operation_exists()

Covers remaining 20% (trigger-based invariants)

Related: ADR-INV-TRAIN-002 Gate 2
```

### Commit 5: Full Gate Orchestrator
```
feat(gates): add invariants_full_gate.ps1 orchestrator

- Detect table from SPEC block
- Execute 4 gates in order (fail-fast)
- Support --SkipGate for debugging
- Color-coded output (Green/Yellow/Red)

Tested with INV-TRAIN-033

Related: ADR-INV-TRAIN-002
```

### Commit 6: Smoke Tests
```
test(gates): add smoke tests for Gate 2 and full gate

- Test happy path (INV-TRAIN-033)
- Test negative cases (table not found, constraint invalid)
- Test constraint type mismatch
- Test full gate end-to-end

All tests passing

Related: ADR-INV-TRAIN-002
```

### Commit 7: Documentation
```
docs(gates): add troubleshooting guide for invariants gate

- FAQ covering all violation codes
- Debugging workflow step-by-step
- Manual verification examples
- Common errors and solutions

Related: ADR-INV-TRAIN-002
```

---

## 🚨 BLOQUEADORES E DEPENDÊNCIAS

### Dependências

- ✅ `docs/_generated/schema.sql` deve existir e estar atualizado
- ✅ `docs/_generated/openapi.json` deve existir (opcional para API validations)
- ✅ `INVARIANTS_TRAINING.md` deve ter pelo menos 1 invariante com SPEC
- ✅ `scripts/model_requirements.py` deve existir (Gate 1)
- ✅ `scripts/verify_invariants_tests.py` deve existir (Gate 3)

### Bloqueadores Conhecidos

- ⚠️ Parsing de YAML em markdown pode ser frágil (mitigação: regex robusto + testes)
- ⚠️ Regex de schema.sql pode falhar em casos edge (mitigação: testes com múltiplas tabelas)
- ⚠️ PowerShell inline Python pode ter encoding issues (mitigação: UTF-8 explícito)

---

## 📊 MÉTRICAS DE SUCESSO

### Cobertura

- [ ] 100% das validações V1-V6 implementadas
- [ ] 100% dos exit codes documentados (0, 1, 2)
- [ ] 100% dos violation codes documentados no FAQ

### Testes

- [ ] 6 test cases obrigatórios passando
- [ ] 0 false positives (rejeitar anchor válido)
- [ ] 0 false negatives (aceitar anchor inválido)

### Performance

- [ ] <5s para validar 1 invariante
- [ ] <30s para validar todas as 46 invariantes DONE

### Adoção

- [ ] Davi consegue rodar smoke test sem assistência
- [ ] Output de erro é claro o suficiente para self-service debugging
- [ ] FAQ cobre 100% dos erros encontrados durante smoke tests

---

## 🎓 ORIENTAÇÕES PARA O AGENTE

### Ordem de Implementação Recomendada

1. **Começar com parsing** (commit 2)
   - `parse_invariants_md()` é a base de tudo
   - Testar com INV-TRAIN-033 antes de prosseguir

2. **Implementar V1 e V2** (commit 3, parte 1)
   - Validações mais comuns (80% dos casos)
   - Smoke test após cada validação

3. **Implementar V3-V6** (commits 3 e 4)
   - Validações menos comuns mas críticas
   - Testar com INV-TRAIN-031 (trigger) e INV-TRAIN-046 (trigger)

4. **Orquestrador** (commit 5)
   - Integração com gates existentes
   - Testar fail-fast behavior

5. **Documentação** (commit 7)
   - FAQ baseado em erros REAIS encontrados durante implementação

### Padrões de Código Esperados

**Python**:
- Type hints completos: `def validate_db_table_exists(inv: Invariant, schema_text: str) -> List[Violation]:`
- Docstrings Google style
- Uso de `pathlib.Path` ao invés de strings
- `encoding='utf-8'` explícito em todos os file reads

**PowerShell**:
- `$ErrorActionPreference = "Stop"` no início
- Colors: `Write-Host "..." -ForegroundColor Green/Yellow/Red`
- Exit codes explícitos: `exit 1`, `exit 2`, etc.
- Verbose support: `if ($Verbose) { ... }`

### Debugging Tips

- Use `--verbose` desde o início (facilita debugging)
- Teste cada validation function standalone antes de integrar
- Print intermediate results (parsing de SPEC, regex matches)
- Salve outputs reais para documentação (copy/paste no FAQ)

---

## ✅ DEFINITION OF DONE

- [ ] Todos os 7 commits criados e testados
- [ ] 6 test cases obrigatórios passando
- [ ] Smoke test em INV-TRAIN-033 executado com sucesso
- [ ] FAQ documentado com erros reais
- [ ] Code review por Davi aprovado
- [ ] Gates integrados em `.github/workflows/ci.yml` (Fase 3, fora do escopo)

---

## 📝 NOTAS FINAIS

Este é um task de **alta complexidade** mas **alto impacto**. O Gate 2 sozinho elimina ~15% dos erros de rastreabilidade que hoje só são detectados em code review.

**Foco da Fase 1**: Implementar Gate 2 com **qualidade excepcional**. Priorizar qualidade sobre quantidade de gates.

**Próximas Fases** (não incluídas neste task):
- Fase 2: Extensões ao Gate 3 (SQLSTATE validation, constraint_name structural)
- Fase 3: CI/CD integration (GitHub Actions)
- Fase 4: Backlog cleanup (57 candidatas)

**Boa implementação!** 🚀

---

**Criado por**: Davi (Product Owner)  
**Revisado por**: Claude Sonnet 4.5 (Technical Advisor)  
**Data**: 2026-02-08  
**Versão**: 1.0
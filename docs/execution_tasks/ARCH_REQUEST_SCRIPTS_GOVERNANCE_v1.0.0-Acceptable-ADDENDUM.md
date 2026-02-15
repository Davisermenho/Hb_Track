# ARCH_REQUEST v1.0.0-Acceptable — ADDENDUM: Auditoria e Correções

**Status:** DRAFT (Auditoria de Implementação)  
**Autor:** Sistema (Agent) + Revisão Técnica  
**Data:** 2026-02-14  
**Versão:** 1.0.0-Addendum  
**Referência:** [ARCH_REQUEST_SCRIPTS_GOVERNANCE_v1.0.0-Acceptable.md](ARCH_REQUEST_SCRIPTS_GOVERNANCE_v1.0.0-Acceptable.md)

---

## RESUMO EXECUTIVO

Este addendum **audita a implementação atual** de `scripts/_policy/policy_lib.py` contra as regras R0-R9 do ARCH_REQUEST e identifica **gaps críticos** que causam não-determinismo.

**Status da implementação:** ⚠️ **PARCIALMENTE CONFORME** (4 gaps críticos + 2 gaps de cobertura)

---

## 1. AUDITORIA DA IMPLEMENTAÇÃO ATUAL

### 1.1 Arquivo: `scripts/_policy/policy_lib.py` (871 linhas)

#### ✅ CONFORME (O que está correto)

| Regra | Status | Evidência |
|-------|--------|-----------|
| R0.3 (Exit codes 0/2/3) | ✅ OK | Linha 10-13, função `validate_policy_compliance` retorna (0, 2, 3) |
| R2.0 (Meta-dirs) | ✅ OK | Linha 516-519: `if category in ["_policy", "_lib"]: continue` |
| R3 (Prefixo↔pasta) | ✅ OK | Linha 550-556: `get_expected_prefix()` + linha 533-537 validação |
| R4 (Header obrigatório) | ✅ OK | Linha 560-584: `validate_headers()` checa `REQUIRED_HEADERS` |
| R8.3 (run/ não referencia temp/) | ✅ OK | Linha 677-696: `references_temp()` detecta padrões |

#### ❌ NÃO CONFORME (Gaps críticos)

| Regra | Gap | Localização | Impacto | Prioridade |
|-------|-----|-------------|---------|------------|
| **R1.1** | `git ls-files scripts/` sem `-z` | Linha 490 | Quebra com paths com espaços | **🔴 CRÍTICO** |
| **R0.1** | Violations NÃO ordenadas | Linha 494, retorno sem sort | Output não determinístico | **🔴 CRÍTICO** |
| **R6.2** | Sem filtro de comentários | Linha 436-458: `detect_side_effects()` | Falso positivo em docstrings | **🟡 ALTO** |
| **R0.1** | Normalização incompleta | Linha 503: só `as_posix()` parcial | Windows/Linux podem divergir | **🟡 ALTO** |

#### 🚫 GAPS DE COBERTURA (Regras não implementadas)

| Regra | Descrição | Impacto | Prioridade |
|-------|-----------|---------|------------|
| **R1.3** | Arquivo sem header em categoria operacional | Falso negativo (scripts "perdidos") | **🔴 CRÍTICO** |
| **R12** | Layout repo-wide (.py fora de raízes) | Não detecta scripts fora de `scripts/` | **🟢 MÉDIO** |

---

## 2. CORREÇÕES OBRIGATÓRIAS (Para R0-R9)

### 2.1 CRÍTICO — R1.1: Git scope portável com `-z`

**Arquivo:** `scripts/_policy/policy_lib.py`  
**Linha:** 490

**Problema:**
```python
# ❌ ATUAL (linha 490)
result = subprocess.run(
    ["git", "ls-files", "scripts/"],  # Sem -z
    cwd=repo_root,
    capture_output=True,
    text=True,  # ❌ text=True quebra com -z
    check=False,
)
```

**Correção:**
```python
# ✅ CORRETO
result = subprocess.run(
    ["git", "ls-files", "-z", "--", "scripts"],  # Com -z e --
    cwd=repo_root,
    capture_output=True,
    text=False,  # ✅ bytes para -z
    check=False,
)
if result.returncode == 0:
    # Split by NUL, decode UTF-8, filter empty
    paths_raw = result.stdout.decode('utf-8').split('\0')
    tracked = [
        repo_root / p.strip()
        for p in paths_raw
        if p.strip()
    ]
else:
    tracked = []  # Empty on git error
```

**Evidência:** [Git Documentation - ls-files](https://git-scm.com/docs/git-ls-files) recomenda `-z` para paths com espaços/newlines.

---

### 2.2 CRÍTICO — R0.1: Ordenar violations antes de retornar

**Arquivo:** `scripts/_policy/policy_lib.py`  
**Linha:** 494 (retorno de `validate_scripts`)

**Problema:**
```python
# ❌ ATUAL (linha 494)
return violations  # Não ordenado
```

**Correção:**
```python
# ✅ CORRETO
# Ordenar por path (segundo elemento da tupla)
violations_sorted = sorted(violations, key=lambda v: v[1])
return violations_sorted
```

**Impacto:** Sem isso, ordem de erros varia entre execuções (não determinístico).

---

### 2.3 ALTO — R6.2: Filtro de comentários em heurísticas

**Arquivo:** `scripts/_policy/policy_lib.py`  
**Linha:** 436-458 (`detect_side_effects`)

**Problema:**
```python
# ❌ ATUAL (linha 436-458)
def detect_side_effects(script_path: Path, heuristics: Dict[str, Any]) -> Set[str]:
    # ...
    content = script_path.read_text(encoding="utf-8", errors="ignore")
    # ... aplica regex diretamente em content (SEM filtrar comentários)
```

**Correção:**
```python
# ✅ CORRETO
def is_comment_line(line: str, ext: str) -> bool:
    """Detecta se linha é comentário (simples, não parseia linguagem completa)."""
    stripped = line.strip()
    if ext in ['.ps1', '.py']:
        return stripped.startswith('#')
    elif ext == '.sql':
        return stripped.startswith('--')
    return False

def detect_side_effects(script_path: Path, heuristics: Dict[str, Any]) -> Set[str]:
    if not script_path.exists():
        return set()

    ext = script_path.suffix.lower()
    content = script_path.read_text(encoding="utf-8", errors="ignore")
    
    detect = heuristics.get("detect", {})
    lang_map = {".py": "python", ".ps1": "powershell", ".sql": "sql"}
    lang = lang_map.get(ext)
    if not lang:
        return set()

    lang_rules = detect.get(lang, {})
    detected: Set[str] = set()

    # ✅ NOVO: Filtra comentários linha por linha
    for line in content.splitlines():
        if is_comment_line(line, ext):
            continue  # Ignora comentários
        
        for effect, patterns in lang_rules.items():
            if not isinstance(patterns, list):
                continue
            for pattern in patterns:
                if isinstance(pattern, str):
                    try:
                        if re.search(pattern, line, re.IGNORECASE):
                            detected.add(effect)
                            break
                    except Exception:
                        pass

    return detected
```

**Evidência:** Reduz falso positivo em docstrings com exemplos de código.

---

### 2.4 ALTO — R0.1: Normalização completa de paths

**Arquivo:** `scripts/_policy/policy_lib.py`  
**Linha:** 503 (e outros)

**Problema:**
```python
# ❌ ATUAL (linha 503)
rel_path = script_path.relative_to(repo_root).as_posix()
# Mas não normaliza consistentemente em todos os lugares
```

**Correção:**
```python
# ✅ CORRETO: Usar helper de normalização
def normalize_path(path: Path, relative_to: Path) -> str:
    """Normaliza path para formato Unix (/) relativo a root."""
    try:
        return path.relative_to(relative_to).as_posix()
    except ValueError:
        # Path fora de relative_to
        return path.as_posix()

# Usar em validate_scripts:
rel_path = normalize_path(script_path, repo_root)
```

**Aplicar em:**
- Linha 503 (validate_scripts)
- Linha 562 (validate_headers)
- Linha 642 (validate_side_effects)
- Linha 677 (references_temp)

---

## 3. NOVAS REGRAS (Gaps de Cobertura)

### 3.1 R1.3 — POLICY-E_UNTAGGED_SCRIPT (Novo)

**Objetivo:** Detectar arquivos `.py/.ps1/.sql` em categorias operacionais sem header.

**Regra:**
> Qualquer arquivo com extensão `.ps1`, `.py`, `.sql` **dentro de `scripts/<categoria>/`** (exceto meta-dirs, README.md, .gitignore, `__init__.py`) **MUST** ter header `HB_SCRIPT_KIND`.  
> Se não tiver → **FAIL** `POLICY-E_UNTAGGED_SCRIPT`

**Implementação:**
```python
# Adicionar em validate_scripts() após linha 509

# Rule R1.3: Untagged script in operational category
if category not in ["_policy", "_lib", "artifacts", "temp"]:
    # É um script candidato?
    if script_path.suffix.lower() in VALID_EXTS_DEFAULT:
        # Exceções explícitas
        if script_path.name not in ["README.md", ".gitignore", "__init__.py"]:
            # Verificar se tem header HB_SCRIPT_KIND
            has_header = has_script_header(script_path)
            if not has_header:
                violations.append(
                    ("POLICY-E_UNTAGGED_SCRIPT", rel_path,
                     "Script in operational category without HB_SCRIPT_KIND header")
                )

def has_script_header(script_path: Path) -> bool:
    """Verifica se script tem header HB_SCRIPT_KIND nas primeiras 50 linhas."""
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines()[:50]:
            if re.search(r"HB_SCRIPT_KIND", line):
                return True
        return False
    except Exception:
        return False
```

**Caso de teste:**
```python
# scripts/checks/orphan_script.py (SEM header)
def test(): pass

# Esperado: POLICY-E_UNTAGGED_SCRIPT | scripts/checks/orphan_script.py | ...
```

---

### 3.2 R12 — Layout Repo-Wide (Gate Separado)

**Objetivo:** Validar que `.py` só existe em raízes permitidas.

**Regra:**
> Arquivos `.py` **MUST** estar apenas em:
> - `scripts/`
> - `app/`
> - `tests/`
> - `db/`
> - `docs/scripts/`
> - `Hb Track - Backend/` (subpastas específicas)
>
> Se `.py` fora dessas raízes → **FAIL** `LAYOUT-E_PYTHON_OUTSIDE_ROOT`

**Implementação:** Criar `scripts/checks/layout/check_python_layout.py`

```python
#!/usr/bin/env python3
# HB_SCRIPT_KIND: checks
# HB_SCRIPT_SCOPE: layout
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: scripts/checks/layout/check_python_layout.py
# HB_SCRIPT_OUTPUTS: stdout

"""
Check Project Layout (Repo-Wide)

Validates that .py files only exist in approved roots.
"""

import subprocess
import sys
from pathlib import Path

ALLOWED_ROOTS = [
    "scripts/",
    "app/",
    "tests/",
    "db/",
    "docs/scripts/",
    "Hb Track - Backend/app/",
    "Hb Track - Backend/tests/",
    "Hb Track - Backend/db/",
]

def main():
    repo_root = Path(__file__).resolve().parents[3]
    
    # Get all .py files (versioned)
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=repo_root,
        capture_output=True,
        text=False,
        check=False,
    )
    
    if result.returncode != 0:
        print("ERROR: git ls-files failed")
        sys.exit(3)
    
    paths = result.stdout.decode('utf-8').split('\0')
    violations = []
    
    for p in paths:
        if not p.strip():
            continue
        
        # Normalizar para /
        norm_path = p.strip().replace('\\', '/')
        
        # Verificar se começa com alguma raiz permitida
        allowed = any(norm_path.startswith(root) for root in ALLOWED_ROOTS)
        
        if not allowed:
            violations.append(f"LAYOUT-E_PYTHON_OUTSIDE_ROOT | {norm_path} | Not in allowed roots")
    
    if violations:
        for v in sorted(violations):
            print(v)
        sys.exit(2)
    
    print("PASS: All .py files in allowed roots")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Caso de teste:**
```
# scripts_para_organizar_01/foo.py (versionado)
# Esperado: LAYOUT-E_PYTHON_OUTSIDE_ROOT | scripts_para_organizar_01/foo.py | ...
```

---

## 4. PLANO DE VALIDAÇÃO (Sentinelas de Teste)

### 4.1 Criar Fixtures de Teste

**Local:** `tests/policy_scripts/fixtures/` (ou `scripts/temp/test_fixtures/` não versionado)

#### Sentinela 1: PASS — Check correto
```python
# fixtures/check_contract_PASS.py
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: openapi
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: fixtures/check_contract_PASS.py
# HB_SCRIPT_OUTPUTS: stdout

import json
def validate(): pass
```

#### Sentinela 2: PASS — Wrapper com pytest
```powershell
# fixtures/run_tests_PASS.ps1
# HB_SCRIPT_KIND: RUNNER
# HB_SCRIPT_SCOPE: testing
# HB_SCRIPT_SIDE_EFFECTS: PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT: false
# HB_SCRIPT_ENTRYPOINT: fixtures/run_tests_PASS.ps1
# HB_SCRIPT_OUTPUTS: stdout

pytest tests/
```

#### Sentinela 3: FAIL — Check com pytest (R7)
```python
# fixtures/check_tests_FAIL_R7.py
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: testing
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: fixtures/check_tests_FAIL_R7.py
# HB_SCRIPT_OUTPUTS: stdout

import subprocess
subprocess.run(["pytest", "tests/"])  # ❌ Forbidden invoke
```

**Esperado:** `CHECKS-E_FORBIDDEN_INVOKE | fixtures/check_tests_FAIL_R7.py | pytest`

#### Sentinela 4: FAIL — Check com FS_WRITE (R6)
```powershell
# fixtures/check_log_FAIL_R6.ps1
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: diagnostics
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: fixtures/check_log_FAIL_R6.ps1
# HB_SCRIPT_OUTPUTS: stdout

"log" | Out-File debug.log  # ❌ Side-effect
```

**Esperado:** `CHECKS-E_SIDE_EFFECT_DETECTED | fixtures/check_log_FAIL_R6.ps1 | FS_WRITE`

#### Sentinela 5: FAIL — Script sem header (R1.3)
```python
# fixtures/orphan_script_FAIL_R13.py
def test(): pass
# ❌ Sem header HB_SCRIPT_KIND
```

**Esperado:** `POLICY-E_UNTAGGED_SCRIPT | fixtures/orphan_script_FAIL_R13.py | ...`

#### Sentinela 6: FAIL — Kind/Path mismatch (R4.2)
```python
# fixtures/check_auth_FAIL_R4.py
# HB_SCRIPT_KIND: RUNNER  # ❌ Errado (path é checks/)
# HB_SCRIPT_SCOPE: auth
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: fixtures/check_auth_FAIL_R4.py
# HB_SCRIPT_OUTPUTS: stdout

def validate(): pass
```

**Esperado:** `HB005 | fixtures/check_auth_FAIL_R4.py | KIND mismatch: header='RUNNER', expected='CHECK'`

---

### 4.2 Script de Validação Automatizado

```powershell
# scripts/checks/docs/check_policy_determinism.ps1
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: docs
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: scripts/checks/docs/check_policy_determinism.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    Valida determinismo do gate de scripts policy
.DESCRIPTION
    Roda gate 3x e compara outputs (devem ser idênticos)
#>

param()

$ErrorActionPreference = "Stop"
Set-Location "C:\HB TRACK"

Write-Host "[check_policy_determinism] Running gate 3x..." -ForegroundColor Cyan

$Outputs = @()
for ($i = 1; $i -le 3; $i++) {
    $Output = & "scripts\_policy\check_scripts_policy.ps1" 2>&1 | Out-String
    $Outputs += $Output
    Write-Host "[Run $i] Exit: $LASTEXITCODE" -ForegroundColor Gray
}

# Comparar outputs
$Output1 = $Outputs[0]
$Output2 = $Outputs[1]
$Output3 = $Outputs[2]

if ($Output1 -eq $Output2 -and $Output2 -eq $Output3) {
    Write-Host "[OK] Determinism verified: 3 identical outputs" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] Determinism violation: outputs differ" -ForegroundColor Red
    Write-Host "`nDiff 1 vs 2:"
    Compare-Object $Output1.Split("`n") $Output2.Split("`n") | Format-Table
    exit 2
}
```

---

### 4.3 Evidências de Prova (Artefatos)

Após rodar sentinelas, salvar:

```
tests/policy_scripts/evidence/
├── command.txt          # Comando exato executado
├── run_log_1.txt        # Saída execução 1
├── run_log_2.txt        # Saída execução 2
├── run_log_3.txt        # Saída execução 3
├── diff_1_vs_2.txt      # Diff entre runs (esperado: vazio)
├── git_state.txt        # git rev-parse HEAD + git status --porcelain
└── env.txt              # Environment: interpreter version, git version, shell version
```

---

## 5. PRIORIZAÇÃO DE CORREÇÕES

### 5.1 Sprint 1 (Determinismo Básico)
- [x] **R1.1**: Corrigir `git ls-files -z`
- [x] **R0.1**: Ordenar violations
- [ ] **R1.3**: Adicionar POLICY-E_UNTAGGED_SCRIPT
- [ ] Criar sentinelas 1-6
- [ ] Validar determinismo (3x runs idênticos)

### 5.2 Sprint 2 (Redução de Falso Positivo)
- [ ] **R6.2**: Filtro de comentários em heurísticas
- [ ] **R0.1**: Normalização completa de paths
- [ ] Adicionar R7 (forbidden invocations) ao heuristics.yaml
- [ ] Rodar em CI Linux (validar cross-platform)

### 5.3 Sprint 3 (Cobertura Completa)
- [ ] **R12**: Gate de layout repo-wide (check_python_layout.py)
- [ ] Enforçar em CI (bloquear merge se exit ≠ 0)
- [ ] Documentar em `scripts/README.md`

---

## 6. CHECKLIST DE CONFORMIDADE FINAL

### 6.1 Critérios de Aceitação

- [ ] Git scope usa `-z` (portável)
- [ ] Violations ordenadas por path
- [ ] Filtro de comentários em heurísticas
- [ ] Normalização completa de paths (`/`)
- [ ] R1.3 implementado (POLICY-E_UNTAGGED_SCRIPT)
- [ ] Sentinelas 1-6 criadas e testadas
- [ ] 3 runs idênticos (Windows PowerShell 5.1)
- [ ] 3 runs idênticos (Windows PowerShell 7+)
- [ ] Gate roda em CI Linux (opcional, mas recomendado)
- [ ] Documentação atualizada (scripts/README.md)

### 6.2 Definição de "Determinístico Provado"

Um gate é **determinístico provado** SE:
1. Output idêntico em 3 runs consecutivos (mesmo commit)
2. Output idêntico em ambientes diferentes (Windows/Linux)
3. Exit code estável (0/2/3)
4. Ordem de erros estável (alfabética por path)
5. Sem timestamps ou dados variáveis no output

---

## 7. RESUMO DE MUDANÇAS PARA policy_lib.py

### Diff Conceitual (4 mudanças críticas + 1 nova regra)

```diff
# 1) Git scope portável (linha 490)
- result = subprocess.run(["git", "ls-files", "scripts/"], ...)
+ result = subprocess.run(["git", "ls-files", "-z", "--", "scripts"], text=False, ...)
+ paths = result.stdout.decode('utf-8').split('\0')

# 2) Ordenar violations (linha 494)
- return violations
+ return sorted(violations, key=lambda v: v[1])

# 3) Filtro de comentários (linha 436-458)
+ def is_comment_line(line: str, ext: str) -> bool: ...
  def detect_side_effects(...):
+     for line in content.splitlines():
+         if is_comment_line(line, ext): continue

# 4) Normalização completa (várias linhas)
+ def normalize_path(path: Path, relative_to: Path) -> str: ...
- rel_path = script_path.relative_to(repo_root).as_posix()
+ rel_path = normalize_path(script_path, repo_root)

# 5) Nova regra R1.3 (após linha 509)
+ if category not in ["_policy", "_lib", "artifacts", "temp"]:
+     if not has_script_header(script_path):
+         violations.append(("POLICY-E_UNTAGGED_SCRIPT", ...))
```

---

## 8. AUTORIDADE E REFERÊNCIAS

### 8.1 Documentos Canônicos
- [ARCH_REQUEST v1.0.0-Acceptable](ARCH_REQUEST_SCRIPTS_GOVERNANCE_v1.0.0-Acceptable.md) (especificação R0-R9)
- `scripts/_policy/policy_lib.py` (implementação auditada)
- `scripts/_policy/side_effects_heuristics.yaml` (heurísticas)

### 8.2 Evidências Externas
- [Git ls-files documentation](https://git-scm.com/docs/git-ls-files) (-z para paths com espaços)
- [Pre-commit best practices](https://pre-commit.com/) (determinismo em hooks)
- PEP 8 style guide (ordenação e normalização)

### 8.3 Histórico
| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0.0-Addendum | 2026-02-14 | Auditoria inicial + 6 gaps identificados |

---

**STATUS:** ⚠️ Aguardando correções (4 gaps críticos) antes de declarar conformidade total.

**PRÓXIMO PASSO:** Implementar correções 2.1-2.4 + criar sentinelas 4.1 + validar determinismo 4.2.


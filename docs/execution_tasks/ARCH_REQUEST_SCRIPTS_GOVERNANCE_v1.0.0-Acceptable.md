# ARCH_REQUEST — Governança Determinística de Scripts (HB Track)

**Status:** APPROVED (v1.0.0-Acceptable)  
**Autor:** Sistema (Agent) + Revisão Humana  
**Data:** 2026-02-14  
**Versão:** 1.0.0-Acceptable  
**Autoridade:** `docs/_canon/ARCH_REQUEST_GENERATION_PROTOCOL.md`  
**Implementação:** `scripts/_policy/` (EXISTENTE)

---

## RESUMO EXECUTIVO

Este ARCH_REQUEST formaliza a governança determinística de scripts existente em `scripts/_policy/`, com correções críticas para:
- Tratar `_policy` e `_lib` como meta-dirs (não categorias operacionais)
- Usar `git ls-files -z` para escopo portável (Windows/Linux)
- Unificar SSOT em `scripts/_policy/scripts.policy.yaml`
- Separar engine (Python) de wrapper (PowerShell)

**Implementação atual:**
- ✅ `scripts/_policy/scripts.policy.yaml` (SSOT)
- ✅ `scripts/_policy/side_effects_heuristics.yaml` (heurísticas)
- ✅ `scripts/_policy/check_scripts_policy.ps1` (gate principal)
- ✅ `scripts/_policy/policy_lib.py` (engine Python)

---

## 1. CONTEXTO E MOTIVAÇÃO

### 1.1 Problema Atual
Scripts em `scripts/**` requerem governança determinística para:
- Prevenir "checks" com side-effects (ex.: runners de testes)
- Enforcar coerência path/prefixo/header
- Validar categorização sem ambiguidade
- Garantir determinismo em CI (Windows/Linux)

### 1.2 Impacto
- **Agentes de IA** podem validar scripts antes de criar PR
- **CI/CD** tem exit codes estáveis (0/2/3)
- **Desenvolvedores** sabem onde colocar novos scripts
- **Auditoria** de side-effects é automática

### 1.3 Objetivo da Proposta
Formalizar as regras existentes com ajustes críticos para fechar gaps de determinismo.

---

## 2. REGRAS CANÔNICAS (AUTHORITY)

### R0 — Normalização e Ordenação (Fundação do Determinismo)

**R0.1 (Normalização)**  
- Sempre normalizar paths para `/` (cross-platform)
- Sempre ordenar lista de arquivos e erros por `path` (string sort)

**R0.2 (Formato de erro estável)**  
```
<CODE> | <PATH> | <DETAILS>
```
Exemplo:
```
POLICY-E_PREFIX_MISMATCH | scripts/checks/runner_tests.py | Expected prefix 'check_', got 'runner_'
```
❌ Proibido: timestamps, mensagens variáveis, ordem não determinística

**R0.3 (Exit codes fixos)**  
```
0 = PASS (todos os scripts OK)
2 = FAIL (violação de policy)
3 = HARNESS ERROR (SSOT inválido, exceção não tratada)
```

---

### R1 — Escopo e Definição de "Script-Candidato"

**R1.1 (Scope — CORREÇÃO CRÍTICA)**  
O gate varre **APENAS** arquivos versionados por git em `scripts/`:

```powershell
# ❌ FRÁGIL (varia por shell/quoting)
git ls-files 'scripts/**'

# ✅ CORRETO (portável, NUL-separated)
git ls-files -z -- scripts
```

**Implementação Python:**
```python
import subprocess
from pathlib import Path

def get_versioned_scripts():
    """Enumera arquivos versionados em scripts/ (portável)."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "scripts"],
        cwd=repo_root,
        capture_output=True,
        text=False,
        check=True
    )
    paths = result.stdout.decode('utf-8').split('\0')
    return [p for p in paths if p]  # remove empty string final
```

**R1.2 (Script-candidato)**  
Um arquivo entra no julgamento SE:
- Extensão ∈ `{.ps1, .py, .sql}` **E**
- (Tem prefixo canônico `check_|diag_|fix_|gen_|mig_|ops_|reset_|seed_|run_|tmp_`) **OU**
- (Contém `HB_SCRIPT_KIND` nas primeiras 50 linhas)

**Exceções explícitas (não são candidatos):**
- `README.md`
- `.gitignore`
- `__init__.py` (sem prefixo/header)
- Arquivos em `scripts/_policy/**` e `scripts/_lib/**` (ver R2.0)

**R1.3 (Untagged script — NOVA REGRA)**  
Qualquer arquivo `.ps1`, `.py`, `.sql` **dentro de `scripts/<categoria>/`** (exceto meta-dirs, exceções explícitas) **MUST** ter header `HB_SCRIPT_KIND`.

Se arquivo executável em categoria operacional NÃO tem header → **FAIL** `POLICY-E_UNTAGGED_SCRIPT`.

**Objetivo:** Evitar "scripts perdidos" sem classificação em categorias operacionais.

**Exemplo:**
```python
# ❌ scripts/checks/orphan_script.py (SEM header)
def test(): pass

# FAIL: POLICY-E_UNTAGGED_SCRIPT | scripts/checks/orphan_script.py | Missing HB_SCRIPT_KIND
```

---

### R2 — Categoria por Path (Com Meta-Dirs) — CORREÇÃO CRÍTICA

**R2.0 (Meta-dirs — NOVA REGRA)**  
Diretórios `scripts/_*` são **meta-dirs** e ficam fora da classificação operacional:

```yaml
meta_dirs:
  _policy:  # Policy files, schemas, validators
    allowed_files: ["*.yaml", "*.json", "*.py", "*.ps1", "README.md"]
    validation: "structural_only"  # não aplicar R3-R9
  _lib:     # Shared libraries (importadas por outros scripts)
    allowed_files: ["*.py", "README.md"]
    validation: "structural_only"
```

**Regra:** Meta-dirs não passam por validação de categoria/prefixo/header (R3-R9), mas podem ter validações específicas (ex.: "schema valida", "templates existem").

**R2.1 (Categoria = 1º segmento após meta-dir)**  
Para paths `scripts/<category>/...`:
```yaml
allowed_categories:
  - artifacts   # Generated outputs (não aceita script-candidato)
  - checks      # Read-only validators
  - diagnostics # Read-only analysis
  - fixes       # Automated corrections
  - generate    # Code/doc generators
  - migrate     # Data migrations
  - ops         # Operational scripts
  - reset       # Environment reset
  - run         # Wrappers/orchestrators
  - seeds       # Test data population
  - temp        # Quarantine (não versionado)
```

**R2.2 (Categoria inválida)**  
Qualquer outra pasta top-level em `scripts/` (exceto `_*`) = **FAIL** `POLICY-E_INVALID_CATEGORY`.

---

### R3 — Prefixo ↔ Pasta (Determinístico)

**R3.1 (Regra por categoria)**
| Categoria     | Prefixo obrigatório | Exceções                          |
|---------------|---------------------|-----------------------------------|
| checks        | `check_`            | -                                 |
| diagnostics   | `diag_`             | -                                 |
| fixes         | `fix_`              | -                                 |
| generate      | `gen_`              | -                                 |
| migrate       | `mig_`              | -                                 |
| ops           | `ops_`              | -                                 |
| reset         | `reset_`            | -                                 |
| run           | `run_`              | -                                 |
| seeds         | `seed_`             | -                                 |
| temp          | `tmp_`              | -                                 |
| artifacts     | N/A                 | Não aceita script-candidato       |

**R3.2 (Mismatch)**  
Se `category=checks` mas `filename` NÃO começa com `check_` → **FAIL** `POLICY-E_PREFIX_MISMATCH`.

**Exemplo:**
```
❌ scripts/checks/runner_tests.py  → FAIL (prefixo 'runner_', esperado 'check_')
✅ scripts/checks/check_openapi.py → PASS
```

---

### R4 — Header Obrigatório e Coerência com Path

**R4.1 (Header obrigatório)**  
Todo script-candidato **MUST** ter header parseável (comentários nas primeiras 50 linhas):

```yaml
# PowerShell / Python:
# HB_SCRIPT_KIND: checks
# HB_SCRIPT_SCOPE: openapi
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: scripts/checks/openapi/check_contract.py
# HB_SCRIPT_OUTPUTS: stdout

-- SQL:
-- HB_SCRIPT_KIND: seeds
-- HB_SCRIPT_SCOPE: test_data
-- HB_SCRIPT_SIDE_EFFECTS: DB_WRITE
-- ...
```

**Campos obrigatórios:**
- `HB_SCRIPT_KIND` (str, enum de categoria)
- `HB_SCRIPT_SCOPE` (str, módulo/subscope)
- `HB_SCRIPT_SIDE_EFFECTS` (enum: NONE, FS_WRITE, DB_WRITE, etc.)
- `HB_SCRIPT_IDEMPOTENT` (bool)
- `HB_SCRIPT_ENTRYPOINT` (str, path relativo normalizado com `/`)
- `HB_SCRIPT_OUTPUTS` (list[str] ou "stdout")

**R4.2 (Kind ↔ pasta)**  
`HB_SCRIPT_KIND` **MUST** bater com a categoria do path:
```python
# Exemplo: scripts/checks/check_openapi.py
HB_SCRIPT_KIND: checks  # ✅ OK
HB_SCRIPT_KIND: run     # ❌ FAIL: POLICY-E_KIND_PATH_MISMATCH
```

**R4.3 (Scope ↔ subpath)**  
`HB_SCRIPT_SCOPE` **MUST** refletir o sub-scope (quando existir):
```python
# Exemplo: scripts/checks/openapi/check_contract.py
HB_SCRIPT_SCOPE: openapi  # ✅ OK
HB_SCRIPT_SCOPE: auth     # ❌ FAIL: POLICY-E_SCOPE_PATH_MISMATCH
```

**R4.4 (Entrypoint)**  
`HB_SCRIPT_ENTRYPOINT` **MUST** ser o path relativo real (normalizado com `/`):
```python
# Exemplo: scripts/checks/check_openapi.py
HB_SCRIPT_ENTRYPOINT: scripts/checks/check_openapi.py  # ✅ OK
HB_SCRIPT_ENTRYPOINT: scripts/old/check_openapi.py     # ❌ FAIL: POLICY-E_ENTRYPOINT_MISMATCH (script movido?)
```

---

### R5 — Sub-scope Obrigatório por Categoria

**R5.1 (Allowlist no SSOT)**  
Em `scripts/_policy/scripts.policy.yaml`:
```yaml
categories:
  checks:
    require_subscope: true
    allowed_subscopes:
      - auth         # scripts/checks/auth/
      - db           # scripts/checks/db/
      - docs         # scripts/checks/docs/
      - lint         # scripts/checks/lint/
      - models       # scripts/checks/models/
      - openapi      # scripts/checks/openapi/
      - security     # scripts/checks/security/
  
  run:
    require_subscope: false  # wrappers genéricos OK
  
  temp:
    require_subscope: false
  
  # ... (outras categorias)
```

**R5.2 (Validação)**  
Se `require_subscope=true` e path NÃO está em subscope permitido → **FAIL** `POLICY-E_SUBSCOPE_REQUIRED`.

---

### R6 — Checks/Diagnostics Realmente "Read-Only"

**R6.1 (Declaração)**  
Em `scripts/checks/**` e `scripts/diagnostics/**`:
```yaml
HB_SCRIPT_SIDE_EFFECTS: NONE  # obrigatório
```

**R6.2 (Verificação por padrões — COM FILTRO DE COMENTÁRIOS)**  
Use `side_effects_heuristics.yaml` para detectar side-effects:

```yaml
# side_effects_heuristics.yaml
effects:
  FS_WRITE:
    powershell:
      - "\\bNew-Item\\b"
      - "\\bSet-Content\\b"
      - "\\bOut-File\\b"
      - "\\s>\\s"  # redirection
    python:
      - "\\bopen\\s*\\([^)]*['\"]w"
      - "\\bPath\\.write_"
      - "\\bos\\.makedirs\\b"
  
  DB_WRITE:
    sql:
      - "\\bINSERT\\b"
      - "\\bUPDATE\\b"
      - "\\bDELETE\\b"
    python:
      - "\\bexecute\\s*\\([^)]*\\b(insert|update|delete)\\b"
      - "\\bsession\\.(add|delete|merge)\\b"
  
  PROC_EXEC:
    powershell:
      - "\\bStart-Process\\b"
      - "\\bInvoke-Command\\b"
    python:
      - "\\bsubprocess\\."
      - "\\bos\\.system\\b"
```

**Filtro de falso positivo (comentários):**
```python
def is_comment_line(line: str, extension: str) -> bool:
    """Detecta se linha é comentário (simples, não parseia linguagem completa)."""
    stripped = line.strip()
    if extension in ['.ps1', '.py']:
        return stripped.startswith('#')
    elif extension == '.sql':
        return stripped.startswith('--')
    return False

def scan_side_effects(content: str, extension: str, heuristics: dict) -> List[str]:
    """Detecta side-effects, ignorando comentários."""
    detected = []
    for line in content.splitlines():
        if is_comment_line(line, extension):
            continue  # ignora exemplos em comentários
        for effect_name, patterns in heuristics.items():
            for pattern in patterns.get(extension_group, []):
                if re.search(pattern, line, re.IGNORECASE):
                    detected.append(effect_name)
    return list(set(detected))
```

**R6.3 (Regra)**  
Se script em `checks/` ou `diagnostics/` contém padrão de side-effect → **FAIL** `CHECKS-E_SIDE_EFFECT_DETECTED`.

---

### R7 — Forbidden Invocations por Categoria (REGRA CHAVE CONTRA "CHECK QUE RODA TESTES")

**R7.1 (Checks: forbidden invocations)**  
Em `scripts/checks/**`, **PROIBIDO** invocar:

```yaml
forbidden_invocations:
  checks:
    - "\\bpytest\\b"
    - "\\bpython\\s+-m\\s+pytest\\b"
    - "\\buvicorn\\b"
    - "\\balembic\\s+(upgrade|downgrade)\\b"
    - "\\bdocker(\\s+compose)?\\b"
    - "\\bpsql\\b"
    - "\\bInvoke-WebRequest\\b"
    - "\\bcurl\\b"
    - "\\bwget\\b"
```

**R7.2 (Detecção com bordas de palavra)**  
Use `\b` (word boundary) para evitar falso positivo em strings/variáveis.

**R7.3 (Filtro de comentários)**  
Aplicar mesmo filtro de R6.2 (ignorar linhas comentadas).

**R7.4 (Penalidade)**  
Se script em `checks/` contém forbidden invocation → **FAIL** `CHECKS-E_FORBIDDEN_INVOKE`.

**Exemplo prático:**
```python
# ❌ scripts/checks/check_tests.py (FAIL)
# HB_SCRIPT_KIND: checks
import subprocess
subprocess.run(["pytest", "tests/"])  # CHECKS-E_FORBIDDEN_INVOKE: pytest

# ✅ scripts/run/run_tests.py (PASS)
# HB_SCRIPT_KIND: run
import subprocess
subprocess.run(["pytest", "tests/"])  # OK (wrappers podem orquestrar)
```

**Resultado:** "Runners" devem ir para `run/` (wrapper) ou `ops/` (operacional), não `checks/`.

---

### R8 — Regra para `run/` (Wrappers de Verdade)

**R8.1 (Dispatcher apenas)**  
Scripts em `run/` podem ter `PROC_EXEC`, mas **MUST** referenciar apenas `scripts/**` (não executáveis externos arbitrários).

**R8.2 (Sem side-effects diretos)**  
Wrappers em `run/` **MUST NOT** ter `DB_WRITE`, `FS_WRITE` (exceto logs temporários).

**R8.3 (Proibido referenciar `temp/`)**  
Scan simples: procurar string `scripts/temp` em arquivos `run_*`.  
Se encontrar → **FAIL** `RUN-E_REFERENCES_TEMP`.

---

### R9 — `temp/` e `artifacts/` como Invariantes

**R9.1 (temp/)**  
- `scripts/temp/**` **MUST** estar em `.gitignore`
- Se houver arquivos versionados (exceto `.gitignore`, `README.md`) → **FAIL** `TEMP-E_VERSIONED_FILE`

**R9.2 (artifacts/)**  
- `scripts/artifacts/**` é output-only
- Scripts **MUST NOT** usá-lo como SSOT/input
- `run/` **MUST NOT** depender de `artifacts/` como "verdade"

---

### R10 — Determinismo de Execução e Output (já documentado em R0)

Ver R0.1, R0.2, R0.3 para regras de normalização, formato de erro e exit codes.

---

### R11 — Separação "Check" vs "Fix" (já documentado)

Ver R6 (checks são read-only) e categorias `checks/` vs `fixes/`.

---

### R12 — Layout Repo-Wide (Gate Separado) — NOVA REGRA

**R12.1 (Raízes permitidas para .py)**  
Arquivos `.py` **MUST** estar apenas em:
```yaml
allowed_python_roots:
  - scripts/
  - app/
  - tests/
  - db/
  - docs/scripts/
  - Hb Track - Backend/app/
  - Hb Track - Backend/tests/
  - Hb Track - Backend/db/
```

**R12.2 (Arquivo perdido)**  
Se `.py` fora de raiz permitida → **FAIL** `LAYOUT-E_PYTHON_OUTSIDE_ROOT`.

**R12.3 (Implementação)**  
Gate separado: `scripts/checks/layout/check_python_layout.py`

**Escopo:**
```python
# Enumerar TODOS os .py versionados
subprocess.run(["git", "ls-files", "-z", "--", "*.py"], ...)
```

**Objetivo:** Detectar scripts "perdidos" fora de `scripts/` (ex.: `scripts_para_organizar_01/`).

**Exemplo:**
```python
# ❌ scripts_para_organizar_01/foo.py (versionado)
# FAIL: LAYOUT-E_PYTHON_OUTSIDE_ROOT | scripts_para_organizar_01/foo.py | Not in allowed roots
```

**Nota:** Este gate é **complementar** ao gate de scripts policy (R1-R9). Enquanto R1-R9 validam `scripts/**`, R12 valida o repo inteiro.

---

## 3. ESTRUTURA DE ARTEFATOS (EXISTENTE)

### 3.1 SSOT: `scripts/_policy/scripts.policy.yaml`
**Autoridade:** ✅ EXISTENTE  
**Path:** `scripts/_policy/scripts.policy.yaml`

Contém:
- Categorias permitidas
- Prefixos por categoria
- Subscopes allowlist
- Side-effects permitidos por categoria
- Exit codes por categoria

**Validado por:** `scripts/_policy/scripts.policy.schema.json`

---

### 3.2 Heurísticas: `scripts/_policy/side_effects_heuristics.yaml`
**Autoridade:** ✅ EXISTENTE  
**Path:** `scripts/_policy/side_effects_heuristics.yaml`

Contém:
- Padrões regex por linguagem (.ps1/.py/.sql)
- Side-effects: FS_WRITE, DB_WRITE, PROC_EXEC, etc.
- Global ignores (meta-dirs, README, .gitignore)

**Usado por:** `policy_lib.py`

---

### 3.3 Engine: `scripts/_policy/policy_lib.py`
**Autoridade:** ✅ EXISTENTE  
**Path:** `scripts/_policy/policy_lib.py`

Responsabilidades:
- Parse SSOT (YAML)
- Enumerar scripts versionados (`git ls-files -z`)
- Aplicar regras R0-R9
- Retornar lista de erros (código estável)

**Exit codes:**
- 0 = PASS
- 2 = FAIL (violação)
- 3 = HARNESS ERROR

---

### 3.4 Gate Principal: `scripts/_policy/check_scripts_policy.ps1`
**Autoridade:** ✅ EXISTENTE  
**Path:** `scripts/_policy/check_scripts_policy.ps1`

Responsabilidades:
- Wrapper PowerShell para `policy_lib.py`
- Validar pré-requisitos (Python, venv, SSOT)
- Retornar exit code estável
- Formatear output para CI

**Invocação:**
```powershell
cd "C:\HB TRACK"
& scripts\_policy\check_scripts_policy.ps1
```

---

## 4. VALIDAÇÃO E CRITÉRIOS DE SUCESSO

### 4.1 Sentinelas de Teste (Validação Determinística)

Criar 6 arquivos de teste e validar saída idêntica em múltiplas execuções:

1. **PASS — Check correto e read-only**
   ```python
   # scripts/checks/openapi/check_contract_TEST.py
   # HB_SCRIPT_KIND: checks
   # HB_SCRIPT_SCOPE: openapi
   # HB_SCRIPT_SIDE_EFFECTS: NONE
   # ... (resto do header)
   
   import json
   def validate(): pass  # read-only
   ```
   **Esperado:** PASS (0)

2. **PASS — Wrapper que roda pytest**
   ```powershell
   # scripts/run/run_tests_TEST.ps1
   # HB_SCRIPT_KIND: run
   # HB_SCRIPT_SIDE_EFFECTS: PROC_EXEC
   # ...
   
   pytest tests/
   ```
   **Esperado:** PASS (0)

3. **FAIL — Check com pytest (forbidden invoke)**
   ```python
   # scripts/checks/check_tests_TEST.py
   # HB_SCRIPT_KIND: checks
   # HB_SCRIPT_SIDE_EFFECTS: NONE
   # ...
   
   import subprocess
   subprocess.run(["pytest", "tests/"])
   ```
   **Esperado:** FAIL (2) `CHECKS-E_FORBIDDEN_INVOKE: pytest`

4. **FAIL — Check com side-effect (FS_WRITE)**
   ```powershell
   # scripts/checks/check_log_TEST.ps1
   # HB_SCRIPT_KIND: checks
   # HB_SCRIPT_SIDE_EFFECTS: NONE
   # ...
   
   "log" | Out-File debug.log
   ```
   **Esperado:** FAIL (2) `CHECKS-E_SIDE_EFFECT_DETECTED: FS_WRITE`

5. **FAIL — Arquivo versionado em temp/**
   ```
   scripts/temp/orphan_script_TEST.py
   ```
   **Esperado:** FAIL (2) `TEMP-E_VERSIONED_FILE`

6. **FAIL — Kind/Path mismatch**
   ```python
   # scripts/checks/check_auth_TEST.py
   # HB_SCRIPT_KIND: run  # ❌ errado
   # ...
   ```
   **Esperado:** FAIL (2) `POLICY-E_KIND_PATH_MISMATCH`

### 4.2 Determinismo Cross-Platform

Rodar gate 3x no mesmo commit:
- Windows PowerShell 5.1
- Windows PowerShell 7+
- Linux bash (com intérprete py3.11+)

**Critério:** Output idêntico (diff = 0) em todas as execuções.

---

## 5. IMPACTO E RISCOS

### 5.1 Impacto Positivo
- ✅ Governança determinística (sem falsos positivos em CI)
- ✅ Agentes de IA podem validar script ANTES de PR
- ✅ Exit codes fixos (0/2/3) para integração CI/CD
- ✅ Auditoria automática de side-effects

### 5.2 Riscos Mitigados
- ⚠️ Scripts existentes violando policy → Criar `fixes/fix_scripts_headers.py` (semi-automático)
- ⚠️ Heurísticas com falso positivo → Filtro de comentários (R6.2) + bordas de palavra (R7.2)
- ⚠️ Diferenças Windows/Linux → `git ls-files -z` + normalização `/` (R1.1)

### 5.3 Plano de Rollout
1. **Fase 1 (atual):** Gate em modo "report-only" (não bloqueia CI)
2. **Fase 2 (1 sprint):** Corrigir violações existentes com `fixes/`
3. **Fase 3 (após cleanup):** Enforçar em CI (bloqueia merge se exit ≠ 0)

---

## 6. PRÓXIMOS PASSOS

### 6.1 Tarefas Imediatas (este ARCH_REQUEST)
- [x] Formalizar regras existentes
- [x] Corrigir `git ls-files` para `-z` portável
- [x] Adicionar R2.0 (meta-dirs)
- [x] Adicionar filtro de comentários (R6.2, R7.3)
- [x] Adicionar R1.3 (POLICY-E_UNTAGGED_SCRIPT)
- [x] Adicionar R12 (Layout repo-wide)
- [ ] Implementar correções em policy_lib.py (ver ADDENDUM)
- [ ] Validar sentinelas de teste (seção 4.1)
- [ ] Documentar em `scripts/README.md` (derivado deste ARCH_REQUEST)

### 6.2 Tarefas Futuras (outros ARCH_REQUEST/EXEC_TASK)
- [ ] Criar `fixes/fix_scripts_headers.py` (correção semi-automática)
- [ ] Criar `docs/scripts/MIGRATION_GUIDE.md` (exemplos before/after)
- [ ] Criar `scripts/checks/layout/check_python_layout.py` (R12)
- [ ] Rodar gate em CI Linux (validar determinismo cross-platform)
- [ ] Integrar gates em pre-commit hooks (opcional)

---

## 7. AUTORIDADE E REFERÊNCIAS

### 7.1 Documentos Canônicos
- `docs/_canon/ARCH_REQUEST_GENERATION_PROTOCOL.md` (protocolo de geração)
- `docs/_canon/03_WORKFLOWS.md` (workflows operacionais)
- `docs/_canon/08_APPROVED_COMMANDS.md` (comandos aprovados)

### 7.2 Implementação Atual
- `scripts/_policy/scripts.policy.yaml` (SSOT)
- `scripts/_policy/side_effects_heuristics.yaml` (heurísticas)
- `scripts/_policy/policy_lib.py` (engine)
- `scripts/_policy/check_scripts_policy.ps1` (gate)

### 7.3 Histórico de Revisões
| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0.0  | 2026-02-14 | Draft inicial (gerado por agent) |
| 1.0.0-Acceptable | 2026-02-14 | Correções críticas: meta-dirs, git ls-files -z, filtro comentários |

---

**FIM DO ARCH_REQUEST v1.0.0-Acceptable**

---

## ANEXO A — Comparação Draft vs Acceptable

### Mudanças Críticas

| Item | v1.0.0 (draft) | v1.0.0-Acceptable |
|------|----------------|-------------------|
| **Meta-dirs** | Não mencionado | R2.0: `_policy` e `_lib` excluídos de R3-R9 |
| **Git scope** | `git ls-files 'scripts/**'` (frágil) | `git ls-files -z -- scripts` (portável) |
| **SSOT naming** | `scripts_policy.yaml` (genérico) | `scripts/_policy/scripts.policy.yaml` (existente) |
| **Gate location** | `scripts/checks/check_scripts_policy.py` | Engine: `_policy/policy_lib.py` + Wrapper: `_policy/check_scripts_policy.ps1` |
| **Comentários** | Não tratado | R6.2, R7.3: filtro explícito de comentários |
| **Status** | Especulativo | Formalização do existente ✅ |

### Impacto das Mudanças

1. **R2.0 (meta-dirs):** Elimina falso positivo "categoria inválida" para `_policy` e `_lib`
2. **R1.1 (git -z):** Garante determinismo Windows/Linux (encoding, espaços)
3. **R6.2/R7.3 (comentários):** Reduz falso positivo de heurísticas (exemplos em docstrings)
4. **SSOT naming:** Remove ambiguidade sobre qual arquivo é autoridade

---

## ANEXO B — Template de Script Conforme

```python
#!/usr/bin/env python3
# HB_SCRIPT_KIND: checks
# HB_SCRIPT_SCOPE: openapi
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: scripts/checks/openapi/check_contract.py
# HB_SCRIPT_OUTPUTS: stdout
# HB_SCRIPT_EXIT_CODES: 0=PASS, 2=FAIL, 3=ERROR

"""
OpenAPI Contract Validator (Read-Only)

Validates openapi.json against HB Track contract rules.
Does NOT modify any files or execute external processes.

Usage:
    Invoke via policy gate or directly from repo root.
"""

import json
import sys
from pathlib import Path

def main():
    # Read-only validation logic
    schema_path = Path("docs/_generated/openapi.json")
    if not schema_path.exists():
        print("ERROR: openapi.json not found")
        sys.exit(3)
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    # ... validation logic (no side-effects) ...
    
    print("PASS: OpenAPI contract valid")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

```powershell
#Requires -Version 5.1
# HB_SCRIPT_KIND: run
# HB_SCRIPT_SCOPE: testing
# HB_SCRIPT_SIDE_EFFECTS: PROC_EXEC
# HB_SCRIPT_IDEMPOTENT: false
# HB_SCRIPT_ENTRYPOINT: scripts/run/run_tests.ps1
# HB_SCRIPT_OUTPUTS: stdout
# HB_SCRIPT_EXIT_CODES: pytest exit codes

<#
.SYNOPSIS
    Test Runner Wrapper
.DESCRIPTION
    Orchestrates pytest execution with proper environment setup.
    This is a WRAPPER (not a check), so PROC_EXEC is allowed.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Setup environment
Push-Location "$PSScriptRoot\..\..\Hb Track - Backend"

try {
    # Wrapper can execute external processes
    & "venv\Scripts\python.exe" -m pytest tests/
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
```

---

**APROVAÇÃO:**
- [ ] Agente IA
- [ ] Revisor Humano
- [ ] CI (sentinelas de teste)


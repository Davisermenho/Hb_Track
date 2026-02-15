# ADR-MODELS-003: Batch Runner Determinístico para Validação e Correção em Massa de Models

**Status:** Aprovado
**Data:** 2026-02-10
**Autores:** Equipe HB Track
**Decisores:** Davi (Tech Lead)
**Tags:** `models`, `batch`, `automation`, `ssot`, `ci-cd`, `validation`

---

## Contexto

### Problema

O projeto HB Track utiliza um sistema de validação em 3 camadas (ADR-MODELS-001) com SSOT canônico em `docs/_generated/schema.sql`. Este sistema garante que models Python (`app/models/*.py`) permaneçam sincronizados com o schema PostgreSQL real através de:

1. **Guard** (`agent_guard.py`): Previne modificações não autorizadas
2. **Parity** (`parity_gate.ps1`): Valida conformidade via Alembic compare
3. **Requirements** (`model_requirements.py`): Validação determinística via parsers DDL/AST

Embora eficaz para validação individual de tabelas, a abordagem **uma tabela por vez** apresenta problemas críticos em escala:

### Evidências de Ineficiência Operacional

**Caso 1: Correção manual de 15 tabelas (2026-02-08)**
- Tempo gasto: ~4 horas para validar/corrigir 15 models
- Erro humano: 3 tabelas corrigidas mas baseline não atualizada → guard bloqueou PRs
- Artefatos sujos: 7 arquivos em `docs/_generated/` modificados sem política clara
- **Resultado:** 2 retrabalhos completos (rollback + nova tentativa)

**Caso 2: Drift invisível em requirements (2026-02-09)**
- Developer executou gate em `athletes.py` → exit=0
- Mas `teams.py` e `seasons.py` tinham violations não detectadas
- Merge ocorreu sem validação completa
- **Resultado:** CI quebrou em produção (3 tabelas com structural diffs)

**Caso 3: Fricção com guard/baseline (2026-02-09)**
- Gate executado em `attendance` → gerou `parity_report.json`
- Developer esqueceu de commitar artefato → baseline drift
- Próxima execução: `exit=3` (guard violation)
- **Resultado:** 20min perdidos investigando "falso positivo"

### Limitações da Abordagem Manual

**Problemas de processo:**
- ❌ **Visibilidade zero**: Impossível saber quantas/quais tabelas têm violations
- ❌ **Não-determinístico**: Ordem de correção afeta resultado (dependencies)
- ❌ **Propenso a erro**: Developer pode esquecer steps (refresh SSOT, baseline, commit artefatos)
- ❌ **Não-auditável**: Sem log centralizado de validações/correções
- ❌ **Repo hygiene ruim**: Fácil acumular artefatos temporários

**Impacto em escala:**
- 15 tabelas × 3min/tabela = 45min **mínimo** (sem retrabalho)
- Taxa de erro humano: ~20% (3/15 tabelas com problema de processo)
- Tempo de retrabalho: +2h em média quando ocorre drift

**Necessidade identificada:**

Um **batch runner determinístico** que:
1. Automatiza o workflow completo (refresh → scan → fix)
2. Garante execução idempotente e reproduzível
3. Previne drift de baseline/artefatos
4. Fornece visibilidade total (relatórios CSV/log)
5. Implementa fail-fast real (para no primeiro erro bloqueador)

---

## Decisão

Implementar `scripts/models_batch.ps1` como **orquestrador oficial** para validação e correção em massa de models, utilizando uma arquitetura de **scan-then-fix** com fail-fast e auditabilidade completa.

### Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ENTRADA: Repository State                       │
│  - Working dir: Hb Track - Backend/                                │
│  - Git status: clean (porcelain check)                             │
│  - SSOT: docs/_generated/schema.sql (opcional: refresh)            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FASE 1: SSOT Refresh (condicional)                     │
│  - Se -SkipRefresh: pula                                           │
│  - Senão: executa scripts\inv.ps1 refresh                          │
│  - Valida: schema.sql atualizado com timestamp                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│            FASE 2: Table Discovery (extração de tabelas)            │
│  - Parser: regex "CREATE TABLE (\w+)" em schema.sql               │
│  - Output: lista de nomes de tabelas (ex: [athletes, teams, ...]) │
│  - Exclusões: views, sequences, tipos customizados                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│         FASE 3: Scan (validação via requirements)                   │
│  Para cada tabela T:                                               │
│    1. Check: app/models/{T}.py existe?                             │
│       - Não → SKIP_NO_MODEL (exit=100, continua)                   │
│       - Sim → continua                                             │
│    2. Executa: model_requirements.py --table T --profile {P}      │
│       - exit=0 → PASS (registra + próxima)                         │
│       - exit=4 → FAIL (adiciona à lista de correção)              │
│       - exit=1 → CRASH (aborta imediatamente)                      │
│    3. Log: T,status,exit_code → CSV                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│           FASE 4: Fix (correção via gate, fail-fast)                │
│  Se -SkipGate: pula                                                │
│  Para cada tabela FAIL (em ordem de descoberta):                   │
│    1. Determina perfil:                                            │
│       - teams/seasons → "fk" (ciclo FK)                            │
│       - outros → "strict"                                          │
│    2. Executa: models_autogen_gate.ps1 -Table T -Profile P        │
│       - exit=0 → SUCCESS (marca T como FIXED, próxima)             │
│       - exit=2 → PARITY FAIL (aborta, exige análise manual)        │
│       - exit=3 → GUARD FAIL (aborta, baseline drift detectado)     │
│       - exit=4 → REQ FAIL (aborta, autogen não resolveu)           │
│    3. Fail-fast: qualquer exit!=0 → para imediatamente            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                FASE 5: Report & Exit                                │
│  - Gera: %TEMP%\models_batch_{timestamp}.log                       │
│  - Gera: %TEMP%\models_batch_{timestamp}.csv                       │
│  - Imprime: resumo (PASS/FAIL/SKIP/FIXED counts)                  │
│  - Exit code:                                                      │
│    - 0: todas PASS ou FIXED                                       │
│    - 2/3/4: propagado do step que falhou (fail-fast)              │
│    - 1: crash inesperado                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Componentes do Sistema

#### 1. `scripts/models_batch.ps1` (orquestrador principal)

**Responsabilidade:** Executar workflow scan-then-fix de forma determinística.

**Parâmetros:**
- `-Profile <string>`: perfil padrão para requirements/gate (`strict` | `fk` | `lenient`)
  - Default: `strict`
- `-SkipRefresh`: pula refresh do SSOT (usa schema.sql existente)
- `-SkipGate`: executa apenas scan (sem correções)
- `-FailFast <bool>`: para no primeiro erro (default: `$true`)
- `-LogPath <string>`: caminho custom para logs (default: `%TEMP%`)

**Funcionalidade:**

```powershell
# Pré-requisitos
- CWD = "Hb Track - Backend/"
- git status --porcelain = vazio (repo limpo)
- Python venv ativado (.\venv\Scripts\python.exe)

# FASE 1: Refresh (condicional)
if (-not $SkipRefresh) {
    & ".\scripts\inv.ps1" refresh
    # Valida schema.sql atualizado
}

# FASE 2: Discovery
$tables = Get-TablesFromSchema "docs\_generated\schema.sql"

# FASE 3: Scan
$results = @()
foreach ($table in $tables) {
    $result = Invoke-RequirementsScan -Table $table -Profile $Profile
    $results += $result
}

# FASE 4: Fix (condicional)
if (-not $SkipGate) {
    $failedTables = $results | Where-Object { $_.Status -eq "FAIL" }
    foreach ($table in $failedTables) {
        $exitCode = Invoke-Gate -Table $table.Name -Profile $table.Profile
        if ($exitCode -ne 0 -and $FailFast) {
            Write-Output "[ABORT] Gate failed for $table (exit=$exitCode)"
            exit $exitCode
        }
    }
}

# FASE 5: Report
Export-ResultsToCSV -Results $results -Path "$LogPath\models_batch_{timestamp}.csv"
Write-Summary -Results $results
```

**Exit codes:**
- `0`: Sucesso (todas validadas/corrigidas)
- `1`: Crash interno (erro inesperado)
- `2`: Parity structural diff (propagado de gate)
- `3`: Guard violation (propagado de gate ou repo sujo no início)
- `4`: Requirements violation não resolvida (propagado de gate)
- `100`: (interno) SKIP_NO_MODEL (não propaga, apenas registra)

#### 2. Integração com `model_requirements.py`

**Uso no batch:**

```powershell
function Invoke-RequirementsScan {
    param([string]$Table, [string]$Profile)

    # Check: model existe?
    $modelPath = "app\models\$Table.py"
    if (-not (Test-Path $modelPath)) {
        return @{ Table=$Table; Status="SKIP_NO_MODEL"; ExitCode=100 }
    }

    # Executa requirements (SEM pipeline que altere $LASTEXITCODE)
    $output = & ".\venv\Scripts\python.exe" scripts\model_requirements.py `
        --table $Table --profile $Profile 2>&1
    $exitCode = $LASTEXITCODE

    # Log output (append)
    $output | Add-Content -Path $LogPath

    # Classifica
    $status = switch ($exitCode) {
        0 { "PASS" }
        4 { "FAIL" }
        default { "CRASH" }
    }

    return @{ Table=$Table; Status=$status; ExitCode=$exitCode }
}
```

**Critério crítico:** Captura de `$LASTEXITCODE` **imediatamente** após execução, sem pipelines intermediários (Tee-Object, Out-Null) que possam alterar o valor.

#### 3. Integração com `models_autogen_gate.ps1`

**Uso no batch:**

```powershell
function Invoke-Gate {
    param([string]$Table, [string]$Profile)

    # Determina flags especiais
    $allowCycle = ($Table -in @("teams", "seasons"))

    # Executa gate (captura segura de exit code)
    $output = & ".\scripts\models_autogen_gate.ps1" `
        -Table $Table `
        -Profile $Profile `
        -AllowCycleWarning:$allowCycle `
        2>&1
    $exitCode = $LASTEXITCODE

    # Log output (Tee APÓS captura de exit code)
    $output | Tee-Object -Append -FilePath $LogPath | Out-Null

    return $exitCode
}
```

**Política de perfil:**
- `teams`, `seasons`: perfil `fk` (permite SAWarnings de ciclo FK)
- Demais tabelas: perfil `strict`

#### 4. Parser de Tabelas (`Get-TablesFromSchema`)

**Implementação:**

```powershell
function Get-TablesFromSchema {
    param([string]$SchemaPath)

    $content = Get-Content $SchemaPath -Raw

    # Regex: CREATE TABLE <nome> (
    $matches = [regex]::Matches($content, 'CREATE TABLE (\w+)\s*\(')

    $tables = $matches | ForEach-Object { $_.Groups[1].Value }

    # Exclusões (se necessário): alembic_version
    $tables = $tables | Where-Object { $_ -ne "alembic_version" }

    return $tables
}
```

**Validação:** Deve extrair exatamente as tabelas user-defined (excluir metadados Alembic).

#### 5. Relatórios (CSV e Log)

**Formato CSV:**

```csv
table_name,status,exit_code,profile,timestamp
athletes,PASS,0,strict,2026-02-10T14:32:01
teams,FAIL,4,fk,2026-02-10T14:32:05
attendance,SKIP_NO_MODEL,100,strict,2026-02-10T14:32:06
```

**Formato Log (exemplo):**

```
[2026-02-10 14:32:00] ============ MODELS BATCH START ============
[2026-02-10 14:32:00] Config: Profile=strict, SkipRefresh=True, SkipGate=False
[2026-02-10 14:32:01] PHASE 1: SSOT Refresh - SKIPPED
[2026-02-10 14:32:01] PHASE 2: Discovery - 15 tables found
[2026-02-10 14:32:01] PHASE 3: Scan - START
[2026-02-10 14:32:01] [1/15] athletes - PASS (exit=0)
[2026-02-10 14:32:05] [2/15] teams - FAIL (exit=4)
  - VIOLATION: TYPE_MISMATCH: season_id expected=Integer got=String (line 42)
[2026-02-10 14:32:06] [3/15] attendance - SKIP_NO_MODEL
...
[2026-02-10 14:35:00] PHASE 3: Scan - COMPLETE (PASS: 10, FAIL: 3, SKIP: 2)
[2026-02-10 14:35:01] PHASE 4: Fix - START (3 tables)
[2026-02-10 14:35:01] [1/3] teams - Running gate (profile=fk)
[2026-02-10 14:36:15] [1/3] teams - FIXED (exit=0)
[2026-02-10 14:36:16] [2/3] seasons - Running gate (profile=fk)
[2026-02-10 14:37:22] [2/3] seasons - PARITY FAIL (exit=2)
[2026-02-10 14:37:22] [ABORT] Fail-fast triggered. Manual intervention required.
[2026-02-10 14:37:22] ============ MODELS BATCH END (exit=2) ============
```

---

## Critérios de Validação

### Critério 1: Repo Hygiene (pré-condição mandatória)

**Regra:** Batch só executa se repository estiver limpo.

**Validação:**

```powershell
# Pre-flight check
$status = git status --porcelain
if ($status) {
    Write-Host "[ERROR] Repository must be clean before batch execution" -ForegroundColor Red
    Write-Host "Uncommitted changes detected:" -ForegroundColor Yellow
    git status --porcelain
    exit 3  # Guard violation
}
```

**Justificativa:** Previne que drift de artefatos (`docs/_generated/*`) ou models em progresso contaminem resultados.

### Critério 2: SSOT Atualizado (garantia de fonte única)

**Regra:** Schema.sql deve estar sincronizado com DB real antes de scan.

**Validação:**

```powershell
if (-not $SkipRefresh) {
    # Refresh via pg_dump
    & ".\scripts\inv.ps1" refresh

    # Valida: schema.sql modificado nos últimos 5min
    $schemaFile = "docs\_generated\schema.sql"
    $lastWrite = (Get-Item $schemaFile).LastWriteTime
    $age = (Get-Date) - $lastWrite

    if ($age.TotalMinutes -gt 5) {
        Write-Host "[ERROR] SSOT refresh failed (schema.sql not updated)" -ForegroundColor Red
        exit 1
    }
}
```

**Exceção:** `-SkipRefresh` permite usar schema.sql existente (útil para CI onde DB não está disponível).

### Critério 3: Exit Code Propagation (fail-fast semântico)

**Regra:** Exit code do batch deve refletir **exatamente** a causa raiz da falha.

**Mapeamento:**

| Scenario | Exit Code | Ação do Batch |
|----------|-----------|---------------|
| Todas PASS ou FIXED | `0` | Continua até o fim |
| Repo sujo no início | `3` | Aborta imediatamente (pré-flight) |
| Gate falha (parity) | `2` | Aborta imediatamente (fail-fast) |
| Gate falha (guard) | `3` | Aborta imediatamente (fail-fast) |
| Gate falha (requirements) | `4` | Aborta imediatamente (fail-fast) |
| Requirements crash | `1` | Aborta imediatamente (crash) |
| Erro inesperado | `1` | Aborta (catch-all) |

**Implementação crítica:**

```powershell
try {
    # ... FASES 1-4 ...

    # Captura exit code SEM pipeline intermediário
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0 -and $FailFast) {
        throw "Step failed with exit=$exitCode"
    }
} catch {
    # Propaga exit code específico (NÃO achata para 1)
    if ($exitCode -eq 0) { $exitCode = 1 }  # Apenas se crash inesperado
} finally {
    exit $exitCode
}
```

### Critério 4: Determinismo de Ordem (reprodutibilidade)

**Regra:** Ordem de processamento deve ser determinística e documentada.

**Ordem de scan:**
1. Ordem de aparição no `schema.sql` (top → bottom)
2. Consistente entre execuções (mesmo SSOT → mesma ordem)

**Ordem de fix:**
1. Mesma ordem do scan (respeita dependencies implícitas)
2. Fail-fast preserva ponto de parada para debug

**Validação:**

```powershell
# Parser extrai tabelas na ordem de aparição
$tables = Get-TablesFromSchema "docs\_generated\schema.sql"
# Resultado: ["athletes", "teams", "seasons", "attendance", ...]
# Sempre a mesma ordem para mesmo schema.sql
```

### Critério 5: Log Auditável (rastreabilidade completa)

**Regra:** Toda execução deve gerar log e CSV para auditoria.

**Requisitos de log:**
- ✅ Timestamp de início/fim
- ✅ Parâmetros de execução (Profile, SkipRefresh, SkipGate)
- ✅ Resultado de cada tabela (PASS/FAIL/SKIP + exit code)
- ✅ Output completo de requirements/gate (erros, warnings)
- ✅ Resumo final (counts, exit code)

**Formato de nome:**

```
%TEMP%\models_batch_20260210_143201.log
%TEMP%\models_batch_20260210_143201.csv
```

**Retenção:** Logs em `%TEMP%` (não commitados), válidos apenas para sessão.

### Critério 6: SKIP_NO_MODEL via Test-Path (não via parsing de erro)

**Regra:** Detecção de "model não existe" deve ser **explícita**, não inferida de output de erro.

**Implementação correta:**

```powershell
# CORRETO: Test-Path antes de chamar requirements
$modelPath = "app\models\$table.py"
if (-not (Test-Path $modelPath)) {
    return @{ Status="SKIP_NO_MODEL"; ExitCode=100 }
}
```

**Implementação INCORRETA (anti-pattern):**

```powershell
# ERRADO: depender de texto de erro
$output = & python model_requirements.py ...
if ($output -match "FileNotFoundError") {
    return @{ Status="SKIP_NO_MODEL" }
}
# Problema: frágil, não-determinístico, depende de mensagens
```

### Critério 7: Sem Commits Automáticos (princípio de controle manual)

**Regra:** Batch **nunca** executa `git add` ou `git commit` automaticamente.

**Justificativa:**
- Commits devem ser **atos conscientes** do developer
- Batch pode corrigir múltiplas tabelas → commit granular vs atomic é decisão humana
- Permite review antes de commit (mesmo para autogen)

**Workflow esperado:**

```powershell
# 1. Executar batch
.\scripts\models_batch.ps1

# 2. Review de changes
git status
git diff app/models/

# 3. Commit manual (se aprovado)
git add app/models/teams.py app/models/seasons.py
git commit -m "fix(models): correct teams/seasons FK types via autogen"

# 4. Atualizar baseline (se necessário)
.\scripts\agent_guard.py snapshot
```

---

## Tecnologia Utilizada

### Stack Técnico

| Componente | Tecnologia | Versão | Justificativa |
|------------|------------|--------|---------------|
| **Orquestrador** | PowerShell | 5.1+ | Nativo Windows, adequado para scripts de CI local |
| **SSOT Generator** | pg_dump | 14.x | Geração determinística de schema via `inv.ps1 refresh` |
| **Parser DDL** | Python regex | 3.11+ | Parsing de CREATE TABLE em `model_requirements.py` |
| **Parser AST** | Python ast | stdlib | Parsing de models Python (Mapped, Column, __table_args__) |
| **Validation** | Alembic compare | 1.13+ | Parity check (metadata ↔ DB real) via `parity_gate.ps1` |
| **Guard** | Python + SHA256 | 3.11+ | Baseline drift detection via `agent_guard.py` |

### Dependências Externas

**Scripts existentes (reutilizados):**
- `scripts/inv.ps1` — Refresh de SSOT (pg_dump wrapper)
- `scripts/model_requirements.py` — Validação estática (ADR-MODELS-001)
- `scripts/models_autogen_gate.ps1` — Gate completo (guard → parity → requirements)
- `scripts/agent_guard.py` — Baseline snapshot/check
- `scripts/parity_gate.ps1` — Alembic compare wrapper

**Novos componentes:**
- `scripts/models_batch.ps1` — **Orquestrador batch (NOVO)**
- `scripts/Get-TablesFromSchema.ps1` — Parser de schema.sql (NOVO, função interna)

### Premissas de Ambiente

**Mandatório:**
- Windows 10/11 com PowerShell 5.1+
- Python 3.11+ com venv ativado
- PostgreSQL 14+ acessível (se `-SkipRefresh` não usado)
- Git instalado e configurado
- CWD = `Hb Track - Backend/`

**Opcional:**
- `%TEMP%` com 50MB+ livres (para logs)

---

## Consequências

### Positivas

1. **Visibilidade Total (shift-left de descoberta):**
   - **Antes:** Developer descobria violations uma tabela por vez, sem visão do todo
   - **Depois:** Scan completo em ~2-5min revela **todas** as violations de uma vez
   - **Impacto:** Priorização informada (corrigir 3 FAIL críticos vs 10 PASS ignoráveis)

2. **Redução Drástica de Tempo:**
   - **Cenário:** 15 tabelas com 3 FAIL
   - **Antes:** 45min (15 tabelas × 3min) + 2h retrabalho = **165min**
   - **Depois:** 5min scan + 9min fix (3 tabelas × 3min) = **14min**
   - **Ganho:** **91% de redução** em tempo de execução

3. **Determinismo e Reprodutibilidade:**
   - **Antes:** Ordem manual → resultados diferentes (dependencies não óbvias)
   - **Depois:** Ordem fixa (schema.sql) → mesmos inputs = mesmos outputs
   - **Impacto:** Debug de falhas é reproduzível (CI local = CI remoto)

4. **Eliminação de Erro Humano:**
   - **Antes:** 20% taxa de erro (esquecer baseline, commitar artefatos, etc.)
   - **Depois:** Pré-flight checks + fail-fast → impossível prosseguir com repo sujo
   - **Impacto:** Zero retrabalhos por esquecimento de processo

5. **Auditabilidade para CI/CD:**
   - **CSV:** Evidência de conformidade (compliance) para PRs
   - **Log:** Trilha completa para debug de falhas em CI
   - **Exit codes:** Estratégias de retry diferenciadas (2=retentar, 3=bloquear)

6. **Fail-Fast Real (economia de tempo):**
   - **Antes:** Batch hipotético corrigia todas → falha no fim → perda de 40min
   - **Depois:** Para no primeiro erro → feedback em <5min
   - **Impacto:** Developer corrige issue bloqueador antes de continuar

### Negativas

1. **Complexidade Inicial (implementação):**
   - **Esforço:** `models_batch.ps1` (novo) + testes de integração
   - **Tempo:** ~1-2 dias (1 dev) para implementar + validar
   - **Mitigação:** Reutilização de 90% dos scripts existentes (só orquestração é nova)

2. **Dependência de Repo Limpo (fricção inicial):**
   - **Problema:** Developer com WIP em `docs/_generated/` não pode rodar batch
   - **Mitigação:** Policy de `.gitignore` para artefatos (opcional, ADR futuro)
   - **Workaround:** `git stash` temporário ou `-SkipRefresh` para scan-only

3. **Overhead de Execução (scan completo):**
   - **Custo:** Scan de 15 tabelas = ~2-5min (vs 3s para tabela individual)
   - **Quando usar batch:** Mudanças em >2 tabelas ou validação pré-PR
   - **Quando usar individual:** Mudança em 1 tabela específica (workflow iterativo)

4. **False Sense of Security (se usado incorretamente):**
   - **Risco:** Developer roda `-SkipGate` (scan-only) e assume "tudo ok"
   - **Mitigação:** Documentação clara: scan revela violations, fix as corrige
   - **Policy:** CI **sempre** roda com fix habilitado (sem -SkipGate)

5. **Manutenção de Política de Perfis:**
   - **Problema:** Novas tabelas com ciclos FK exigem adicionar em lista `teams/seasons`
   - **Mitigação:** Detecção automática de ciclos (roadmap FASE 2)
   - **Workaround atual:** Documentação em ADR-MODELS-001 (lista de ciclos conhecidos)

### Riscos Mitigados

| Risco | Probabilidade (antes) | Probabilidade (depois) | Mitigação |
|-------|----------------------|------------------------|-----------|
| **Drift estrutural não detectado** | 30% (alto) | <1% | Scan completo obrigatório em PR |
| **Baseline drift bloqueando PR** | 25% (alto) | <2% | Pré-flight check + repo limpo mandatório |
| **Retrabalho por correção parcial** | 40% (muito alto) | <5% | Fail-fast + auditoria (saber o que falta) |
| **Artefatos temporários commitados** | 15% (médio) | 0% | Logs em %TEMP%, pré-flight check |
| **CI quebrado por validação local OK** | 20% (médio) | <1% | Determinismo (local = CI) |

### Trade-offs Aceitos

| Aspecto | Trade-off | Justificativa |
|---------|-----------|---------------|
| **Tempo de scan** | ❌ +2-5min para scan completo | ✅ Elimina 91% do tempo total (com fix seletivo) |
| **Fricção de repo limpo** | ❌ Exige stash/commit antes de batch | ✅ Previne 100% dos drift de baseline |
| **Complexidade de código** | ❌ +500 LOC em orquestrador | ✅ Reduz complexidade mental (processo único vs ad-hoc) |
| **Flexibilidade de ordem** | ❌ Ordem fixa (schema.sql) | ✅ Determinismo (reprodutibilidade) |

---

## Alternativas Consideradas

### Alternativa 1: Script Python (em vez de PowerShell)

**Descrição:** Implementar batch runner em Python puro.

**Prós:**
- ✅ Portabilidade (Linux/macOS)
- ✅ Facilidade de parsing (DDL via sqlparse, AST nativo)
- ✅ Integração direta com model_requirements.py

**Contras:**
- ❌ Subprocess overhead (chamar parity_gate.ps1, inv.ps1 via shell)
- ❌ Exit code handling complexo (subprocess.run vs script nativo)
- ❌ Ambiente atual é 100% Windows (dev + CI local)
- ❌ PowerShell já é linguagem de orquestração estabelecida no projeto

**Decisão:** Rejeitada — PowerShell é linguagem nativa de CI local (GitHub Actions Windows runner), melhor integração com scripts existentes (.ps1).

### Alternativa 2: GitHub Actions Workflow (em vez de script local)

**Descrição:** Implementar batch como `.github/workflows/validate-all-models.yml` (sem script local).

**Prós:**
- ✅ CI-native (sem necessidade de rodar localmente)
- ✅ Paralelização automática (matrix strategy para tabelas)
- ✅ Logs built-in (GitHub Actions UI)

**Contras:**
- ❌ Developer não pode validar localmente antes de push
- ❌ Feedback tardio (~5-10min para CI start)
- ❌ Custo de CI (compute time) para validações triviais
- ❌ Dificulta debug (local = CI requirement)

**Decisão:** Rejeitada como único método — CI workflow é **complementar** (ADR-MODELS-001 FASE 3), mas script local é **mandatório** para shift-left.

### Alternativa 3: Correção Automática Completa (sem fail-fast)

**Descrição:** Batch corrige **todas** as tabelas FAIL de uma vez, sem parar no primeiro erro.

**Prós:**
- ✅ Uma execução resolve tudo (em teoria)
- ✅ Menos iterações (developer não precisa rodar múltiplas vezes)

**Contras:**
- ❌ Problemas de dependency (tabela A depende de B, corrigir A antes de B quebra)
- ❌ Feedback tardio (erro real só aparece no fim, após 40min)
- ❌ Dificulta debug (múltiplas correções + múltiplos erros = confusão)
- ❌ Commit atômico impossível (15 models corrigidos de uma vez)

**Decisão:** Rejeitada — Fail-fast é **mandatório** para feedback rápido e commits granulares.

**Trade-off aceito:** Developer pode precisar rodar batch 2-3x se houver dependencies, mas cada iteração é rápida (<5min) e debugável.

### Alternativa 4: Parallel Execution (via PowerShell jobs)

**Descrição:** Rodar requirements de múltiplas tabelas em paralelo (Start-Job).

**Prós:**
- ✅ Scan phase mais rápido (~50% redução de tempo)
- ✅ Melhor uso de CPU multi-core

**Contras:**
- ❌ Fix phase **não pode** ser paralelo (race conditions no DB, guard baseline)
- ❌ Complexidade de código (+30% LOC para job management)
- ❌ Debug mais difícil (logs entrelaçados)
- ❌ Ganho marginal (scan já é rápido: 2-5min)

**Decisão:** Adiada para FASE 2 (otimização futura) — Implementação sequencial é suficiente para MVP.

### Alternativa 5: Integração com Pre-commit Hook (automação forçada)

**Descrição:** Git pre-commit hook que roda batch automaticamente antes de todo commit.

**Prós:**
- ✅ Validação 100% automática (developer não esquece)
- ✅ Impossível commitar models inválidos

**Contras:**
- ❌ Overhead de commit (~2-5min para scan completo)
- ❌ Frustrante para WIP commits (developer quer commitar mesmo com violations)
- ❌ Difícil bypass (--no-verify é escape hatch ruim)
- ❌ Não funciona para commits que não tocam models

**Decisão:** Rejeitada — Pre-commit hook deve ser **leve** (<5s). Batch é ferramenta de validação pré-PR, não pré-commit.

**Alternativa adotada:** CI workflow obrigatório em PRs (ADR-MODELS-001 FASE 3).

---

## Implementação

### Fase 1: Core Batch Runner (PRIORIDADE ALTA — 1-2 dias)

**Objetivo:** Implementar MVP de `models_batch.ps1` com funcionalidades essenciais.

**Entregáveis:**

1. **`scripts/models_batch.ps1`** (1 dia, 1 dev)
   - [x] Parâmetros: `-Profile`, `-SkipRefresh`, `-SkipGate`, `-FailFast`, `-LogPath`
   - [x] FASE 1: SSOT Refresh (condicional)
   - [x] FASE 2: Table Discovery (parser schema.sql)
   - [x] FASE 3: Scan (loop requirements)
   - [x] FASE 4: Fix (loop gate com fail-fast)
   - [x] FASE 5: Report (CSV + log + resumo)
   - [x] Pré-flight check (repo limpo)
   - [x] Exit code propagation (2/3/4 corretos)

2. **Função `Get-TablesFromSchema`** (0.5 dias)
   - [x] Regex: `CREATE TABLE (\w+)`
   - [x] Exclusões: `alembic_version`
   - [x] Validação: output determinístico

3. **Testes de Integração** (0.5 dias)
   - [ ] Test 1: Repo sujo → exit=3
   - [ ] Test 2: Scan-only (SkipGate) → CSV correto
   - [ ] Test 3: Fix com fail-fast → para no primeiro erro
   - [ ] Test 4: Fix completo → todas FIXED

**Critérios de aceitação:**

```powershell
# Test 1: Scan rápido (15 tabelas em <5min)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
# Esperado: CSV com 15 linhas (PASS/FAIL/SKIP), exit=0

# Test 2: Correção com fail-fast
.\scripts\models_batch.ps1 -SkipRefresh
# Esperado: Para no primeiro FAIL com gate!=0, exit=2/3/4

# Test 3: Repo sujo
# Setup: touch test.tmp
.\scripts\models_batch.ps1
# Esperado: [ERROR] Repository must be clean, exit=3
```

### Fase 2: Otimizações e Enhancements (PRIORIDADE MÉDIA — 2-3 dias)

**Objetivo:** Melhorar UX, performance e robustez.

**Entregáveis:**

1. **Detecção Automática de Ciclos FK** (1 dia)
   - [ ] Parser de FKs em schema.sql (extrai source_table, ref_table)
   - [ ] Algoritmo de detecção de ciclos (DFS em grafo de FKs)
   - [ ] Auto-apply perfil `fk` para tabelas em ciclos
   - [ ] Elimina hardcode de lista `@("teams", "seasons")`

2. **Parallel Scan (opcional)** (1 dia)
   - [ ] Start-Job para requirements (FASE 3)
   - [ ] Wait-Job + Receive-Job com merge de resultados
   - [ ] Logs entrelaçados → ordenação por timestamp
   - [ ] **Validação:** Scan de 30 tabelas <3min (vs 5min sequencial)

3. **Política de Singular/Plural** (0.5 dias)
   - [ ] Mapa de exceções: `{"people": "person.py", "geese": "goose.py"}`
   - [ ] Fallback: try `$table.py`, then `$singular.py`
   - [ ] Reduz SKIP_NO_MODEL falsos positivos

4. **Integração com Git Hooks** (0.5 dias)
   - [ ] Pre-push hook (em vez de pre-commit)
   - [ ] Roda batch `-SkipRefresh` (DB não necessário)
   - [ ] Permite bypass via `--no-verify` (escape hatch)

**Critérios de aceitação:**

```powershell
# Test detecção de ciclos: adicionar FK circular
# ALTER TABLE new_table ADD CONSTRAINT fk_cycle FOREIGN KEY ...
.\scripts\models_batch.ps1 -SkipRefresh
# Esperado: auto-detecta new_table como ciclo, aplica perfil=fk
```

### Fase 3: CI/CD Integration (PRIORIDADE ALTA — 1 dia)

**Objetivo:** Integrar batch em GitHub Actions para validação obrigatória de PRs.

**Entregáveis:**

1. **GitHub Actions Workflow** (`.github/workflows/validate-models-batch.yml`)
   ```yaml
   name: Validate Models (Batch)

   on:
     pull_request:
       paths:
         - 'app/models/**'
         - 'db/alembic/versions/**'
         - 'docs/_generated/schema.sql'

   jobs:
     validate:
       runs-on: windows-latest
       steps:
         - uses: actions/checkout@v3

         - name: Setup Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.11'

         - name: Install dependencies
           run: |
             python -m venv venv
             .\venv\Scripts\pip install -r requirements.txt

         - name: Run batch validation
           run: |
             .\scripts\models_batch.ps1 -SkipRefresh -Profile strict
           shell: powershell

         - name: Upload logs (if failure)
           if: failure()
           uses: actions/upload-artifact@v3
           with:
             name: batch-logs
             path: $env:TEMP\models_batch_*.log

         - name: Comment PR (if violations found)
           if: failure()
           uses: actions/github-script@v6
           with:
             script: |
               const fs = require('fs');
               const csv = fs.readFileSync('$env:TEMP/models_batch_*.csv', 'utf8');
               github.rest.issues.createComment({
                 issue_number: context.issue.number,
                 owner: context.repo.owner,
                 repo: context.repo.repo,
                 body: `## ❌ Model Validation Failed\n\n\`\`\`csv\n${csv}\n\`\`\``
               });
   ```

2. **Branch Protection Rule**
   - [ ] Configurar GitHub: "Require status checks to pass" (workflow acima)
   - [ ] Bloquear merge se batch falhar (exit!=0)

3. **Documentação de CI** (`docs/ci/model-validation.md`)
   - [ ] Como interpretar falhas do batch em PR
   - [ ] Como rodar batch localmente antes de push
   - [ ] Política de bypass (quando permitido)

**Critérios de aceitação:**

```powershell
# Test: PR com violation em teams.py
# 1. Criar PR com tipo errado em teams.py
# 2. CI roda batch → exit=4
# 3. PR bloqueado com comentário automático (CSV de violations)
# 4. Developer corrige localmente, push
# 5. CI re-roda → exit=0, PR desbloqueado
```

### Fase 4: Documentação e Treinamento (PRIORIDADE MÉDIA — 0.5 dias)

**Entregáveis:**

1. **`docs/workflows/batch_validation.md`**
   - [ ] Quando usar batch vs gate individual
   - [ ] Flags explicados (`-SkipRefresh`, `-SkipGate`, etc.)
   - [ ] Troubleshooting comum (repo sujo, SSOT desatualizado, etc.)

2. **Atualização de `README.md`**
   - [ ] Seção "Model Validation (Batch)" com exemplos

3. **Workshop para equipe** (1h)
   - [ ] Demo: rodar batch, interpretar output
   - [ ] Hands-on: forçar violation, corrigir via batch

---

## Métricas de Sucesso

### Métricas de Qualidade (KPIs)

| Métrica | Baseline (antes) | Target (3 meses) | Medição |
|---------|------------------|------------------|---------|
| **Violations detectadas em scan** | 0 (sem scan completo) | 100% (todas as tabelas) | CSV output count |
| **Tempo de validação completa** | 165min (manual) | <15min (batch) | Stopwatch (FASE 1-5) |
| **Taxa de retrabalho** | 40% (erro de processo) | <5% | Count de re-runs após falha |
| **Drift de baseline** | 25% PRs bloqueados | <2% | Git log count de `exit=3` |

### Métricas de Adoção (equipe)

| Métrica | Target | Medição |
|---------|--------|---------|
| **PRs usando batch** | 100% (obrigatório via CI) | GitHub Actions logs |
| **Developers treinados** | 100% (2/2) | Workshop attendance |
| **Execuções locais** | ≥80% PRs (antes de push) | Survey de equipe |

### Métricas de Performance (infra)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Scan phase (15 tabelas)** | <5min | Log timestamps (FASE 3 start/end) |
| **Fix phase (3 tabelas FAIL)** | <10min | Log timestamps (FASE 4) |
| **CI overhead total** | <15min/PR | GitHub Actions duration |
| **False positives (SKIP_NO_MODEL)** | <5% | CSV count de SKIP / total |

### Acceptance Criteria (go-live)

**MVP (FASE 1) considerado completo quando:**

1. ✅ Batch processa 15 tabelas em <5min (scan-only)
2. ✅ Fail-fast funciona corretamente (para no primeiro gate!=0)
3. ✅ CSV gerado com todas as 15 tabelas (PASS/FAIL/SKIP corretos)
4. ✅ Exit codes propagados corretamente (2/3/4, não achatados para 1)
5. ✅ Repo limpo obrigatório (pré-flight check funciona)
6. ✅ Smoke test: corrigir `teams` e `seasons` via batch → ambas FIXED

**Production-ready (FASE 3) quando:**

7. ✅ CI workflow configurado em GitHub Actions
8. ✅ PR bloqueado automaticamente se batch falhar
9. ✅ Comentário automático em PR com violations (CSV)
10. ✅ Documentação completa (`batch_validation.md` + `README.md`)

---

## Revisões Futuras

### Gatilhos de Revisão

Esta ADR deve ser revisitada quando:

1. **Número de tabelas > 50**
   - Scan sequencial pode exceder 10min
   - Considerar implementar FASE 2 (parallel scan)

2. **Taxa de SKIP_NO_MODEL > 10%**
   - Indica problema de naming (singular/plural)
   - Implementar política de mapa de exceções (FASE 2)

3. **Emergência de ciclos FK não documentados**
   - Hardcode `@("teams", "seasons")` quebra
   - Implementar detecção automática (FASE 2)

4. **CI executando em Linux/macOS**
   - PowerShell Core necessário (ou reescrever em Python)
   - Reavaliar Alternativa 1 (Python batch runner)

5. **Feedback de equipe: batch muito lento**
   - Considerar parallel execution (FASE 2)
   - Ou caching de scan results (incremental validation)

### Roadmap (6-12 meses)

**FASE 5: Incremental Validation**
- Detectar quais tabelas mudaram (git diff)
- Rodar batch apenas em subset (não todas as 15)
- Reduz overhead de CI (<2min vs <15min)

**FASE 6: Dashboard de Conformidade**
- Web UI mostrando histórico de batch executions
- Trend de violations ao longo do tempo
- Alertas para tabelas com FAIL recorrente

**FASE 7: Auto-fix com Review**
- Batch cria PR automático com correções
- Developer aprova/rejeita via GitHub review
- Reduz friction de "rodar batch + commit manual"

---

## Cenários de Validação

### Categoria A: Pré-condições e Setup

**Teste A1: Repository Hygiene Check (pré-flight)**

```powershell
# Setup: criar arquivo temporário
New-Item -Path "test_temp.tmp" -ItemType File

# Executar batch
.\scripts\models_batch.ps1

# Validação esperada:
# - Output: [ERROR] Repository must be clean
# - Output: git status --porcelain (mostra test_temp.tmp)
# - Exit code: 3 (guard violation)
# - Batch não prossegue para FASE 1
```

**Teste A2: SSOT Refresh (quando habilitado)**

```powershell
# Setup: schema.sql com timestamp antigo (>5min)
$oldTime = (Get-Date).AddMinutes(-10)
(Get-Item "docs\_generated\schema.sql").LastWriteTime = $oldTime

# Executar batch (sem -SkipRefresh)
.\scripts\models_batch.ps1

# Validação esperada:
# - inv.ps1 refresh executado
# - schema.sql.LastWriteTime < 5min ago
# - Batch prossegue para FASE 2
```

**Teste A3: SSOT Refresh Skip**

```powershell
# Executar batch com flag
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Log: "PHASE 1: SSOT Refresh - SKIPPED"
# - inv.ps1 NÃO executado
# - Batch prossegue para FASE 2 com schema.sql existente
```

### Categoria B: Table Discovery e Scan

**Teste B1: Discovery de Tabelas (parser schema.sql)**

```powershell
# Setup: schema.sql com 3 tabelas
# CREATE TABLE athletes (...
# CREATE TABLE teams (...
# CREATE TABLE alembic_version (...

# Executar parser (interno)
$tables = Get-TablesFromSchema "docs\_generated\schema.sql"

# Validação esperada:
# - $tables = @("athletes", "teams")
# - alembic_version EXCLUÍDO
# - Ordem = ordem de aparição no schema.sql
```

**Teste B2: Scan - Tabela PASS**

```powershell
# Setup: athletes.py correto (sem violations)

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada CSV:
# athletes,PASS,0,strict,2026-02-10T14:32:01

# Validação esperada log:
# [1/15] athletes - PASS (exit=0)
```

**Teste B3: Scan - Tabela FAIL**

```powershell
# Setup: teams.py com tipo errado
# season_id = Column(String)  # schema.sql: INTEGER

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada CSV:
# teams,FAIL,4,strict,2026-02-10T14:32:05

# Validação esperada log:
# [2/15] teams - FAIL (exit=4)
#   - VIOLATION: TYPE_MISMATCH: season_id expected=Integer got=String
```

**Teste B4: Scan - Model Não Existe (SKIP_NO_MODEL)**

```powershell
# Setup: deletar app/models/attendance.py
Remove-Item "app\models\attendance.py"

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada CSV:
# attendance,SKIP_NO_MODEL,100,strict,2026-02-10T14:32:06

# Validação esperada:
# - Batch NÃO aborta (continua próxima tabela)
# - Exit code interno: 100 (não propagado)
# - Exit code final: 0 (SKIP não é falha)
```

**Teste B5: Scan - Requirements Crash**

```powershell
# Setup: corromper model_requirements.py (syntax error)

# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Log: [CRASH] requirements failed with exit=1
# - Batch aborta imediatamente (fail-fast)
# - Exit code: 1
# - CSV parcial (somente tabelas processadas antes do crash)
```

### Categoria C: Correção (Gate Execution)

**Teste C1: Fix - Gate SUCCESS (autogen corrige)**

```powershell
# Setup:
# - teams.py com TYPE_MISMATCH (scan detectou FAIL)
# - autogen_model_from_db.py corrige corretamente

# Executar batch (com fix)
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - FASE 3: teams classificado como FAIL
# - FASE 4: gate executado para teams
# - Gate exit=0 (parity + requirements PASS)
# - teams marcado como FIXED
# - Batch continua próxima tabela FAIL
# - Exit code final: 0
```

**Teste C2: Fix - Gate PARITY FAIL (structural diff persiste)**

```powershell
# Setup:
# - teams.py com violation complexa (autogen não resolve)

# Executar batch (fail-fast ON)
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Gate executado para teams
# - Parity detecta structural diff (exit=2)
# - Log: [ABORT] Gate failed for teams (exit=2)
# - Batch para imediatamente
# - Exit code: 2 (propagado)
# - CSV tem teams=FAIL (não FIXED)
```

**Teste C3: Fix - Gate GUARD FAIL (baseline drift)**

```powershell
# Setup:
# - Modificar baseline artificialmente (simular drift)

# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Gate executado
# - Guard detecta baseline drift (exit=3)
# - Log: [ABORT] Gate failed (exit=3)
# - Batch para imediatamente
# - Exit code: 3 (propagado)
```

**Teste C4: Fix - Gate REQUIREMENTS FAIL (autogen não resolveu)**

```powershell
# Setup:
# - teams.py com lógica custom (não-autogen)
# - Autogen adiciona campos mas lógica custom persiste violation

# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Gate executado
# - Requirements detecta violation (exit=4)
# - Log: [ABORT] Gate failed for teams (exit=4)
# - Batch para imediatamente
# - Exit code: 4 (propagado)
```

**Teste C5: Fix - Múltiplas Tabelas FAIL (correção sequencial)**

```powershell
# Setup:
# - teams.py: FAIL (corrigível)
# - seasons.py: FAIL (corrigível)
# - athletes.py: PASS

# Executar batch (fail-fast ON)
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - FASE 3: teams=FAIL, seasons=FAIL
# - FASE 4: gate(teams) → exit=0 (FIXED)
# - FASE 4: gate(seasons) → exit=0 (FIXED)
# - Exit code final: 0
# - CSV: teams=FIXED, seasons=FIXED, athletes=PASS
```

### Categoria D: Validações Estruturais (integração com requirements)

**Teste D1: Tipos Complexos**

```powershell
# Setup: schema.sql com tipos complexos
# - birth_date DATE
# - salary NUMERIC(10,2)
# - created_at TIMESTAMP WITH TIME ZONE
# - uuid_field UUID

# Model correto:
# birth_date = Column(Date)
# salary = Column(Numeric(precision=10, scale=2))
# created_at = Column(DateTime(timezone=True))
# uuid_field = Column(UUID)

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada: PASS (todos os tipos corretos)
```

**Teste D2: Nullability Explícita**

```powershell
# Setup: schema.sql
# email VARCHAR(100) NOT NULL
# nickname VARCHAR(50)  -- nullable

# Model incorreto:
# email = Column(String(100))  # falta nullable=False
# nickname = Column(String(50), nullable=False)  # deveria ser nullable=True

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada: FAIL
# - VIOLATION: NULLABLE_MISMATCH: email expected=NOT NULL got=omitted
# - VIOLATION: NULLABLE_MISMATCH: nickname expected=nullable got=nullable=False
```

**Teste D3: Foreign Keys com ondelete**

```powershell
# Setup: schema.sql
# CONSTRAINT fk_teams_season_id FOREIGN KEY (season_id)
#   REFERENCES seasons(id) ON DELETE RESTRICT

# Model correto:
# season_id = Column(Integer,
#     ForeignKey("seasons.id", name="fk_teams_season_id", ondelete="RESTRICT"))

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada: PASS
```

**Teste D4: Ciclos FK (teams/seasons)**

```powershell
# Setup:
# - teams.season_id → seasons.id
# - seasons.champion_team_id → teams.id
# - Models sem use_alter=True

# Executar batch (perfil strict)
.\scripts\models_batch.ps1 -SkipRefresh -Profile strict

# Validação esperada:
# - FASE 3: teams=FAIL, seasons=FAIL (requirements detecta falta de use_alter)
# - FASE 4: gate com perfil=fk (auto-detectado ou hardcoded)
# - Gate adiciona use_alter=True
# - Exit code: 0 (corrigido)
```

**Teste D5: CHECK Constraints**

```powershell
# Setup: schema.sql
# CONSTRAINT ck_attendance_source_valid CHECK (source IN ('manual', 'import'))

# Model correto:
# __table_args__ = (
#     CheckConstraint("source IN ('manual', 'import')",
#                     name="ck_attendance_source_valid"),
# )

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada: PASS
```

### Categoria E: Flags e Configurações

**Teste E1: Flag -SkipGate (scan-only mode)**

```powershell
# Setup: teams.py com FAIL

# Executar batch
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada:
# - FASE 3: teams=FAIL detectado
# - FASE 4: pulada (log: "Fix phase - SKIPPED")
# - Exit code: 0 (FAIL não é erro em scan-only)
# - CSV: teams=FAIL (não FIXED)
```

**Teste E2: Flag -FailFast=false (continuar após erro)**

```powershell
# Setup:
# - teams.py: FAIL (gate vai falhar com exit=2)
# - seasons.py: FAIL (corrigível)

# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh -FailFast:$false

# Validação esperada:
# - Gate(teams) → exit=2 (falha)
# - Log: [ERROR] Gate failed for teams (exit=2)
# - Batch CONTINUA (não aborta)
# - Gate(seasons) → exit=0 (corrigido)
# - Exit code final: 2 (primeiro erro encontrado)
# - CSV: teams=FAIL, seasons=FIXED
```

**Teste E3: Perfil Customizado**

```powershell
# Executar batch com perfil lenient
.\scripts\models_batch.ps1 -SkipRefresh -Profile lenient

# Validação esperada:
# - requirements executado com --profile lenient
# - Gate executado com -Profile lenient
# - Violations menos estritas aceitas
```

### Categoria F: Auditoria e Relatórios

**Teste F1: Geração de CSV**

```powershell
# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Arquivo criado: %TEMP%\models_batch_{timestamp}.csv
# - Formato correto: table_name,status,exit_code,profile,timestamp
# - 1 linha por tabela processada
# - Timestamp ISO 8601
```

**Teste F2: Geração de Log**

```powershell
# Executar batch
.\scripts\models_batch.ps1 -SkipRefresh

# Validação esperada:
# - Arquivo criado: %TEMP%\models_batch_{timestamp}.log
# - Contém: parâmetros, output de requirements, output de gate
# - Resumo final (counts, exit code)
```

**Teste F3: Resumo no Console**

```powershell
# Setup: 15 tabelas (10 PASS, 3 FAIL, 2 SKIP)

# Executar batch (scan-only)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Validação esperada no console:
# ============ SUMMARY ============
# Total tables: 15
# PASS: 10
# FAIL: 3
# SKIP_NO_MODEL: 2
# Exit code: 0
# ================================
```

---

## Padrões de Implementação (Detalhamento Técnico)

### Padrão 1: Captura de Exit Code (sem pipeline que altere $LASTEXITCODE)

**Correto:**

```powershell
$output = & ".\venv\Scripts\python.exe" scripts\model_requirements.py --table $table 2>&1
$exitCode = $LASTEXITCODE  # Captura IMEDIATA
$output | Add-Content -Path $logPath  # Pipeline APÓS captura
return $exitCode
```

**Incorreto (anti-pattern):**

```powershell
# ERRADO: Tee-Object entre execução e captura
& ".\venv\Scripts\python.exe" scripts\model_requirements.py --table $table 2>&1 | Tee-Object -FilePath $logPath
$exitCode = $LASTEXITCODE  # Valor foi alterado por Tee-Object!
```

### Padrão 2: Test-Path para SKIP_NO_MODEL (não regex de erro)

**Correto:**

```powershell
$modelPath = "app\models\$table.py"
if (-not (Test-Path $modelPath)) {
    return @{ Table=$table; Status="SKIP_NO_MODEL"; ExitCode=100 }
}
# Prossegue apenas se model existe
```

**Incorreto (anti-pattern):**

```powershell
# ERRADO: depender de parsing de stderr
try {
    $output = & python model_requirements.py --table $table 2>&1
} catch {
    if ($_ -match "FileNotFoundError") {
        return "SKIP_NO_MODEL"  # Frágil!
    }
}
```

### Padrão 3: Fail-Fast com Propagação de Exit Code

**Correto:**

```powershell
$exitCode = Invoke-Gate -Table $table
if ($exitCode -ne 0) {
    if ($FailFast) {
        Write-Host "[ABORT] Fail-fast triggered (exit=$exitCode)"
        exit $exitCode  # Propaga 2/3/4 específico
    } else {
        $firstError = $exitCode  # Armazena para exit final
        # Continua próxima tabela
    }
}
```

**Incorreto (anti-pattern):**

```powershell
# ERRADO: achatar para exit=1
try {
    Invoke-Gate -Table $table
} catch {
    exit 1  # Perde informação (2/3/4 → 1)
}
```

### Padrão 4: Logs em %TEMP% (não no repo)

**Correto:**

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = "$env:TEMP\models_batch_$timestamp.log"
$csvPath = "$env:TEMP\models_batch_$timestamp.csv"
```

**Incorreto (anti-pattern):**

```powershell
# ERRADO: criar logs no repo
$logPath = ".\logs\batch.log"  # → git status mostra ?? logs/batch.log
```

---

## Referências

### Documentos Relacionados

- **ADR-MODELS-001** (`docs/ADR/013-ADR-MODELS.md`) — Gate de Validação Estrutural (fundação deste ADR)
- **TRD Training** (`docs/02-modulos/training/TRD_TRAINING.md`) — Referência técnica de models
- **INVARIANTS Training** (`docs/02-modulos/training/INVARIANTS_TRAINING.md`) — Invariantes de negócio
- `docs/workflows/model_validation.md` — Workflow SSOT completo (ADR-MODELS-001)
- `docs/_canon/05_MODELS_PIPELINE.md` — Pipeline canônico de models (A ATUALIZAR)

### Código Relacionado

**Scripts existentes (reutilizados):**
- `scripts/inv.ps1` — Refresh de SSOT via pg_dump
- `scripts/model_requirements.py` — Validação estática (parser DDL + AST)
- `scripts/models_autogen_gate.ps1` — Gate completo (3 camadas)
- `scripts/agent_guard.py` — Baseline snapshot/check
- `scripts/parity_gate.ps1` — Alembic compare wrapper
- `scripts/parity_classify.py` — Classificação de diffs (structural vs warnings)

**Novos componentes (este ADR):**
- `scripts/models_batch.ps1` — **Orquestrador batch (NOVO)**
- `Get-TablesFromSchema` — Parser de schema.sql (função interna)

**CI/CD (futuro):**
- `.github/workflows/validate-models-batch.yml` — GitHub Actions workflow (FASE 3)

### Evidências de Decisão

**Issues/PRs relacionados:**
- **Caso 1:** "15 tabelas corrigidas manualmente em 4h" (conversa Slack, 2026-02-08)
- **Caso 2:** "CI quebrou em prod por validation parcial" (incident log, 2026-02-09)
- **Caso 3:** "Guard bloqueou PR por parity_report.json esquecido" (Slack thread, 2026-02-09)

**Benchmarks de tempo:**
- Manual (15 tabelas): 165min (45min base + 120min retrabalho)
- Batch scan (15 tabelas): ~3-5min
- Batch fix (3 FAIL): ~9min (3min/tabela)
- **Total batch:** ~14min (91% redução)

### Tecnologias de Referência Externa

**Inspiração de design:**
- **Django migrations** (`manage.py migrate`) — Batch execution com fail-fast
- **Flyway** (DB versioning) — Validação determinística de schema
- **Terraform plan/apply** — Scan-then-fix pattern
- **ESLint** `--fix` — Auto-correção com auditoria

---

## Aprovação

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| **Tech Lead** | Davi | 2026-02-10 | ✅ Aprovado |
| **Reviewer** | Claude (AI Assistant) | 2026-02-10 | ✅ Validado |

**Status final:** ✅ **APROVADO**

**Próximos passos:**

1. Implementar `models_batch.ps1` MVP (FASE 1) — **PRIORIDADE ALTA**
   - [ ] Parâmetros e pré-flight checks
   - [ ] FASE 1-5 (refresh, discovery, scan, fix, report)
   - [ ] Exit code propagation correta
   - [ ] Testes de integração (A1-F3)

2. Validar com smoke tests (15 tabelas reais)
   - [ ] Scan-only: todas classificadas corretamente
   - [ ] Fix: teams/seasons corrigidos via autogen
   - [ ] Fail-fast: para no primeiro gate!=0

3. Documentação (`batch_validation.md`)
   - [ ] Quando usar batch vs gate individual
   - [ ] Interpretação de CSV/logs
   - [ ] Troubleshooting comum

4. CI/CD Integration (FASE 3)
   - [ ] GitHub Actions workflow
   - [ ] Branch protection rule
   - [ ] PR comments automáticos

5. Treinamento de equipe (workshop 1h)
   - [ ] Demo de batch execution
   - [ ] Hands-on: forçar violation + corrigir

**Riscos identificados:**

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Developer usa `-SkipGate` e assume "tudo ok" | Médio | Alto | Documentação + CI obrigatório com fix |
| Batch demora >10min para 50+ tabelas | Baixo | Médio | FASE 2 (parallel scan) quando necessário |
| Ciclos FK não documentados quebram perfil | Baixo | Alto | FASE 2 (auto-detecção de ciclos) |

---

## Anexos

### Comandos Canônicos

**Varredura rápida (scan-only):**

```powershell
# Usa schema.sql existente, sem correções
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh

# Output: CSV com PASS/FAIL/SKIP
# Tempo: ~2-5min (15 tabelas)
# Exit code: 0 (scan não falha)
```

**Execução completa (scan + fix):**

```powershell
# Refresh SSOT, scan, corrige FAIL com fail-fast
.\scripts\models_batch.ps1

# Output: CSV + log + resumo
# Tempo: ~5-15min (depende de quantas FAIL)
# Exit code: 0 (sucesso) | 2/3/4 (primeiro erro)
```

**Scan com refresh (CI local):**

```powershell
# Atualiza schema.sql do DB real, depois scan
.\scripts\models_batch.ps1 -SkipGate

# Use case: validação pré-PR com SSOT atualizado
# Tempo: +2min (pg_dump) + 2-5min (scan)
```

**Fix sem fail-fast (continuar após erros):**

```powershell
# Corrige todas FAIL mesmo se alguma falhar
.\scripts\models_batch.ps1 -FailFast:$false

# Use case: debug (coletar múltiplos erros de uma vez)
# Exit code: primeiro erro encontrado (não 0)
```

### Troubleshooting Comum

**Problema: "Repository must be clean"**

```powershell
# Causa: arquivos uncommitted (docs/_generated/*, models em WIP)
# Solução 1: commit changes
git add . && git commit -m "wip: models validation"

# Solução 2: stash temporário
git stash
.\scripts\models_batch.ps1
git stash pop

# Solução 3: scan-only com schema.sql existente (se SSOT ok)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
```

**Problema: "SSOT refresh failed"**

```powershell
# Causa: pg_dump não conseguiu atualizar schema.sql
# Solução 1: verificar DB acessível
psql -h localhost -U hbtrack -d hbtrack_dev -c "SELECT 1;"

# Solução 2: usar schema.sql existente (se recente)
.\scripts\models_batch.ps1 -SkipRefresh
```

**Problema: Exit code 3 (guard) mas repo está limpo**

```powershell
# Causa: baseline desatualizada (.hb_guard/baseline.json)
# Solução: refresh baseline
.\scripts\agent_guard.py snapshot

# Depois, re-rodar batch
.\scripts\models_batch.ps1
```

**Problema: Exit code 4 (requirements) mas autogen foi executado**

```powershell
# Causa: model tem lógica custom (não-autogen) com violation
# Solução: revisar violation no log e corrigir manualmente
# Ex: remover campo extra, corrigir tipo, adicionar constraint

# Log mostrará linha específica:
# VIOLATION: EXTRA_COLUMN: nickname (model line 42, not in schema.sql)
```

### Interpretação de CSV

**Formato:**

```csv
table_name,status,exit_code,profile,timestamp
athletes,PASS,0,strict,2026-02-10T14:32:01
teams,FAIL,4,fk,2026-02-10T14:32:05
attendance,SKIP_NO_MODEL,100,strict,2026-02-10T14:32:06
seasons,FIXED,0,fk,2026-02-10T14:35:22
```

**Status possíveis:**

| Status | Significado | Ação necessária |
|--------|-------------|-----------------|
| `PASS` | Model válido | Nenhuma (✅) |
| `FAIL` | Requirements violation detectada | Corrigir manualmente ou rodar batch com fix |
| `SKIP_NO_MODEL` | Model não existe (`app/models/{table}.py`) | Criar model ou ignorar (se tabela não precisa model) |
| `FIXED` | Era FAIL, gate corrigiu via autogen | Revisar diff, commitar se ok |

**Exit codes possíveis:**

| Exit Code | Significado | Origem |
|-----------|-------------|--------|
| `0` | Sucesso | requirements (PASS) ou gate (FIXED) |
| `4` | Requirements violation | requirements |
| `100` | Model não existe (interno) | batch (SKIP_NO_MODEL) |
| `2` | Parity structural diff | gate (durante fix) |
| `3` | Guard violation | gate (durante fix) |
| `1` | Crash inesperado | requirements ou gate |

### Critérios de Sucesso (Acceptance)

**MVP (FASE 1) considerado pronto quando:**

- [x] ✅ Batch processa 15 tabelas em <5min (scan-only)
- [x] ✅ Fail-fast para no primeiro gate!=0 com exit code correto
- [x] ✅ CSV gerado com formato correto (todas as tabelas)
- [x] ✅ Pré-flight check bloqueia repo sujo (exit=3)
- [x] ✅ SKIP_NO_MODEL via Test-Path (não parsing de erro)
- [x] ✅ Smoke test: teams + seasons corrigidos e marcados FIXED

**Production-ready (FASE 3) quando:**

- [ ] CI workflow em GitHub Actions funcionando
- [ ] PR bloqueado se batch exit!=0
- [ ] Comentário automático com violations (CSV)
- [ ] Documentação completa (README + batch_validation.md)
- [ ] Workshop de equipe concluído (2/2 developers treinados)

---

**Changelog:**

- `2026-02-11`: Autogen hardening (multiline imports, ARRAY types, bare Mapped[], orphan lines)
- `2026-02-10`: Versão inicial (baseada em ADR-MODELS-001 e evidências de ineficiência operacional)
- `2026-02-10`: Adição de seções detalhadas (Arquitetura, Componentes, Critérios, Cenários de Validação)
- `2026-02-10`: Adição de Alternativas Consideradas, Implementação em Fases, Métricas de Sucesso
- `2026-02-10`: Adição de Referências, Aprovação, Anexos (comandos canônicos + troubleshooting)



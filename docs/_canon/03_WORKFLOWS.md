# Workflows Operacionais (Canônico)

| Propriedade | Valor |
|---|---|
| ID | CANON-WORKFLOWS-003 |
| Status | CANÔNICO |
| Última verificação | 2026-02-10 (America/Sao_Paulo) |
| Porta de entrada | docs/_canon/00_START_HERE.md |
| Depende de | 01_AUTHORITY_SSOT.md, 05_MODELS_PIPELINE.md, 08_APPROVED_COMMANDS.md |
| Objetivo | Protocolos executáveis passo-a-passo para tarefas operacionais comuns |

---

## Natureza deste Documento

Este documento contém **workflows executáveis** (protocolos passo-a-passo) para tarefas operacionais do HB Track.

**Diferença entre workflow e pipeline:**
- **Workflow** = sequência de ações **humanas** (instalar invariante, corrigir model, validar conformidade)
- **Pipeline** = sequência **automatizada** de validações (guard → parity → requirements)

**Quando usar:**
- Você precisa executar uma tarefa operacional específica (ex: adicionar invariante, corrigir parity)
- Precisa de um checklist verificável com comandos concretos
- Precisa de evidências objetivas de conclusão

**Quando NÃO usar:**
- Para entender conceitos → leia `02_CONTEXT_MAP.md`
- Para comandos específicos de models → leia `05_MODELS_PIPELINE.md`
- Para troubleshooting de exit codes → leia `09_TROUBLESHOOTING_GUARD_PARITY.md`

---

## Glossário de Termos (Quick Reference)

| Termo | Definição | Onde Ver Mais |
|-------|-----------|---------------|
| **SSOT** | Single Source of Truth (schema.sql, openapi.json) | `01_AUTHORITY_SSOT.md` |
| **Parity** | Conformidade Model↔DB via Alembic compare | `05_MODELS_PIPELINE.md` |
| **Requirements** | Validação model vs schema.sql via parsers | `model_requirements_guide.md` |
| **Guard** | Proteção contra modificação não autorizada | `INVARIANTS_AGENT_GUARDRAILS.md` |
| **Gate** | Validação atomicamente composta (guard+parity+requirements) | `05_MODELS_PIPELINE.md` |
| **Baseline** | Snapshot de estado conformante para guard | `08_APPROVED_COMMANDS.md` |
| **Invariante** | Regra de negócio que nunca deve ser violada | `INVARIANTS_TRAINING.md` |

---

## Convenções de Notação

**Comandos executáveis:**
```powershell
# ✅ Formato padrão - copie e cole
.\scripts\comando.ps1 -Param "valor"
```

**Pré-requisitos obrigatórios:**
```powershell
# [PREREQ] Validação antes de executar workflow
Set-Location "C:\HB TRACK\Hb Track - Backend"
git status --porcelain  # deve retornar vazio
```

**Validação pós-execução:**
```powershell
# [VALIDAÇÃO] Critério objetivo de sucesso
$LASTEXITCODE  # esperado: 0
git status --porcelain  # esperado: vazio (ou lista de arquivos intencionais)
```

**Exit codes:**
- `0` = sucesso
- `1` = crash/erro interno
- `2` = parity diffs (Model≠DB)
- `3` = guard violation (arquivo protegido modificado)
- `4` = requirements violation (model viola schema.sql)

---

## Índice de Workflows

| ID | Nome | Quando Usar | Tempo Estimado para Humanos|
|----|------|-------------|----------------|
| **WF-1** | Adicionar Invariante de Training | Nova regra de negócio a ser validada | 2-4h |
| **WF-2** | Corrigir Parity/Guard Violations | Exit code 2/3 em gates | 30min-2h |
| **WF-3** | Validar Model Conformance | Verificar Model↔schema.sql | 15-30min |
| **WF-4** | Varredura em Lote (Batch Scan) | Validar todas as tabelas de uma vez | 5-15min |
| **WF-5** | Diagnosticar parity_report.json | Investigar conteúdo de relatório de paridade | 10-20min |
| **WF-6** | Refresh SSOT Completo | Atualizar artefatos gerados (schema.sql, openapi.json) | 2-5min |
| **WF-7** | Snapshot Baseline (Guard) | Registrar novo estado conformante | 5min |
| **WF-8** | Criar Migration Alembic | Adicionar/modificar estrutura de tabela | 30min-2h |

---

## Protocolo de Finalização de Tarefa (Obrigatório)

Ao concluir QUALQUER tarefa (Manual ou via EXEC_TASK), o executor DEVE seguir este protocolo para garantir a integridade dos logs e a rastreabilidade via artefatos.

### 1. Registrar Artefatos da Tarefa
Certifique-se de que todos os relatórios relevantes (parity, requirements, etc.) estejam em `docs/execution_tasks/artifacts/<TASK_ID>/reports/`.

### 2. Gerar Evento de Execução
Crie ou atualize o arquivo `docs/execution_tasks/artifacts/<TASK_ID>/event.json` com os metadados da execução (status, timestamps, escopo).

### 3. Atualizar Índices (Compacted Logs)
Execute o script de compactação para atualizar o `CHANGELOG.md` e `EXECUTIONLOG.md`.

```powershell
# [CMD] Atualizar logs compactados (CWD: C:\HB TRACK)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { Set-Location 'C:\HB TRACK'; & 'C:\HB TRACK\Hb Track - Backend\venv\Scripts\python.exe' 'scripts\compact_exec_logs.py' }"
```

### 4. Validar Saída e Conformidade
Execute a auditoria de logs para garantir que não houve "drift" narrativo ou órfãos.

```powershell
# [CMD] Validar conformidade de logs (CWD: C:\HB TRACK)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { Set-Location 'C:\HB TRACK'; & 'C:\HB TRACK\Hb Track - Backend\venv\Scripts\python.exe' 'scripts\_ia\check_logs_compaction.py' --changelog 'docs\ADR\architecture\CHANGELOG.md' --exec-log 'docs\ADR\workflows\EXECUTIONLOG.md' }"
```

### 5. Validar Estado do Repositório
- O comando de auditoria deve retornar `[OK] Logs compaction check passed.`.
- `git status` deve mostrar apenas as mudanças esperadas nos índices e novos artefatos.
- Uma segunda execução da compactação NÃO deve gerar diffs adicionais (idempotência).

---

# WF-1: Adicionar Invariante de Training

## Objetivo

Instalar nova restrição de negócio (invariante) no módulo Training, validada por testes automatizados.

**Exemplo de invariante:** "Duração de sessão de treino deve ser ≤ 180 minutos" (INV-TRAIN-037)

---

## Pré-requisitos Obrigatórios

### 1. Ambiente
```powershell
# CWD correto
Set-Location "C:\HB TRACK"

# Repo limpo
git status --porcelain
# Esperado: vazio (sem uncommitted changes)

# Venv ativado (se necessário rodar testes)
& "Hb Track - Backend\venv\Scripts\python.exe" --version
# Esperado: Python 3.11+
```

### 2. Documentação lida
- [ ] `INVARIANTS_TESTING_CANON.md` — Protocolo canônico de testes (DoD, classes A-F)
- [ ] `INVARIANTS_AGENT_PROTOCOL.md` — Workflow obrigatório local-first
- [ ] `INVARIANTS_TRAINING.md` — Invariantes existentes (evitar duplicação)

### 3. Definição clara da invariante
- [ ] Enunciado não-técnico claro (ex: "duração ≤ 180min")
- [ ] Critério de aceitação objetivo (ex: "raise ValidationError se duration > 180")
- [ ] Evidência canônica identificada (ex: `schema.sql` linha 450: CHECK constraint)

---

## Passos Executáveis

### Passo 1: Verificar Estado Atual

```powershell
# [PREREQ] Validar repo limpo
git status --porcelain
# Esperado: vazio

# [PREREQ] Verificar se invariante já existe
Select-String -Path "docs\02_modulos\training\INVARIANTS\INVARIANTS_TRAINING.md" -Pattern "duração.*180" -CaseSensitive:$false
# Esperado: nenhum match (se houver, invariante já existe)
```

**Se encontrar match:** Pare aqui e revise a invariante existente antes de prosseguir.

---

### Passo 2: Determinar Classe da Invariante

**Consultar:** `INVARIANTS_TESTING_CANON.md` seção "Matriz de Classificação"

| Classe | Tipo | Exemplo | Onde Implementar |
|--------|------|---------|------------------|
| **A** | DB Constraint | CHECK duration <= 180 | schema.sql (via migration) |
| **B** | Trigger/Function | audit_log trigger | Alembic migration (SQL function) |
| **C1** | Service puro | Validação sem IO | `app/services/training.py` |
| **C2** | Service com DB | Validação + query | `app/services/training.py` + DB check |
| **D** | Router/RBAC | Permissão de acesso | `app/routes/training.py` + RBAC guard |
| **E1** | Celery puro | Task sem DB | `app/tasks/training.py` |
| **E2** | Celery com DB | Task com DB check | `app/tasks/training.py` + query |
| **F** | OpenAPI | Contract validation | openapi.json (schema validation) |

**Para este exemplo:** `CHECK duration <= 180` → **Classe A** (DB Constraint)

---

### Passo 3: Implementar a Invariante

#### 3.1: Classe A (DB Constraint) — Criar Migration

```powershell
# [CMD] Criar migration Alembic
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" -m alembic revision -m "add check constraint training_sessions duration"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Migration criada
if ($ec -eq 0) {
    Write-Host "[OK] Migration criada em alembic\versions\"
} else {
    Write-Host "[FAIL] Migration falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

**Editar migration gerada:**

```python
# alembic/versions/XXXX_add_check_constraint_training_sessions_duration.py

def upgrade():
    op.execute("""
        ALTER TABLE training_sessions
        ADD CONSTRAINT ck_training_sessions_duration_max
        CHECK (duration <= 180)
    """)

def downgrade():
    op.execute("""
        ALTER TABLE training_sessions
        DROP CONSTRAINT ck_training_sessions_duration_max
    """)
```

#### 3.2: Aplicar Migration

```powershell
# [CMD] Rodar migration
& "venv\Scripts\python.exe" -m alembic upgrade head
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Migration aplicada
if ($ec -eq 0) {
    Write-Host "[OK] Migration aplicada"
} else {
    Write-Host "[FAIL] Migration falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

---

### Passo 4: Refresh SSOT e Validar Parity

```powershell
# [CMD] Regenerar schema.sql
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh
$ec = $LASTEXITCODE

# [VALIDAÇÃO] SSOT atualizado
if ($ec -ne 0) {
    Write-Host "[FAIL] SSOT refresh falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}

# [CMD] Verificar parity
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "training_sessions"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Parity clean
if ($ec -ne 0) {
    Write-Host "[WARN] Parity diff detectado (exit=$ec)"
    Write-Host "Consulte: docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md"
}
```

---

### Passo 5: Criar Testes de Invariante

**Arquivo:** `tests/invariants/test_inv_train_037_duration_max.py`

```python
"""
INV-TRAIN-037: Training session duration ≤ 180 minutes

Evidência: schema.sql linha 450 — CHECK constraint ck_training_sessions_duration_max
Classe: A (DB Constraint)
"""

import pytest
from sqlalchemy.exc import IntegrityError

class TestInvTrain037DurationMax:
    """Classe A: Runtime Integration com async_db"""

    async def test_valid_duration_180(self, async_db):
        """PASS: Duração = 180 (limite) deve ser aceita"""
        # Payload mínimo com duração no limite
        session = TrainingSession(
            team_id=1,
            date=date.today(),
            duration=180  # exatamente no limite
        )
        async_db.add(session)
        await async_db.commit()  # Esperado: sucesso
        assert session.id is not None

    async def test_invalid_duration_181(self, async_db):
        """FAIL: Duração = 181 (violação mínima) deve rejeitar"""
        session = TrainingSession(
            team_id=1,
            date=date.today(),
            duration=181  # violação mínima específica
        )
        async_db.add(session)

        with pytest.raises(IntegrityError) as exc_info:
            await async_db.commit()

        # Validar SQLSTATE + constraint_name (anti-falso-positivo)
        assert "ck_training_sessions_duration_max" in str(exc_info.value)
        assert "23514" in str(exc_info.value)  # CHECK constraint violation

    async def test_invalid_duration_999(self, async_db):
        """FAIL: Duração extrema (999) deve rejeitar"""
        session = TrainingSession(
            team_id=1,
            date=date.today(),
            duration=999
        )
        async_db.add(session)

        with pytest.raises(IntegrityError) as exc_info:
            await async_db.commit()

        assert "ck_training_sessions_duration_max" in str(exc_info.value)
```

---

### Passo 6: Executar Testes

```powershell
# [CMD] Rodar testes da invariante
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" -m pytest tests\invariants\test_inv_train_037_duration_max.py -v
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Testes passam
if ($ec -eq 0) {
    Write-Host "[OK] Testes da invariante passaram"
} else {
    Write-Host "[FAIL] Testes falharam (exit=$ec)" -ForegroundColor Red
    exit $ec
}

# [CMD] Rodar suite completa de testes (opcional)
& "venv\Scripts\python.exe" -m pytest tests\ -k "train" --maxfail=1
```

---

### Passo 7: Documentar Invariante

**Arquivo:** `docs/02_modulos/training/INVARIANTS/INVARIANTS_TRAINING.md`

Adicionar entry:

```markdown
## INV-TRAIN-037: Duração Máxima de Sessão de Treino

**Classe:** A (DB Constraint)
**Status:** CONFIRMED
**Prioridade:** P1

**Enunciado:**
A duração de uma sessão de treino (`training_sessions.duration`) não pode exceder 180 minutos.

**Evidência canônica:**
- `schema.sql:450` — `CONSTRAINT ck_training_sessions_duration_max CHECK (duration <= 180)`

**Justificativa:**
Sessões >3h indicam erro de entrada ou planejamento inadequado; limite previne dados inválidos.

**Testes:**
- `tests/invariants/test_inv_train_037_duration_max.py`
  - `test_valid_duration_180` — Duração limite (PASS)
  - `test_invalid_duration_181` — Violação mínima (FAIL esperado)
  - `test_invalid_duration_999` — Violação extrema (FAIL esperado)

**SQLSTATE esperado:** `23514` (CHECK constraint violation)
**Constraint name:** `ck_training_sessions_duration_max`

**Changelog:**
- 2026-02-10: Criado (migration XXXX)
```

---

### Passo 8: Commit e PR

```powershell
# [VALIDAÇÃO] Verificar mudanças
git status --porcelain

# [CMD] Adicionar arquivos relevantes
git add "Hb Track - Backend\alembic\versions\XXXX*.py"
git add "Hb Track - Backend\tests\invariants\test_inv_train_037*.py"
git add "docs\02_modulos\training\INVARIANTS\INVARIANTS_TRAINING.md"

# [CMD] Commit
git commit -m "feat(invariants): add INV-TRAIN-037 duration max constraint

- Migration: CHECK constraint duration <= 180
- Tests: Classe A (3 cenários: valid, invalid min, invalid extreme)
- Docs: INVARIANTS_TRAINING.md entry

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# [CMD] Push (se autorizado)
# git push -u origin HEAD
```

---

## Validação Final (DoD)

**Definition of Done para WF-1:**

- [ ] Migration criada e aplicada (`alembic upgrade head` exit=0)
- [ ] SSOT refresh executado com sucesso (`inv.ps1 refresh` exit=0)
- [ ] Parity scan clean para tabela afetada (exit=0)
- [ ] Testes criados seguindo Classe A pattern (3 cenários mínimos)
- [ ] Testes executados e passaram (`pytest` exit=0)
- [ ] Invariante documentada em `INVARIANTS_TRAINING.md` com evidência canônica
- [ ] Commit criado com mensagem estruturada (feat/fix/docs)
- [ ] Repo limpo após commit (`git status --porcelain` vazio)

---

## Troubleshooting WF-1

### Problema: Migration falha com "constraint already exists"

**Causa:** Constraint já foi criado manualmente ou em migration anterior.

**Solução:**
```powershell
# Verificar se constraint existe no DB
psql -h localhost -U hbtrack -d hbtrack_dev -c "\d training_sessions"
# Procurar por ck_training_sessions_duration_max

# Se existir: reverter migration e criar nova sem duplicate
& "venv\Scripts\python.exe" -m alembic downgrade -1
```

### Problema: Testes falham com "table not found"

**Causa:** Migration não foi aplicada no DB de testes.

**Solução:**
```powershell
# Aplicar migrations no DB de testes
$env:DATABASE_URL = "postgresql://hbtrack:pass@localhost/hbtrack_test"
& "venv\Scripts\python.exe" -m alembic upgrade head
```

### Problema: Parity scan retorna exit=2 após migration

**Causa:** Model não reflete constraint criado.

**Solução:**
```powershell
# Atualizar model com __table_args__
# app/models/training_session.py

__table_args__ = (
    CheckConstraint("duration <= 180", name="ck_training_sessions_duration_max"),
)

# Rodar parity novamente
.\scripts\parity_scan.ps1 -TableFilter "training_sessions"
```

---

# WF-2: Corrigir Parity/Guard Violations

## Objetivo

Resolver divergências entre Model (SQLAlchemy) e DB (PostgreSQL schema.sql) quando gate retorna exit=2 (parity) ou exit=3 (guard).

**Quando usar:** Após rodar `parity_scan.ps1` ou `models_autogen_gate.ps1` e receber exit code 2 ou 3.

---

## Pré-requisitos Obrigatórios

### 1. Ambiente
```powershell
# CWD correto
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Repo limpo
git status --porcelain
# Esperado: vazio

# SSOT atualizado (se ainda não fez refresh nesta sessão)
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh
```

### 2. Documentação lida
- [ ] `05_MODELS_PIPELINE.md` — Pipeline canônico de validação
- [ ] `09_TROUBLESHOOTING_GUARD_PARITY.md` — Diagnóstico de exit codes 2/3/4
- [ ] `exit_codes.md` — Semântica de exit codes

---

## Passos Executáveis

### Passo 1: Executar Parity Scan e Capturar Exit Code

```powershell
# [CMD] Parity scan para tabela específica
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "teams"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Capturar exit code
Write-Host "Parity scan exit code: $ec"

# [DECISÃO] Roteamento por exit code
switch ($ec) {
    0 { Write-Host "[OK] Parity clean (nenhuma ação necessária)"; exit 0 }
    2 { Write-Host "[WARN] Structural diffs detectados → continuar WF-2" }
    3 { Write-Host "[ERROR] Guard violation → verificar baseline"; exit 3 }
    default { Write-Host "[ERROR] Crash (exit=$ec)"; exit $ec }
}
```

---

### Passo 2: Analisar parity_report.json

```powershell
# [CMD] Abrir relatório de paridade
$reportPath = "docs\_generated\parity_report.json"
if (Test-Path $reportPath) {
    $report = Get-Content $reportPath -Raw | ConvertFrom-Json
    Write-Host "Diffs encontrados:" ($report.diffs | Measure-Object).Count

    # Mostrar diffs estruturais
    $report.diffs | Where-Object { $_.type -eq "structural" } | Format-Table table, column, diff_type
} else {
    Write-Host "[ERROR] parity_report.json não encontrado"
    exit 1
}
```

**Formato esperado do diff:**
```json
{
  "table": "teams",
  "column": "season_id",
  "diff_type": "modify_nullable",
  "expected": "nullable=False",
  "got": "nullable=True",
  "severity": "high"
}
```

---

### Passo 3: Consultar SSOT (schema.sql) para Verdade Canônica

```powershell
# [CMD] Buscar definição da tabela no schema.sql
$table = "teams"
Select-String -Path "docs\_generated\schema.sql" -Pattern "CREATE TABLE $table" -Context 0,50
```

**Exemplo de output:**
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    season_id INTEGER NOT NULL,  -- ← Verdade canônica: NOT NULL
    CONSTRAINT fk_teams_season_id FOREIGN KEY (season_id)
        REFERENCES seasons(id) ON DELETE RESTRICT
);
```

**Decisão:** `schema.sql` diz `NOT NULL` → Model deve ter `nullable=False`

---

### Passo 4: Corrigir Model Manualmente OU Via Autogen

#### Opção A: Correção Manual (Recomendado para Casos Simples)

**Arquivo:** `app/models/team.py`

```python
# ANTES (incorreto)
season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))
# nullable implícito = True (ERRADO)

# DEPOIS (correto)
season_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("seasons.id", name="fk_teams_season_id", ondelete="RESTRICT"),
    nullable=False  # ← Correção
)
```

#### Opção B: Autogen (Para Casos Complexos ou Múltiplas Tabelas)

```powershell
# [CMD] Rodar gate com autogen
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile strict
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Gate passou
if ($ec -eq 0) {
    Write-Host "[OK] Autogen corrigiu model (exit=0)"
} else {
    Write-Host "[FAIL] Gate falhou (exit=$ec)"
    Write-Host "Consulte: docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md (Exit Code $ec)"
    exit $ec
}
```

---

### Passo 5: Revalidar Parity (POST-correção)

```powershell
# [CMD] Parity scan novamente
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "teams"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Parity deve estar clean
if ($ec -ne 0) {
    Write-Host "[FAIL] Parity ainda tem diffs (exit=$ec)" -ForegroundColor Red
    Write-Host "Revise: docs\_generated\parity_report.json"
    exit $ec
} else {
    Write-Host "[OK] Parity clean (exit=0)"
}
```

---

### Passo 6: Validar Requirements (Confirmar Conformidade SSOT)

```powershell
# [CMD] Requirements validation
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" scripts\model_requirements.py --table teams --profile strict
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Requirements clean
if ($ec -eq 4) {
    Write-Host "[FAIL] Requirements violations (exit=4)" -ForegroundColor Red
    Write-Host "Consulte: docs\references\model_requirements_guide.md"
    exit $ec
} else {
    Write-Host "[OK] Requirements clean (exit=0)"
}
```

---

### Passo 7: Snapshot Baseline (Se Guard Violation)

**Somente se você recebeu exit=3 (guard violation) anteriormente:**

```powershell
# [CMD] Snapshot baseline (SOMENTE após gates OK)
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot baseline
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Baseline atualizada
if ($ec -eq 0) {
    Write-Host "[OK] Baseline snapshot criada"
} else {
    Write-Host "[FAIL] Snapshot falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

⚠️ **ATENÇÃO:** Só rode snapshot após confirmar que:
- Parity clean (exit=0)
- Requirements clean (exit=0)
- Repo limpo (`git status --porcelain` vazio ou apenas mudanças intencionais)

---

### Passo 8: Commit (Se Mudanças Foram Feitas)

```powershell
# [VALIDAÇÃO] Verificar mudanças
git status --porcelain
git diff app\models\team.py

# [CMD] Commit apenas arquivos intencionais
git add app\models\team.py
git commit -m "fix(models): correct teams.season_id nullable via parity

- Parity diff: nullable=True → nullable=False
- Evidence: schema.sql:150 NOT NULL constraint
- Validation: parity_scan exit=0, requirements exit=0

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Validação Final (DoD)

**Definition of Done para WF-2:**

- [ ] Parity scan executado e capturado exit code
- [ ] `parity_report.json` analisado (diffs identificados)
- [ ] SSOT (`schema.sql`) consultado para verdade canônica
- [ ] Model corrigido (manual ou autogen)
- [ ] Parity scan POST-correção retorna exit=0
- [ ] Requirements validation retorna exit=0
- [ ] Baseline snapshot executada (se necessário)
- [ ] Commit criado com evidência (antes/depois do parity_report)

---

## Troubleshooting WF-2

### Problema: parity_report.json tem `table: null` e `column: null`

**Causa:** Bug crítico de encoding (UTF-16LE do Tee-Object truncou parser).

**Solução:**
```powershell
# Verificar encoding do log
$logPath = "docs\_generated\parity-scan.log"
[System.IO.File]::ReadAllBytes($logPath)[0..3]
# Esperado: 35 35 35 (### em ASCII UTF-8)
# Se vir FF FE ou bytes 00 intercalados → UTF-16LE problemático

# Regenerar parity scan
.\scripts\parity_scan.ps1 -TableFilter "teams"
```

**Referência:** `docs/references/exit_codes.md` seção "parity_report table null"

### Problema: Autogen não resolve parity diff (exit=2 persiste)

**Causa:** Diff estrutural complexo que autogen não sabe corrigir (ex: UNIQUE constraint, CHECK constraint).

**Solução:**
```powershell
# 1. Revisar parity_report.json para tipo de diff
cat docs\_generated\parity_report.json | jq '.diffs[0]'

# 2. Se diff_type = "add_constraint" → criar migration Alembic
# 3. Se diff_type = "modify_type" → corrigir model manualmente
```

### Problema: Guard violation (exit=3) após parity clean

**Causa:** Baseline desatualizada (não reflete mudanças recentes em SSOT).

**Solução:**
```powershell
# Snapshot baseline APÓS confirmar gates OK
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot baseline

# Revalidar guard
& "venv\Scripts\python.exe" scripts\agent_guard.py check --baseline .hb_guard\baseline.json
```

---

# WF-3: Validar Model Conformance

## Objetivo

Certificar que `app/models/*.py` segue 100% as constraints de `schema.sql` (SSOT).

**Quando usar:**
- Antes de criar PR com mudanças em models
- Após rodar migrations
- Para diagnóstico read-only (sem modificar código)

---

## Pré-requisitos Obrigatórios

```powershell
# CWD correto
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Repo limpo (opcional para validation read-only)
git status --porcelain

# SSOT atualizado
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh
```

---

## Passos Executáveis

### Passo 1: Executar Model Requirements (Read-Only)

```powershell
# [CMD] Validar conformidade model vs schema.sql
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" scripts\model_requirements.py --table "teams" --profile strict
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Capturar exit code
switch ($ec) {
    0 { Write-Host "[OK] Model conforme (100% match com schema.sql)"; exit 0 }
    4 { Write-Host "[WARN] Requirements violations detectadas → revisar output" }
    1 { Write-Host "[ERROR] Crash (exit=1)"; exit 1 }
    default { Write-Host "[ERROR] Exit code inesperado ($ec)"; exit $ec }
}
```

**Exemplo de output (exit=4):**
```
[FAIL] model_requirements strict profile violations (table=teams)
  - TYPE_MISMATCH: season_id expected=Integer got=String (model line 42)
  - MISSING_SERVER_DEFAULT: is_active expected=default_literal:false model_line=55
  - NULLABLE_MISMATCH: name expected=NOT NULL got=nullable=True (model line 38)

Exit code: 4
```

---

### Passo 2: Analisar Violations Detalhadas

**Tipos de violations comuns:**

| Código | Violation | Exemplo | Fix Suggestion |
|--------|-----------|---------|----------------|
| **A1** | EXTRA_COLUMN | Coluna no model que não existe em schema.sql | Remover coluna OU criar migration |
| **A2** | MISSING_COLUMN | Coluna em schema.sql ausente no model | Adicionar coluna no model |
| **B1** | TYPE_MISMATCH | Tipo PG ≠ SA (Date vs String) | Corrigir tipo no model |
| **C1** | NULLABLE_MISMATCH | NOT NULL no DB mas nullable=True no model | Adicionar `nullable=False` |
| **D4** | MISSING_USE_ALTER | FK de ciclo sem use_alter=True | Adicionar `use_alter=True, name=...` |
| **E1** | MISSING_CHECK | CHECK constraint faltando | Adicionar `CheckConstraint` em `__table_args__` |
| **H1** | MISSING_SERVER_DEFAULT | Server default faltando | Adicionar `server_default=text("false")` |

**Referência completa:** `docs/references/exit_codes.md` seção "Exit Code 4"

---

### Passo 3: Corrigir Violations (Opcional - Não Read-Only)

**Se quiser corrigir (não apenas validar):**

```powershell
# [CMD] Rodar gate com autogen para corrigir
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile strict
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Gate passou
if ($ec -ne 0) {
    Write-Host "[FAIL] Gate falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

---

### Passo 4: Revalidar (POST-correção)

```powershell
# [CMD] Revalidar requirements
& "venv\Scripts\python.exe" scripts\model_requirements.py --table "teams" --profile strict
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Deve estar clean
if ($ec -ne 0) {
    Write-Host "[FAIL] Requirements ainda tem violations (exit=$ec)" -ForegroundColor Red
    exit $ec
} else {
    Write-Host "[OK] Requirements clean (exit=0)"
}
```

---

### Passo 5: Executar Testes (Validação Runtime)

```powershell
# [CMD] Rodar testes da tabela/model
& "venv\Scripts\python.exe" -m pytest tests\models\test_team.py -v
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Testes passam
if ($ec -ne 0) {
    Write-Host "[FAIL] Testes falharam (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

---

### Passo 6: Commit (Se Correções Foram Feitas)

```powershell
# [VALIDAÇÃO] Verificar mudanças
git status --porcelain
git diff app\models\team.py

# [CMD] Commit
git add app\models\team.py
git commit -m "fix(models): teams model conformance (requirements violations)

- TYPE_MISMATCH: season_id String → Integer
- NULLABLE_MISMATCH: name nullable=True → False
- MISSING_SERVER_DEFAULT: is_active + server_default

Validation: model_requirements.py exit=0

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Validação Final (DoD)

**Definition of Done para WF-3:**

- [ ] Model requirements executado (`model_requirements.py` exit=0 ou lista de violations capturada)
- [ ] Se exit=4: violations analisadas e categorizadas (tipo A1/B1/C1/etc.)
- [ ] Se correções feitas: model atualizado seguindo fix suggestions
- [ ] Requirements revalidado (exit=0)
- [ ] Testes executados e passaram (pytest exit=0)
- [ ] Commit criado (se modificações foram feitas)

---

## Troubleshooting WF-3

### Problema: TYPE_MISMATCH mas schema.sql e model parecem iguais

**Causa:** Tipo do SQLAlchemy não mapeia exatamente para tipo PostgreSQL.

**Exemplo:**
```python
# Model diz
birth_date: Mapped[str] = mapped_column(String(20))  # ❌ ERRADO

# schema.sql diz
birth_date DATE  # Tipo DATE

# Fix
birth_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)  # ✅ CORRETO
```

### Problema: MISSING_SERVER_DEFAULT para boolean

**Solução:**
```python
# ANTES
is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

# DEPOIS (com server_default)
from sqlalchemy import text
is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
```

### Problema: MISSING_USE_ALTER para teams/seasons (ciclo FK)

**Solução:**
```python
# teams.py
season_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("seasons.id", use_alter=True, name="fk_teams_season_id"),
    nullable=False
)

# seasons.py
champion_team_id: Mapped[int | None] = mapped_column(
    Integer,
    ForeignKey("teams.id", use_alter=True, name="fk_seasons_champion_team_id"),
    nullable=True
)
```

---

# WF-4: Varredura em Lote (Batch Scan)

## Objetivo

Verificar conformidade de **todas as tabelas** do SSOT de uma vez (scan-only, sem correções).

**Quando usar:**
- Validação pré-PR (descobrir quantas/quais tabelas têm violations)
- Após mudanças em schema.sql (validar impacto)
- Diagnóstico rápido de estado do sistema

**Tempo estimado:** 5-15 minutos (15-50 tabelas)

---

## Pré-requisitos Obrigatórios

```powershell
# CWD correto
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Repo limpo (mandatório para batch)
git status --porcelain
# Esperado: vazio (batch aborta se repo sujo)
```

---

## Passos Executáveis

### Passo 1: Executar Batch Scan (DryRun)

```powershell
# [CMD] Batch scan (SSOT refresh + scan, SEM correções)
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\models_batch.ps1 -DryRun
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Batch concluiu
Write-Host "Batch scan exit code: $ec"
```

**Flags disponíveis:**
- `-DryRun` ou `-SkipGate`: Scan-only (sem correções)
- `-SkipRefresh`: Usa schema.sql existente (pula SSOT refresh)
- `-Profile <strict|fk|lenient>`: Perfil de validação (default: strict)
- `-FailFast $false`: Continuar após erros (default: para no primeiro)

---

### Passo 2: Revisar Resumo no Console

**Exemplo de output:**
```
============ MODELS BATCH START ============
Config: Profile=strict, SkipRefresh=False, SkipGate=True
PHASE 1: SSOT Refresh - COMPLETE (2.3s)
PHASE 2: Discovery - 15 tables found
PHASE 3: Scan - START
[1/15] athletes - PASS (exit=0)
[2/15] teams - FAIL (exit=4)
  - VIOLATION: TYPE_MISMATCH: season_id expected=Integer got=String
[3/15] attendance - SKIP_NO_MODEL
...
[15/15] seasons - PASS (exit=0)
PHASE 3: Scan - COMPLETE (PASS: 10, FAIL: 3, SKIP: 2)

============ SUMMARY ============
Total tables: 15
PASS: 10
FAIL: 3 (teams, training_sessions, wellness_pre)
SKIP_NO_MODEL: 2
Exit code: 0 (scan-only não falha)
CSV: C:\Users\user\AppData\Local\Temp\models_batch_20260210_143201.csv
================================
```

---

### Passo 3: Analisar CSV Detalhado

```powershell
# [CMD] Abrir CSV gerado
$csvPath = Get-ChildItem "$env:TEMP\models_batch_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Import-Csv $csvPath.FullName | Format-Table

# [CMD] Filtrar apenas FAIL
Import-Csv $csvPath.FullName | Where-Object { $_.status -eq "FAIL" } | Format-Table table_name, exit_code, profile
```

**Formato CSV:**
```csv
table_name,status,exit_code,profile,timestamp
athletes,PASS,0,strict,2026-02-10T14:32:01
teams,FAIL,4,strict,2026-02-10T14:32:05
attendance,SKIP_NO_MODEL,100,strict,2026-02-10T14:32:06
seasons,PASS,0,strict,2026-02-10T14:32:10
```

---

### Passo 4: Corrigir FAIL Seletivamente (Opcional)

**Se quiser corrigir apenas tabelas FAIL:**

#### Opção A: Gate Individual (Uma por Vez)

```powershell
# [CMD] Corrigir tabela específica via gate
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile strict
$ec = $LASTEXITCODE

# Repetir para outras FAIL
.\scripts\models_autogen_gate.ps1 -Table "training_sessions" -Profile strict
```

#### Opção B: Batch com Fix (Todas FAIL de Uma Vez)

```powershell
# [CMD] Batch completo (scan + fix)
.\scripts\models_batch.ps1
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Exit code
if ($ec -ne 0) {
    Write-Host "[FAIL] Batch falhou em alguma tabela (exit=$ec)" -ForegroundColor Red
    Write-Host "Revise log: $env:TEMP\models_batch_*.log"
    exit $ec
}
```

⚠️ **ATENÇÃO:** Batch com fix usa fail-fast (para no primeiro erro). Se preferir corrigir todas (mesmo com erros), use `-FailFast:$false`.

---

### Passo 5: Revalidar Batch (POST-correção)

```powershell
# [CMD] Batch scan novamente
.\scripts\models_batch.ps1 -DryRun
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Todas PASS ou SKIP
# Esperado output:
# PASS: 13, FAIL: 0, SKIP: 2
```

---

## Validação Final (DoD)

**Definition of Done para WF-4:**

- [ ] Batch scan executado com sucesso (exit=0 em scan-only)
- [ ] Resumo revisado (counts de PASS/FAIL/SKIP)
- [ ] CSV gerado e analisado (tabelas FAIL identificadas)
- [ ] Se correções feitas: batch revalidado (FAIL → 0)
- [ ] Commits criados para cada tabela corrigida (se aplicável)

---

## Troubleshooting WF-4

### Problema: "Repository must be clean" (exit=3)

**Causa:** Batch detectou arquivos uncommitted (pré-flight check).

**Solução:**
```powershell
# Opção 1: Commit changes
git add . && git commit -m "wip: changes before batch"

# Opção 2: Stash temporário
git stash
.\scripts\models_batch.ps1 -DryRun
git stash pop

# Opção 3: Scan-only com schema.sql existente (se SSOT OK)
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
```

### Problema: Exit=2 em batch mas parity_scan individual retorna exit=0

**Causa:** Batch refresh gerou novo schema.sql → parity diff apareceu.

**Solução:**
```powershell
# Refresh SSOT manualmente ANTES de batch
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh

# Rodar batch SEM refresh
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\models_batch.ps1 -SkipRefresh
```

---

# WF-5: Diagnosticar parity_report.json

## Objetivo

Investigar conteúdo de `parity_report.json` quando há dúvida sobre diffs ou para auditoria.

**Quando usar:**
- parity_scan retornou exit=2 e você quer entender o diff
- Verificar se `table` e `column` estão preenchidos (bug de encoding)
- Auditar mudanças estruturais após migrations

---

## Passos Executáveis

### Passo 1: Abrir parity_report.json

```powershell
# [CMD] Abrir relatório
$reportPath = "C:\HB TRACK\Hb Track - Backend\docs\_generated\parity_report.json"
if (Test-Path $reportPath) {
    Get-Content $reportPath -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 10
} else {
    Write-Host "[ERROR] parity_report.json não encontrado"
    exit 1
}
```

---

### Passo 2: Verificar que `table` e `column` Estão Preenchidos

```powershell
# [CMD] Validar campos não-null
$report = Get-Content $reportPath -Raw | ConvertFrom-Json

# Check por table null (bug crítico)
$nullTables = $report.diffs | Where-Object { $_.table -eq $null -or $_.table -eq "" }
if ($nullTables.Count -gt 0) {
    Write-Host "[ERROR] BUG CRÍTICO: parity_report tem table=null ($($nullTables.Count) diffs)" -ForegroundColor Red
    Write-Host "Causa: UTF-16LE encoding do log (ver exit_codes.md seção 'parity_report table null')"
    exit 1
} else {
    Write-Host "[OK] Todos os diffs têm table preenchido"
}
```

**Se `table: null` → Consultar:** `docs/references/exit_codes.md` seção "Q: parity_report.json mostra `table: null`"

---

### Passo 3: Filtrar Diffs por Tipo

```powershell
# [CMD] Filtrar structural diffs
$report = Get-Content $reportPath -Raw | ConvertFrom-Json
$structuralDiffs = $report.diffs | Where-Object { $_.type -eq "structural" }
Write-Host "Structural diffs: $($structuralDiffs.Count)"
$structuralDiffs | Format-Table table, column, diff_type, severity

# [CMD] Filtrar warnings (não-bloqueadores)
$warnings = $report.diffs | Where-Object { $_.type -eq "warning" }
Write-Host "Warnings: $($warnings.Count)"
$warnings | Format-Table table, column, diff_type
```

**Tipos de diff:**
- `structural`: Diff bloqueador (ex: coluna faltando, tipo errado)
- `warning`: Diff não-bloqueador (ex: SAWarning de ciclo FK)

---

### Passo 4: Regenerar parity_report (Se Necessário)

```powershell
# [CMD] Regenerar parity report para tabela específica
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "teams"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Report regenerado
if ($ec -eq 0) {
    Write-Host "[OK] parity_report.json regenerado (exit=0)"
} else {
    Write-Host "[WARN] Parity diffs detectados (exit=$ec)"
}
```

---

### Passo 5: Scan sem SSOT Refresh (Diagnóstico Rápido)

```powershell
# [CMD] Parity scan sem refresh (usa schema.sql existente)
.\scripts\parity_scan.ps1 -TableFilter "teams" -SkipDocsRegeneration
$ec = $LASTEXITCODE

# Útil quando:
# - Você acabou de rodar inv.ps1 refresh
# - Quer diagnóstico rápido sem overhead de pg_dump
```

---

## Validação Final (DoD)

**Definition of Done para WF-5:**

- [ ] `parity_report.json` aberto e inspecionado
- [ ] Validado que `table` e `column` não são null
- [ ] Diffs categorizados (structural vs warning)
- [ ] Se necessário: relatório regenerado via `parity_scan.ps1`

---

## Troubleshooting WF-5

### Problema: parity_report.json tem `table: null` (P0 Bug)

**Causa raiz:** `Tee-Object` do PowerShell 5.1 escreveu log em UTF-16LE → parser Python truncou.

**Verificação:**
```powershell
# [CMD] Verificar encoding do log
$logPath = "docs\_generated\parity-scan.log"
[System.IO.File]::ReadAllBytes($logPath)[0..3]
# UTF-8 correto: 35 35 35 (### em ASCII)
# UTF-16LE problemático: FF FE (BOM) ou bytes 00 intercalados
```

**Solução:**
```powershell
# Confirmar que parity_scan.ps1 usa WriteAllText (não Tee-Object)
# Confirmar que parity_classify.py tem strip de NUL bytes em read_log_lines()

# Regenerar parity scan
.\scripts\parity_scan.ps1 -TableFilter "teams"
```

**Referência:** `docs/references/exit_codes.md` (bug corrigido em 2026-02-10)

---

# WF-6: Refresh SSOT Completo

## Objetivo

Regenerar **todos** os artefatos gerados (schema.sql, openapi.json, alembic_state.txt, manifest.json).

**Quando usar:**
- Antes de rodar gates/parity (1x por sessão)
- Após rodar migrations (`alembic upgrade head`)
- Após mudanças em API routes ou models
- Quando manifest.json está desatualizado

---

## Pré-requisitos Obrigatórios

```powershell
# CWD correto (REPO ROOT, não backend)
Set-Location "C:\HB TRACK"

# PostgreSQL acessível
psql -h localhost -U hbtrack -d hbtrack_dev -c "SELECT 1;"
# Esperado: (1 row)
```

---

## Passos Executáveis

### Passo 1: Executar inv.ps1 refresh

```powershell
# [CMD] Refresh SSOT
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Refresh concluído
if ($ec -ne 0) {
    Write-Host "[FAIL] SSOT refresh falhou (exit=$ec)" -ForegroundColor Red
    Write-Host "Verifique: DB acessível, pg_dump disponível"
    exit $ec
} else {
    Write-Host "[OK] SSOT refresh concluído (exit=0)"
}
```

---

### Passo 2: Validar Artefatos Atualizados

```powershell
# [CMD] Verificar timestamp dos artefatos
$schemaFile = "Hb Track - Backend\docs\_generated\schema.sql"
$openapiFile = "Hb Track - Backend\docs\_generated\openapi.json"
$alembicFile = "Hb Track - Backend\docs\_generated\alembic_state.txt"
$manifestFile = "Hb Track - Backend\docs\_generated\manifest.json"

$files = @($schemaFile, $openapiFile, $alembicFile, $manifestFile)
foreach ($file in $files) {
    if (Test-Path $file) {
        $lastWrite = (Get-Item $file).LastWriteTime
        $age = (Get-Date) - $lastWrite
        Write-Host "$file - Age: $($age.TotalMinutes.ToString('F2')) minutes"
    } else {
        Write-Host "[WARN] $file não encontrado" -ForegroundColor Yellow
    }
}

# [VALIDAÇÃO] Todos devem ter age < 5min
```

---

### Passo 3: Verificar Manifest.json (Rastreabilidade)

```powershell
# [CMD] Inspecionar manifest
$manifestPath = "Hb Track - Backend\docs\_generated\manifest.json"
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

Write-Host "Git commit: $($manifest.git_commit)"
Write-Host "Timestamp: $($manifest.timestamp)"
Write-Host "Schema checksum: $($manifest.checksums.schema_sql)"
```

**Campos esperados no manifest:**
```json
{
  "git_commit": "abc123def456...",
  "timestamp": "2026-02-10T14:32:01Z",
  "checksums": {
    "schema_sql": "sha256:...",
    "openapi_json": "sha256:..."
  }
}
```

---

## Validação Final (DoD)

**Definition of Done para WF-6:**

- [ ] `inv.ps1 refresh` executado (exit=0)
- [ ] Artefatos atualizados (age < 5min):
  - [ ] `schema.sql`
  - [ ] `openapi.json`
  - [ ] `alembic_state.txt`
  - [ ] `manifest.json`
- [ ] Manifest.json contém git commit atual e checksums válidos

---

## Troubleshooting WF-6

### Problema: "pg_dump: command not found"

**Causa:** PostgreSQL client tools não estão no PATH.

**Solução:**
```powershell
# Adicionar PostgreSQL bin ao PATH temporariamente
$env:PATH += ";C:\Program Files\PostgreSQL\14\bin"

# Reexecutar refresh
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh
```

### Problema: schema.sql não foi atualizado (age > 5min)

**Causa:** pg_dump falhou silenciosamente ou script não completou.

**Solução:**
```powershell
# Executar pg_dump manualmente para diagnóstico
pg_dump -h localhost -U hbtrack -d hbtrack_dev --schema-only --no-owner --no-acl -f "Hb Track - Backend\docs\_generated\schema.sql"

# Verificar se arquivo foi atualizado
Get-Item "Hb Track - Backend\docs\_generated\schema.sql" | Select-Object LastWriteTime
```

---

# WF-7: Snapshot Baseline (Guard)

## Objetivo

Registrar novo estado conformante do sistema após gates OK (para guard detectar diffs futuros).

**Quando usar:**
- Após `models_autogen_gate.ps1` com exit=0
- Após commit que altera arquivos protegidos/SSOT
- Quando autorizado explicitamente pelo usuário

⚠️ **CRÍTICO:** **Nunca** snapshot com repo quebrado (exit 2/3/4).

---

## Pré-requisitos Mandatórios

```powershell
# CWD correto
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Repo limpo OU apenas mudanças intencionais staged
git status --porcelain

# Gates OK (parity + requirements)
# Você DEVE ter confirmado exit=0 em:
# - parity_scan.ps1 -TableFilter <TABLE>
# - model_requirements.py --table <TABLE> --profile strict
```

**Regra de ouro:** Snapshot = "registrar estado conformante e testado". **Nunca** snapshot de repo quebrado.

---

## Quando é PROIBIDO Snapshot

❌ **NUNCA snapshot se:**
- Exit code 2 (parity diffs não resolvidos)
- Exit code 3 (guard violation - criar snapshot não resolve isso)
- Exit code 4 (requirements violations não resolvidas)
- `git status --porcelain` mostra arquivos não intencionais (ex: `docs/_generated/*` modificados acidentalmente)
- Parity ainda falha (structural diffs persistentes)

---

## Passos Executáveis

### Passo 1: Validar Pré-requisitos

```powershell
# [PREREQ 1] Repo limpo ou staged intencional
git status --porcelain
# Esperado: vazio OU apenas app/models/*.py staged

# [PREREQ 2] Parity clean
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "teams"
$ec = $LASTEXITCODE
if ($ec -ne 0) {
    Write-Host "[ABORT] Parity não está clean (exit=$ec)" -ForegroundColor Red
    exit $ec
}

# [PREREQ 3] Requirements clean
& "venv\Scripts\python.exe" scripts\model_requirements.py --table teams --profile strict
$ec = $LASTEXITCODE
if ($ec -ne 0) {
    Write-Host "[ABORT] Requirements não está clean (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

---

### Passo 2: Executar Snapshot Baseline

```powershell
# [CMD] Snapshot baseline
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot baseline
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Snapshot criada
if ($ec -ne 0) {
    Write-Host "[FAIL] Snapshot falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
} else {
    Write-Host "[OK] Baseline snapshot criada"
}
```

**Comando alternativo (se wrapper PowerShell disponível):**
```powershell
.\scripts\agent_guard.ps1 snapshot baseline
```

---

### Passo 3: Verificar Baseline Atualizada

```powershell
# [CMD] Verificar baseline.json
$baselinePath = ".hb_guard\baseline.json"
if (Test-Path $baselinePath) {
    $baseline = Get-Content $baselinePath -Raw | ConvertFrom-Json
    Write-Host "Baseline timestamp: $($baseline.timestamp)"
    Write-Host "Files tracked: $($baseline.files.Count)"
} else {
    Write-Host "[ERROR] baseline.json não foi criada" -ForegroundColor Red
    exit 1
}
```

---

## Validação Final (DoD)

**Definition of Done para WF-7:**

- [ ] Pré-requisitos validados (parity clean, requirements clean, repo limpo/staged)
- [ ] Snapshot baseline executado (exit=0)
- [ ] `baseline.json` atualizado (timestamp recente)
- [ ] Baseline commitado (se modificado)
- [ ] Guard check passou (exit=0) após snapshot

---

## Troubleshooting WF-7

### Problema: Snapshot falha com "files not in allowlist"

**Causa:** Guard detectou arquivos fora da allowlist (ex: `app/routes/*.py` modificado).

**Solução:**
```powershell
# Opção 1: Adicionar arquivo à allowlist (se legítimo)
.\scripts\models_autogen_gate.ps1 -Table "teams" -Allow "app/routes/teams.py"

# Opção 2: Reverter mudanças não intencionais
git restore app/routes/teams.py

# Após resolver: snapshot novamente
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot baseline
```

### Problema: Baseline não mudou mas guard ainda falha (exit=3)

**Causa:** Baseline em memória (cache) desatualizada.

**Solução:**
```powershell
# Forçar re-read da baseline
Remove-Item .hb_guard\baseline.json.cache -ErrorAction SilentlyContinue
& "venv\Scripts\python.exe" scripts\agent_guard.py check --baseline .hb_guard\baseline.json
```

---

# WF-8: Criar Migration Alembic

## Objetivo

Adicionar ou modificar estrutura de tabela no PostgreSQL via Alembic migration.

**Quando usar:**
- Adicionar nova tabela
- Adicionar/remover coluna
- Modificar tipo de coluna
- Adicionar/remover constraint (FK, CHECK, UNIQUE)

---

## Pré-requisitos Obrigatórios

```powershell
# CWD correto
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Repo limpo
git status --porcelain

# DB acessível
psql -h localhost -U hbtrack -d hbtrack_dev -c "SELECT 1;"
```

---

## Passos Executáveis

### Passo 1: Criar Migration (Manual ou Autogenerate)

#### Opção A: Autogenerate (Recomendado para Mudanças em Models)

```powershell
# [CMD] Autogenerate migration a partir de mudanças em models
& "venv\Scripts\python.exe" -m alembic revision --autogenerate -m "add column is_active to teams"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Migration criada
if ($ec -ne 0) {
    Write-Host "[FAIL] Autogenerate falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
}
```

#### Opção B: Manual (Para Mudanças SQL Diretas)

```powershell
# [CMD] Criar migration vazia
& "venv\Scripts\python.exe" -m alembic revision -m "add check constraint duration max"
$ec = $LASTEXITCODE

# Editar migration gerada manualmente
```

---

### Passo 2: Editar Migration (Se Necessário)

**Arquivo:** `alembic/versions/XXXX_add_column_is_active_to_teams.py`

```python
"""add column is_active to teams

Revision ID: abc123def456
Create Date: 2026-02-10 14:32:01
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('teams', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))

def downgrade():
    op.drop_column('teams', 'is_active')
```

---

### Passo 3: Validar Migration (Dry-Run)

```powershell
# [CMD] Mostrar SQL que será executado (sem aplicar)
& "venv\Scripts\python.exe" -m alembic upgrade head --sql
# Review do SQL gerado
```

---

### Passo 4: Aplicar Migration

```powershell
# [CMD] Aplicar migration no DB
& "venv\Scripts\python.exe" -m alembic upgrade head
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Migration aplicada
if ($ec -ne 0) {
    Write-Host "[FAIL] Migration falhou (exit=$ec)" -ForegroundColor Red
    exit $ec
} else {
    Write-Host "[OK] Migration aplicada"
}
```

---

### Passo 5: Atualizar Model (Se Aplicável)

**Se migration adicionou coluna → atualizar model:**

**Arquivo:** `app/models/team.py`

```python
class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Nova coluna adicionada
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
```

---

### Passo 6: Refresh SSOT e Validar Parity

```powershell
# [CMD] Refresh SSOT
Set-Location "C:\HB TRACK"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\inv.ps1" refresh

# [CMD] Validar parity
Set-Location "C:\HB TRACK\Hb Track - Backend"
.\scripts\parity_scan.ps1 -TableFilter "teams"
$ec = $LASTEXITCODE

# [VALIDAÇÃO] Parity clean
if ($ec -ne 0) {
    Write-Host "[WARN] Parity diff detectado (exit=$ec)"
    Write-Host "Revise: model pode estar desatualizado"
}
```

---

### Passo 7: Commit

```powershell
# [VALIDAÇÃO] Verificar mudanças
git status --porcelain

# [CMD] Commit migration + model
git add "alembic\versions\XXXX*.py"
git add "app\models\team.py"
git commit -m "feat(db): add is_active column to teams

- Migration: ADD COLUMN is_active BOOLEAN DEFAULT true
- Model: teams.py updated with is_active field
- Validation: parity_scan exit=0

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Validação Final (DoD)

**Definition of Done para WF-8:**

- [ ] Migration criada (`alembic revision` exit=0)
- [ ] Migration aplicada (`alembic upgrade head` exit=0)
- [ ] Model atualizado (se aplicável)
- [ ] SSOT refresh executado (`inv.ps1 refresh` exit=0)
- [ ] Parity clean (`parity_scan` exit=0)
- [ ] Commit criado com migration + model

---

## Troubleshooting WF-8

### Problema: Autogenerate não detecta mudanças no model

**Causa:** Alembic não vê mudanças (model não importado, ou mudança não suportada por autogenerate).

**Solução:**
```powershell
# Criar migration manual
& "venv\Scripts\python.exe" -m alembic revision -m "manual migration"

# Editar migration com SQL direto
```

### Problema: Migration falha com "column already exists"

**Causa:** Coluna já foi criada manualmente ou em migration anterior.

**Solução:**
```powershell
# Reverter migration
& "venv\Scripts\python.exe" -m alembic downgrade -1

# Editar migration para usar op.execute com IF NOT EXISTS
op.execute("""
    ALTER TABLE teams ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true
""")
```

---

## Referências Cruzadas

**Para mais informações:**

| Tópico | Documento |
|--------|-----------|
| Exit codes (0/1/2/3/4) | `docs/references/exit_codes.md` |
| Pipeline de models | `docs/_canon/05_MODELS_PIPELINE.md` |
| Troubleshooting guard/parity | `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md` |
| Comandos aprovados | `docs/_canon/08_APPROVED_COMMANDS.md` |
| Agent prompts | `docs/_ai/06_AGENT-PROMPTS.md` |
| Testing canon | `docs/02_modulos/training/INVARIANTS/INVARIANTS_TESTING_CANON.md` |
| Model requirements guide | `docs/references/model_requirements_guide.md` |
| SSOT precedência | `docs/ADR/001-ADR-TRAIN-ssot-precedencia.md` |
| Models ADR | `docs/ADR/013-ADR-MODELS.md` |
| Batch ADR | `docs/ADR/014-ADR-MODELS.md` |

---

## Changelog

- **2026-02-10:** Versão inicial (expandida de 79 para 2000+ linhas)
  - Adicionados 8 workflows executáveis detalhados
  - Comandos PowerShell completos com validação
  - Exit codes documentados por workflow
  - Troubleshooting específico por workflow
  - Cross-references para documentação canônica
  - DoD (Definition of Done) para cada workflow
  - Pré-requisitos objetivos e verificáveis

---

**Última atualização:** 2026-02-10
**Responsável:** Tech Lead + AI Assistant
**Status:** CANÔNICO (precedência sobre outros docs em caso de conflito sobre workflows)

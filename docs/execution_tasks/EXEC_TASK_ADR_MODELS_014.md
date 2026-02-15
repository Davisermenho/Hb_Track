## EXEC_TASK — Batch determinístico para varredura e correção de Models (14-ADR-MODELS)

Status: ✅ DONE (2026-02-10)
Prioridade: P0
Assignee: Você + Cline
Escopo: Backend (`Hb Track - Backend/`)

**Resultado:** Script `models_batch.ps1` já estava implementado e funcional. Todos os 5 smoke tests passaram com sucesso.

Smoke Tests Executados:
1. ✅ Repo sujo aborta com exit=3
2. ✅ Scan completo sem gate (exit=0, LOG e CSV gerados)
3. ✅ SKIP_NO_MODEL funciona (advantage_states)
4. ✅ Gate fail-fast para no primeiro erro (competition_matches, exit=2)
5. ✅ Guard violation detectado (exit=3)

---

# 0) Fase de Preparação

## 0.1 Ler primeiro (ordem obrigatória)

1. `docs/_canon/00_START_HERE.md`
2. `docs/_canon/01_AUTHORITY_SSOT.md` (SSOT = `docs/_generated/schema.sql`)
3. `docs/_canon/05_MODELS_PIPELINE.md` (pipeline atual)
4. `docs/references/exit_codes.md` (0/1/2/3/4)
5. `docs/ADR/014-ADR-MODELS.md` (decisão arquitetural detalhada)
6. Scripts existentes:

   * `Hb Track - Backend/scripts/models_autogen_gate.ps1`
   * `Hb Track - Backend/scripts/parity_gate.ps1`
   * `Hb Track - Backend/scripts/agent_guard.py`
   * `Hb Track - Backend/scripts/model_requirements.py`
   * `Hb Track - Backend/scripts/inv.ps1` (ou wrapper central)

## 0.2 Dependências / ambiente (não instalar nada novo sem necessidade)

* PowerShell 5.1 (assumido)
* venv existente: `Hb Track - Backend/venv/Scripts/python.exe`
* `git` funcional
* DB local acessível para `inv.ps1 refresh` quando necessário

Verificações obrigatórias (ABORT se falhar):

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
Test-Path .\venv\Scripts\python.exe
Test-Path .\scripts\model_requirements.py
Test-Path .\scripts\models_autogen_gate.ps1
Test-Path .\scripts\agent_guard.py
git status --porcelain
```

Esperado:

* `Test-Path` tudo True
* `git status --porcelain` vazio

---

# 1) Implementação do Script

## 1.1 Onde criar

Criar/atualizar:

* `Hb Track - Backend/scripts/models_batch.ps1`

> Importante: **logs e CSV vão para `%TEMP%`**. Proibido criar arquivos temporários no repo.

## 1.2 Funções obrigatórias (mínimo)

O script deve ser determinístico e fail-fast.

### (A) Infra / segurança

* `Abort(message, exitcode)`
* `Ensure-BackendRoot()` (confirma CWD + venv + scripts)
* `Ensure-CleanRepo()` (git status porcelain vazio → senão abort com exit=3)

### (B) SSOT e tabelas

* `Run-RefreshSSOT()` (chama `C:\HB TRACK\scripts\inv.ps1 refresh` 1x; respeita `-SkipRefresh`)
* `Load-TablesFromSSOT(exclude[])` (extrai tabelas de `docs/_generated/schema.sql`)
* `Load-TablesManual(-Tables/-TablesFile)` (quando AutoTables=None)

### (C) Profiles

* `Get-ProfileForTable(table)`

  * default = strict
  * tabelas de ciclo FK conhecidas → profile `fk` (pode começar com teams/seasons)

### (D) Hygiene (gerados)

* `Restore-GeneratedArtifacts()`

  * restaurar apenas paths conhecidos (`docs/_generated/*` no backend e no root)
  * **não** engolir erro silenciosamente: se restore falhar, abort exit=1

### (E) Execuções

* `Run-Requirements(table, profile, logPath)`
  Regras:

  * **SKIP_NO_MODEL por Test-Path** antes do python: `app/models/<table>.py` ausente → retornar código interno `100`
  * executar `venv\Scripts\python.exe scripts\model_requirements.py ...`
  * capturar `$LASTEXITCODE` **antes** de pipeline/log
* `Run-Gate(table, profile, logPath)`
  Regras:

  * chamar `scripts\models_autogen_gate.ps1`
  * para profile `fk`, passar `-AllowCycleWarning`
  * capturar `$LASTEXITCODE` imediatamente (sem Tee antes de salvar)

### (F) Baseline (apenas se autorizado)

* `Invoke-ConditionalBaseline(logPath)`

  * default OFF
  * só roda se `-AllowBaselineSnapshot`
  * **não commita** baseline automaticamente

## 1.3 Regras comportamentais do script (obrigatórias)

* Fail-fast ON por padrão (implementar corretamente: `-NoFailFast` ou bool)
* Não usar códigos canônicos (2/3/4) para SKIP → usar `100`
* Não depender de texto de erro para missing model
* Capturar `$LASTEXITCODE` imediatamente
* Não deixar repo sujo:

  * rodar restore de gerados após cada tabela
  * validar `git status --porcelain` nos checkpoints

---

# 2) Migração / Integração

## 2.1 Desativar script antigo (se existir)

Se houver `scripts/models_batch_old.ps1` ou equivalente:

* Não deletar de imediato.
* Marcar como deprecated no topo:

  * “DEPRECATED — use scripts/models_batch.ps1”
* Opcional: mover para `scripts/_deprecated/` (somente se o guard permitir e com commit isolado).

## 2.2 Integração com models_autogen_gate.ps1

Sem mudar comportamento do gate (somente integração/documentação):

* `models_batch.ps1` deve usar `models_autogen_gate.ps1` como “gate unitário”.
* Não duplicar lógica do gate no batch.
* `models_autogen_gate.ps1` não deve chamar `models_batch.ps1`.

Opcional (somente se fizer sentido):

* adicionar uma seção em `docs/_canon/05_MODELS_PIPELINE.md` “Batch Mode” com comando canônico.

---

# 3) Critérios de Aceite (Testes obrigatórios)

## 3.1 Smoke tests (repo hygiene + scan)

1. **Repo sujo aborta**:

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
New-Item -ItemType File -Path ".\_tmp_should_fail.txt" | Out-Null
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
$LASTEXITCODE
Remove-Item ".\_tmp_should_fail.txt"
```

Esperado:

* abort
* exit code = 3
* mensagem com `Repo não está limpo`

2. **Scan completo sem gate**

```powershell
git status --porcelain   # vazio
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
$LASTEXITCODE
```

Esperado:

* exit=0
* gera LOG+CSV em `%TEMP%`
* CSV contém PASS/FAIL/SKIP_NO_MODEL

3. **SKIP_NO_MODEL funciona**

* Confirmar que uma tabela sem model (ex.: `advantage_states`) aparece como `SKIP_NO_MODEL` (exit=100 no CSV).

## 3.2 Gate mode (fail-fast real)

4. **Rodar gate apenas nas FAIL e parar no primeiro erro**

```powershell
git status --porcelain   # vazio
.\scripts\models_batch.ps1 -SkipRefresh
$LASTEXITCODE
```

Esperado:

* se encontrar erro real: para imediatamente e mostra tabela + caminho do log
* exit code propagado do gate (2/3/4/1)

## 3.3 Exit code integrity

5. Induzir guard violation (não editar gerados; editar um arquivo tracked):

```powershell
Add-Content .\docs\references\exit_codes.md "`n<!-- smoke_guard -->"
.\scripts\models_batch.ps1 -SkipGate -SkipRefresh
$LASTEXITCODE
git restore -- .\docs\references\exit_codes.md
```

Esperado:

* abort exit=3 no Ensure-CleanRepo

---

# 4) O Prompt Final

```text
--- 
description: Executar ADR-MODELS-003 — implementar batch runner determinístico para varredura e correção de models (SSOT → requirements → gate) com fail-fast e repo hygiene
# applyTo: 'Hb Track - Backend/scripts/models_batch.ps1'
---

Você é o agente Cline trabalhando no repo HB Track. Siga estritamente o escopo abaixo e pare no primeiro erro.

OBJETIVO
Implementar/atualizar o script: Hb Track - Backend/scripts/models_batch.ps1 conforme ADR-MODELS-003:
- Refresh SSOT 1x (inv.ps1 refresh) quando permitido
- Extrair tabelas automaticamente do SSOT docs/_generated/schema.sql
- Rodar requirements em lote e classificar PASS/FAIL/SKIP_NO_MODEL
- Rodar models_autogen_gate.ps1 apenas nas FAIL, 1 por vez
- Fail-fast: parar imediatamente no primeiro erro real (exit != 0) em qualquer etapa
- Repo hygiene: nunca criar arquivos temporários no repo; logs e CSV devem ir para %TEMP%
- Capturar $LASTEXITCODE imediatamente após cada comando (sem pipeline que altere o valor)
- SKIP_NO_MODEL deve ser detectado via Test-Path do arquivo app/models/<table>.py (não por texto)
- Usar código interno 100 para SKIP_NO_MODEL (não usar 2/3/4)

PREPARAÇÃO (LEITURA OBRIGATÓRIA)
Leia e siga:
1) docs/_canon/00_START_HERE.md
2) docs/_canon/01_AUTHORITY_SSOT.md
3) docs/_canon/05_MODELS_PIPELINE.md
4) docs/references/exit_codes.md
5) scripts/models_autogen_gate.ps1, scripts/model_requirements.py, scripts/agent_guard.py

REGRAS
- Não criar/modificar outros arquivos além de scripts/models_batch.ps1 (exceto se estritamente necessário e justificado).
- Não atualizar baseline automaticamente. Apenas implementar flag -AllowBaselineSnapshot que executa snapshot mas NÃO commita.
- Não alterar modelos, não rodar “fixes” nos models nesta tarefa.
- Não rodar comandos “tentando até dar certo”: se um comando falhar, pare e reporte o erro com o comando e saída.

ENTREGÁVEIS
1) scripts/models_batch.ps1 implementado com funções:
   Abort, Ensure-BackendRoot, Ensure-CleanRepo, Run-RefreshSSOT, Load-TablesFromSSOT, Load-TablesManual,
   Get-ProfileForTable, Restore-GeneratedArtifacts (sem engolir erro), Run-Requirements (Test-Path + 100),
   Run-Gate (captura exitcode segura), Invoke-ConditionalBaseline (somente com flag)
2) Parâmetros:
   -AutoTables FromSSOT/None, -ExcludeTables, -Tables, -TablesFile, -DefaultProfile strict/fk/lenient,
   -SkipRefresh, -SkipGate, -NoFailFast (failfast ON por default), -AllowBaselineSnapshot
3) Logs e CSV em %TEMP%: hb_models_batch_<timestamp>.log / .csv

TESTES (OBRIGATÓRIOS)
Após implementar, rode e cole os outputs:
A) git status --porcelain (deve estar vazio)
B) .\scripts\models_batch.ps1 -SkipGate -SkipRefresh (deve sair 0 e gerar CSV/LOG)
C) Confirmar que ao menos uma tabela sem model aparece como SKIP_NO_MODEL no CSV

PARE IMEDIATAMENTE se qualquer teste falhar e reporte:
- comando
- exit code
- últimas 30 linhas do output

```



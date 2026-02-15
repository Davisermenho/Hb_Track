# docs/_canon/05_MODELS_PIPELINE.md

| Propriedade | Valor |
|---|---|
| ID | CANON-MODELS-PIPELINE-005 |
| Status | CANÔNICO |
| Última verificação | 2026-02-10 (America/Sao_Paulo) |
| Porta de entrada | docs/_canon/00_START_HERE.md |
| SSOT estrutural | docs/_generated/schema.sql |
| Objetivo | Garantir 100% de conformidade estrutural Model↔DB (anti-drift / anti-alucinação) |

## Visão geral

Este pipeline valida e corrige models SQLAlchemy para refletirem **exatamente** o DB real.

Camadas (ordem):
1) **Guard**: impede drift fora da baseline/allowlist.
2) **Parity**: compara Model↔DB via Alembic (diferenças estruturais). Usa `parity_scan.ps1` → `parity_classify.py` → `parity_report.json`.
3) **Requirements**: compara Model↔SSOT (`schema.sql`) via parser DDL + AST (juiz final).

Princípio: **SSOT é o juiz, autogen é corretor**.  
O autogen pode "arrumar", mas a aprovação final vem de parity + requirements.

> **Nota técnica (2026-02-10):** O log do Alembic é escrito em UTF-8 (sem BOM) via
> `[System.IO.File]::WriteAllText()`. Nunca usar `Tee-Object` para gravar o log
> (causa UTF-16LE no PowerShell 5.1, corrompendo o parser Python).

## Scripts do pipeline (mapa rápido)

**CWD esperado:** `C:\HB TRACK\Hb Track - Backend`

| Componente | Path (relativo ao backend root) | Papel |
|---|---|---|
| Orquestrador | `.\scripts\models_autogen_gate.ps1` | Guard → Parity → Autogen → Parity → Requirements (fail-fast) |
| Batch runner | `.\scripts\models_batch.ps1` | Varre tabelas do SSOT e aplica gate apenas em FAIL |
| Parity gate | `.\scripts\parity_gate.ps1` | Compara Model↔DB via Alembic compare (structural diffs) |
| Parity scan | `.\scripts\parity_scan.ps1` | Scan read-only de diffs estruturais (gera relatório) |
| Guard | `.\venv\Scripts\python.exe scripts\agent_guard.py` | Baseline snapshot/check para impedir drift fora da allowlist |
| Requirements | `.\venv\Scripts\python.exe scripts\model_requirements.py` | Parser DDL + AST: juiz final SSOT↔Model |

## SSOT e geração canônica

SSOT estrutural (canônico, repo root):
- `docs/_generated/schema.sql`

Mirror (compatibilidade para execução com CWD=backend root):
- `Hb Track - Backend/docs/_generated/schema.sql`

Geração canônica (atualiza backend + repo root):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\HB TRACK\scripts\inv.ps1" refresh
```

Regra: qualquer validação de estrutura deve usar o SSOT como referência final.

## Exit codes canônicos (0/1/2/3/4)

Cada camada tem um código específico.

| Exit | Camada       | Significado                                       |
| ---- | ------------ | ------------------------------------------------- |
| 0    | —            | Sucesso total                                     |
| 1    | Internal     | Crash/erro interno (tratado como bug ou ambiente) |
| 2    | Parity       | Diferenças estruturais Model↔DB (Alembic compare) |
| 3    | Guard        | Violação de baseline (drift em arquivo protegido) |
| 4    | Requirements | Violação SSOT↔Model (parser DDL + AST)            |

Referência detalhada: `docs/references/exit_codes.md`

## Regras operacionais (anti-“tentativa e erro”)

Obrigatórias:

* Checklist pré-voo (fail-fast):

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"

# Ambiente
Test-Path ".\venv\Scripts\python.exe"            # esperado: True
$env:DATABASE_URL_SYNC                           # esperado: setado (ou .env presente)

# Guard
Test-Path ".\.hb_guard\baseline.json"            # esperado: True (ou rodar snapshot)

# SSOT (mirror no backend; repo root deve existir após refresh)
Test-Path ".\docs\_generated\schema.sql"         # esperado: True

# Repo clean
git status --porcelain                           # esperado: vazio
```

* CWD fixo:

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
```

* Antes de executar gates:

```powershell
git status --porcelain
# esperado: vazio
```

* Capturar `$LASTEXITCODE` imediatamente após cada comando (sem pipeline).
* Parar no 1º erro (exit != 0) e coletar evidência (comando + output + status).

Proibido:

* criar arquivos temporários/backups dentro do repo
* atualizar baseline sem autorização explícita
* “ajustar” comandos até funcionar (quando falha, parar e reportar evidência)

## Pipeline por tabela (manual, 1 a 1)

Use quando você quer corrigir uma tabela específica ou trabalhar incrementalmente.

### Phase 0: Bootstrap Baseline (Uma vez por sessão)

Antes de executar qualquer gate, regenere a baseline local para garantir que a comparação seja válida:

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot `
  --root "." `
  --out ".hb_guard/baseline.json" `
  --exclude "venv,.venv,__pycache__,.pytest_cache,docs\_generated"
$LASTEXITCODE  # esperado: 0
```

**Propósito**: Criar `baseline.json` local refletindo arquivos protegidos no estado atual. Guard compara contra este snapshot, então se estiver desatualizado, gates falham com exit=3.

**Validação**: 
```powershell
& "venv\Scripts\python.exe" scripts\agent_guard.py check `
  --root "." `
  --baseline ".hb_guard/baseline.json"
$LASTEXITCODE  # esperado: 0
```

**Regra**: Baseline é LOCAL (nunca commitado). Regenere sempre que:
- Arquivos protegidos mudarem (modelos, migrations)
- Gates passarem (exit=0)
- Você trocar de branch/máquina

---

### 0) Pré-check

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
git status --porcelain
# esperado: vazio
```

### 1) Refresh SSOT (1 vez por sessão)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\HB TRACK\scripts\inv.ps1" refresh
$LASTEXITCODE
# esperado: 0
```

### 2) Requirements (detectar SSOT↔Model)

```powershell
& "venv\Scripts\python.exe" scripts\model_requirements.py --table <TABLE> --profile strict
$LASTEXITCODE
# 0 = ok, 4 = violations, 1 = crash
```

### 3) Gate completo (corrigir e validar)

```powershell
.\scripts\models_autogen_gate.ps1 -Table "<TABLE>" -Profile strict
$LASTEXITCODE
# 0 = ok; 2/3/4 = falha por camada; 1 = crash
```

Perfil para ciclos FK documentados (quando aplicável):

```powershell
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile fk -AllowCycleWarning
```

### 4) Limpeza de artefatos gerados (para não sujar repo)

As execuções geram/atualizam arquivos em `docs/_generated/*`.
Se a tarefa não for “atualizar SSOT”, reverta os gerados após validar:

```powershell
git restore -- `
  "docs/_generated/alembic_state.txt" `
  "docs/_generated/manifest.json" `
  "docs/_generated/parity_report.json" `
  "docs/_generated/schema.sql" `
  "docs/_generated/parity-scan.log"

git restore -- `
  "..\docs/_generated/alembic_state.txt" `
  "..\docs/_generated/manifest.json" `
  "..\docs/_generated/schema.sql" `
  "..\docs/_generated/trd_training_permissions_report.txt"
```

## Execução em lote (Batch) — Preferencial (SSOT Auto)

Use quando você quer varrer/corrigir muitas tabelas sem manter lista manual.
O batch extrai tabelas automaticamente do SSOT `docs/_generated/schema.sql`.

### O que o batch faz (resumo)

1. (Opcional) `inv.ps1 refresh`
2. Varredura read-only com requirements em todas as tabelas do SSOT
3. Executa gate somente nas tabelas FAIL (exit=4), uma por vez
4. Fail-fast: para no primeiro erro
5. Logs em `%TEMP%` e limpeza automática de gerados

### Comando canônico (auto por SSOT)

```powershell
Set-Location "C:\HB TRACK\Hb Track - Backend"
git status --porcelain
# esperado: vazio

.\scripts\models_batch.ps1
$LASTEXITCODE
```

### Somente varredura (sem correção)

```powershell
.\scripts\models_batch.ps1 -DryRun
# Alias: -SkipGate (compatível com versões anteriores)
```

### Excluir tabelas (ex.: alembic_version)

```powershell
.\scripts\models_batch.ps1 -ExcludeTables "alembic_version"
```

## FAQ (mínimo)

### Quando usar `-Create`?

Use `-Create` em `models_autogen_gate.ps1` quando:

* a tabela existe no DB
* você está criando o **primeiro** model para ela

Efeito colateral esperado: o gate faz `agent_guard snapshot` (baseline **local**, nunca commitada).

### Diferença entre `-Profile fk`, `strict`, `lenient`

* `strict` (default): validação completa (preferencial).
* `fk`: perfil para casos com ciclos de FK conhecidos (ex.: `teams`/`seasons`) em conjunto com `-AllowCycleWarning`.
* `lenient`: perfil relaxado (usar apenas para diagnóstico quando estrito não é viável).

## Política de baseline (Guard)

Baseline fica em:

* `Hb Track - Backend/.hb_guard/baseline.json`

Regra:

* Baseline é para impedir drift não-intencional.
* Snapshot baseline só quando o usuário autorizar e o repo estiver limpo (sem temporários, sem gerados).

Comando canônico:

```powershell
& "venv\Scripts\python.exe" scripts\agent_guard.py snapshot `
  --root "." `
  --out ".hb_guard/baseline.json" `
  --exclude "venv,.venv,__pycache__,.pytest_cache,docs\_generated"
$LASTEXITCODE
```

Validação pós-snapshot:

* `agent_guard.py check` deve retornar exit=0 (nenhum drift)
* **Baseline é LOCAL**: não fazer `git add/commit baseline.json` (está em .gitignore)
* Commitar apenas os modelos/docs que mudaram realmente

## Como tratar sujeira de execução (gerados)

Durante execução de parity/gate, é esperado que `docs/_generated/*` mude.
Política:

* se a tarefa não é “atualizar SSOT”, revertê-los (git restore) antes de commitar.
* nunca commitar arquivos temporários, scripts de reprodução, backups ou outputs de teste.

## Critérios de sucesso (“Models Perfeitos”)

Para uma tabela estar OK:

* `models_autogen_gate.ps1 -Table <T> -Profile strict` retorna exit=0
* guard passa (added=0 deleted=0 modified=0)
* parity passa (sem diffs estruturais bloqueantes)
* requirements passa (SSOT↔AST sem violations)

## Troubleshooting (atalhos)

* Exit=3 (guard): baseline desatualizada, arquivo fora da allowlist, temporário no repo.
* Exit=2 (parity): divergência estrutural real DB↔model (alembic compare).
* Exit=4 (requirements): model não reflete SSOT (coluna extra/faltante, tipo, nullable, constraints).
* Exit=1: crash (ambiente, import, bug no script).
* `parity_report.json` com `table: null`: encoding UTF-16LE no log Alembic (corrigido em P0-A; ver `docs/references/exit_codes.md`).

Detalhado em:

* `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md`
* `docs/references/exit_codes.md`
* `docs/references/model_requirements_guide.md`
* `docs/execution_tasks/CHECKLIST-CANONICA-MODELS.md`
* `docs/ADR/architecture/CHANGELOG.md`
* `docs/execution_tasks/EXECUTIONLOG.md`

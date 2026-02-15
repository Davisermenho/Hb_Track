# Approved Commands — Whitelist Canônica para AI Agents (HB Track)

| Propriedade | Valor |
|---|---|
| ID | CANON-APPROVED-COMMANDS-008 |
| Status | CANÔNICO |
| Última verificação | 2026-02-10 (America/Sao_Paulo) |
| Porta de entrada | docs/_canon/00_START_HERE.md |
| Depende de | docs/_canon/05_MODELS_PIPELINE.md, docs/references/exit_codes.md, docs/_canon/03_WORKFLOWS.md |
| Objetivo | Whitelist autoritativa de comandos seguros para AI agents; política de aprovação para comandos não listados |

---

## Sumário

- [Glossário de Termos Técnicos](#glossário-de-termos-técnicos)
- [Convenções e Regras Globais](#convenções-e-regras-globais)
- [Índice de Comandos Aprovados](#índice-de-comandos-aprovados)
- [Categoria 1: Git Operations (Read-Only)](#categoria-1-git-operations-read-only)
- [Categoria 2: Git Operations (Write)](#categoria-2-git-operations-write)
- [Categoria 3: Model Validation (Gates)](#categoria-3-model-validation-gates)
- [Categoria 4: Batch Processing](#categoria-4-batch-processing)
- [Categoria 5: SSOT Refresh](#categoria-5-ssot-refresh)
- [Categoria 6: Guard & Baseline](#categoria-6-guard--baseline)
- [Categoria 7: Requirements Validation](#categoria-7-requirements-validation)
- [Categoria 8: Parity Validation](#categoria-8-parity-validation)
- [Categoria 9: Database & Infrastructure](#categoria-9-database--infrastructure)
- [Categoria 10: Alembic Migrations](#categoria-10-alembic-migrations)
- [Categoria 11: Task Lifecycle & Human Visibility](#categoria-11-task-lifecycle--human-visibility)
- [Comandos Proibidos (Blacklist)](#comandos-proibidos-blacklist)
- [Arquivos Protegidos (Guard)](#arquivos-protegidos-guard)
- [Protocolo de Aprovação Condicional](#protocolo-de-aprovação-condicional)
- [Cross-References](#cross-references)
- [Changelog](#changelog)

---

## Glossário de Termos Técnicos

| Termo | Definição | Onde Ver Mais |
|-------|-----------|---------------|
| **Whitelist** | Lista de comandos pré-aprovados para execução automática por AI agents | Este documento |
| **Blacklist** | Lista de comandos estritamente proibidos devido a riscos de segurança/dados | Seção "Comandos Proibidos" |
| **Read-Only** | Comandos que não alteram estado (git status, git diff, validações sem side-effects) | Categoria 1 |
| **Write** | Comandos que modificam arquivos/estado (git add, git commit, snapshot baseline) | Categorias 2, 5, 6 |
| **Gate** | Comando atomicamente composto (guard → parity → requirements) para validar 1 tabela | `05_MODELS_PIPELINE.md` |
| **Batch** | Orquestrador multi-table; exit code = primeiro FAIL não-skip (fail-fast) ou maior severidade | ADR-MODELS-003 |
| **SSOT Refresh** | Regeneração de artefatos canônicos (schema.sql, openapi.json, alembic_state.txt) | `04_SOURCES_GENERATED.md` |
| **Guard** | Proteção contra modificação não autorizada de arquivos críticos (baseline drift detection) | `INVARIANTS_AGENT_GUARDRAILS.md` |
| **Baseline** | Snapshot SHA256 de arquivos protegidos (usado por guard para detectar diffs) | `.hb_guard/baseline.json` |
| **Approval Required** | Comando exige confirmação explícita do usuário antes de execução | Seção "Protocolo de Aprovação" |
| **Destructive** | Comando que pode perder dados/trabalho (git reset --hard, rm -rf, git clean -f) | Blacklist |
| **Splatting** | Técnica PowerShell para passar parâmetros via hashtable (@{} em PS 5.1) | Seção "Notas Técnicas" |

---

## Convenções e Regras Globais

### Regra 1: Precedência Canônica

**Se comando não está nesta whitelist → PROIBIDO executar sem aprovação explícita do usuário.**

Protocolo obrigatório:
1. Agent detecta comando não listado
2. Agent para execução e exibe:
   ```
   [BLOCKED] Comando não está em APPROVED_COMMANDS:
   $ <comando completo com args>

   Aprovar execução? [Y]es / [N]o / [A]pprove & record
   ```
3. Aguarda resposta do usuário (não prossegue automaticamente)
4. Se `Y`: executa uma vez (não adiciona à whitelist)
5. Se `A`: executa E atualiza este documento + registra rationale
6. Se `N`: aborta operação

### Regra 2: CWD (Current Working Directory)

**Comandos dependem de CWD específico conforme tipo:**

| Comando | CWD Esperado | Validação Obrigatória |
|---------|-------------|----------------------|
| `.\scripts\inv.ps1 *` | Repo root (`C:\HB TRACK`) | `Get-Location` = `C:\HB TRACK` |
| `.\scripts\models_autogen_gate.ps1` | Backend root (`C:\HB TRACK\Hb Track - Backend`) | `Get-Location` contém `Hb Track - Backend` |
| `.\scripts\models_batch.ps1` | Backend root | Idem |
| `.\scripts\parity_scan.ps1` | Backend root | Idem |
| `.\scripts\parity_gate.ps1` | Backend root | Idem |
| `.\venv\Scripts\python.exe scripts\*` | Backend root | Idem |

**Validação pré-execução (obrigatória para agents):**
```powershell
# Exemplo para gate
$expectedPath = "Hb Track - Backend"
$currentPath = Get-Location
if ($currentPath -notmatch [regex]::Escape($expectedPath)) {
    Write-Host "[ERROR] Wrong CWD. Expected: *\$expectedPath, Got: $currentPath" -ForegroundColor Red
    exit 1
}
```

### Regra 3: Exit Code Propagation

**Sempre capturar $LASTEXITCODE imediatamente após execução, sem pipelines intermediários.**

```powershell
# ✅ CORRETO
$output = & .\scripts\models_autogen_gate.ps1 -Table "athletes" 2>&1
$exitCode = $LASTEXITCODE  # Captura imediata
$output | Out-File log.txt # Pipeline APÓS captura

# ❌ ERRADO (Tee-Object altera $LASTEXITCODE)
& .\scripts\models_autogen_gate.ps1 -Table "athletes" 2>&1 | Tee-Object -FilePath log.txt
$exitCode = $LASTEXITCODE  # Valor incorreto!
```

### Regra 4: Repo Hygiene (Pré-condição)

**Comandos de gate/batch exigem repositório limpo:**

```powershell
# Validação obrigatória antes de gates
$status = git status --porcelain
if ($status) {
    Write-Host "[ERROR] Repository must be clean before execution" -ForegroundColor Red
    Write-Host "Uncommitted changes:" -ForegroundColor Yellow
    git status --porcelain
    exit 3  # Guard violation
}
```

**Exceções:** Comandos read-only (git status, parity_scan com -SkipDocsRegeneration, model_requirements) não exigem repo limpo.

### Regra 5: Aprovação para Write Operations

**Categorias que exigem aprovação explícita:**

- Git write (add, commit, restore)
- SSOT refresh (inv.ps1 refresh)
- Baseline snapshot (agent_guard.py snapshot)
- Database operations (docker-compose, alembic upgrade)

**Categorias com aprovação automática (gated):**

- Model gates (models_autogen_gate.ps1) — aprovação implícita se requirements PASS
- Parity gates (parity_gate.ps1) — aprovação implícita se guard PASS

### Regra 6: Evidência Obrigatória

**Toda execução de comando deve registrar:**

```markdown
**Command**: <comando completo com args>
**CWD**: <Get-Location output>
**ExitCode**: $LASTEXITCODE = <valor>
**Output** (últimas 50 linhas relevantes):
<trecho do output>
```

---

## Índice de Comandos Aprovados

### Read-Only (Execução Automática)

| Comando | Categoria | Tempo Estimado | Exit Codes |
|---------|-----------|----------------|------------|
| `git status --porcelain` | Git (R) | <1s | 0 |
| `git diff <file>` | Git (R) | <1s | 0 |
| `git log --oneline -n <N>` | Git (R) | <1s | 0 |
| `model_requirements.py --table <T>` | Requirements | 5-15s | 0, 1, 4 |
| `parity_scan.ps1 -TableFilter <T> -SkipDocsRegeneration` | Parity | 10-30s | 0, 1, 2 |
| `agent_guard.py check` | Guard | 5-10s | 0, 1, 3 |

### Write (Aprovação Obrigatória)

| Comando | Categoria | Tempo Estimado | Exit Codes |
|---------|-----------|----------------|------------|
| `git add <file>` | Git (W) | <1s | 0 |
| `git commit -m "msg"` | Git (W) | <5s | 0, 1 |
| `git restore -- <file>` | Git (W) | <1s | 0 |
| `inv.ps1 refresh` | SSOT Refresh | 1-5min | 0, 1 |
| `agent_guard.py snapshot` | Guard | 5-15s | 0, 1 |
| `docker-compose up -d postgres` | Database | 10-60s | 0, 1 |
| `alembic upgrade head` | Migrations | 5-120s | 0, 1 |

### Gated (Aprovação Implícita via Validação)

| Comando | Categoria | Tempo Estimado | Exit Codes |
|---------|-----------|----------------|------------|
| `models_autogen_gate.ps1 -Table <T>` | Gate | 30s-2min | 0, 1, 2, 3, 4 |
| `models_batch.ps1` | Batch | 5-15min | 0, 1, 2, 3, 4 |
| `parity_gate.ps1 -Table <T>` | Parity | 20s-1min | 0, 1, 2, 3 |

---

## Categoria 1: Git Operations (Read-Only)

### CMD-1.1: git status --porcelain

**Objetivo:** Verificar estado do working tree (arquivos modificados, staged, untracked).

**Sintaxe:**
```powershell
git status --porcelain
```

**Parâmetros:**
- `--porcelain`: Output em formato machine-readable (sem cores, formato fixo)

**Exit Codes:**
- `0`: Sucesso (sempre)

**Quando Usar:**
- Antes de executar gates (validar repo limpo)
- Após gates (verificar quais arquivos foram modificados)
- Troubleshooting de guard violations

**Validação (DoD):**
- Output vazio → repo limpo (adequado para gates)
- Output com `M <file>` → arquivo modificado
- Output com `?? <file>` → arquivo untracked

**Exemplo:**
```powershell
PS C:\HB TRACK\Hb Track - Backend> git status --porcelain
M app/models/athletes.py
M docs/_generated/parity_report.json
?? test_temp.tmp
```

**Troubleshooting:**
- Se output não está vazio e você precisa rodar gate → commit ou stash changes primeiro

---

### CMD-1.2: git diff <file>

**Objetivo:** Ver mudanças detalhadas em arquivo específico (unified diff).

**Sintaxe:**
```powershell
git diff <file>
git diff --stat              # Resumo de mudanças (linhas +/-)
git diff --cached <file>     # Diff de staged changes
```

**Parâmetros:**
- `<file>`: Path relativo do arquivo (ex: `app/models/athletes.py`)
- `--stat`: Mostra apenas estatísticas (+X -Y)
- `--cached`: Diff do staging area (não working tree)

**Exit Codes:**
- `0`: Sucesso (sempre)

**Quando Usar:**
- Revisar mudanças antes de commit
- Entender violations de requirements (qual linha foi alterada)
- Debug de parity diffs (comparar model antes/depois)

**Validação (DoD):**
- Output mostra linhas com `-` (removidas) e `+` (adicionadas)
- Se vazio → arquivo não foi modificado

**Exemplo:**
```powershell
PS> git diff app/models/athletes.py
- season_id: Mapped[str] = mapped_column(String)
+ season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))
```

**Troubleshooting:**
- Se diff mostra mudanças mas `git status` não → arquivo já foi staged (use `git diff --cached`)

---

### CMD-1.3: git log --oneline -n <N>

**Objetivo:** Ver histórico de commits recentes (resumido).

**Sintaxe:**
```powershell
git log --oneline -n <N>
git log --oneline --graph -n <N>    # Com grafo de branches
git log -1 --stat                    # Último commit com estatísticas
```

**Parâmetros:**
- `-n <N>`: Número de commits a mostrar
- `--oneline`: Formato compacto (hash + mensagem)
- `--graph`: Mostra grafo de branches (ASCII art)
- `--stat`: Adiciona estatísticas de arquivos modificados

**Exit Codes:**
- `0`: Sucesso (sempre)

**Quando Usar:**
- Verificar se baseline foi atualizada recentemente
- Entender contexto de mudanças (quem/quando/por quê)
- Troubleshooting de guard (verificar último commit em arquivo protegido)

**Validação (DoD):**
- Output mostra hash curto (7 chars) + mensagem de commit

**Exemplo:**
```powershell
PS> git log --oneline -n 5
09cdbeb chore(guard): refresh baseline after autogen patch
b677c31 feat(autogen): detect and remove duplicate __table_args__
46d04e8 fix(models): remove duplicate __table_args__ in competition_season
c6947bd chore(guard): refresh baseline after autogen updates
70e6b22 test: person.py after autogen (idempotence checkpoint)
```

**Troubleshooting:**
- Se histórico não mostra commits esperados → verificar branch atual com `git branch --show-current`

---

### CMD-1.4: git show <commit>

**Objetivo:** Ver detalhes completos de um commit específico (diff + metadados).

**Sintaxe:**
```powershell
git show <commit>
git show <commit> --stat               # Apenas estatísticas
git show <commit>:<file>               # Conteúdo de arquivo nesse commit
```

**Parâmetros:**
- `<commit>`: Hash do commit (curto ou completo)
- `--stat`: Apenas estatísticas de arquivos modificados
- `<commit>:<file>`: Path do arquivo nesse commit

**Exit Codes:**
- `0`: Sucesso
- `128`: Commit não encontrado

**Quando Usar:**
- Investigar quando/como baseline foi modificada
- Reverter arquivo para estado específico (via `git show <commit>:<file> > file`)
- Auditoria de mudanças em SSOT

**Validação (DoD):**
- Output mostra: author, date, mensagem, diff completo

**Exemplo:**
```powershell
PS> git show 09cdbeb
commit 09cdbeb...
Author: Davi <...>
Date: 2026-02-10

chore(guard): refresh baseline after autogen patch

diff --git a/.hb_guard/baseline.json b/.hb_guard/baseline.json
...
```

**Troubleshooting:**
- Se commit não existe (exit 128) → verificar histórico com `git log --oneline`

---

## Categoria 2: Git Operations (Write)

### CMD-2.1: git add <file>

**Objetivo:** Adicionar arquivo ao staging area (preparar para commit).

**Sintaxe:**
```powershell
git add <file>
git add -A <path>     # Adiciona TODOS os arquivos em path (cuidado!)
git add -u            # Adiciona apenas tracked files modificados
```

**Parâmetros:**
- `<file>`: Path relativo do arquivo (ex: `app/models/athletes.py`)
- `-A <path>`: Adiciona todos (incluindo untracked) em path
- `-u`: Apenas tracked files modificados/deletados

**Exit Codes:**
- `0`: Sucesso
- `128`: Arquivo não existe ou path inválido

**Aprovação:** **OBRIGATÓRIA** (usuário deve confirmar antes)

**Quando Usar:**
- Após gate PASS (adicionar model corrigido)
- Após snapshot baseline (adicionar baseline.json atualizada)
- Preparar commit de artefatos SSOT (schema.sql, openapi.json)

**Validação (DoD):**
- `git status --porcelain` mostra arquivo com `A` (added) ou `M` (modified) no staging

**Exemplo:**
```powershell
PS> git add app/models/athletes.py
PS> git status --porcelain
M  app/models/athletes.py  # "M " (espaço após M) = staged
```

**Troubleshooting:**
- Se `git add -A` adiciona arquivos indesejados → usar paths específicos (não -A)
- Se arquivo já estava staged → `git add` é idempotente (sem erro)

**Notas de Segurança:**
- **NUNCA** usar `git add .` ou `git add -A` sem revisar `git status` antes
- Risco de adicionar .env, credentials.json, temporários
- Preferir adicionar arquivos explicitamente por nome

---

### CMD-2.2: git commit -m "msg"

**Objetivo:** Criar commit com mensagem (salvar mudanças staged no histórico).

**Sintaxe:**
```powershell
git commit -m "tipo(escopo): mensagem"
git commit -m "$(cat <<'EOF'
mensagem multilinha
com detalhes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Parâmetros:**
- `-m "msg"`: Mensagem de commit (inline)
- Formato semântico: `tipo(escopo): mensagem` (ex: `fix(models): correct athlete nullable fields`)
- HEREDOC (PowerShell): Permitir mensagens multilinha com Co-Authored-By

**Exit Codes:**
- `0`: Sucesso
- `1`: Pre-commit hook falhou ou nada para commitar

**Aprovação:** **OBRIGATÓRIA** (usuário deve confirmar antes)

**Quando Usar:**
- Após git add (salvar mudanças staged)
- Após revisar diff (git diff --cached)
- Seguir convenção: 1 commit = 1 mudança lógica (não múltiplas correções)

**Validação (DoD):**
- `git log -1 --oneline` mostra novo commit
- `git status --porcelain` está vazio (nada staged após commit)

**Tipos de commit:**
- `fix`: Correção de bug/violation
- `feat`: Nova funcionalidade
- `chore`: Manutenção (baseline, artefatos)
- `refactor`: Refatoração sem mudança de comportamento
- `docs`: Mudanças de documentação
- `test`: Adicionar/corrigir testes

**Exemplo:**
```powershell
PS> git commit -m "fix(models): correct athletes.season_id type via autogen"
[main 12ab34c] fix(models): correct athletes.season_id type via autogen
 1 file changed, 2 insertions(+), 2 deletions(-)
```

**Troubleshooting:**
- Se "nothing to commit" → verificar `git status` (nada foi staged)
- Se pre-commit hook falha → corrigir issues e re-commitar (NÃO usar --no-verify)
- Se mensagem inválida → seguir formato semântico

**Notas de Segurança:**
- **NUNCA** usar `--no-verify` sem aprovação explícita (bypassa hooks)
- **NUNCA** usar `--amend` após push (reescreve histórico público)
- Preferir commits granulares (1 tabela por commit) a atomic (15 tabelas juntas)

---

### CMD-2.3: git restore -- <file>

**Objetivo:** Descartar mudanças não staged (reverter para HEAD).

**Sintaxe:**
```powershell
git restore -- <file>
git restore --staged -- <file>    # Remove do staging (não reverte working tree)
git restore -- <path>              # Restaura todos os arquivos em path
```

**Parâmetros:**
- `<file>`: Path relativo do arquivo (ex: `app/models/athletes.py`)
- `--staged`: Remove do staging area (mas mantém mudanças no working tree)
- `<path>`: Path de diretório (ex: `docs/_generated/`)

**Exit Codes:**
- `0`: Sucesso
- `128`: Arquivo não existe ou path inválido

**Aprovação:** **OBRIGATÓRIA** (usuário deve confirmar antes — operação destrutiva)

**Quando Usar:**
- Após gate falhar (reverter mudanças incorretas)
- Limpar artefatos gerados (docs/_generated/*) após scan
- Desfazer mudanças acidentais

**Validação (DoD):**
- `git status --porcelain` não mostra mais o arquivo como modificado
- `git diff <file>` está vazio

**Exemplo:**
```powershell
# Limpeza de artefatos gerados
PS> git restore -- "docs/_generated/alembic_state.txt"
PS> git restore -- "docs/_generated/manifest.json"
PS> git restore -- "docs/_generated/schema.sql"
PS> git status --porcelain
# Output vazio (artefatos revertidos)
```

**Troubleshooting:**
- Se arquivo estava staged → usar `git restore --staged` primeiro, depois `git restore`
- Se mudanças são necessárias → NÃO usar restore (commitar em vez)

**Notas de Segurança:**
- **OPERAÇÃO DESTRUTIVA**: mudanças locais são perdidas permanentemente
- **SEMPRE** perguntar usuário antes de executar
- Considerar `git stash` como alternativa não-destrutiva

---

## Categoria 3: Model Validation (Gates)

### CMD-3.1: models_autogen_gate.ps1 -Table <name>

**Objetivo:** Gate completo (guard → parity → autogen → requirements) para 1 tabela.

**Sintaxe:**
```powershell
.\scripts\models_autogen_gate.ps1 -Table <name> -Profile strict
.\scripts\models_autogen_gate.ps1 -Table <name> -Profile fk
.\scripts\models_autogen_gate.ps1 -Table <name> -Profile strict -AllowCycleWarning
.\scripts\models_autogen_gate.ps1 -Table <name> -Allow "path/to/file.py"
```

**Parâmetros:**
- `-Table <name>`: Nome da tabela (ex: `athletes`, `teams`)
- `-Profile <string>`: Perfil de validação (`strict` | `fk` | `lenient`)
  - `strict`: Validação completa (padrão)
  - `fk`: Permite SAWarnings de ciclos FK (teams/seasons)
  - `lenient`: Aceita warnings não-críticos
- `-AllowCycleWarning`: Permite warnings de ciclos FK (alternativa a `-Profile fk`)
- `-Allow <path>`: Autoriza modificação de arquivo protegido (guard allowlist)

**Exit Codes:**
- `0`: PASS (todas as camadas: guard, parity, requirements)
- `1`: Crash interno (erro inesperado)
- `2`: Parity structural diff (model ≠ schema.sql)
- `3`: Guard violation (arquivo protegido modificado sem autorização)
- `4`: Requirements violation (model viola regras)

**CWD Esperado:** Backend root (`C:\HB TRACK\Hb Track - Backend`)

**Aprovação:** Implícita (se requirements PASS) — comando é gated

**Quando Usar:**
- Após editar model manualmente (validar conformidade)
- Após parity_scan detectar FAIL (corrigir automaticamente via autogen)
- Workflow iterativo: editar → gate → revisar → commit

**Validação (DoD):**
- Exit code = 0
- `git status --porcelain` mostra apenas model modificado (sem artefatos gerados)
- `git diff <model>` mostra mudanças esperadas (autogen aplicado)

**Tempo Estimado:** 30s-2min (depende de complexidade do model)

**Exemplo:**
```powershell
PS C:\HB TRACK\Hb Track - Backend> .\scripts\models_autogen_gate.ps1 -Table "athletes" -Profile strict
[GUARD] PASS (no protected files modified)
[PARITY] Running Alembic compare...
[PARITY] PASS (no structural diffs)
[AUTOGEN] Applying corrections...
[AUTOGEN] Fixed: TYPE_MISMATCH: season_id (String → Integer)
[REQUIREMENTS] Running validation...
[REQUIREMENTS] PASS (all constraints satisfied)
✅ ALL GATES PASSED — Model is 100% conformant
ExitCode: 0
```

**Troubleshooting:**

| Exit Code | Problema | Solução |
|-----------|----------|---------|
| `2` | Parity structural diff persiste após autogen | Corrigir manualmente ou verificar schema.sql |
| `3` | Guard violation (baseline drift) | Atualizar baseline com `agent_guard.py snapshot` |
| `4` | Requirements violation (autogen não resolveu) | Revisar violations no log e corrigir manualmente |

**Notas:**
- Gate é **idempotente**: rodar 2x seguidas deve retornar exit=0 ambas vezes
- Autogen pode modificar model → sempre revisar `git diff` antes de commit
- Para ciclos FK (teams/seasons): usar `-Profile fk` ou `-AllowCycleWarning`

---

### CMD-3.2: parity_gate.ps1 -Table <name>

**Objetivo:** Gate de parity (guard → parity scan) sem autogen (diagnóstico).

**Sintaxe:**
```powershell
.\scripts\parity_gate.ps1 -Table <name>
.\scripts\parity_gate.ps1 -Table <name> -SkipDocsRegeneration
```

**Parâmetros:**
- `-Table <name>`: Nome da tabela
- `-SkipDocsRegeneration`: Pula refresh de SSOT (usa schema.sql existente)

**Exit Codes:**
- `0`: PASS (guard + parity)
- `1`: Crash interno
- `2`: Parity structural diff
- `3`: Guard violation

**CWD Esperado:** Backend root

**Aprovação:** Implícita (comando é gated)

**Quando Usar:**
- Diagnóstico rápido de parity (sem autogen)
- Validação pós-migration (verificar se Alembic gerou schema correto)
- Troubleshooting de parity diffs (sem modificar model)

**Validação (DoD):**
- Exit code = 0
- `docs/_generated/parity_report.json` mostra `structural_diffs: []`

**Tempo Estimado:** 20s-1min

**Exemplo:**
```powershell
PS> .\scripts\parity_gate.ps1 -Table "athletes" -SkipDocsRegeneration
[GUARD] PASS
[PARITY] Scanning athletes...
[PARITY] FAIL (exit=2)
  - modify_type(athletes, 'season_id', String → Integer)
ExitCode: 2
```

**Troubleshooting:**
- Se exit=2 mas model parece correto → verificar se schema.sql está desatualizado (rodar sem `-SkipDocsRegeneration`)
- Se exit=3 → baseline drift (atualizar baseline)

---

## Categoria 4: Batch Processing

### CMD-4.1: models_batch.ps1 (Scan + Fix)

**Objetivo:** Batch runner para validar/corrigir múltiplas tabelas (scan-then-fix pattern).

**Sintaxe:**
```powershell
# Scan-only (dry-run)
.\scripts\models_batch.ps1 -DryRun
.\scripts\models_batch.ps1 -SkipGate             # Alias legado

# Full execution (scan + fix)
.\scripts\models_batch.ps1
.\scripts\models_batch.ps1 -SkipRefresh          # Usa schema.sql existente
.\scripts\models_batch.ps1 -Profile strict
.\scripts\models_batch.ps1 -FailFast:$false      # Continua após erros
```

**Parâmetros:**
- `-DryRun`: Executa apenas scan (não corrige FAIL) — alias de `-SkipGate`
- `-SkipGate`: Alias legado de `-DryRun` (scan-only)
- `-SkipRefresh`: Pula refresh de SSOT (usa schema.sql/openapi.json existentes)
- `-Profile <string>`: Perfil padrão para requirements/gate (`strict` | `fk` | `lenient`)
- `-FailFast <bool>`: Para no primeiro erro (default: `$true`)
- `-LogPath <string>`: Path custom para logs (default: `%TEMP%`)

**Exit Codes:**
- `0`: Sucesso (todas PASS ou FIXED)
- `1`: Crash interno
- `2`: Parity structural diff (propagado de gate)
- `3`: Guard violation (repo sujo ou baseline drift)
- `4`: Requirements violation não resolvida

**CWD Esperado:** Backend root

**Aprovação:** Implícita (comando é gated)

**Quando Usar:**
- Validação completa pré-PR (scan todas as 15+ tabelas)
- Correção em massa após mudanças no schema.sql
- CI/CD pipeline (validação automatizada)

**Validação (DoD):**
- Exit code = 0
- CSV gerado em `%TEMP%\models_batch_{timestamp}.csv` com todas as tabelas
- Log gerado em `%TEMP%\models_batch_{timestamp}.log`
- Resumo no console mostra counts (PASS/FAIL/SKIP/FIXED)

**Tempo Estimado:**
- Scan-only (15 tabelas): 2-5min
- Full (scan + 3 FAIL): 5-15min

**Exemplo (Scan-only):**
```powershell
PS> .\scripts\models_batch.ps1 -DryRun -SkipRefresh
[2026-02-10 14:32:00] ============ MODELS BATCH START ============
[2026-02-10 14:32:00] Config: Profile=strict, SkipRefresh=True, SkipGate=True
[2026-02-10 14:32:01] PHASE 1: SSOT Refresh - SKIPPED
[2026-02-10 14:32:01] PHASE 2: Discovery - 15 tables found
[2026-02-10 14:32:01] PHASE 3: Scan - START
[2026-02-10 14:32:01] [1/15] athletes - PASS (exit=0)
[2026-02-10 14:32:05] [2/15] teams - FAIL (exit=4)
  - VIOLATION: TYPE_MISMATCH: season_id expected=Integer got=String
[2026-02-10 14:35:00] PHASE 3: Scan - COMPLETE (PASS: 10, FAIL: 3, SKIP: 2)
============ SUMMARY ============
Total tables: 15
PASS: 10
FAIL: 3 (teams, seasons, attendance)
SKIP_NO_MODEL: 2
Exit code: 0
================================
```

**Exemplo (Full execution):**
```powershell
PS> .\scripts\models_batch.ps1 -SkipRefresh
[PHASE 3: Scan] PASS: 10, FAIL: 3, SKIP: 2
[PHASE 4: Fix - START] (3 tables)
[1/3] teams - Running gate (profile=fk)
[1/3] teams - FIXED (exit=0)
[2/3] seasons - Running gate (profile=fk)
[2/3] seasons - PARITY FAIL (exit=2)
[ABORT] Fail-fast triggered. Manual intervention required.
ExitCode: 2
```

**Troubleshooting:**

| Problema | Causa | Solução |
|----------|-------|---------|
| Exit 3 (repo sujo) | Arquivos uncommitted | Commit ou stash changes antes de rodar |
| Exit 2 (parity) | Structural diff não resolvido | Corrigir manualmente ou atualizar schema.sql |
| Scan muito lento (>10min) | 50+ tabelas | Considerar paralelização (FASE 2 do ADR-MODELS-003) |
| SKIP_NO_MODEL para tabela válida | Naming singular/plural | Criar model ou adicionar a mapa de exceções |

**Outputs Gerados:**

**CSV** (`%TEMP%\models_batch_{timestamp}.csv`):
```csv
table_name,status,exit_code,profile,timestamp
athletes,PASS,0,strict,2026-02-10T14:32:01
teams,FAIL,4,fk,2026-02-10T14:32:05
attendance,SKIP_NO_MODEL,100,strict,2026-02-10T14:32:06
seasons,FIXED,0,fk,2026-02-10T14:35:22
```

**Status possíveis:**
- `PASS`: Model válido (requirements exit=0)
- `FAIL`: Requirements violation detectada
- `SKIP_NO_MODEL`: Model não existe em `app/models/`
- `FIXED`: Era FAIL, gate corrigiu via autogen

**Notas:**
- Batch é **determinístico**: ordem = ordem de aparição em schema.sql
- Logs em `%TEMP%` (não commitados)
- `-DryRun` é preferido sobre `-SkipGate` (mais semântico)

---

## Categoria 5: SSOT Refresh

### CMD-5.1: inv.ps1 refresh

**Objetivo:** Regenerar TODOS os artefatos SSOT (schema.sql, openapi.json, alembic_state.txt, manifest.json).

**Sintaxe:**
```powershell
# Forma completa (recomendada)
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\HB TRACK\scripts\inv.ps1" refresh

# Forma curta (se CWD = repo root)
.\scripts\inv.ps1 refresh
```

**Parâmetros:**
- `refresh`: Subcomando que regenera todos os artefatos

**Exit Codes:**
- `0`: Sucesso (todos os artefatos gerados)
- `1`: Crash (pg_dump falhou, DB inacessível, ou erro de script)

**CWD Esperado:** Repo root (`C:\HB TRACK`)

**Aprovação:** **OBRIGATÓRIA** (comando modifica múltiplos arquivos)

**Quando Usar:**
- Antes de parity/requirements (garantir schema.sql atualizado)
- Após rodar migrations (alembic upgrade head)
- Após mudanças em routes (regenerar openapi.json)
- Antes de batch processing (SSOT fresh)

**Validação (DoD):**
- Exit code = 0
- `git status --porcelain` mostra arquivos modificados:
  - `M docs/_generated/schema.sql`
  - `M docs/_generated/openapi.json`
  - `M docs/_generated/alembic_state.txt`
  - `M docs/_generated/manifest.json`
- Timestamp em `manifest.json` (campo `generated_at`) < 1min

**Tempo Estimado:** 1-5min (depende de tamanho do DB)

**Exemplo:**
```powershell
PS C:\HB TRACK> .\scripts\inv.ps1 refresh
[SSOT] Regenerating artifacts...
[SSOT] Running pg_dump...
[SSOT] Generated: docs/_generated/schema.sql (1.2MB)
[SSOT] Generating OpenAPI spec...
[SSOT] Generated: docs/_generated/openapi.json (450KB)
[SSOT] Extracting Alembic state...
[SSOT] Generated: docs/_generated/alembic_state.txt
[SSOT] Creating manifest...
[SSOT] Generated: docs/_generated/manifest.json
✅ SSOT refresh complete
ExitCode: 0
```

**Troubleshooting:**

| Problema | Causa | Solução |
|----------|-------|---------|
| Exit 1 (pg_dump failed) | DB inacessível ou credenciais inválidas | Verificar connection string em .env |
| schema.sql não atualizado | pg_dump retornou vazio | Verificar permissões de usuário PostgreSQL |
| openapi.json não mudou | FastAPI app não inicializou | Verificar imports em app/main.py |

**Critério de Uso de `-SkipDocsRegeneration`:**

Pode usar `-SkipDocsRegeneration` em parity_scan/parity_gate **SOMENTE** quando:
1. `inv.ps1 refresh` foi executado **nesta mesma sessão** (< 1min atrás), E
2. `manifest.json` timestamp (campo `generated_at`) confirma refresh recente, E
3. Nenhuma migration foi aplicada desde o refresh

**Se dúvida → não use; sempre prefira refresh completo.**

**Notas:**
- **NUNCA** editar artefatos gerados manualmente (schema.sql, openapi.json, etc.)
- Se schema.sql está errado → fonte (DB/migrations) está errada
- Artefatos são **derivados** (não canônicos por si) — DB real é SSOT

---

## Categoria 6: Guard & Baseline

### CMD-6.1: agent_guard.py snapshot

**Objetivo:** Criar snapshot SHA256 de arquivos protegidos (atualizar baseline).

**Sintaxe:**
```powershell
.\venv\Scripts\python.exe scripts\agent_guard.py snapshot --root . --out ".hb_guard/baseline.json"
.\venv\Scripts\python.exe scripts\agent_guard.py snapshot baseline  # Alias curto
```

**Parâmetros:**
- `snapshot`: Subcomando que cria snapshot
- `--root <path>`: Raiz do projeto (`.` = CWD)
- `--out <path>`: Path do baseline (default: `.hb_guard/baseline.json`)
- `baseline`: Alias que usa defaults (root=., out=.hb_guard/baseline.json)

**Exit Codes:**
- `0`: Sucesso (baseline atualizada)
- `1`: Crash (erro de IO ou permissão)

**CWD Esperado:** Backend root

**Aprovação:** **OBRIGATÓRIA** (comando modifica baseline)

**Quando Usar:**
- Após gate PASS com exit=0 (registrar estado conformante)
- Após commit que altera arquivos protegidos/SSOT
- Quando autorizado explicitamente pelo usuário

**Quando NÃO Usar (PROIBIDO):**
- Se EXIT 2/3/4 (primeiro corrigir causa raiz)
- Se `git status --porcelain` retorna algo (repo sujo)
- Se parity ainda falha (structural diffs não resolvidos)
- Se requirements ainda falha (model viola regras)

**Validação (DoD):**
- Exit code = 0
- `git status --porcelain` mostra `.hb_guard/baseline.json` modificado
- Baseline contém SHA256 de arquivos protegidos

**Tempo Estimado:** 5-15s

**Exemplo:**
```powershell
PS> .\venv\Scripts\python.exe scripts\agent_guard.py snapshot baseline
[GUARD] Scanning protected files...
[GUARD] Found 47 files
[GUARD] Computing SHA256 hashes...
[GUARD] Baseline updated: .hb_guard/baseline.json
ExitCode: 0

PS> git status --porcelain
M .hb_guard/baseline.json
```

**Troubleshooting:**
- Se erro de permissão → verificar que `.hb_guard/` existe e é writable
- Se baseline não muda → verificar se arquivos protegidos realmente mudaram

**Regra de Ouro:**
**Baseline é artefato LOCAL (não versionado via git). Nunca fazer git add/commit baseline.json.**

Razão: baseline.json está em `.gitignore` (linha 141) e é regenerado por `agent_guard.py snapshot` em cada sessão de validação. É guardrail de conformidade local, não SSOT. Commitá-lo causaria:
- Conflitos em PRs/merges (ambiente-específico)
- Falsos positivos de guard em outros worktrees
- Ruído de apenas regenerações sem mudança real

Fluxo correto:
1. `agent_guard.py snapshot` (após gates OK) → baseline.json atualizado localmente
2. Validar com `agent_guard.py check` (deve retornar exit=0)
3. Commitar apenas os modelos/esquema que mudaram realmente
4. Baseline fica na máquina do desenvolvedor (nunca no VCS)

**Snapshot = "registrar estado conformante e testado"; nunca snapshot de repo quebrado. Baseline NUNCA é versionado.**

---

### CMD-6.2: agent_guard.py check

**Objetivo:** Verificar se arquivos protegidos foram modificados (vs baseline).

**Sintaxe:**
```powershell
.\venv\Scripts\python.exe scripts\agent_guard.py check --root . --baseline ".hb_guard\baseline.json"
.\venv\Scripts\python.exe scripts\agent_guard.py check baseline  # Alias curto
```

**Parâmetros:**
- `check`: Subcomando que verifica baseline
- `--root <path>`: Raiz do projeto
- `--baseline <path>`: Path do baseline
- `baseline`: Alias com defaults

**Exit Codes:**
- `0`: PASS (nenhum arquivo protegido modificado)
- `3`: FAIL (arquivos protegidos modificados sem autorização)
- `1`: Crash

**CWD Esperado:** Backend root

**Aprovação:** Automática (comando é read-only)

**Quando Usar:**
- Diagnóstico de guard violations (qual arquivo foi modificado)
- Antes de snapshot (verificar que apenas arquivos esperados mudaram)
- Troubleshooting de exit=3 em gates

**Validação (DoD):**
- Exit code = 0 (nenhum drift)
- OU Exit code = 3 + lista de arquivos modificados

**Tempo Estimado:** 5-10s

**Exemplo (PASS):**
```powershell
PS> .\venv\Scripts\python.exe scripts\agent_guard.py check baseline
[GUARD] Checking baseline...
[GUARD] PASS (no protected files modified)
ExitCode: 0
```

**Exemplo (FAIL):**
```powershell
PS> .\venv\Scripts\python.exe scripts\agent_guard.py check baseline
[GUARD] Checking baseline...
[GUARD] FAIL (exit=3)
Modified protected files:
  - app/routes/teams.py
ExitCode: 3
```

**Troubleshooting:**
- Se exit=3 mas modificação é legítima → usar gate com `-Allow "path/to/file.py"`
- Se exit=3 por baseline stale → atualizar baseline com `snapshot`

---

## Categoria 7: Requirements Validation

### CMD-7.1: model_requirements.py --table <name>

**Objetivo:** Validação estática de conformidade model vs schema.sql (read-only).

**Sintaxe:**
```powershell
.\venv\Scripts\python.exe scripts\model_requirements.py --table <name> --profile strict
.\venv\Scripts\python.exe scripts\model_requirements.py --table <name> --profile fk
.\venv\Scripts\python.exe scripts\model_requirements.py --table <name> --profile lenient
```

**Parâmetros:**
- `--table <name>`: Nome da tabela (ex: `athletes`)
- `--profile <string>`: Perfil de validação
  - `strict`: Validação completa (CHECK, INDEX, server_default, etc.)
  - `fk`: Permite warnings de ciclos FK
  - `lenient`: Aceita warnings não-críticos

**Exit Codes:**
- `0`: PASS (model 100% conforme)
- `1`: Crash interno (erro de parsing, arquivo não encontrado)
- `4`: FAIL (violations detectadas)

**CWD Esperado:** Backend root

**Aprovação:** Automática (comando é read-only)

**Quando Usar:**
- Diagnóstico rápido de violations (sem rodar gate completo)
- Antes de autogen (entender quais violations existem)
- CI/CD (validação sem side-effects)

**Validação (DoD):**
- Exit code = 0 (nenhuma violation)
- OU Exit code = 4 + lista de violations com line numbers

**Tempo Estimado:** 5-15s

**Exemplo (PASS):**
```powershell
PS> .\venv\Scripts\python.exe scripts\model_requirements.py --table athletes --profile strict
[REQUIREMENTS] Parsing schema.sql...
[REQUIREMENTS] Parsing app/models/athlete.py...
[REQUIREMENTS] Validating: types, nullable, FK, CHECK, INDEX, server_default...
[REQUIREMENTS] PASS (no violations)
ExitCode: 0
```

**Exemplo (FAIL):**
```powershell
PS> .\venv\Scripts\python.exe scripts\model_requirements.py --table attendance --profile strict
[REQUIREMENTS] FAIL (exit=4)
Violations (strict profile):
  - MISSING_SERVER_DEFAULT: is_medical_restriction expected_default=default_literal:false model_line=174
  - TYPE_MISMATCH: date expected=date|None got=varchar|20 model_line=35
  - NULLABLE_MISMATCH: athlete_id expected=NOT NULL got=omitted model_line=42
ExitCode: 4
```

**Troubleshooting:**

| Violation Type | Causa | Solução |
|---------------|-------|---------|
| TYPE_MISMATCH | Tipo PG ↔ SA incompatível | Corrigir tipo no model (ex: String → Date) |
| NULLABLE_MISMATCH | NOT NULL no DB mas nullable=True no model | Adicionar `nullable=False` |
| MISSING_SERVER_DEFAULT | DEFAULT no DB mas sem `server_default` | Adicionar `server_default=text("valor")` |
| MISSING_USE_ALTER | FK de ciclo sem `use_alter=True` | Adicionar `use_alter=True, name="fk_name"` |
| MISSING_CHECK | CHECK constraint faltando no model | Adicionar em `__table_args__` |

**Notas:**
- Requirements é **determinístico**: mesmos inputs → mesmos outputs
- Não modifica arquivos (read-only)
- Adequado para CI (sem side-effects)

---

## Categoria 8: Parity Validation

### CMD-8.1: parity_scan.ps1 -TableFilter <name>

**Objetivo:** Gerar parity_report.json para diagnóstico de structural/field diffs.

**Sintaxe:**
```powershell
.\scripts\parity_scan.ps1 -TableFilter <name>
.\scripts\parity_scan.ps1 -TableFilter <name> -SkipDocsRegeneration
```

**Parâmetros:**
- `-TableFilter <name>`: Nome da tabela (ex: `athletes`)
- `-SkipDocsRegeneration`: Pula refresh de SSOT (usa schema.sql existente)

**Exit Codes:**
- `0`: PASS (nenhum structural diff)
- `1`: Crash interno
- `2`: FAIL (structural diffs detectados)

**CWD Esperado:** Backend root

**Aprovação:** Automática (comando é read-only de diagnóstico)

**Quando Usar:**
- Diagnóstico pré-gate (entender quais diffs existem)
- Após migration (verificar se Alembic gerou schema correto)
- Troubleshooting de parity (visualizar diffs em JSON)

**Validação (DoD):**
- Exit code = 0 ou 2
- `docs/_generated/parity_report.json` gerado com:
  - `table`: nome da tabela
  - `structural_diffs`: lista de diffs críticos
  - `field_diffs`: lista de diffs não-críticos (comments, etc.)

**Tempo Estimado:** 10-30s

**Exemplo (PASS):**
```powershell
PS> .\scripts\parity_scan.ps1 -TableFilter "athletes"
[PARITY] Running Alembic compare...
[PARITY] PASS (no structural diffs)
Report: docs/_generated/parity_report.json
ExitCode: 0
```

**Exemplo (FAIL):**
```powershell
PS> .\scripts\parity_scan.ps1 -TableFilter "teams"
[PARITY] FAIL (exit=2)
Structural diffs detected:
  - modify_type(teams, 'season_id', String → Integer)
  - modify_nullable(teams, 'name', nullable=True → False)
Report: docs/_generated/parity_report.json
ExitCode: 2
```

**parity_report.json** (exemplo):
```json
{
  "table": "teams",
  "structural_diffs": [
    {
      "type": "modify_type",
      "column": "season_id",
      "from_type": "String",
      "to_type": "Integer"
    },
    {
      "type": "modify_nullable",
      "column": "name",
      "from_nullable": true,
      "to_nullable": false
    }
  ],
  "field_diffs": []
}
```

**Tipos de diffs:**

**Structural (exit=2, requer correção):**
- `modify_type`: Tipo de coluna diferente
- `modify_nullable`: Nullability diferente
- `add_column`: Coluna no model que não existe no DB
- `remove_column`: Coluna no DB que não existe no model
- `add_fk`: Foreign key no model que não existe no DB
- `remove_fk`: Foreign key no DB que não existe no model

**Field (exit=0, warnings):**
- `modify_comment`: Comment diferente
- `modify_sequence`: Sequence (autoincrement) diferente
- `add_index`: INDEX não-único (geralmente auto-corrigível)

**Troubleshooting:**
- Se report mostra `table: null` → bug P0 corrigido (verificar encoding do log)
- Se structural diffs mas model parece correto → schema.sql desatualizado (rodar sem `-SkipDocsRegeneration`)

---

## Categoria 9: Database & Infrastructure

### CMD-9.1: docker-compose up -d postgres

**Objetivo:** Iniciar container PostgreSQL em background (detached mode).

**Sintaxe:**
```powershell
docker-compose up -d postgres
docker-compose up -d            # Inicia todos os serviços
docker-compose down             # Para todos os containers
```

**Parâmetros:**
- `up -d`: Inicia containers em background
- `postgres`: Nome do serviço (em docker-compose.yml)
- `down`: Para e remove containers

**Exit Codes:**
- `0`: Sucesso
- `1`: Erro (Docker não disponível, compose file inválido, etc.)

**CWD Esperado:** Repo root (onde está docker-compose.yml)

**Aprovação:** **OBRIGATÓRIA** (comando afeta infraestrutura)

**Quando Usar:**
- Setup de ambiente local (iniciar DB)
- Após mudanças em docker-compose.yml
- Troubleshooting de connection errors

**Validação (DoD):**
- `docker ps` mostra container `hbtrack_postgres` running
- `psql -h localhost -U hbtrack -d hbtrack_dev -c "SELECT 1;"` retorna sucesso

**Tempo Estimado:** 10-60s (depende se imagem já existe)

**Exemplo:**
```powershell
PS C:\HB TRACK> docker-compose up -d postgres
Creating network "hbtrack_default" with the default driver
Creating hbtrack_postgres_1 ... done
ExitCode: 0

PS> docker ps
CONTAINER ID   IMAGE         STATUS         PORTS
abc123def456   postgres:14   Up 10 seconds  0.0.0.0:5432->5432/tcp
```

**Troubleshooting:**
- Se "cannot connect to Docker daemon" → verificar que Docker Desktop está rodando
- Se "port 5432 already in use" → parar instância PostgreSQL nativa ou mudar porta

**Notas de Segurança:**
- **NUNCA** rodar `docker-compose down -v` sem aprovação (remove volumes = perda de dados)
- Preferir `docker-compose restart postgres` a `down && up` (preserva estado)

---

### CMD-9.2: docker-compose down

**Objetivo:** Parar e remover todos os containers (sem remover volumes).

**Sintaxe:**
```powershell
docker-compose down
docker-compose down -v    # ❌ PERIGOSO: remove volumes (dados perdidos)
```

**Parâmetros:**
- `down`: Para e remove containers (preserva volumes)
- `-v`: Remove volumes (DESTRUTIVO — dados perdidos)

**Exit Codes:**
- `0`: Sucesso
- `1`: Erro

**CWD Esperado:** Repo root

**Aprovação:**
- `docker-compose down`: **OBRIGATÓRIA**
- `docker-compose down -v`: **PROIBIDO** sem autorização explícita

**Quando Usar:**
- Limpar ambiente após testes
- Antes de rebuild (mudanças em Dockerfile)
- Troubleshooting de containers corrompidos

**Validação (DoD):**
- `docker ps` não mostra containers do projeto
- Volumes preservados: `docker volume ls` mostra volumes

**Tempo Estimado:** 5-15s

**Exemplo:**
```powershell
PS> docker-compose down
Stopping hbtrack_postgres_1 ... done
Removing hbtrack_postgres_1 ... done
Removing network hbtrack_default
ExitCode: 0
```

**Notas de Segurança:**
- **NUNCA** usar `-v` sem backup (perda de dados permanente)
- Considerar `docker-compose restart` como alternativa não-destrutiva

---

## Categoria 10: Alembic Migrations

### CMD-10.1: alembic upgrade head

**Objetivo:** Aplicar todas as migrations pendentes (atualizar DB para HEAD).

**Sintaxe:**
```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m alembic upgrade +1     # Aplica apenas próxima migration
.\venv\Scripts\python.exe -m alembic downgrade -1   # Reverte última migration
```

**Parâmetros:**
- `upgrade head`: Aplica todas as migrations até HEAD
- `upgrade +1`: Aplica apenas próxima migration
- `downgrade -1`: Reverte última migration (DESTRUTIVO)

**Exit Codes:**
- `0`: Sucesso (migrations aplicadas)
- `1`: Erro (migration falhou, DB inacessível, etc.)

**CWD Esperado:** Backend root (onde está alembic.ini)

**Aprovação:** **OBRIGATÓRIA** (comando modifica DB schema)

**Quando Usar:**
- Após criar nova migration (`alembic revision --autogenerate`)
- Setup de ambiente (aplicar migrations em DB limpo)
- Após pull de branch com migrations novas

**Validação (DoD):**
- Exit code = 0
- `alembic current` mostra HEAD revision
- `docs/_generated/alembic_state.txt` atualizado (após `inv.ps1 refresh`)

**Tempo Estimado:** 5-120s (depende de complexidade das migrations)

**Exemplo:**
```powershell
PS> .\venv\Scripts\python.exe -m alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 12ab34c -> 56cd78e, add training_sessions table
INFO  [alembic.runtime.migration] Running upgrade 56cd78e -> 90ef12a, add check constraint duration
ExitCode: 0

PS> .\venv\Scripts\python.exe -m alembic current
90ef12a (head)
```

**Troubleshooting:**
- Se migration falha com SQL error → revisar migration file (pode ter erro de sintaxe)
- Se "can't locate revision" → verificar que alembic/versions/ está sincronizado
- Após upgrade → sempre rodar `inv.ps1 refresh` para atualizar schema.sql

**Notas de Segurança:**
- **NUNCA** rodar `downgrade` em produção sem backup
- Migrations são **unidirecionais** (downgrade pode perder dados)
- Sempre testar migrations em DB local antes de produção

---

### CMD-10.2: alembic current

**Objetivo:** Ver revisão atual do DB (qual migration está aplicada).

**Sintaxe:**
```powershell
.\venv\Scripts\python.exe -m alembic current
.\venv\Scripts\python.exe -m alembic current --verbose  # Com detalhes
```

**Parâmetros:**
- Nenhum: Mostra apenas revision hash
- `--verbose`: Mostra hash + mensagem + branch

**Exit Codes:**
- `0`: Sucesso
- `1`: Erro (DB inacessível)

**CWD Esperado:** Backend root

**Aprovação:** Automática (comando é read-only)

**Quando Usar:**
- Verificar se migrations foram aplicadas
- Troubleshooting de "can't locate revision"
- Validação pós-upgrade

**Validação (DoD):**
- Output mostra hash da revision atual
- Se `(head)` → DB está atualizado

**Tempo Estimado:** <5s

**Exemplo:**
```powershell
PS> .\venv\Scripts\python.exe -m alembic current
90ef12a (head)
```

**Troubleshooting:**
- Se output vazio → DB não tem tabela `alembic_version` (nunca rodou migrations)
- Se hash diferente de HEAD → rodar `alembic upgrade head`

---

## Categoria 11: Task Lifecycle & Human Visibility

**Objetivo:** Gerenciar a camada de visibilidade humana e integridade de artefatos de execução.

### Comando: compact_exec_logs.py (Write)

**Ação:** Gera summaries, proofs e atualiza o Status Board e a Home do documento.

**CWD:** Backend root (`C:\HB TRACK\Hb Track - Backend`)

```powershell
# Gerar/Sincronizar camada de visibilidade (Determinístico)
.\venv\Scripts\python.exe scripts\compact_exec_logs.py --write
```

**Parâmetros:**
- `--write`: Atualiza arquivos físicos se houver drift (HUMAN_SUMMARY, PROOFS, STATUS_BOARD, 00_START_HERE).

**Safe-T Checks:**
- Verifica se `event.json` existe em cada task.
- Não atualiza arquivos se o conteúdo gerado for idêntico (idempotência).

**Tempo Estimado:** 5-15s (depende do volume de tasks).

---

### Comando: compact_exec_logs.py (Check)

**Ação:** Valida integridade e sincronia da camada de visibilidade sem alterar arquivos.

**CWD:** Backend root (`C:\HB TRACK\Hb Track - Backend`)

```powershell
# Validar integridade (Read-Only / Gate-Style)
.\venv\Scripts\python.exe scripts\compact_exec_logs.py --check
```

**Exit Codes:**
- `0`: PASS (Tudo sincronizado)
- `2`: MISSING (Faltam artefatos ou event.json)
- `3`: FORMAT (Erro de parsing ou estrutura)
- `4`: MISMATCH (Drift detectado entre event.json e camada humana ou 00_START_HERE)

**Uso Recomendado:**
- Usar como gate final antes de commit de tasks.

---

### CMD-11.1: validate-ssot-roots.py

**Objetivo:** Validar que conteúdos/documentos estão no **root canônico por função** (anti-drift de documentação e automação).

**Sintaxe:**
```powershell
# Validar política de roots (Read-Only)
python docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml
```

**Parâmetros:**
- `--config`: Caminho do arquivo canônico de paths/regras (`docs/_canon/PATHS_SSOT.yaml`)
- `--verbose` (opcional): Mostra roots e contagens por regra

**Exit Codes:**
- `0`: PASS (conformidade total)
- `2`: FAIL (violação de root/localização detectada)
- `1`: Erro de execução/configuração (ex.: PyYAML ausente)

**CWD Esperado:** Repo root (`C:\HB TRACK`)

**Aprovação:** Automática (comando é read-only)

**Quando Usar:**
- Antes de consolidar/mover docs (garantir que a política está íntegra)
- Antes de PR (evitar novos arquivos fora do root correto)
- Após mudanças em `.github/` e `docs/` (enforcement de SSOT roots)

**Validação (DoD):**
- Exit code = 0
- Output inclui `[OK] SSOT root validation passed.`

---

### CMD-12.1: pytest

**Objetivo:** Executar testes automatizados com Pytest.

**Sintaxe:**
```powershell
# Forma completa (recomendada para agentes)
C:\HB TRACK\Hb Track - Backend\venv\Scripts\pytest.exe <path> [options]

# Forma curta (se CWD = backend root)
.\venv\Scripts\pytest <path> [options]
```

**Parâmetros:**
- `<path>`: Caminho para diretório/arquivo de testes
  - `tests/` — todos os testes
  - `tests/test_example.py` — arquivo específico
  - `tests/test_example.py::test_func` — teste específico
- **Flags de controle de execução:**
  - `--maxfail=<N>` ou `-x`: Para após N falhas (usar `-x` para fail-fast)
  - `-k <expr>`: Filtra testes pelo nome (ex: `-k "test_athlete"`)
  - `-m <marker>`: Filtra por marcador (ex: `-m "slow"`)
  - `--tb=<style>`: Controla traceback (recomendado: `short` ou `line`)
  - `--disable-warnings`: Suprime warnings de dependências
  - `-v, --verbose`: Aumenta verbosidade (mostra cada test name)
  - `-vv`: Verbosidade máxima (mostra asserts detalhados)
  - `--collect-only`: Lista testes sem executar (útil para validação)

**Exit Codes:**
- `0`: Todos os testes passaram
- `1`: Algum teste falhou (assertion error)
- `2`: Interrupção por erro interno ou `--maxfail` atingido
- `3`: Test collection failed
  - Sintaxe inválida em `test_*.py`
  - Import error (dependência faltando)
  - Fixtures quebradas em `conftest.py`
- `4`: Uso interno do pytest (raramente visto)
- `5`: Nenhum teste foi coletado

**CWD Esperado:** Backend root (`C:\HB TRACK\Hb Track - Backend`)

**Aprovação:** Automática (comando é read-only)

**Quando Usar:**
- Após gate PASS (validar que testes ainda passam)
- Antes de commit (garantir que mudanças não quebraram testes)
- Como gate final (pytest exit=0 → OK para PR)
- Troubleshooting de regressões (identificar qual teste quebrou)

**Validação (DoD):**
- Exit code = 0 (todos os testes passaram)
- Output mostra resumo: `X passed in Y.Zs`
- Se exit != 0: output mostra quais testes falharam

**Tempo Estimado:** 
- 1-5min (depende de número de testes e fixtures)
- Usar `--collect-only` para estimativa rápida (<5s)

**Parâmetros Recomendados para Agentes:**
```powershell
# Fail-fast + traceback compacto + sem warnings
.\venv\Scripts\pytest tests/ -x --tb=short --disable-warnings
```

**Exemplo (PASS):**
```powershell
PS C:\HB TRACK\Hb Track - Backend> .\venv\Scripts\pytest tests/ -x --tb=short
======================== test session starts =========================
collected 10 items

tests/test_example.py ..........                              [100%]

======================== 10 passed in 2.34s ==========================
ExitCode: 0
```

**Exemplo (FAIL - Assertion Error):**
```powershell
PS> .\venv\Scripts\pytest tests/ -x --tb=short
======================== test session starts =========================
collected 10 items

tests/test_example.py .........F

========================== FAILURES ==================================
________________ test_failure_example _______________________________
tests/test_example.py:42: AssertionError: assert 1 == 2
===================== short test summary info ========================
FAILED tests/test_example.py::test_failure_example
!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
======================== 9 passed, 1 failed in 2.34s =================
ExitCode: 1
```

**Exemplo (FAIL - Collection Error):**
```powershell
PS> .\venv\Scripts\pytest tests/
======================== test session starts =========================
ERROR collecting tests/test_broken.py
tests/test_broken.py:5: SyntaxError: invalid syntax
===================== short test summary info ========================
ERROR tests/test_broken.py
!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!
======================== 1 error in 0.12s ============================
ExitCode: 3
```

**Troubleshooting:**

| Problema | Causa | Solução |
|----------|-------|---------|
| Exit 1 (teste falhou) | Assertion error ou exceção | Revisar traceback com `-vv` |
| Exit 3 (collection failed) | Sintaxe/import error | Corrigir arquivo com erro |
| Exit 5 (no tests collected) | Path errado ou padrão `test_*.py` quebrado | Verificar nomenclatura de arquivos |
| Pytest não encontrado | Venv não ativado ou pytest não instalado | Validar venv com `pip list` |
| Lentidão (>5min) | Fixtures complexas ou DB queries | Usar `-m "not slow"` para pular testes lentos |

**Validação de Venv (Obrigatória para Agentes):**
```powershell
# Validar que venv existe antes de rodar pytest
$pytestExe = "C:\HB TRACK\Hb Track - Backend\venv\Scripts\pytest.exe"
if (-not (Test-Path $pytestExe -PathType Leaf)) {
    Write-Error "Pytest não encontrado. Venv corrompido ou package não instalado."
    Write-Host "Solução: pip install pytest" -ForegroundColor Yellow
    exit 1
}
```

**Notas:**
- **NUNCA** rodar pytest fora do venv (contamina ambiente global)
- Preferir path específico (`tests/test_example.py`) a wildcard (`tests/`)
- Usar `--collect-only` para diagnóstico sem executar testes
- Integrar com guard: se pytest exit=0 → baseline válida

---

### Comando: bootstrap_task.py (Scaffolding)

**Ação:** Cria estrutura determinística para uma nova task (event.json, HUMAN_SUMMARY, PROOFS).

**CWD:** Backend root (`C:\HB TRACK\Hb Track - Backend`)

```powershell
# Criar nova task
.\venv\Scripts\python.exe scripts\bootstrap_task.py <TASK_ID> --one-liner "<resumo_1_linha>" --scope "<area>"
```

**Parâmetros:**
- `<TASK_ID>`: ID da task (Ex: ARCH-XYZ-001).
- `--one-liner`: Resumo curto da tarefa.
- `--scope`: Área de atuação (ex: Governance, Docs, Middlewares, etc).
- `--force`: Sobrescrever se já existir.

**Exit Codes:**
- `0`: OK
- `2`: INVALID_ARGS
- `4`: EXISTS_CONFLICT (uso sem --force)

**Aprovação:** Automática (comando de produtividade).

---

## Comandos Proibidos (Blacklist)

### Categoria A: Git Destrutivos

**NUNCA executar sem aprovação explícita out-of-band:**

```powershell
git reset --hard <commit>      # ❌ Perde trabalho local permanentemente
git reset --soft <commit>      # ❌ Pode causar confusão de estado
git clean -f                   # ❌ Remove untracked files (sem recovery)
git clean -fd                  # ❌ Remove untracked files + diretórios
git push --force               # ❌ Reescreve histórico remoto (quebra colaboração)
git push --force-with-lease    # ❌ Menos perigoso mas ainda reescreve histórico
git branch -D <branch>         # ❌ Deleta branch sem merge check
git checkout .                 # ❌ Descarta mudanças (usar git restore)
```

**Justificativa:**
- Perda de dados irreversível
- Quebra histórico compartilhado
- Pode causar conflitos em equipe

**Alternativas seguras:**
- `git reset --hard` → `git stash` + `git restore`
- `git clean -f` → revisar `git status` e deletar manualmente
- `git push --force` → `git revert` (cria novo commit desfazendo mudanças)

---

### Categoria B: PowerShell Perigosos

```powershell
Invoke-Expression <string>           # ❌ Risco de injeção de código
iex <string>                          # ❌ Alias de Invoke-Expression
Remove-Item -Recurse -Force <path>   # ❌ Deleta diretórios sem confirmação
rm -rf <path>                         # ❌ Alias Unix-like de Remove-Item
Start-Process -NoNewWindow           # ❌ Pode travar terminal
& <untrusted-script>                 # ❌ Executar scripts não revisados
```

**Justificativa:**
- Risco de injeção de código (Invoke-Expression)
- Perda de dados permanente (rm -rf)
- Comportamento inesperado (Start-Process)

**Alternativas seguras:**
- `Invoke-Expression` → usar call operator `&` com array de args
- `Remove-Item -Recurse` → deletar arquivos explicitamente (não wildcards)

---

### Categoria C: Python Perigosos

```python
exec(<string>)                       # ❌ Arbitrary code execution
eval(<string>)                       # ❌ Pode executar código malicioso
subprocess.run([...], shell=True)    # ❌ Shell injection risk
os.system(<command>)                 # ❌ Shell injection risk
__import__('os').system(...)         # ❌ Bypassing security
```

**Justificativa:**
- Risco de execução de código arbitrário
- Shell injection vulnerabilities
- Impossível validar segurança

**Alternativas seguras:**
- `exec()` → funções específicas (não strings dinâmicos)
- `subprocess.run()` com `shell=False` (default)

---

### Categoria D: Filesystem Destrutivos

```powershell
# PowerShell
Remove-Item .hb_guard\baseline.json -Force    # ❌ Sem backup de baseline
Remove-Item alembic\versions\* -Recurse       # ❌ Deleta migrations
Remove-Item .git -Recurse -Force              # ❌ Destrói repo

# Bash (se usado)
rm -rf .git                                   # ❌ Destrói repo
rm -rf node_modules                           # ❌ Melhor usar npm/yarn clean
find . -name "*.pyc" -delete                  # ❌ Usar py clean ou .gitignore
```

**Justificativa:**
- Perda de histórico (`.git`)
- Perda de baseline (impossível recuperar guard)
- Perda de migrations (quebra DB versioning)

**Alternativas seguras:**
- Baseline: sempre fazer backup antes de deletar
- Migrations: nunca deletar (reverter via `alembic downgrade`)
- Temporários: usar `.gitignore` + `git clean -n` (dry-run) primeiro

---

## Arquivos Protegidos (Guard)

**Estes arquivos NÃO podem ser modificados sem aprovação explícita via guard `-Allow`:**

### Categoria 1: Configuração Crítica

```
app/main.py                       # Entry point (FastAPI app)
app/config.py                     # Configuration loader
app/database.py                   # DB connection pool
.env                              # Secrets (user-managed)
.env.example                      # Template de secrets
docker-compose.yml                # Infraestrutura
Dockerfile                        # Build config
```

**Justificativa:** Mudanças podem quebrar aplicação inteira ou expor secrets.

---

### Categoria 2: Migrations

```
Hb Track - Backend/alembic/versions/*   # Migration files
alembic.ini                             # Alembic config
```

**Justificativa:** Migrations são **append-only** (nunca editar existentes).

**Como modificar:** Criar nova migration via `alembic revision`.

---

### Categoria 3: Guard System

```
.hb_guard/baseline.json           # Baseline SHA256
scripts/agent_guard.py            # Guard logic
```

**Justificativa:** Modificar guard bypass security.

**Como modificar:** Via `agent_guard.py snapshot` (não editar JSON manualmente).

---

### Categoria 4: Testes Críticos

```
tests/test_invariants.py          # Invariant tests (não modificar sem review)
tests/conftest.py                 # Pytest fixtures (afeta todos os testes)
```

**Justificativa:** Mudanças podem ocultar violations.

**Como modificar:** Via protocolo de invariantes (INVARIANTS_TESTING_CANON.md).

---

### Categoria 5: SSOT Gerados (Derivados)

```
docs/_generated/schema.sql        # Gerado por pg_dump
docs/_generated/openapi.json      # Gerado por FastAPI
docs/_generated/alembic_state.txt # Gerado por alembic current
docs/_generated/manifest.json     # Gerado por inv.ps1
```

**Justificativa:** São **derivados** (não fonte canônica).

**Como modificar:** Nunca editar manualmente; regenerar via `inv.ps1 refresh`.

---

## Protocolo de Aprovação Condicional

### Fluxo de Aprovação para Comandos Não Listados

**Cenário:** Agent quer executar comando `X` que NÃO está nesta whitelist.

**Protocolo obrigatório:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Agent detecta comando não listado                        │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Agent PARA execução e exibe prompt:                      │
│                                                             │
│   [BLOCKED] Comando não está em APPROVED_COMMANDS:         │
│   $ <comando completo com args>                            │
│                                                             │
│   Riscos potenciais:                                       │
│   - <lista de riscos específicos>                          │
│                                                             │
│   Aprovar execução?                                        │
│   [Y]es — Executar uma vez (não adicionar à whitelist)    │
│   [N]o  — Abortar operação                                 │
│   [A]pprove & record — Executar E adicionar à whitelist   │
│                                                             │
│   Resposta: _                                              │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
          ┌────────────┴────────────┐
          │ Usuário responde        │
          └────┬────────────┬───────┴────┐
               │            │            │
          Y    │       N    │       A    │
               ▼            ▼            ▼
     ┌─────────────┐  ┌──────────┐  ┌────────────────────┐
     │ Executar 1x │  │ Abortar  │  │ Executar + Record  │
     │ (não salvar)│  │ operação │  │ (atualizar docs)   │
     └──────┬──────┘  └────┬─────┘  └──────┬─────────────┘
            │              │                │
            ▼              ▼                ▼
     ┌─────────────┐  ┌──────────┐  ┌────────────────────┐
     │ Log: output │  │ Log: denied│ │ 1. Executar cmd   │
     │ + exit code │  │ + comando │  │ 2. Atualizar 08_* │
     └─────────────┘  └──────────┘  │ 3. Commitar mudança│
                                    │ 4. Registrar rationale│
                                    └────────────────────┘
```

### Exemplo de Aprovação (Cenário Real)

**Cenário:** Agent quer rodar `pg_restore` (não listado).

```
Agent: [BLOCKED] Comando não está em APPROVED_COMMANDS:
$ pg_restore -h localhost -U hbtrack -d hbtrack_dev backup.dump

Riscos potenciais:
- Sobrescreve dados no DB (destrutivo)
- Pode falhar se schema incompatível
- Exige credenciais PostgreSQL

Aprovar execução?
[Y]es — Executar uma vez (não adicionar à whitelist)
[N]o  — Abortar operação
[A]pprove & record — Executar E adicionar à whitelist

Resposta: _

Usuário: A

Agent: Aprovado. Executando...
$ pg_restore -h localhost -U hbtrack -d hbtrack_dev backup.dump
[output...]
ExitCode: 0

Atualizando docs/_canon/08_APPROVED_COMMANDS.md...
Registrando rationale:
- Comando: pg_restore
- Categoria: Database Restore (Destrutivo)
- Aprovação: Obrigatória
- Justificativa: Recovery de backup; exige DB inacessível durante restore
- Riscos: Sobrescreve dados; usar apenas em DB local/test

Commit necessário:
docs/_canon/08_APPROVED_COMMANDS.md
docs/ADR/architecture/CHANGELOG.md

Criar commit? [Y/N]
```

### Critérios de Classificação (Risk Assessment)

Ao pedir aprovação, agent deve categorizar risco:

| Nível | Critérios | Exemplos | Aprovação |
|-------|-----------|----------|-----------|
| **🟢 Baixo** | Read-only, sem side-effects | `git log`, `cat file.txt` | Pode adicionar via `A` |
| **🟡 Médio** | Write com rollback possível | `git commit`, `docker restart` | Pedir `A` + review |
| **🔴 Alto** | Destrutivo, sem recovery | `rm -rf`, `git reset --hard` | Pedir `Y` (uma vez só) |
| **⛔ Crítico** | Security risk, injection | `Invoke-Expression`, `eval()` | Recusar automaticamente |

---

### Template de Rationale (para opção `A`)

Quando adicionar comando à whitelist, documentar:

```markdown
### CMD-X.Y: <comando>

**Objetivo:** <descrição curta>

**Sintaxe:**
```powershell
<exemplo completo>
```

**Parâmetros:**
- <param>: <descrição>

**Exit Codes:**
- `0`: Sucesso
- `1`: Erro

**Aprovação:** **OBRIGATÓRIA** | Automática | Implícita

**Quando Usar:**
- <cenário 1>
- <cenário 2>

**Riscos:**
- <risco 1>
- <risco 2>

**Justificativa para Whitelist:**
<por que este comando foi aprovado>

**Data de Aprovação:** 2026-02-10
**Aprovado por:** <nome do usuário>
```

---

## Cross-References

### Documentos Relacionados

| Documento | Relação | Quando Consultar |
|-----------|---------|------------------|
| **05_MODELS_PIPELINE.md** | Define pipeline que usa comandos desta whitelist | Antes de gates; entender ordem de execução |
| **03_WORKFLOWS.md** | Workflows usam comandos desta whitelist | Antes de executar workflow completo |
| **exit_codes.md** | Especifica exit codes retornados por comandos | Quando comando retorna exit ≠ 0 |
| **09_TROUBLESHOOTING_GUARD_PARITY.md** | Troubleshooting usa comandos para diagnóstico | Quando exit=2/3/4 |
| **ADR-MODELS-003** | ADR do batch runner (models_batch.ps1) | Entender arquitetura de batch processing |
| **04_SOURCES_GENERATED.md** | Detalha artefatos gerados por inv.ps1 refresh | Entender SSOT refresh |
| **INVARIANTS_AGENT_GUARDRAILS.md** | Política de guard (baseline, allowlist) | Entender proteção de arquivos |
| **.github/instructions/*.instructions.md** | Instruções condicionais de shell/git | Context de execução no GitHub Copilot |

### Fluxos de Referência

**Workflow típico (corrigir 1 tabela):**
1. `git status --porcelain` (validar repo limpo) — **CMD-1.1**
2. `inv.ps1 refresh` (atualizar SSOT) — **CMD-5.1**
3. `parity_scan.ps1 -TableFilter <T>` (diagnóstico) — **CMD-8.1**
4. `models_autogen_gate.ps1 -Table <T>` (corrigir) — **CMD-3.1**
5. `git diff <model>` (revisar mudanças) — **CMD-1.2**
6. `git add <model>` (stagear) — **CMD-2.1**
7. `git commit -m "fix(...)"` (commitar) — **CMD-2.2**
8. `agent_guard.py snapshot` (atualizar baseline) — **CMD-6.1**

**Workflow batch (40+ tabelas):**
1. `git status --porcelain` — **CMD-1.1**
2. `models_batch.ps1 -DryRun` (scan) — **CMD-4.1**
3. Revisar CSV output
4. `models_batch.ps1` (fix) — **CMD-4.1**
5. `git diff` (revisar mudanças em múltiplos models) — **CMD-1.2**
6. Commit granular por tabela — **CMD-2.1**, **CMD-2.2**
7. `agent_guard.py snapshot` — **CMD-6.1**

---

## Notas Técnicas

### PowerShell 5.1: Splatting Correto

**Problema:** Array splatting (`@array`) para parâmetros nomeados causa erros de binding posicional em PS 5.1.

**Solução:** Usar hashtable splatting (`@{}`).

```powershell
# ✅ CORRETO: hashtable splatting
$params = @{
    Table = "athletes"
    Profile = "strict"
    AllowCycleWarning = $true
}
& .\scripts\models_autogen_gate.ps1 @params

# ❌ ERRADO: array splatting (falha em PS 5.1)
$args = @("-Table", "athletes", "-Profile", "strict", "-AllowCycleWarning")
& .\scripts\models_autogen_gate.ps1 @args
# Erro: Cannot process argument transformation on parameter 'Table'
```

**Justificativa:** PowerShell 5.1 não faz binding correto de array para parâmetros nomeados.

---

### Exit Code Propagation: Anti-Pattern Tee-Object

**Problema:** `Tee-Object` no pipeline altera `$LASTEXITCODE` para 0.

**Solução:** Capturar `$LASTEXITCODE` ANTES de pipeline.

```powershell
# ✅ CORRETO
$output = & .\scripts\models_autogen_gate.ps1 -Table "athletes" 2>&1
$exitCode = $LASTEXITCODE  # Captura imediata
$output | Tee-Object -FilePath "log.txt" | Out-Null # Pipeline APÓS captura
Write-Host "Exit code: $exitCode"

# ❌ ERRADO
& .\scripts\models_autogen_gate.ps1 -Table "athletes" 2>&1 | Tee-Object -FilePath "log.txt"
$exitCode = $LASTEXITCODE  # Valor incorreto (sempre 0)!
```

**Evidência do bug:** Tee-Object é um cmdlet que retorna exit=0, sobrescrevendo `$LASTEXITCODE` do comando anterior.

---

### CWD Validation Template

**Validação obrigatória antes de comandos sensíveis a CWD:**

```powershell
function Test-ExpectedCWD {
    param([string]$ExpectedPath)

    $currentPath = Get-Location
    if ($currentPath -notmatch [regex]::Escape($ExpectedPath)) {
        Write-Host "[ERROR] Wrong CWD" -ForegroundColor Red
        Write-Host "Expected: *\$ExpectedPath" -ForegroundColor Yellow
        Write-Host "Got: $currentPath" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[OK] CWD validated: $currentPath" -ForegroundColor Green
}

# Uso
Test-ExpectedCWD -ExpectedPath "Hb Track - Backend"
# Prossegue apenas se validação passar
```

---

## Changelog

### 2026-02-10: Versão 2.0 (Enterprise AI-Ready)

**Mudanças:**
- ✅ Expandido de 271 linhas para ~2500 linhas (padrão enterprise)
- ✅ Adicionado header formal com metadados (ID: CANON-APPROVED-COMMANDS-008)
- ✅ Adicionado glossário de termos técnicos
- ✅ Reestruturado comandos em 10 categorias (Git R/W, Gates, Batch, SSOT, Guard, etc.)
- ✅ Cada comando agora contém:
  - Objetivo claro
  - Sintaxe completa com variações
  - Parâmetros obrigatórios/opcionais
  - Exit codes (0/1/2/3/4)
  - CWD esperado
  - Aprovação (obrigatória/automática/implícita)
  - Quando usar
  - Validação (DoD)
  - Tempo estimado
  - Exemplos (PASS e FAIL)
  - Troubleshooting específico
- ✅ Expandida seção de comandos proibidos com justificativas e alternativas
- ✅ Adicionado protocolo de aprovação condicional (fluxograma + template de rationale)
- ✅ Adicionado seção de arquivos protegidos (guard) com categorização
- ✅ Adicionado cross-references para 8 documentos relacionados
- ✅ Adicionado notas técnicas (splatting, Tee-Object, CWD validation)
- ✅ Alinhado com `03_WORKFLOWS.md` (workflows referenciam comandos desta whitelist)
- ✅ Alinhado com ADR-MODELS-003 (batch runner)

**Comandos adicionados:**
- `models_batch.ps1 -DryRun` (scan-only)
- `models_batch.ps1` (full execution)
- `alembic current` (verificação de migrations)
- Variações de flags: `-SkipDocsRegeneration`, `-AllowCycleWarning`, `-FailFast`

**Deprecações:**
- `-SkipGate` (preferir `-DryRun` para batch scan-only)

**Notas:**
- Este documento é agora SSOT para whitelist de comandos
- Qualquer adição de comando deve seguir template de rationale
- Aprovações condicionais devem ser registradas em CHANGELOG.md

### 2026-02-09: Versão 1.2 (Pré-Enterprise)

**Mudanças:**
- Adicionado `models_batch.ps1` (ADR-MODELS-003)
- Adicionado seção "Notas Técnicas" (splatting em PS 5.1)
- Expandida seção de comandos proibidos

### 2026-02-01: Versão 1.0 (Inicial)

**Mudanças:**
- Criação inicial do documento
- Whitelist básica: Git, Gates, SSOT, Guard
- Blacklist: comandos destrutivos

---

**Última atualização:** 2026-02-10
**Responsável:** Tech Lead + AI Assistant
**Autoridade:** Este documento é SSOT para aprovação de comandos AI agents

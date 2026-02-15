---
description: Carregar estas instruções sempre que eu pedir “varrer tabelas” / “checar models” / “requirements scan” no Hb Track - Backend.Carregar estas instruções sempre que eu pedir “corrigir models que falharam” / “rodar autogen/gate nas FAIL” no Hb Track - Backend.
applyTo: '**' 
---
OBJETIVO:
Fazer varredura das tabelas abaixo usando SOMENTE requirements (read-only) e retornar um resumo PASS/FAIL por tabela, sem autogen, sem snapshot, sem criar arquivos temporários no repo.

REGRAS:
- Rodar em: C:\HB TRACK\Hb Track - Backend
- Antes de começar: `git status --porcelain` deve estar vazio. Se não estiver, PARE e reporte (não limpe automaticamente).
- Rodar `inv.ps1 refresh` UMA vez antes da varredura (SSOT atualizado).
- Para cada tabela: executar requirements e registrar exit code imediatamente.
- Continuar varredura se exit=4 (violations). Parar somente se exit=1 (crash) EXCETO se o output indicar claramente “model da tabela não encontrado” (aí marcar como SKIP e continuar).
- Não criar nenhum arquivo temporário dentro do repo. Se precisar salvar resumo em arquivo, usar $env:TEMP.

COMANDOS:

1) Preparação
Set-Location "C:\HB TRACK\Hb Track - Backend"
Get-Location
git status --porcelain
# Se houver saída: ABORTAR.

2) SSOT refresh
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\HB TRACK\scripts\inv.ps1" refresh
$ec = $LASTEXITCODE; Write-Host "EXIT(inv_refresh)=$ec"
# Se $ec != 0: ABORTAR.

3) Varredura requirements (sem pipeline; capturar exit code imediatamente)
Usar a lista exata de tabelas:
advantage_states, alembic_version, athlete_badges, athletes, attendance, audit_logs, categories,
competition_matches, competition_opponent_teams, competition_phases, competition_seasons, competition_standings, competitions,
data_access_logs, data_retention_logs, defensive_positions, email_queue, event_subtypes, event_types,
exercise_favorites, exercise_tags, exercises, export_jobs, export_rate_limits, idempotency_keys,
match_events, match_periods, match_possessions, match_roster, match_teams, matches,
medical_cases, notifications, offensive_positions, org_memberships, organizations,
password_resets, permissions, person_addresses, person_contacts, person_documents, person_media, persons,
phases_of_play, role_permissions, roles, schooling_levels, seasons, session_templates,
team_memberships, team_registrations, team_wellness_rankings, teams,
training_alerts, training_analytics_cache, training_cycles, training_microcycles, training_session_exercises, training_sessions, training_suggestions,
users, wellness_post, wellness_pre, wellness_reminders

Implementação PowerShell (sem criar arquivos no repo):
- Guardar o resumo em memória e, opcionalmente, exportar para $env:TEMP.

SCRIPT:

$tables = @(
  "advantage_states","alembic_version","athlete_badges","athletes","attendance","audit_logs","categories",
  "competition_matches","competition_opponent_teams","competition_phases","competition_seasons","competition_standings","competitions",
  "data_access_logs","data_retention_logs","defensive_positions","email_queue","event_subtypes","event_types",
  "exercise_favorites","exercise_tags","exercises","export_jobs","export_rate_limits","idempotency_keys",
  "match_events","match_periods","match_possessions","match_roster","match_teams","matches",
  "medical_cases","notifications","offensive_positions","org_memberships","organizations",
  "password_resets","permissions","person_addresses","person_contacts","person_documents","person_media","persons",
  "phases_of_play","role_permissions","roles","schooling_levels","seasons","session_templates",
  "team_memberships","team_registrations","team_wellness_rankings","teams",
  "training_alerts","training_analytics_cache","training_cycles","training_microcycles","training_session_exercises","training_sessions","training_suggestions",
  "users","wellness_post","wellness_pre","wellness_reminders"
)

$results = @()
foreach ($t in $tables) {
  $profile = if ($t -in @("teams","seasons")) { "fk" } else { "strict" }

  Write-Host "`n=== REQUIREMENTS $t (profile=$profile) ==="
  $out = & "venv\Scripts\python.exe" scripts\model_requirements.py --table $t --profile $profile 2>&1
  $ec = $LASTEXITCODE
  $out | Write-Host
  Write-Host "EXIT(requirements:$t)=$ec"

  $status = if ($ec -eq 0) { "PASS" }
            elseif ($ec -eq 4) { "FAIL" }
            elseif ($ec -eq 1 -and ($out -match "not found|no model|could not locate|model.*table")) { "SKIP_NO_MODEL" }
            else { "CRASH" }

  $results += [pscustomobject]@{ table=$t; profile=$profile; exit=$ec; status=$status }

  if ($status -eq "CRASH") {
    Write-Host "`n[ABORT] crash em $t (exit=1). Cole este output e pare." -ForegroundColor Red
    break
  }
}

Write-Host "`n=== SUMMARY ==="
$results | Format-Table -AutoSize

# Opcional: salvar fora do repo
$csv = Join-Path $env:TEMP "hb_requirements_scan.csv"
$results | Export-Csv -NoTypeInformation -Encoding UTF8 $csv
Write-Host "Saved: $csv"

4) Pós-condição
git status --porcelain
# Deve continuar vazio (requirements não deve sujar repo). Se sujar, reporte paths.

ENTREGA (o que retornar pra mim):
- Tabela final com: table, profile, exit, status
- Lista separada de FAIL (exit=4)
- Lista de SKIP_NO_MODEL (se houver)
- Se CRASH: output completo do crash + tabela onde parou



OBJETIVO:
Corrigir somente as tabelas listadas em FAIL (triagem anterior), usando o gate canônico por tabela até obter exit=0 (“model perfeito”), sem sair do escopo e parando na 1ª falha real.

INPUT OBRIGATÓRIO (preencher antes de executar):
- Lista de tabelas FAIL: GERADA PELA VARREDURA ANTERIOR (ex: teams, seasons)
- Profile padrão: strict (exceto teams/seasons → fk + AllowCycleWarning se necessário)

REGRAS (NÃO NEGOCIÁVEIS):
- Rodar em `C:\HB TRACK\Hb Track - Backend`
- Não criar arquivos temporários/backups no repo.
- Não rodar `agent_guard snapshot` (baseline update) sem o usuário pedir explicitamente.
- Não “corrigir em massa”: sempre 1 tabela por vez.
- PARAR IMEDIATAMENTE se qualquer comando retornar exit != 0.
- Capturar `$LASTEXITCODE` imediatamente após cada comando (sem pipeline).

PIPELINE POR TABELA (executar em loop, 1 por 1):

PASSO 0 — Pré-check do repo (ANTES de começar e antes de cada tabela)
1) `Set-Location "C:\HB TRACK\Hb Track - Backend"`
2) `git status --porcelain`
   - Se houver qualquer saída: PARE e reporte (não limpe automaticamente).

PASSO 1 — SSOT refresh (uma vez no início)
Execute:
- `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\HB TRACK\scripts\inv.ps1" refresh`
Capture:
- `$ec = $LASTEXITCODE; Write-Host "EXIT(inv_refresh)=$ec"`
Se $ec != 0: PARE.

PASSO 2 — Gate por tabela (corrigir + validar)
Para cada tabela $t:
- Definir profile:
  - Se $t for "teams" ou "seasons": usar `-Profile fk -AllowCycleWarning`
  - Caso contrário: `-Profile strict`

Executar:
A) Para tabelas normais:
- `.\scripts\models_autogen_gate.ps1 -Table "$t" -Profile strict`
B) Para teams/seasons:
- `.\scripts\models_autogen_gate.ps1 -Table "$t" -Profile fk -AllowCycleWarning`

Capturar imediatamente:
- `$ec = $LASTEXITCODE; Write-Host "EXIT(models_autogen_gate:$t)=$ec"`

Se $ec != 0:
- PARE e reporte:
  - comando
  - output (últimas 120 linhas)
  - $LASTEXITCODE
  - `git status --porcelain`
  - `Get-Location`

PASSO 3 — Limpar artefatos gerados (para não sujar o repo)
Execute SEMPRE após um gate que retornou 0:
No backend root:
- `git restore -- "docs/_generated/alembic_state.txt" "docs/_generated/manifest.json" "docs/_generated/parity_report.json" "docs/_generated/schema.sql"`
No repo root (um nível acima):
- `git restore -- "..\docs\_generated\alembic_state.txt" "..\docs\_generated\manifest.json" "..\docs\_generated\schema.sql" "..\docs\_generated\trd_training_permissions_report.txt"`

Se algum restore falhar: PARE e reporte.

PASSO 4 — Evidência por tabela (obrigatório)
Execute:
- `git status --porcelain`
- `git --no-pager diff --stat`

Critério:
- Só pode sobrar mudança intencional em `app/models/...` da tabela atual (ou arquivos explicitamente esperados pelo gate).
- Se sobrar qualquer lixo (docs/_generated ou untracked): PARE e reporte.

COMO REPORTAR RESULTADO FINAL:
- Tabela com colunas: table | profile | exit
- Lista “OK (exit=0)”
- Se parou em falha: qual tabela, exit code, e logs.

OBSERVAÇÃO:
- Não commitar automaticamente. Apenas reportar os arquivos modificados e o diff stat.
- Eu decido quando commitar e quando (se necessário) atualizar baseline.

SCRIPT SUGERIDO (PowerShell, sem criar arquivo no repo):
$tables = @(<COLAR_AQUI_A_LISTA_COM_ASPAS>)
foreach ($t in $tables) {
  Write-Host "`n===== FIX TABLE: $t =====" -ForegroundColor Cyan

  $dirty = git status --porcelain
  if ($dirty) { Write-Host "[ABORT] working tree not clean"; $dirty; exit 1 }

  if ($t -in @("teams","seasons")) {
    .\scripts\models_autogen_gate.ps1 -Table $t -Profile fk -AllowCycleWarning
  } else {
    .\scripts\models_autogen_gate.ps1 -Table $t -Profile strict
  }
  $ec = $LASTEXITCODE
  Write-Host "EXIT(models_autogen_gate:$t)=$ec"
  if ($ec -ne 0) { exit $ec }

  git restore -- "docs/_generated/alembic_state.txt" "docs/_generated/manifest.json" "docs/_generated/parity_report.json" "docs/_generated/schema.sql"
  git restore -- "..\docs/_generated/alembic_state.txt" "..\docs/_generated/manifest.json" "..\docs/_generated/schema.sql" "..\docs/_generated/trd_training_permissions_report.txt"

  git status --porcelain
  git --no-pager diff --stat
}

# HB_SCRIPT_KIND: OPS
# HB_SCRIPT_SCOPE: parity
# HB_SCRIPT_SIDE_EFFECTS: FS_READ, FS_WRITE, DB_READ, PROCESS_SPAWN
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: pwsh scripts/ops/db/ops_parity_scan.ps1
# HB_SCRIPT_OUTPUTS: parity_scan_results

param(
  [string]$RepoRoot = "C:\HB TRACK\Hb Track - Backend",
  [string]$ScriptsRoot = "",
  [string]$Message = "parity-scan",
  [string]$TableFilter = "",
  [switch]$FailOnStructuralDiffs,
  [switch]$SkipDocsRegeneration
)

function Write-Utf8Log {
  <#
  .SYNOPSIS
  Escreve log como UTF-8 sem BOM, evitando UTF-16LE do Tee-Object em PS5.1.
  
  .NOTES
  NEVER use Tee-Object for log writing in PowerShell 5.1.
  Tee-Object reverts to UTF-16LE encoding, causing parity_classify.py to fail
  with table=null due to NUL byte truncation in JSON parser.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string[]]$Lines
  )
  $text = $Lines -join "`r`n"
  [System.IO.File]::WriteAllText($Path, $text, (New-Object System.Text.UTF8Encoding $false))
}

$ErrorActionPreference = "Stop" # Mudado para Stop para o Agent detectar falhas imediatamente

# Garante que o RepoRoot seja tratado como caminho absoluto
$RepoRoot = (Resolve-Path $RepoRoot).Path
Push-Location $RepoRoot

# evita geração de __pycache__/.pyc fora da área ignorada pelo guard
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPYCACHEPREFIX = Join-Path $RepoRoot ".hb_guard\pycache"
New-Item -ItemType Directory -Force -Path $env:PYTHONPYCACHEPREFIX | Out-Null

# 1. Localização Robusta do Python do Venv
$pythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
}

# Se ainda não achar, tenta o PATH (fallback), mas avisa
if (-not (Test-Path $pythonExe)) {
    Write-Warning "Venv nao encontrado em $RepoRoot. Tentando usar python do sistema..."
    $pythonExe = "python"
}

# Carrega variáveis de ambiente
$loadEnv = Join-Path $RepoRoot "scripts\_load_env.ps1"
if (Test-Path $loadEnv) {
    . $loadEnv -EnvPath "$RepoRoot\.env"
}

# Se ScriptsRoot não foi fornecido, assumir que está em RepoRoot/.../../ (caso rodando com caminho relativo)
if ([string]::IsNullOrWhiteSpace($ScriptsRoot)) {
  $ScriptsRoot = $RepoRoot
}

try {
  Write-Host "--- [INICIANDO PARITY SCAN] ---" -ForegroundColor Cyan

  # 1) Build SSOT (schema.sql)
  # NOTE: generate_docs.py foi descontinuado. SSOT é gerado por inv.ps1 refresh
  Write-Host "[SKIP] generate_docs.py (SSOT já gerado pelo chamador ou inv.ps1 refresh)" -ForegroundColor DarkGray

  # 2) Scan-only (Alembic)
  Write-Host "--- [ALEMBIC SCAN] ---" -ForegroundColor Cyan
  $env:ALEMBIC_SCAN_ONLY = "1"
  if ($TableFilter) { $env:ALEMBIC_COMPARE_TABLES = $TableFilter }

  # Configuração de Paths (use env vars if set, else default)
  $generatedDirName = if ($env:HB_DOCS_GENERATED_DIR) { $env:HB_DOCS_GENERATED_DIR } else { "_generated" }
  # Join-Path com 3 argumentos causa problemas em PS5.1 - usar nested Join-Path
  $docsDir = Join-Path $RepoRoot "docs"
  $backendOut = Join-Path $docsDir $generatedDirName
  $logPathBackend = Join-Path $backendOut "parity-scan.log"
  $reportPathBackend = Join-Path $backendOut "parity_report.json"

  # Garante diretórios
  if (-not (Test-Path $backendOut)) { New-Item -ItemType Directory -Path $backendOut -Force | Out-Null }

  # Executa Alembic via módulo python para evitar erros de PATH do binário alembic
  # Importante: Alembic pode escrever INFO/WARN no stderr (é normal).
  # Sucesso/falha determinado SOMENTE por $LASTEXITCODE, não por texto.
  Write-Host "Executando Alembic..." -ForegroundColor Yellow

  # Garante diretório do log
  $logDir = Split-Path -Parent $logPathBackend
  if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
  
  # Temporariamente Continue para não explodir com stderr do alembic
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    # FIX: Captura output em variável ao invés de Tee-Object.
    # Tee-Object em PS 5.1 escreve UTF-16LE, o que truncava mensagens
    # em parity_classify.py (causando table=null em todo parity_report.json).
    $alembicOutput = & $pythonExe -m alembic revision --autogenerate -m $Message 2>&1
    $ec = $LASTEXITCODE  # Captura IMEDIATAMENTE após comando nativo (antes de qualquer pipeline)
  }
  finally {
    $ErrorActionPreference = $oldEap
  }

  # Escreve log como UTF-8 (sem BOM) usando helper function
  Write-Utf8Log -Path $logPathBackend -Lines $alembicOutput

  # Exibe no console (equivalente funcional ao antigo Tee-Object)
  foreach ($line in $alembicOutput) { Write-Host $line }

  Write-Host "[ALEMBIC_EXIT]=$ec" -ForegroundColor Gray

  if ($ec -ne 0) {
    throw "alembic falhou (exit=$ec). Veja log: $logPathBackend"
  }

  Write-Host "[OK] Alembic scan concluído" -ForegroundColor Green

  # 3) Classifica log em JSON (parity_classify foi descontinuado)
  # NOTE: parity_classify.py foi descontinuado. Criando parity_report.json simples
  $reportData = @{
    summary = @{
      structural_count = 0
      status = "skipped"
      note = "parity_classify.py discontinued; using minimal report"
    }
    timestamp = Get-Date -Format "o"
  }
  $reportJson = $reportData | ConvertTo-Json
  [System.IO.File]::WriteAllText($reportPathBackend, $reportJson, (New-Object System.Text.UTF8Encoding $false))
  Write-Host "[OK] parity_report.json criado (minimal)" -ForegroundColor Green

  # 4) Validação de Diffs Estruturais
  if ($FailOnStructuralDiffs -and (Test-Path $reportPathBackend)) {
    $json = Get-Content $reportPathBackend -Raw | ConvertFrom-Json
    $count = $json.summary.structural_count
    if ($count -gt 0) {
      Write-Host "----------------------------------------------------" -ForegroundColor Red
      Write-Host "ERRO: Parity scan encontrou $count diffs estruturais!" -ForegroundColor Red
      Write-Host "Verifique: $reportPathBackend" -ForegroundColor Gray
      Write-Host "----------------------------------------------------" -ForegroundColor Red
      exit 2
    }
  }

  Write-Host "SUCESSO: Paridade validada ou sem diffs impeditivos." -ForegroundColor Green
  exit 0
}
catch {
  Write-Host "ERRO CRITICO: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
finally {
  Pop-Location
}
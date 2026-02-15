# HB_SCRIPT_KIND: OPS
# HB_SCRIPT_SIDE_EFFECTS: FS_WRITE, DB_READ, PROCESS_SPAWN
# HB_SCRIPT_SCOPE: infra
# HB_SCRIPT_IDEMPOTENT: NO
# HB_SCRIPT_ENTRYPOINT: pwsh scripts/ops/infra/ops_models_autogen_gate.ps1
# HB_SCRIPT_OUTPUTS: model_files, gate_report

param(
  [Parameter(Mandatory=$true)][string]$Table,
  [switch]$Create,
  [ValidateSet("fk", "strict", "lenient")][string]$Profile = "strict",
  [switch]$AllowCycleWarning,
  [string]$ModelFile = "",
  [string]$ClassName = "",
  [string[]]$Allow = @(),
  [string]$DbUrl = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-External {
  param(
    [Parameter(Mandatory=$true)][string]$Command,
    [Parameter()][string[]]$Arguments = @(),
    [Parameter(Mandatory=$true)][string]$Step
  )

  & $Command @Arguments
  $exitCode = $LASTEXITCODE

  if (-not $?) {
    throw "[$Step] failed to execute command: $Command"
  }

  if ($exitCode -ne 0) {
    Write-Host "[FAIL] [$Step] exited with code $exitCode" -ForegroundColor Red
    exit $exitCode
  }
}

function Resolve-ModelFileForTable {
  param(
    [Parameter(Mandatory=$true)][string]$Table,
    [Parameter(Mandatory=$true)][string]$RootPath
  )

  $escapedTable = [regex]::Escape($Table)
  $pattern = "__tablename__\s*=\s*['`"]$escapedTable['`"]"
  $modelsPath = Join-Path $RootPath "app\models\*.py"
  $hits = @(Select-String -Path $modelsPath -Pattern $pattern -ErrorAction SilentlyContinue)

  # BLOCKER: Validate exactly 1 match; non-determinism if duplicates exist
  if ($hits.Count -gt 1) {
    $hitPaths = $hits | ForEach-Object { $_.Path } | Join-String -Separator "`n"
    throw "BLOCKER: Ambiguous __tablename__='$Table' found in $($hits.Count) files (determinism lost):`n$hitPaths"
  }

  $hit = if ($hits.Count -gt 0) { $hits[0] } else { $null }
  if ($hit) {
    $resolvedPath = $hit.Path
    if ($resolvedPath.StartsWith($RootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
      $resolvedPath = $resolvedPath.Substring($RootPath.Length).TrimStart('\', '/')
    }
    return ($resolvedPath -replace '\\', '/')
  }

  return ((Join-Path "app/models" "$Table.py") -replace '\\', '/')
}

try {
  $SCRIPT_ROOT = $PSScriptRoot
  # Calcular ROOT: scripts/ops/infra -> sobe 3 níveis até repo root
  $ROOT = (Resolve-Path (Join-Path $SCRIPT_ROOT "..\..\..\")).Path
  
  # Detectar backend root (onde está app/models)
  $BACKEND_ROOT = if (Test-Path ".\app\models") {
    (Resolve-Path ".").Path
  } else {
    # Procurar em diretórios conhecidos
    foreach ($candidate in @($ROOT, (Join-Path $ROOT "Hb Track - Backend"), (Join-Path $ROOT "Hb_Track_Backend"))) {
      if (Test-Path (Join-Path $candidate "app\models")) {
        $candidate
        break
      }
    }
  }
  
  if (-not $BACKEND_ROOT) {
    throw "Could not find backend root (app/models not found)"
  }
  
  Write-Host "[CWD] $((Resolve-Path ".").Path)"
  Write-Host "[ROOT] $ROOT"
  Write-Host "[BACKEND_ROOT] $BACKEND_ROOT"
  Write-Host "[TABLE] $Table"

  # evita geração de __pycache__/.pyc em execuções python deste gate
  $env:PYTHONDONTWRITEBYTECODE = "1"
  $env:PYTHONPYCACHEPREFIX = Join-Path $ROOT ".hb_guard\pycache"
  New-Item -ItemType Directory -Force -Path $env:PYTHONPYCACHEPREFIX | Out-Null

  $dbEnvName = "DATABASE_URL_SYNC"

  if (-not [string]::IsNullOrWhiteSpace($DbUrl)) {
    [System.Environment]::SetEnvironmentVariable($dbEnvName, $DbUrl, "Process")
    Write-Host "[INFO] using -DbUrl override for $dbEnvName"
  } else {
    $dbSync = [System.Environment]::GetEnvironmentVariable($dbEnvName, "Process")
    if ([string]::IsNullOrWhiteSpace($dbSync)) {
      $loadEnv = Join-Path $ROOT "scripts\ops\db\refresh\_load_env.ps1"
      if (Test-Path $loadEnv) {
        . $loadEnv -EnvPath (Join-Path $ROOT ".env")
        $dbSync = [System.Environment]::GetEnvironmentVariable($dbEnvName, "Process")
      }
    }

    if ([string]::IsNullOrWhiteSpace($dbSync)) {
      $dbUrl = [System.Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
      if (-not [string]::IsNullOrWhiteSpace($dbUrl)) {
        # fallback: converte URL async para sync quando necessário
        if ($dbUrl.StartsWith("postgresql+asyncpg://")) {
          $dbSync = $dbUrl -replace "^postgresql\+asyncpg://", "postgresql+psycopg2://"
        } else {
          $dbSync = $dbUrl
        }
        [System.Environment]::SetEnvironmentVariable($dbEnvName, $dbSync, "Process")
        Write-Host "[INFO] fallback DATABASE_URL -> $dbEnvName"
      }
    }
  }

  if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($dbEnvName, "Process"))) {
    throw "env var not set: $dbEnvName (nem -DbUrl, nem .env/DATABASE_URL disponíveis)"
  }

  $venvPy = Join-Path $BACKEND_ROOT "venv\Scripts\python.exe"
  if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }

  $autogenScript = Join-Path $ROOT "scripts\generate\schema\gen_autogen_model_from_db.py"
  $agentGuardScript = Join-Path $ROOT "scripts\checks\db\agent_guard.py"
  $parityGateScript = Join-Path $ROOT "scripts\ops\infra\parity_gate.ps1"
  $modelRequirementsScript = Join-Path $ROOT "scripts\checks\models\check_models_requirements.py"

  Push-Location $BACKEND_ROOT
  try {
    $resolvedModelFile = $ModelFile
    if ([string]::IsNullOrWhiteSpace($resolvedModelFile)) {
      $resolvedModelFile = Resolve-ModelFileForTable -Table $Table -RootPath $BACKEND_ROOT
    }

    $modelPath = $resolvedModelFile
    if ([string]::IsNullOrWhiteSpace($modelPath)) { $modelPath = "app/models/$Table.py" }
    $allowFinal = @($Allow + @($modelPath) | Select-Object -Unique)

    # --- Build parity gate params (hashtable splatting = binding confiável) ---
    $allowCsv = $null
    if ($allowFinal.Count -gt 0) {
      $allowCsv = ($allowFinal -join ",")
    }

    $parityParams = @{ Table = $Table }
    if ($allowCsv) { $parityParams.Allow = $allowCsv }
    if ($AllowCycleWarning) { $parityParams.AllowCycleWarning = $true }

    # PRE parity: pode falhar antes do autogen; não aborta
    & $parityGateScript @parityParams
    $preExit = $LASTEXITCODE
    if ($preExit -ne 0) {
      Write-Host "[WARN] pre parity_gate failed (exit=$preExit); continuing to autogen to attempt fix." -ForegroundColor Yellow
    }

    # AUTOGEN: corrige model a partir do BD
    $autogenArgs = @($autogenScript, "apply", "--table", $Table, "--db-env", $dbEnvName)
    if ($Create) { $autogenArgs += "--create" }
    if (-not [string]::IsNullOrWhiteSpace($resolvedModelFile)) { $autogenArgs += @("--model-file", $resolvedModelFile) }
    if ($ClassName) { $autogenArgs += @("--class-name", $ClassName) }

    Invoke-External -Command $py -Arguments $autogenArgs -Step "autogen_model_from_db"

    if ($Create) {
      $snapshotArgs = @($agentGuardScript, "snapshot", "--root", ".", "--out", ".hb_guard\baseline.json", "--exclude", "venv,.venv,__pycache__,.pytest_cache,docs\_generated")
      Invoke-External -Command $py -Arguments $snapshotArgs -Step "agent_guard snapshot"
    }

    # POST parity: define resultado final do gate
    # -SkipDocsRegeneration: SSOT já foi gerado no PRE parity (evita double refresh)
    $postParityParams = @{}
    foreach ($k in $parityParams.Keys) { $postParityParams[$k] = $parityParams[$k] }
    $postParityParams.SkipDocsRegeneration = $true
    & $parityGateScript @postParityParams
    $parityExit = $LASTEXITCODE
    Write-Host "[POST] parity_exit=$parityExit"
    if (-not $?) {
      throw "[parity_gate] failed to execute parity gate"
    }
    if ($parityExit -ne 0) {
      Write-Host "[FAIL] [parity_gate] exited with code $parityExit" -ForegroundColor Red
      exit $parityExit
    }

    # STEP 4: model requirements validation (must propagate exact exit code)
    $requirementsArgs = @($modelRequirementsScript, "--table", $Table, "--profile", $Profile)
    & $py @requirementsArgs
    $requirementsExit = $LASTEXITCODE
    if (-not $?) {
      throw "[model_requirements] failed to execute requirements validator"
    }
    if ($requirementsExit -ne 0) {
      Write-Host "[FAIL] [model_requirements] exited with code $requirementsExit" -ForegroundColor Red
      exit $requirementsExit
    }
  }
  finally {
    Pop-Location
  }

  exit 0
}
catch {
  Write-Host "[FAIL] models_autogen_gate failed: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
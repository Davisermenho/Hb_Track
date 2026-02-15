# HB_SCRIPT_KIND: OPS
# HB_SCRIPT_SIDE_EFFECTS: DB_READ, FS_READ, PROCESS_SPAWN
# HB_SCRIPT_SCOPE: parity
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: pwsh scripts/ops/infra/parity_gate.ps1
# HB_SCRIPT_OUTPUTS: parity_report

param(
  [Parameter(Mandatory=$true)][string]$Table,
  [string[]]$Allow = @(),
  [switch]$AllowEnvPy,
  [switch]$AllowCycleWarning,
  [string]$ParityReportPath = "",
  [switch]$SkipDocsRegeneration
)

$ErrorActionPreference = "Stop"

# Calculate REPO_ROOT and BACKEND_ROOT from script location
$SCRIPT_ROOT = $PSScriptRoot
$REPO_ROOT = (Resolve-Path (Join-Path $SCRIPT_ROOT "..\..\..\")).Path

# Detectar backend root (onde está .hb_guard)
$BACKEND_ROOT = if (Test-Path ".\.hb_guard\baseline.json") {
  (Resolve-Path ".").Path
} else {
  # Procurar em diretórios conhecidos
  foreach ($candidate in @((Resolve-Path "."), (Join-Path (Resolve-Path ".") "Hb Track - Backend"), (Join-Path (Resolve-Path ".") "Hb_Track_Backend"))) {
    if (Test-Path (Join-Path $candidate ".hb_guard\baseline.json")) {
      $candidate
      break
    }
  }
}

if (-not $BACKEND_ROOT) {
  $BACKEND_ROOT = Join-Path $REPO_ROOT "Hb Track - Backend"
}

Write-Host "[CWD] $((Resolve-Path ".").Path)"
Write-Host "[BACKEND_ROOT] $BACKEND_ROOT"
Write-Host "[TABLE] $Table"

$venvPy = Join-Path $BACKEND_ROOT "venv\Scripts\python.exe"
if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }

# Ensure baseline exists
$baselinePath = Join-Path $BACKEND_ROOT ".hb_guard\baseline.json"
if (-not (Test-Path $baselinePath)) {
  $agentGuardPath = Join-Path $REPO_ROOT "scripts\checks\db\agent_guard.py"
  throw "Missing .hb_guard\baseline.json. Run: $py $agentGuardPath snapshot --root . --out .hb_guard/baseline.json"
}

# Build allowlist (relative paths)
$allowList = @("scripts/agent_guard.py", "scripts/parity_gate.ps1")
$allowList += $Allow
if ($AllowEnvPy) { $allowList += "db/alembic/env.py" }

$allowCsv = ($allowList -join ",")

# Build path to agent_guard.py
$agentGuardScript = Join-Path $REPO_ROOT "scripts\checks\db\agent_guard.py"

# Push to BACKEND_ROOT to ensure guard runs with backend scope
Push-Location $BACKEND_ROOT
try {
  Write-Host "[GUARD] allow=$allowCsv"
  & $py $agentGuardScript check --root "." --baseline ".hb_guard\baseline.json" --allow $allowCsv --forbid-new --forbid-delete --assert-skip-model-only-empty "db\alembic\env.py"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}

Push-Location $BACKEND_ROOT
try {
  Write-Host "[PARITY] running parity_scan.ps1 -FailOnStructuralDiffs"
  $useInjectedReport = (-not [string]::IsNullOrWhiteSpace($ParityReportPath)) -and (Test-Path $ParityReportPath)
  if ($useInjectedReport) {
    Write-Host "[PARITY] using injected report: $ParityReportPath"
  } else {
    $scanParams = @{
      RepoRoot = $BACKEND_ROOT
      ScriptsRoot = $REPO_ROOT
      TableFilter = $Table
      FailOnStructuralDiffs = $true
    }
    if ($SkipDocsRegeneration) { $scanParams.SkipDocsRegeneration = $true }
    $parity_scan_script = Join-Path $REPO_ROOT "scripts\diagnostics\db\parity_scan.ps1"
    & $parity_scan_script @scanParams
    $parityExit = $LASTEXITCODE
    if ($parityExit -ne 0) {
      exit $parityExit
    }
  }
} finally {
  Pop-Location
}

# Use env var HB_PARITY_REPORT_PATH if set, else default path
if ([string]::IsNullOrWhiteSpace($ParityReportPath)) {
  $ParityReportPath = $env:HB_PARITY_REPORT_PATH
}
if ([string]::IsNullOrWhiteSpace($ParityReportPath)) {
  $ParityReportPath = "docs\_generated\parity_report.json"
}
if (-not (Test-Path $ParityReportPath)) {
  throw "Missing $ParityReportPath after parity scan"
}
$reportPath = $ParityReportPath

$report = Get-Content $reportPath -Raw | ConvertFrom-Json
$warnings = if ($report | Get-Member -Name "warnings" -ErrorAction SilentlyContinue) {
  @($report.warnings | Where-Object { $_ })
} else {
  @()
}
$cycleWarn = @($warnings | Where-Object {
  ([string]$_.category) -eq "sa_warning" -and (
    ([string]$_.message) -match "unresolvable cycles" -or
    ([string]$_.message) -match "Cannot correctly sort tables"
  )
})

if ($cycleWarn.Count -gt 0) {
  $cycleTables = @("teams", "seasons")
  $isCycleScope = [string]::IsNullOrWhiteSpace($Table) -or ($cycleTables -contains $Table)
  if ($isCycleScope -and -not $AllowCycleWarning) {
    Write-Host "[FAIL] cycle warning detected (teams<->seasons). Use -AllowCycleWarning with mitigation evidence." -ForegroundColor Red
    exit 2
  }

  if ($isCycleScope -and $AllowCycleWarning) {
    $teamModel = "app\models\team.py"
    $seasonModel = "app\models\season.py"

    $teamHasUseAlter = (Select-String -Path $teamModel -Pattern "fk_teams_season_id.*use_alter\s*=\s*True" -Quiet)
    $seasonHasUseAlter = (Select-String -Path $seasonModel -Pattern "fk_seasons_team_id.*use_alter\s*=\s*True" -Quiet)

    if (-not $teamHasUseAlter -or -not $seasonHasUseAlter) {
      Write-Host "[FAIL] -AllowCycleWarning requires mitigations: use_alter=True on both fk_teams_season_id and fk_seasons_team_id." -ForegroundColor Red
      exit 2
    }

    Write-Host "[WARN] cycle warning allowed by override; mitigations validated (use_alter=True on both sides)." -ForegroundColor Yellow
  } else {
    Write-Host "[WARN] cycle warning detected but out of scope for Table=$Table; continuing." -ForegroundColor Yellow
  }
}

exit 0
#Requires -Version 5.1
<#
.SYNOPSIS
    HB Track — Scripts Policy Gate (Principal Validator)

.DESCRIPTION
    Validates all scripts under scripts/ against the Scripts Policy SSOT.
    
    Checks:
    - HB001: Path under scripts/
    - HB002: Valid taxonomy folder
    - HB003: Prefix matches category
    - HB004: Required headers present
    - HB005: KIND header matches category
    - HB006: Side-effects prohibited for category
    - HB007: Side-effects undeclared
    - HB008: run/ references temp/
    - HB009: temp/ tracked in git
    
    Delegates all policy logic to policy_lib.py for determinism.

.PARAMETER Verbose
    Enable verbose output

.OUTPUTS
    Exit codes:
      0 = OK (all scripts comply)
      2 = POLICY_VIOLATION (one or more violations)
      3 = HARNESS_ERROR (missing deps, parse error, etc.)

.EXAMPLE
    .\check_scripts_policy.ps1
    .\check_scripts_policy.ps1 -Verbose

.NOTES
    Version: 1.0.0
    Uses: scripts/_policy/policy_lib.py
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_VIOLATION = 2
$EXIT_ERROR = 3

# Repo root (assume script is in scripts/_policy/)
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$PolicyLib = Join-Path $RepoRoot "scripts\_policy\policy_lib.py"

Write-Host "[check_scripts_policy] Validating scripts governance..." -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $PolicyLib)) {
    Write-Error "[HB000|HARNESS_ERROR] policy_lib.py not found: $PolicyLib"
    exit $EXIT_ERROR
}

# Find Python (prefer venv if in backend, else system python)
$PythonExe = $null
$VenvPython = Join-Path $RepoRoot "Hb Track - Backend\venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "[HB000|HARNESS_ERROR] Python not found. Install Python 3.11+ or activate venv."
        exit $EXIT_ERROR
    }
}

if ($VerbosePreference -eq 'Continue') {
    Write-Host "[INFO] Using Python: $PythonExe" -ForegroundColor Gray
    Write-Host "[INFO] Repo root: $RepoRoot" -ForegroundColor Gray
}

# Run policy validation via policy_lib.py
try {
    Push-Location $RepoRoot
    
    $Output = & $PythonExe $PolicyLib 2>&1
    $ExitCode = $LASTEXITCODE
    
    # Display output
    $Output | ForEach-Object { Write-Host $_ }
    
    # Interpret exit code
    switch ($ExitCode) {
        0 {
            Write-Host "`n[OK] All scripts comply with policy." -ForegroundColor Green
            exit $EXIT_OK
        }
        2 {
            Write-Host "`n[POLICY_VIOLATION] One or more scripts violate policy." -ForegroundColor Red
            Write-Host "Review violations above and fix scripts or update policy YAML with exceptions." -ForegroundColor Yellow
            exit $EXIT_VIOLATION
        }
        3 {
            Write-Host "`n[HARNESS_ERROR] Policy validation failed to run." -ForegroundColor Red
            exit $EXIT_ERROR
        }
        default {
            Write-Host "`n[UNKNOWN_ERROR] Unexpected exit code: $ExitCode" -ForegroundColor Red
            exit $EXIT_ERROR
        }
    }
}
catch {
    Write-Error "[HB000|HARNESS_ERROR] Exception during policy validation: $_"
    exit $EXIT_ERROR
}
finally {
    Pop-Location
}


#Requires -Version 5.1
# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=lint
# HB_SCRIPT_SIDE_EFFECTS=NONE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT: scripts/checks/lint/check_python_layout.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    HB Track — Python Layout Validator (R12 Wrapper).
.DESCRIPTION
    Validates that .py files only exist in approved roots (repo-wide).
    Delegates to scripts/_policy/check_python_layout.py with SSOT policy.
    This is a READ-ONLY check (no modifications).
    Exit codes:
      0 = PASS (or report-only with violations)
      2 = FAIL (violations found in enforce mode)
      3 = HARNESS ERROR (missing deps, git issue).
.NOTES
    Version: 1.1.0
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_VIOLATION = 2
$EXIT_ERROR = 3

# Paths
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$Engine = Join-Path $RepoRoot "scripts\_policy\check_python_layout.py"
$Policy = Join-Path $RepoRoot "scripts\_policy\python_layout.policy.yaml"

Write-Host "[check_python_layout] Validating Python file layout..." -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $Engine)) {
    Write-Error "[ERROR] Engine not found: $Engine"
    exit $EXIT_ERROR
}
if (-not (Test-Path $Policy)) {
    Write-Error "[ERROR] Policy not found: $Policy"
    exit $EXIT_ERROR
}

# Find Python
$PythonExe = $null
$VenvPython = Join-Path $RepoRoot "Hb Track - Backend\venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "[ERROR] Python not found. Install Python 3.11+ or activate venv."
        exit $EXIT_ERROR
    }
}

if ($VerbosePreference -eq 'Continue') {
    Write-Host "[INFO] Using Python: $PythonExe" -ForegroundColor Gray
}

try {
    Push-Location $RepoRoot

    $Output = & $PythonExe $Engine --policy $Policy 2>&1
    $ExitCode = $LASTEXITCODE

    $Output | ForEach-Object { Write-Host $_ }

    switch ($ExitCode) {
        0 {
            Write-Host "`n[OK] Python layout check completed (exit 0)" -ForegroundColor Green
            exit $EXIT_OK
        }
        2 {
            Write-Host "`n[FAIL] Python layout violations found (exit 2)" -ForegroundColor Red
            exit $EXIT_VIOLATION
        }
        3 {
            Write-Host "`n[ERROR] Layout validation failed to run (exit 3)" -ForegroundColor Red
            exit $EXIT_ERROR
        }
        default {
            Write-Host "`n[ERROR] Unexpected exit code: $ExitCode" -ForegroundColor Red
            exit $EXIT_ERROR
        }
    }
}
catch {
    Write-Error "[ERROR] Exception during layout validation: $_"
    exit $EXIT_ERROR
}
finally {
    Pop-Location
}

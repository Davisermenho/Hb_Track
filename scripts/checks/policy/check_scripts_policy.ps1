#Requires -Version 5.1
# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=policy
# HB_SCRIPT_SIDE_EFFECTS=NONE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT: scripts/checks/policy/check_scripts_policy.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    HB Track — Scripts Policy Validator (Governance Wrapper).

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
    
    Delegates all policy logic to scripts/_policy/check_scripts_policy.ps1 (engine).
    This is a READ-ONLY check (no modifications).
    
    Exit codes:
      0 = OK (all scripts comply)
      2 = POLICY_VIOLATION (one or more violations)
      3 = HARNESS_ERROR (missing deps, parse error, etc.)

.NOTES
    Version: 1.0.0
    SSOT: scripts/_policy/scripts.policy.yaml
    Engine: scripts/_policy/check_scripts_policy.ps1
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
$Engine = Join-Path $RepoRoot "scripts\_policy\check_scripts_policy.ps1"

Write-Host "[check_scripts_policy] Validating scripts governance..." -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $Engine)) {
    Write-Error "[ERROR] Engine not found: $Engine"
    exit $EXIT_ERROR
}

try {
    Push-Location $RepoRoot

    # Run engine (delegates to policy_lib.py)
    & $Engine -Verbose
    $ExitCode = $LASTEXITCODE

    switch ($ExitCode) {
        0 {
            Write-Host "`n[OK] Scripts policy validation completed (exit 0)" -ForegroundColor Green
            exit $EXIT_OK
        }
        2 {
            Write-Host "`n[VIOLATION] One or more scripts violate policy (exit 2)" -ForegroundColor Red
            exit $EXIT_VIOLATION
        }
        3 {
            Write-Host "`n[ERROR] Scripts policy validation failed to run (exit 3)" -ForegroundColor Red
            exit $EXIT_ERROR
        }
        default {
            Write-Host "`n[ERROR] Unexpected exit code: $ExitCode" -ForegroundColor Red
            exit $EXIT_ERROR
        }
    }
}
catch {
    Write-Error "[ERROR] Exception during scripts policy validation: $_"
    exit $EXIT_ERROR
}
finally {
    Pop-Location
}

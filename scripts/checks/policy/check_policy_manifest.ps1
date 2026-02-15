#Requires -Version 5.1
# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=policy
# HB_SCRIPT_SIDE_EFFECTS=NONE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT: scripts/checks/policy/check_policy_manifest.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    HB Track — Policy Manifest Validator (Integrity Wrapper).

.DESCRIPTION
    Validates policy.manifest.json by recomputing file hashes and comparing
    with manifest values.
    
    Checks:
    - scripts.policy.yaml hash
    - side_effects_heuristics.yaml hash
    - SCRIPTS_classification.md hash
    
    Fails (exit=2) if any hash mismatch detected (anti-tampering gate).
    
    Delegates to scripts/_policy/check_policy_manifest.ps1 (engine).
    This is a READ-ONLY validation (no modifications).
    
    Exit codes:
      0 = OK (no tampering detected)
      2 = MISMATCH (manifest needs regeneration)
      3 = HARNESS_ERROR (missing file, parse error, etc.)

.NOTES
    Version: 1.0.0
    SSOT: scripts/_policy/policy.manifest.json
    Engine: scripts/_policy/check_policy_manifest.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_MISMATCH = 2
$EXIT_ERROR = 3

# Paths
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$Engine = Join-Path $RepoRoot "scripts\_policy\check_policy_manifest.ps1"

Write-Host "[check_policy_manifest] Validating manifest integrity..." -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $Engine)) {
    Write-Error "[ERROR] Engine not found: $Engine"
    exit $EXIT_ERROR
}

try {
    Push-Location $RepoRoot

    # Run engine
    & $Engine -Verbose
    $ExitCode = $LASTEXITCODE

    switch ($ExitCode) {
        0 {
            Write-Host "`n[OK] Manifest validation completed (exit 0)" -ForegroundColor Green
            exit $EXIT_OK
        }
        2 {
            Write-Host "`n[MISMATCH] Manifest hashes do not match (exit 2)" -ForegroundColor Red
            exit $EXIT_MISMATCH
        }
        3 {
            Write-Host "`n[ERROR] Manifest validation failed to run (exit 3)" -ForegroundColor Red
            exit $EXIT_ERROR
        }
        default {
            Write-Host "`n[ERROR] Unexpected exit code: $ExitCode" -ForegroundColor Red
            exit $EXIT_ERROR
        }
    }
}
catch {
    Write-Error "[ERROR] Exception during manifest validation: $_"
    exit $EXIT_ERROR
}
finally {
    Pop-Location
}

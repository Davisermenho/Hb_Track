#Requires -Version 5.1
# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=policy
# HB_SCRIPT_SIDE_EFFECTS=NONE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT: scripts/checks/policy/check_policy_md_is_derived.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    HB Track — Derived MD Drift Detector (Anti-Drift Wrapper).

.DESCRIPTION
    Verifies that docs/_canon/_agent/SCRIPTS_classification.md matches
    the generated output from scripts.policy.yaml SSOT.
    
    This prevents "drift" where the DERIVED file is edited by hand instead
    of regenerating from SSOT.
    
    Algorithm:
    1. Render MD to temp file using canonical generator (render_policy_md.py)
    2. Normalize EOL (LF) and encoding (UTF-8)
    3. Compare byte-by-byte with versioned DERIVED file
    4. Fail with exit=2 if different
    
    Delegates to scripts/_policy/check_policy_md_is_derived.ps1 (engine).
    This is a READ-ONLY check (no modifications).
    
    Exit codes:
      0 = OK (no drift)
      2 = DRIFT_DETECTED (MD needs regeneration)
      3 = HARNESS_ERROR (missing deps, generator failed, etc.)

.NOTES
    Version: 1.0.0
    SSOT: scripts/_policy/scripts.policy.yaml
    Generator: scripts/_policy/render_policy_md.py
    Engine: scripts/_policy/check_policy_md_is_derived.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_DRIFT = 2
$EXIT_ERROR = 3

# Paths
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$Engine = Join-Path $RepoRoot "scripts\_policy\check_policy_md_is_derived.ps1"

Write-Host "[check_policy_md_is_derived] Checking for drift..." -ForegroundColor Cyan

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
            Write-Host "`n[OK] Drift check completed (exit 0)" -ForegroundColor Green
            exit $EXIT_OK
        }
        2 {
            Write-Host "`n[DRIFT] Derived MD is out of sync with SSOT (exit 2)" -ForegroundColor Red
            exit $EXIT_DRIFT
        }
        3 {
            Write-Host "`n[ERROR] Drift check failed to run (exit 3)" -ForegroundColor Red
            exit $EXIT_ERROR
        }
        default {
            Write-Host "`n[ERROR] Unexpected exit code: $ExitCode" -ForegroundColor Red
            exit $EXIT_ERROR
        }
    }
}
catch {
    Write-Error "[ERROR] Exception during drift check: $_"
    exit $EXIT_ERROR
}
finally {
    Pop-Location
}

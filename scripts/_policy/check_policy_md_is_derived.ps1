#Requires -Version 5.1
<#
.SYNOPSIS
    HB Track — Check DERIVED MD is up-to-date (Anti-Drift Gate)

.DESCRIPTION
    Verifies that docs/_canon/_agent/SCRIPTS_classification.md matches
    the generated output from scripts.policy.yaml SSOT.
    
    This prevents "drift" where the DERIVED file is edited by hand instead
    of regenerating from SSOT.
    
    Algorithm:
    1. Render MD to temp file using canonical generator
    2. Normalize EOL (LF) and encoding (UTF-8)
    3. Compare byte-by-byte with versioned DERIVED file
    4. Fail with exit=2 if different

.PARAMETER Verbose
    Enable verbose output

.OUTPUTS
    Exit codes:
      0 = OK (no drift)
      2 = DRIFT_DETECTED (MD needs regeneration)
      3 = HARNESS_ERROR (missing deps, generator failed, etc.)

.EXAMPLE
    .\check_policy_md_is_derived.ps1
    .\check_policy_md_is_derived.ps1 -Verbose

.NOTES
    Version: 1.0.0
    Uses: scripts/_policy/render_policy_md.py (canonical generator)
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_DRIFT = 2
$EXIT_ERROR = 3

# Canonical paths (must match policy_lib.py constants)
$DERIVED_MD_RELPATH = "docs\_canon\_agent\SCRIPTS_classification.md"

# Repo root
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$Generator = Join-Path $RepoRoot "scripts\_policy\render_policy_md.py"
$DerivedPath = Join-Path $RepoRoot $DERIVED_MD_RELPATH

Write-Host "[check_policy_md_is_derived] Checking for drift..." -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $Generator)) {
    Write-Error "[HB010|HARNESS_ERROR] Canonical generator not found: $Generator"
    exit $EXIT_ERROR
}

if (-not (Test-Path $DerivedPath)) {
    Write-Error "[HB010|DRIFT_DETECTED] DERIVED MD missing: $DerivedPath"
    exit $EXIT_DRIFT
}

# Find Python
$PythonExe = $null
$VenvPython = Join-Path $RepoRoot "Hb Track - Backend\venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "[HB010|HARNESS_ERROR] Python not found. Install Python 3.11+ or activate venv."
        exit $EXIT_ERROR
    }
}

if ($VerbosePreference -eq 'Continue') {
    Write-Host "[INFO] Using Python: $PythonExe" -ForegroundColor Gray
    Write-Host "[INFO] Repo root: $RepoRoot" -ForegroundColor Gray
}

# Render to temp file
try {
    Push-Location $RepoRoot
    
    $TempFile = [System.IO.Path]::GetTempFileName()
    $TempMd = "$TempFile.md"
    Move-Item $TempFile $TempMd -Force
    
    if ($VerbosePreference -eq 'Continue') {
        Write-Host "[INFO] Rendering to temp: $TempMd" -ForegroundColor Gray
    }
    
    # Generate MD
    $Output = & $PythonExe $Generator --out $TempMd 2>&1
    $ExitCode = $LASTEXITCODE
    
    # Propagate Python exit code (preserve 0/2/3 semantics)
    if ($ExitCode -eq 0) {
        # Success: continue to comparison
    }
    elseif ($ExitCode -ne 0) {
        $Output | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        
        switch ($ExitCode) {
            2 {
                Write-Error "[HB010|POLICY_INVALID] Generator failed: policy validation error"
                exit $EXIT_DRIFT  # Exit 2 for policy errors
            }
            3 {
                Write-Error "[HB010|HARNESS_ERROR] Generator failed: harness error"
                exit $EXIT_ERROR  # Exit 3 for harness errors
            }
            default {
                Write-Error "[HB010|HARNESS_ERROR] Generator failed with unexpected exit code $ExitCode"
                exit $EXIT_ERROR  # Exit 3 for unknown errors
            }
        }
    }
    
    # Read both files (normalized)
    $CurrentContent = Get-Content $DerivedPath -Raw -Encoding UTF8
    $GeneratedContent = Get-Content $TempMd -Raw -Encoding UTF8
    
    # Normalize EOL for comparison
    $CurrentNorm = $CurrentContent -replace "`r`n","`n" -replace "`r","`n"
    $GeneratedNorm = $GeneratedContent -replace "`r`n","`n" -replace "`r","`n"
    
    # Compare
    if ($CurrentNorm -eq $GeneratedNorm) {
        Write-Host "`n[OK] DERIVED MD is up-to-date (no drift)." -ForegroundColor Green
        exit $EXIT_OK
    } else {
        Write-Host "`n[DRIFT_DETECTED] DERIVED MD differs from generated version." -ForegroundColor Red
        Write-Host "The DERIVED file was likely edited by hand instead of regenerating from SSOT." -ForegroundColor Yellow
        Write-Host "`nTo fix, regenerate the DERIVED file:" -ForegroundColor Yellow
        Write-Host "  python scripts/_policy/render_policy_md.py" -ForegroundColor Cyan
        Write-Host "  (or use wrapper: python scripts/generate/docs/gen_scripts_policy_md.py --write)" -ForegroundColor Cyan
        
        # Show diff summary (first 10 lines that differ)
        try {
            $CurrentLines = $CurrentNorm -split "`n"
            $GeneratedLines = $GeneratedNorm -split "`n"
            $MaxLines = [Math]::Max($CurrentLines.Count, $GeneratedLines.Count)
            
            Write-Host "`nDifferences (first 10):" -ForegroundColor Gray
            $DiffCount = 0
            for ($i = 0; $i -lt $MaxLines -and $DiffCount -lt 10; $i++) {
                $CurrLine = if ($i -lt $CurrentLines.Count) { $CurrentLines[$i] } else { "" }
                $GenLine = if ($i -lt $GeneratedLines.Count) { $GeneratedLines[$i] } else { "" }
                
                if ($CurrLine -ne $GenLine) {
                    Write-Host "  Line $($i+1):" -ForegroundColor Gray
                    Write-Host "    Current  : $CurrLine" -ForegroundColor Red
                    Write-Host "    Generated: $GenLine" -ForegroundColor Green
                    $DiffCount++
                }
            }
        }
        catch {
            Write-Host "[WARN] Could not generate diff: $_" -ForegroundColor Yellow
        }
        
        exit $EXIT_DRIFT
    }
}
catch {
    Write-Error "[HB010|HARNESS_ERROR] Exception during drift check: $_"
    exit $EXIT_ERROR
}
finally {
    # Cleanup temp file
    if (Test-Path $TempMd) {
        Remove-Item $TempMd -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}

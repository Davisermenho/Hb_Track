#Requires -Version 5.1
<#
.SYNOPSIS
    HB Track — Check Policy Manifest Hashes (Evidence Validation)

.DESCRIPTION
    Validates policy.manifest.json by recomputing file hashes and comparing
    with manifest values.
    
    Checks:
    - scripts.policy.yaml hash
    - side_effects_heuristics.yaml hash
    - SCRIPTS_classification.md hash
    
    Fails (exit=2) if any hash mismatch detected.

.PARAMETER Verbose
    Enable verbose output

.OUTPUTS
    Exit codes:
      0 = OK (all hashes match)
      2 = HASH_MISMATCH (manifest outdated)
      3 = HARNESS_ERROR (manifest missing/invalid, files missing, etc.)

.EXAMPLE
    .\check_policy_manifest.ps1
    .\check_policy_manifest.ps1 -Verbose

.NOTES
    Version: 1.0.0
    Uses: SHA256 for file hashing (deterministic)
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Exit codes
$EXIT_OK = 0
$EXIT_MISMATCH = 2
$EXIT_ERROR = 3

# Canonical paths (must match policy_lib.py constants)
$SSOT_YAML_RELPATH = "scripts\_policy\scripts.policy.yaml"
$DERIVED_MD_RELPATH = "docs\_canon\_agent\SCRIPTS_classification.md"
$MANIFEST_JSON_RELPATH = "scripts\_policy\policy.manifest.json"
$HEURISTICS_YAML_RELPATH = "scripts\_policy\side_effects_heuristics.yaml"

# Repo root
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$ManifestPath = Join-Path $RepoRoot $MANIFEST_JSON_RELPATH

Write-Host "[check_policy_manifest] Validating manifest hashes..." -ForegroundColor Cyan

# Check manifest exists
if (-not (Test-Path $ManifestPath)) {
    Write-Error "[HB012|HARNESS_ERROR] Manifest not found: $ManifestPath"
    exit $EXIT_ERROR
}

# Load manifest
try {
    $Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
}
catch {
    Write-Error "[HB012|HARNESS_ERROR] Failed to parse manifest JSON: $_"
    exit $EXIT_ERROR
}

# Define files to check (using canonical paths)
$FilesToCheck = @{
    "scripts.policy.yaml" = Join-Path $RepoRoot $SSOT_YAML_RELPATH
    "side_effects_heuristics.yaml" = Join-Path $RepoRoot $HEURISTICS_YAML_RELPATH
    "SCRIPTS_classification.md" = Join-Path $RepoRoot $DERIVED_MD_RELPATH
}

# Function to compute SHA256 hash (EOL-normalized for text files)
function Get-FileHashSHA256([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $null
    }
    
    # For text files (.py, .yaml, .md, .json, .ps1), normalize EOL → LF before hashing
    # This matches policy_lib.py compute_file_hash() behavior
    $TextExts = @(".py", ".yaml", ".yml", ".md", ".json", ".ps1", ".txt")
    $Ext = [System.IO.Path]::GetExtension($Path).ToLower()
    
    if ($TextExts -contains $Ext) {
        try {
            # Read as text (UTF-8)
            $Content = Get-Content -Path $Path -Raw -Encoding UTF8
            # Normalize CRLF → LF
            $ContentNormalized = $Content -replace "`r`n", "`n" -replace "`r", "`n"
            # Hash UTF-8 bytes
            $Bytes = [System.Text.Encoding]::UTF8.GetBytes($ContentNormalized)
            $SHA256 = [System.Security.Cryptography.SHA256]::Create()
            $HashBytes = $SHA256.ComputeHash($Bytes)
            $SHA256.Dispose()
            return [System.BitConverter]::ToString($HashBytes).Replace("-", "").ToLower()
        }
        catch {
            # Fallback to binary if text read fails
        }
    }
    
    # Binary files: hash as-is
    $Hash = Get-FileHash -Path $Path -Algorithm SHA256
    return $Hash.Hash.ToLower()
}

# Validate hashes
$Mismatches = @()
$Missing = @()

foreach ($FileName in $FilesToCheck.Keys) {
    $FilePath = $FilesToCheck[$FileName]
    
    if ($VerbosePreference -eq 'Continue') {
        Write-Host "[INFO] Checking: $FileName" -ForegroundColor Gray
    }
    
    # Check file exists
    if (-not (Test-Path $FilePath)) {
        $Missing += $FileName
        Write-Host "  [MISSING] $FileName" -ForegroundColor Red
        continue
    }
    
    # Compute actual hash
    $ActualHash = Get-FileHashSHA256 $FilePath
    
    # Get expected hash from manifest
    $ExpectedHash = $null
    if ($Manifest.hashes.PSObject.Properties.Name -contains $FileName) {
        $ExpectedHash = $Manifest.hashes.$FileName
    }
    
    if (-not $ExpectedHash) {
        Write-Host "  [WARNING] No hash in manifest for: $FileName" -ForegroundColor Yellow
        continue
    }
    
    # Compare
    if ($ActualHash -ne $ExpectedHash) {
        $Mismatches += @{
            File = $FileName
            Expected = $ExpectedHash.Substring(0, 16) + "..."
            Actual = $ActualHash.Substring(0, 16) + "..."
        }
        Write-Host "  [MISMATCH] $FileName" -ForegroundColor Red
        Write-Host "    Expected: $($ExpectedHash.Substring(0, 16))..." -ForegroundColor Gray
        Write-Host "    Actual  : $($ActualHash.Substring(0, 16))..." -ForegroundColor Gray
    } else {
        if ($VerbosePreference -eq 'Continue') {
            Write-Host "  [OK] $FileName" -ForegroundColor Green
        }
    }
}

# Report results
if ($Missing.Count -gt 0) {
    Write-Host "`n[HARNESS_ERROR] Missing files:" -ForegroundColor Red
    $Missing | ForEach-Object { Write-Host "  - $_" }
    exit $EXIT_ERROR
}

if ($Mismatches.Count -gt 0) {
    Write-Host "`n[HASH_MISMATCH] Manifest is outdated." -ForegroundColor Red
    Write-Host "The following files changed since manifest was generated:" -ForegroundColor Yellow
    $Mismatches | ForEach-Object { Write-Host ("  - {0}" -f $_.File) }
    Write-Host "`nTo fix, regenerate manifest:" -ForegroundColor Yellow
    Write-Host "  python scripts/_policy/render_policy_md.py" -ForegroundColor Cyan
    Write-Host "  (this will update policy.manifest.json)" -ForegroundColor Gray
    exit $EXIT_MISMATCH
} else {
    Write-Host "`n[OK] All manifest hashes match." -ForegroundColor Green
    exit $EXIT_OK
}

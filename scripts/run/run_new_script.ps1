# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=run
# HB_SCRIPT_SIDE_EFFECTS=FS_WRITE,PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=powershell scripts/run/run_new_script.ps1 -Kind CHECK -Scope db -Action check_integrity -Ext py
# HB_SCRIPT_OUTPUTS=scripts/{checks,fixes,seeds,generates,migrates,resets,ops}/

<# HB Track — run_new_script.ps1

Purpose:
  Deterministically scaffold a NEW script in the correct category/scope with:
  - correct folder placement
  - correct filename pattern
  - required header template (HB_SCRIPT_*)
  - optional per-category README presence (non-blocking)
  - optional registration in scripts/README.md (OFF by default)

This is a "wrapper" under scripts/run/ (no business logic).

Deterministic exit codes:
  0 = SUCCESS
  2 = POLICY/INPUT FAIL (invalid kind/scope/ext/name)
  3 = HARNESS ERROR (filesystem errors, cannot write)

Usage examples:
  powershell -ExecutionPolicy Bypass -File scripts\run\run_new_script.ps1 `
    -Kind CHECK -Scope openapi -Action contract_security -Ext py

  powershell -ExecutionPolicy Bypass -File scripts\run\run_new_script.ps1 `
    -Kind RESET -Scope db -Action e2e -Ext ps1 -Force

Notes:
  - This script DOES create files (scaffolding).
  - For destructive kinds (RESET/MIGRATE/OPS) it requires -Force.
  - It does NOT attempt to infer side-effects; you must fill HB_SCRIPT_SIDE_EFFECTS.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("CHECK","DIAGNOSTIC","FIX","GENERATE","MIGRATE","OPS","RESET","SEED","RUNNER","TEMP")]
  [string]$Kind,

  [Parameter(Mandatory=$true)]
  [string]$Scope,

  [Parameter(Mandatory=$true)]
  [string]$Action,

  [Parameter(Mandatory=$false)]
  [ValidateSet("py","ps1","sql")]
  [string]$Ext = "py",

  [Parameter(Mandatory=$false)]
  [string]$Qualifier = "",

  [Parameter(Mandatory=$false)]
  [switch]$Force,

  [Parameter(Mandatory=$false)]
  [switch]$OpenAfter,

  [Parameter(Mandatory=$false)]
  [switch]$RegisterInScriptsReadme
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([int]$code, [string]$msg) {
  Write-Host $msg -ForegroundColor Red
  exit $code
}

function Ok([string]$msg) {
  Write-Host $msg -ForegroundColor Green
}

function Warn([string]$msg) {
  Write-Host $msg -ForegroundColor Yellow
}

function To-LowerSafe([string]$s) {
  return ($s ?? "").ToLowerInvariant()
}

function Slugify([string]$s) {
  # deterministic: lowercase, allow a-z0-9_, collapse invalid to _
  $t = To-LowerSafe $s
  $t = [Regex]::Replace($t, "[^a-z0-9_]+", "_")
  $t = [Regex]::Replace($t, "_{2,}", "_")
  $t = $t.Trim("_")
  return $t
}

# -------------------------
# Policy mapping (deterministic, in-script)
# -------------------------
$kindToCategory = @{
  "CHECK"      = "checks"
  "DIAGNOSTIC" = "diagnostics"
  "FIX"        = "fixes"
  "GENERATE"   = "generate"
  "MIGRATE"    = "migrate"
  "OPS"        = "ops"
  "RESET"      = "reset"
  "SEED"       = "seeds"
  "RUNNER"     = "run"
  "TEMP"       = "temp"
}

$categoryToPrefix = @{
  "checks"      = "check_"
  "diagnostics" = "diag_"
  "fixes"       = "fix_"
  "generate"    = "gen_"
  "migrate"     = "mig_"
  "ops"         = "ops_"
  "reset"       = "reset_"
  "seeds"       = "seed_"
  "run"         = "run_"
  "temp"        = "tmp_"
}

# allowed subscopes per category
$subscopes = @{
  "checks"      = @("auth","db","docs","lint","models","openapi","security")
  "diagnostics" = @("auth","db","mail","perf","routes")
  "fixes"       = @("auth","db","docs","models","openapi")
  "generate"    = @("docs","hashes","indexes","openapi","schema")
  "migrate"     = @("backfill","legacy","oneoff")
  "ops"         = @("db/maintenance","db/refresh","infra","mail")
  "reset"       = @("db","env","services")
  "seeds"       = @("dev","official","test","_archived")
  "run"         = @() # no sub-scope
  "temp"        = @() # no sub-scope
}

# For categories that REQUIRE sub-scope directories
$requiresSubscope = @("checks","diagnostics","fixes","generate","migrate","ops","reset","seeds")

# Guard: destructive/manual categories require -Force to create
$forceRequiredKinds = @("RESET","MIGRATE","OPS")

# -------------------------
# Resolve repo root + scripts root
# -------------------------
try {
  $repoRoot = (Resolve-Path ".").Path
} catch {
  Fail 3 "[HARNESS_ERROR] Cannot resolve current directory as repo root."
}

$scriptsRoot = Join-Path $repoRoot "scripts"
if (-not (Test-Path -LiteralPath $scriptsRoot)) {
  Fail 3 "[HARNESS_ERROR] scripts/ folder not found at repo root: $scriptsRoot"
}

# -------------------------
# Input validation + normalization
# -------------------------
if ($forceRequiredKinds -contains $Kind.ToUpperInvariant()) {
  if (-not $Force) {
    Fail 2 "[FAIL] Kind=$Kind requires -Force (destructive/manual class)."
  }
}

$category = $kindToCategory[$Kind.ToUpperInvariant()]
if (-not $category) { Fail 2 "[FAIL] Unknown kind: $Kind" }

$prefix = $categoryToPrefix[$category]
if (-not $prefix) { Fail 2 "[FAIL] Missing prefix mapping for category: $category" }

$scopeRaw = $Scope
$scopeNorm = Slugify $scopeRaw
if ([string]::IsNullOrWhiteSpace($scopeNorm)) {
  Fail 2 "[FAIL] Scope is empty/invalid after normalization."
}

$actionRaw = $Action
$actionNorm = Slugify $actionRaw
if ([string]::IsNullOrWhiteSpace($actionNorm)) {
  Fail 2 "[FAIL] Action is empty/invalid after normalization."
}

$qualNorm = ""
if (-not [string]::IsNullOrWhiteSpace($Qualifier)) {
  $qualNorm = Slugify $Qualifier
  if ([string]::IsNullOrWhiteSpace($qualNorm)) {
    Fail 2 "[FAIL] Qualifier invalid after normalization."
  }
}

# Validate sub-scope against category rules
$targetRelDir = $null

if ($category -in $requiresSubscope) {
  $allowed = $subscopes[$category]
  if (-not $allowed) { Fail 2 "[FAIL] No allowed subscopes configured for category: $category" }

  # ops has nested scopes like db/maintenance; allow exact match.
  $scopeForCompare = $scopeRaw.Trim().ToLowerInvariant()
  $allowedLower = $allowed | ForEach-Object { $_.ToLowerInvariant() }

  if (-not ($allowedLower -contains $scopeForCompare)) {
    $allowedStr = ($allowed -join ", ")
    Fail 2 "[FAIL] Scope '$Scope' not allowed for category '$category'. Allowed: $allowedStr"
  }

  $targetRelDir = Join-Path (Join-Path "scripts" $category) $Scope
} else {
  # run/temp: no subscope
  if ($category -eq "run" -and $scopeNorm -ne "run") {
    # keep deterministic: run scripts are directly under scripts/run; scope in name is usually logical group, but we disallow here.
    Warn "[WARN] For category 'run', Scope is ignored for placement (no sub-scope). Name will still use provided scope token."
  }
  $targetRelDir = Join-Path "scripts" $category
}

# Determine filename
$baseName = "$prefix$scopeNorm" + "__" + "$actionNorm"
if ($qualNorm) { $baseName = $baseName + "_" + $qualNorm }
$fileName = "$baseName.$Ext"

$targetDir = Join-Path $repoRoot $targetRelDir
$targetPath = Join-Path $targetDir $fileName

# -------------------------
# Create folder(s)
# -------------------------
try {
  New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
} catch {
  Fail 3 "[HARNESS_ERROR] Cannot create target directory: $targetDir"
}

if (Test-Path -LiteralPath $targetPath) {
  Fail 2 "[FAIL] Target already exists: $targetPath"
}

# -------------------------
# Header template by extension (deterministic)
# -------------------------
$kindUpper = $Kind.ToUpperInvariant()

# Suggested side-effects placeholder (author must adjust)
$sideEffectsPlaceholder = switch ($kindUpper) {
  "CHECK"      { "FS_READ" }
  "DIAGNOSTIC" { "FS_READ" }
  "GENERATE"   { "FS_WRITE" }
  "FIX"        { "FS_WRITE" }
  "MIGRATE"    { "DB_WRITE" }
  "OPS"        { "DB_WRITE" }
  "RESET"      { "ENV_WRITE,DB_WRITE" }
  "SEED"       { "DB_WRITE" }
  "RUNNER"     { "FS_READ,ENV_WRITE" }
  default      { "NONE" }
}

# Entry point is deterministic (repo relative)
$entrypoint = switch ($Ext) {
  "py"  { "python $($targetRelDir.Replace('\','/'))/$fileName" }
  "ps1" { "powershell -ExecutionPolicy Bypass -File $($targetRelDir.Replace('\','/'))/$fileName" + ($(if ($kindUpper -eq "RESET") { " -Force" } else { "" })) }
  "sql" { "psql `"%DATABASE_URL%`" -f $($targetRelDir.Replace('\','/'))/$fileName" }
  default { "UNKNOWN" }
}

$outputsDefault = "scripts/artifacts/$category/$scopeNorm/$baseName/"

# Compose file content
$headerLines = @(
  "HB_SCRIPT_KIND=$kindUpper",
  "HB_SCRIPT_SCOPE=$scopeNorm",
  "HB_SCRIPT_SIDE_EFFECTS=$sideEffectsPlaceholder",
  "HB_SCRIPT_IDEMPOTENT=YES",
  "HB_SCRIPT_ENTRYPOINT=$entrypoint",
  "HB_SCRIPT_OUTPUTS=$outputsDefault"
)

function Make-Header([string]$ext, [string[]]$kvLines) {
  switch ($ext) {
    "py" {
      return ($kvLines | ForEach-Object { "# $_" }) -join "`r`n"
    }
    "ps1" {
      $body = ($kvLines | ForEach-Object { "$_"} ) -join "`r`n"
      return "<#`r`n$body`r`n#>"
    }
    "sql" {
      return ($kvLines | ForEach-Object { "-- $_" }) -join "`r`n"
    }
    default {
      return ($kvLines | ForEach-Object { "# $_" }) -join "`r`n"
    }
  }
}

$header = Make-Header -ext $Ext -kvLines $headerLines

$body = switch ($Ext) {
  "py" {
@"
$header

def main() -> int:
    # TODO: implement
    # MUST keep behavior consistent with HB_SCRIPT_* header above.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"@
  }
  "ps1" {
@"
$header

Set-StrictMode -Version Latest
`$ErrorActionPreference = "Stop"

# TODO: implement
# MUST keep behavior consistent with HB_SCRIPT_* header above.

Write-Host "[PENDING] Not implemented yet."
exit 2
"@
  }
  "sql" {
@"
$header

-- TODO: implement
-- MUST keep behavior consistent with HB_SCRIPT_* header above.
"@
  }
  default {
@"
$header

# TODO: implement
"@
  }
}

# -------------------------
# Write file
# -------------------------
try {
  # Always UTF8 without BOM? PowerShell defaults can vary; explicit:
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($targetPath, $body, $utf8NoBom)
} catch {
  Fail 3 "[HARNESS_ERROR] Cannot write file: $targetPath"
}

Ok "[SUCCESS] Created: $targetRelDir\$fileName"

# Optional: ensure artifacts base dir exists (non-blocking)
$artBase = Join-Path $repoRoot "scripts\artifacts\.gitignore"
if (-not (Test-Path -LiteralPath $artBase)) {
  Warn "[WARN] scripts/artifacts/.gitignore not found. Consider creating artifacts/ policy files."
}

# Optional: register in scripts/README.md (append deterministic line)
if ($RegisterInScriptsReadme) {
  $scriptsReadme = Join-Path $scriptsRoot "README.md"
  if (Test-Path -LiteralPath $scriptsReadme) {
    $line = "* $($targetRelDir.Replace('\','/'))/$fileName"
    $existing = Get-Content -LiteralPath $scriptsReadme -Raw -Encoding UTF8
    if ($existing -notmatch [Regex]::Escape($line)) {
      try {
        Add-Content -LiteralPath $scriptsReadme -Value ("`r`n" + $line) -Encoding UTF8
        Ok "[INFO] Registered in scripts/README.md"
      } catch {
        Warn "[WARN] Failed to register in scripts/README.md (non-fatal)."
      }
    } else {
      Warn "[WARN] Already registered in scripts/README.md"
    }
  } else {
    Warn "[WARN] scripts/README.md not found; cannot register (non-fatal)."
  }
}

# Optional: open file
if ($OpenAfter) {
  try {
    Start-Process $targetPath | Out-Null
    Ok "[INFO] Opened file in default editor."
  } catch {
    Warn "[WARN] Could not open file automatically (non-fatal)."
  }
}

exit 0
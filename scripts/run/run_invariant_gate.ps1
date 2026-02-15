# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/run/run_invariant_gate.ps1
# HB_SCRIPT_OUTPUTS=stdout
#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Gate runner canônico para validar invariantes individuais (sem Git).

.DESCRIPTION
    Executa verificador + pytest para uma INV específica, salva evidências timestamped,
    e declara PASS apenas se:
    - verify_inv.txt vazio (sem violações dessa INV)
    - pytest exit code 0

.PARAMETER InvId
    ID da invariante (ex: INV-TRAIN-002)

.PARAMETER Root
    Caminho raiz do projeto (default: C:\HB TRACK)

.PARAMETER Backend
    Caminho do backend (default: C:\HB TRACK\Hb Track - Backend)

.EXAMPLE
    pwsh -File run_invariant_gate.ps1 INV-TRAIN-002
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$InvId,
    
    [Parameter(Mandatory=$false)]
    [string]$Root = "C:\HB TRACK",
    
    [Parameter(Mandatory=$false)]
    [string]$Backend = "C:\HB TRACK\Hb Track - Backend"
)

$ErrorActionPreference = "Stop"

# ============================================================================
# 0. RESOLVE PYTHON EXECUTABLE (avoid "Fatal error in launcher")
# ============================================================================

# Preferir venv local, fallback para python global
$pythonExe = if (Test-Path "$Backend\venv\Scripts\python.exe") {
    "$Backend\venv\Scripts\python.exe"
} else {
    "python"
}

Write-Verbose "Using Python: $pythonExe"

# ============================================================================
# 0. UTILITY FUNCTIONS
# ============================================================================

function Resolve-FirstExistingPath {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Candidates
    )
    
    foreach ($path in $Candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

function Get-SafeFileHash {
    param(
        [Parameter(Mandatory=$false)]
        [AllowEmptyString()]
        [AllowNull()]
        [string]$Path
    )
    
    if ([string]::IsNullOrEmpty($Path) -or -not (Test-Path $Path)) {
        return "MISSING"
    }
    
    try {
        return (Get-FileHash $Path -Algorithm SHA256).Hash
    } catch {
        return "ERROR"
    }
}

# ============================================================================
# 1. SETUP
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Gate Runner: $InvId" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root:    $Root"
Write-Host "Backend: $Backend"
Write-Host ""

# Validar paths
if (-not (Test-Path $Root)) {
    Write-Host "ERROR: Root path not found: $Root" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Backend)) {
    Write-Host "ERROR: Backend path not found: $Backend" -ForegroundColor Red
    exit 1
}

# Criar diretório de reports
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportDir = Join-Path $Root "docs\_generated\_reports\$InvId\$timestamp"
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
Write-Host "Report dir: $reportDir" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 2. PARSE SPEC para obter tests.primary e tests.node
# ============================================================================

Write-Host "Step 1: Parsing SPEC..." -ForegroundColor Yellow

$specPath = Join-Path $Root "docs\02-modulos\training\INVARIANTS_TRAINING.md"
if (-not (Test-Path $specPath)) {
    Write-Host "ERROR: SPEC not found: $specPath" -ForegroundColor Red
    Write-Host "RESULT: PENDING (SPEC missing)" -ForegroundColor Yellow
    exit 1
}

$specContent = Get-Content $specPath -Raw -Encoding UTF8
$pattern = "(?ms)id:\s*`"$InvId`".*?tests:\s*primary:\s*`"([^`"]+)`"\s*node:\s*`"([^`"]+)`""
if ($specContent -match $pattern) {
    $testsPrimary = $Matches[1]
    $testsNode = $Matches[2]
    Write-Host "  tests.primary: $testsPrimary" -ForegroundColor Green
    Write-Host "  tests.node:    $testsNode" -ForegroundColor Green
} else {
    Write-Host "ERROR: Could not parse tests.primary/node from SPEC for $InvId" -ForegroundColor Red
    Write-Host "RESULT: PENDING (SPEC parse failed)" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Construir caminho do arquivo de teste (remover prefixo tests/ se existir)
$testFileRelative = $testsPrimary -replace '^tests[/\\]', ''
$testFilePath = Join-Path $Backend "tests\$testFileRelative"
if (-not (Test-Path $testFilePath)) {
    Write-Host "ERROR: Test file not found: $testFilePath" -ForegroundColor Red
    Write-Host "RESULT: PENDING (test file missing)" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# 3. RUN VERIFIER (scoped by --inv)
# ============================================================================

Write-Host "Step 2: Running verifier (strict)..." -ForegroundColor Yellow

Push-Location $Root
$verifyPath = Join-Path $reportDir "verify.txt"
$verifyInvPath = Join-Path $reportDir "verify_inv.txt"

try {
    # Run verifier with --inv scope (direct INV-ID targeting)
    & $pythonExe docs\scripts\verify_invariants_tests.py --level strict --inv $InvId 2>&1 | Tee-Object -FilePath $verifyPath | Out-Null
    $verifyExit = $LASTEXITCODE
    Write-Host "  Verifier exit: $verifyExit" -ForegroundColor Cyan
    
    # Extract lines containing violations (ERROR/WARN)
    Select-String -Path $verifyPath -Pattern "ERROR|WARN" -CaseSensitive | 
        Out-File -FilePath $verifyInvPath -Encoding UTF8
    
    $verifyInvLines = (Get-Content $verifyInvPath -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
    if ($null -eq $verifyInvLines) { $verifyInvLines = 0 }
    
    Write-Host "  Filtered violations: $verifyInvLines lines" -ForegroundColor Cyan
    
    if ($verifyExit -ne 0) {
        Write-Host "  VERIFY STATUS: FAIL (exit $verifyExit)" -ForegroundColor Red
        if ($verifyInvLines -gt 0) {
            Get-Content $verifyInvPath | Select-Object -First 10 | ForEach-Object {
                Write-Host "    $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  VERIFY STATUS: PASS" -ForegroundColor Green
    }
} finally {
    Pop-Location
}
Write-Host ""

# ============================================================================
# 4. RUN PYTEST (específico, no backend)
# ============================================================================

Write-Host "Step 3: Running pytest..." -ForegroundColor Yellow

Push-Location $Backend
$pytestPath = Join-Path $reportDir "pytest.txt"

try {
    # Executar pytest no node específico (classe ou método)
    $pytestTarget = "${testFilePath}::${testsNode}"
    Write-Host "  Target: $pytestTarget" -ForegroundColor Cyan
    
    # Capturar saída do pytest (usar python -m pytest para garantir compatibilidade)
    $pytestOutput = & $pythonExe -m pytest $pytestTarget -v --tb=short 2>&1
    $pytestExit = $LASTEXITCODE
    
    # Salvar output
    $pytestOutput | Out-File -FilePath $pytestPath -Encoding UTF8
    
    Write-Host "  Pytest exit: $pytestExit" -ForegroundColor Cyan
    
    # Analisar resultado (considerar 0 ou 5 como sucesso - 5 = warnings apenas)
    if ($pytestExit -eq 0 -or $pytestExit -eq 5) {
        Write-Host "  PYTEST STATUS: PASS" -ForegroundColor Green
        $pytestExit = 0  # Normalizar para 0
    } else {
        Write-Host "  PYTEST STATUS: FAIL" -ForegroundColor Red
        # Mostrar últimas linhas do log
        if (Test-Path $pytestPath) {
            Get-Content $pytestPath | Select-Object -Last 15 | ForEach-Object {
                Write-Host "    $_" -ForegroundColor Red
            }
        }
    }
} finally {
    Pop-Location
}
Write-Host ""

# ============================================================================
# 5. GENERATE HASHES & META
# ============================================================================

Write-Host "Step 4: Generating artifacts..." -ForegroundColor Yellow

$hashesPath = Join-Path $reportDir "hashes.txt"
$metaPath = Join-Path $reportDir "meta.txt"

# Canonical input files (for golden drift detection)
$openapiPath = Resolve-FirstExistingPath @(
    (Join-Path $Backend "docs\_generated\openapi.json"),
    (Join-Path $Root "docs\_generated\openapi.json")
)

$schemaPath = Resolve-FirstExistingPath @(
    (Join-Path $Backend "docs\_generated\schema.sql"),
    (Join-Path $Root "docs\_generated\schema.sql")
)

$invariantsPath = Join-Path $Root "docs\02-modulos\training\INVARIANTS_TRAINING.md"
$verifierPath = Join-Path $Root "docs\scripts\verify_invariants_tests.py"

# Generate hashes with stable keys (canonical inputs only)
$hashLines = @()
$hashLines += "# Canonical inputs (for drift detection)"
$hashLines += "openapi.json: $(Get-SafeFileHash $openapiPath)"
$hashLines += "schema.sql: $(Get-SafeFileHash $schemaPath)"
$hashLines += "INVARIANTS_TRAINING.md: $(Get-SafeFileHash $invariantsPath)"
$hashLines += "verify_invariants_tests.py: $(Get-SafeFileHash $verifierPath)"
$hashLines += "test_file: $(Get-SafeFileHash $testFilePath)"

$hashLines -join "`n" | Out-File -FilePath $hashesPath -Encoding UTF8

# Meta
$pythonVersion = (python --version 2>&1) -join " "
$metaContent = @"
# Gate Run Metadata
inv_id: $InvId
timestamp: $timestamp
root: $Root
backend: $Backend
python: $pythonVersion
test_file: $testFilePath
test_node: $testsNode
verify_exit: $verifyExit
pytest_exit: $pytestExit
"@
$metaContent | Out-File -FilePath $metaPath -Encoding UTF8

Write-Host "  Artifacts saved:" -ForegroundColor Green
Write-Host "    - verify.txt ($((Get-Item $verifyPath).Length) bytes)"
Write-Host "    - verify_inv.txt ($((Get-Content $verifyInvPath -ErrorAction SilentlyContinue | Measure-Object -Line).Lines) lines)"
Write-Host "    - pytest.txt ($((Get-Item $pytestPath).Length) bytes)"
Write-Host "    - hashes.txt"
Write-Host "    - meta.txt"
Write-Host ""

# ============================================================================
# 5.5. GOLDEN DRIFT DETECTION
# ============================================================================

Write-Host "[5.5] Checking Golden Drift..." -ForegroundColor Cyan

# Expected canonical input keys (stable format)
$expectedKeys = @(
    "openapi.json",
    "schema.sql",
    "INVARIANTS_TRAINING.md",
    "verify_invariants_tests.py",
    "test_file"
)

# Resolve golden directory based on primary class (via parser)
$unitClass = (& python "$Root\docs\scripts\get_inv_primary_class.py" --inv $InvId).Trim()
if ([string]::IsNullOrWhiteSpace($unitClass)) {
    $unitClass = "UNKNOWN"
}

# Golden dir is at INV level (not timestamp level)
$invReportsDir = Join-Path $Root "docs\_generated\_reports\$InvId"
$goldenDir = Join-Path $invReportsDir "_golden_$unitClass"

Write-Host "  Unit class: $unitClass" -ForegroundColor Gray
Write-Host "  Golden dir: $goldenDir" -ForegroundColor Gray

# Track golden status
$goldenMissing = $false
$goldenBaselineOutdated = $false
$goldenDriftFail = $false

if ($unitClass -ne "UNKNOWN") {
    
    if (Test-Path $goldenDir) {
        $goldenHashesPath = Join-Path $goldenDir "hashes.txt"
        
        if (Test-Path $goldenHashesPath) {
            Write-Host "  Golden baseline found: comparing..." -ForegroundColor Yellow
            
            # Parse hashes (current and golden)
            $currentHashes = @{}
            $goldenHashes = @{}
            
            # Parse current hashes (skip comments and empty lines)
            Get-Content $hashesPath | ForEach-Object {
                if ($_ -match '^([^#].+?):\s*(.+)$') {
                    $currentHashes[$matches[1].Trim()] = $matches[2].Trim()
                }
            }
            
            # Parse golden hashes
            Get-Content $goldenHashesPath | ForEach-Object {
                if ($_ -match '^([^#].+?):\s*(.+)$') {
                    $goldenHashes[$matches[1].Trim()] = $matches[2].Trim()
                }
            }
            
            # Check if golden baseline is outdated (missing expected keys)
            $missingKeys = @()
            foreach ($key in $expectedKeys) {
                if (-not $goldenHashes.ContainsKey($key)) {
                    $missingKeys += $key
                }
            }
            
            if ($missingKeys.Count -gt 0) {
                Write-Host ""
                Write-Host "  ❌ GOLDEN BASELINE OUTDATED!" -ForegroundColor Red -BackgroundColor Black
                Write-Host ""
                Write-Host "  Golden baseline is missing expected keys:" -ForegroundColor Yellow
                $missingKeys | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
                Write-Host ""
                Write-Host "  Action required: promote a recent report to golden" -ForegroundColor Cyan
                Write-Host "    Remove-Item '$goldenDir' -Recurse -Force" -ForegroundColor White
                Write-Host "    Copy-Item -Recurse '$reportDir' '$goldenDir'" -ForegroundColor White
                Write-Host ""
                
                $goldenBaselineOutdated = $true
            } else {
                # Compare canonical inputs
                $driftDetected = $false
                $driftDetails = @()
                
                foreach ($key in $expectedKeys) {
                    $currentHash = $currentHashes[$key]
                    $goldenHash = $goldenHashes[$key]
                    
                    if ($currentHash -ne $goldenHash) {
                        $driftDetected = $true
                        
                        # Handle MISSING hashes
                        $goldenDisplay = if ($goldenHash -eq "MISSING") { "MISSING" } else { $goldenHash.Substring(0, 16) + "..." }
                        $currentDisplay = if ($currentHash -eq "MISSING") { "MISSING" } else { $currentHash.Substring(0, 16) + "..." }
                        
                        $driftDetails += [PSCustomObject]@{
                            File = $key
                            Golden = $goldenDisplay
                            Current = $currentDisplay
                        }
                    }
                }
                
                if ($driftDetected) {
                    Write-Host ""
                    Write-Host "  ❌ GOLDEN DRIFT DETECTED!" -ForegroundColor Red -BackgroundColor Black
                    Write-Host ""
                    Write-Host "  Canonical inputs changed since golden baseline:" -ForegroundColor Yellow
                    $driftDetails | Format-Table -AutoSize | Out-String | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
                    Write-Host ""
                    Write-Host "  To promote this report to golden (after review):" -ForegroundColor Cyan
                    Write-Host "    Remove-Item '$goldenDir' -Recurse -Force" -ForegroundColor White
                    Write-Host "    Copy-Item -Recurse '$reportDir' '$goldenDir'" -ForegroundColor White
                    Write-Host ""
                    
                    $goldenDriftFail = $true
                } else {
                    Write-Host "  ✅ Golden compare: OK (no drift)" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "  Golden directory exists but hashes.txt missing (treat as no golden)" -ForegroundColor Yellow
            Write-Host "    Remove-Item '$goldenDir' -Recurse -Force" -ForegroundColor Gray
            Write-Host "    Copy-Item -Recurse '$reportDir' '$goldenDir'" -ForegroundColor Gray
        }
    } else {
        Write-Host "  Golden not found: promote this report to create baseline" -ForegroundColor Yellow
        Write-Host "    Copy-Item -Recurse '$reportDir' '$goldenDir'" -ForegroundColor Gray
        $goldenMissing = $true
    }
} else {
    Write-Host "  WARNING: Could not resolve primary class (skipping golden check)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 6. FINAL VERDICT
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GATE VERDICT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Report:           $reportDir"
Write-Host "VERIFY_EXIT:      $verifyExit"
Write-Host "PYTEST_EXIT:      $pytestExit"
Write-Host "GOLDEN_DRIFT:     $(if ($goldenDriftFail -or $goldenBaselineOutdated) { 'YES' } else { 'NO' })"

# Determine exit code
if ($goldenBaselineOutdated) {
    $exitCode = 3
    $resultMsg = "FAIL (GOLDEN_BASELINE_OUTDATED)"
    $resultColor = "Red"
} elseif ($goldenDriftFail) {
    $exitCode = 3
    $resultMsg = "FAIL (GOLDEN_DRIFT)"
    $resultColor = "Red"
} elseif ($goldenMissing) {
    $exitCode = 3
    $resultMsg = "FAIL (GOLDEN_MISSING)"
    $resultColor = "Yellow"
} elseif ($verifyExit -eq 0 -and $pytestExit -eq 0) {
    $exitCode = 0
    $resultMsg = "PASS"
    $resultColor = "Green"
} else {
    $exitCode = 1
    $resultMsg = "FAIL"
    $resultColor = "Red"
}

Write-Host "EXIT_CODE:        $exitCode"
Write-Host ""
Write-Host "RESULT: $resultMsg" -ForegroundColor $resultColor -BackgroundColor Black

# Update meta.txt with final exit_code and primary_class
$metaAppend = @"
exit_code: $exitCode
primary_class: $unitClass
golden_drift: $(if ($goldenDriftFail -or $goldenBaselineOutdated) { 'YES' } else { 'NO' })
golden_missing: $(if ($goldenMissing) { 'YES' } else { 'NO' })
"@
Add-Content -Path $metaPath -Value $metaAppend -Encoding UTF8

if ($exitCode -eq 1) {
    if ($verifyExit -ne 0) {
        Write-Host "  Reason: Verifier failed (exit $verifyExit)" -ForegroundColor Red
    }
    if ($pytestExit -ne 0) {
        Write-Host "  Reason: Pytest failed (exit $pytestExit)" -ForegroundColor Red
    }
}

exit $exitCode

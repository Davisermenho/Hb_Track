# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/run/run_invariant_gate_all.ps1
# HB_SCRIPT_OUTPUTS=stdout
#!/usr/bin/env pwsh
#
# run_invariant_gate_all.ps1
# Executa gate runner para todos os invariantes com golden baselines
#

param(
    [switch]$Verbose = $false,
    [switch]$Promote = $false,
    [switch]$WhatIf = $false
)

$ErrorActionPreference = "Stop"

# Paths
$ScriptRoot = $PSScriptRoot
$RootDir = Split-Path -Parent $ScriptRoot
$ReportsDir = Join-Path $RootDir "docs\_generated\_reports"
$GateScript = Join-Path $ScriptRoot "run_invariant_gate.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Gate Runner: ALL INVARIANTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root:    $RootDir"
Write-Host "Reports: $ReportsDir"
Write-Host ""

# (1) Descobrir todos os INV-IDs que têm golden baselines
Write-Host "[1] Discovering invariants with golden baselines..." -ForegroundColor Yellow

if (-not (Test-Path $ReportsDir)) {
    Write-Host "ERROR: Reports directory not found: $ReportsDir" -ForegroundColor Red
    exit 1
}

$InvariantsWithGolden = @()
$InvariantsWithMissingGolden = @()

Get-ChildItem -Path $ReportsDir -Directory -Filter "INV-*" | ForEach-Object {
    $InvDir = $_.FullName
    $InvId = $_.Name
    
    # Procurar por pastas _golden_*
    $GoldenDirs = Get-ChildItem -Path $InvDir -Directory -Filter "_golden_*" -ErrorAction SilentlyContinue
    
    if ($GoldenDirs.Count -gt 0) {
        $InvariantsWithGolden += $InvId
        if ($Verbose) {
            Write-Host "  Found: $InvId (goldens: $($GoldenDirs.Count))" -ForegroundColor Gray
        }
    } else {
        # Verificar se tem report recente com golden_missing: YES
        $LatestReport = Get-ChildItem -Path $InvDir -Directory | 
            Where-Object { $_.Name -notlike "_golden_*" } |
            Sort-Object Name -Descending |
            Select-Object -First 1
        
        if ($LatestReport) {
            $MetaFile = Join-Path $LatestReport.FullName "meta.txt"
            if (Test-Path $MetaFile) {
                $MetaContent = Get-Content $MetaFile -Raw
                if ($MetaContent -match 'golden_missing:\s*YES') {
                    $InvariantsWithMissingGolden += $InvId
                    $InvariantsWithGolden += $InvId
                    if ($Verbose) {
                        Write-Host "  Found: $InvId (golden_missing: YES)" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
}

$TotalWithGolden = $InvariantsWithGolden.Count - $InvariantsWithMissingGolden.Count
Write-Host "  Found $TotalWithGolden invariants with golden baselines" -ForegroundColor Green
if ($InvariantsWithMissingGolden.Count -gt 0) {
    Write-Host "  Found $($InvariantsWithMissingGolden.Count) invariants with golden_missing: YES" -ForegroundColor Yellow
}
Write-Host ""

if ($InvariantsWithGolden.Count -eq 0) {
    Write-Host "No invariants with golden baselines found. Nothing to validate." -ForegroundColor Yellow
    exit 0
}

# (2) Para cada INV, executar gate runner individual
Write-Host "[2] Running gate for each invariant..." -ForegroundColor Yellow
Write-Host ""

$Results = @()
$AggregatedExitCode = 0

foreach ($InvId in $InvariantsWithGolden) {
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Write-Host "Running gate: $InvId" -ForegroundColor White
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    
    # Executar gate runner individual
    & $GateScript $InvId
    $ExitCode = $LASTEXITCODE
    
    # Determinar resultado
    $Result = switch ($ExitCode) {
        0 { "PASS" }
        3 { "DRIFT/OUTDATED" }
        default { "FAIL" }
    }
    
    # Armazenar resultado
    $Results += [PSCustomObject]@{
        InvId = $InvId
        ExitCode = $ExitCode
        Result = $Result
    }
    
    # Atualizar exit code agregado
    # Prioridade: 3 (drift) > 1 (fail) > 0 (pass)
    if ($ExitCode -eq 3) {
        $AggregatedExitCode = 3
    } elseif ($ExitCode -ne 0 -and $AggregatedExitCode -ne 3) {
        $AggregatedExitCode = 1
    }
    
    Write-Host ""
}

# (3) Imprimir resumo
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GATE ALL SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Tabela de resultados
Write-Host ("INV_ID".PadRight(20) + "EXIT_CODE".PadRight(12) + "RESULT") -ForegroundColor White
Write-Host ("-" * 50) -ForegroundColor DarkGray

foreach ($Result in $Results) {
    $Color = switch ($Result.Result) {
        "PASS" { "Green" }
        "DRIFT/OUTDATED" { "Yellow" }
        default { "Red" }
    }
    
    Write-Host ($Result.InvId.PadRight(20) + $Result.ExitCode.ToString().PadRight(12) + $Result.Result) -ForegroundColor $Color
}

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor DarkGray

# Estatísticas
$PassCount  = @($Results | Where-Object { [int]$_.ExitCode -eq 0 }).Count
$DriftCount = @($Results | Where-Object { [int]$_.ExitCode -eq 3 }).Count
$FailCount  = @($Results | Where-Object { [int]$_.ExitCode -ne 0 -and [int]$_.ExitCode -ne 3 }).Count

Write-Host "Total:  $($Results.Count)" -ForegroundColor White
Write-Host "PASS:   $PassCount" -ForegroundColor Green
Write-Host "DRIFT:  $DriftCount" -ForegroundColor Yellow
Write-Host "FAIL:   $FailCount" -ForegroundColor Red
Write-Host ""

# (4) Exit code agregado
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AGGREGATED RESULT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$AggregatedResult = switch ($AggregatedExitCode) {
    0 { "ALL PASS" }
    3 { "DRIFT DETECTED" }
    default { "SOME FAILURES" }
}

$AggregatedColor = switch ($AggregatedExitCode) {
    0 { "Green" }
    3 { "Yellow" }
    default { "Red" }
}

Write-Host "EXIT_CODE:  $AggregatedExitCode" -ForegroundColor White
Write-Host "RESULT:     $AggregatedResult" -ForegroundColor $AggregatedColor
Write-Host ""

# (5) Se houver drift e -Promote ou -WhatIf, processar promoções
if ($DriftCount -gt 0 -and ($Promote -or $WhatIf)) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "GOLDEN BASELINE PROMOTION" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($WhatIf) {
        Write-Host "[DRY-RUN MODE] Commands that would be executed:" -ForegroundColor Yellow
        Write-Host ""
    }
    
    $DriftInvariants = $Results | Where-Object { $_.ExitCode -eq 3 }
    $PromotionCount = 0
    
    foreach ($DriftResult in $DriftInvariants) {
        $InvId = $DriftResult.InvId
        $InvDir = Join-Path $ReportsDir $InvId
        
        Write-Host "Processing: $InvId" -ForegroundColor White
        
        # Encontrar o report mais recente (excluindo _golden_*)
        $LatestReport = Get-ChildItem -Path $InvDir -Directory | 
            Where-Object { $_.Name -notlike "_golden_*" } |
            Sort-Object Name -Descending |
            Select-Object -First 1
        
        if (-not $LatestReport) {
            Write-Host "  ERROR: No non-golden reports found for $InvId" -ForegroundColor Red
            continue
        }
        
        $LatestReportPath = $LatestReport.FullName
        $MetaFile = Join-Path $LatestReportPath "meta.txt"
        
        if (-not (Test-Path $MetaFile)) {
            Write-Host "  ERROR: meta.txt not found in $($LatestReport.Name)" -ForegroundColor Red
            continue
        }
        
        # Ler e validar meta.txt
        $MetaContent = Get-Content $MetaFile -Raw
        $VerifyExit = if ($MetaContent -match 'verify_exit:\s*(\d+)') { [int]$Matches[1] } else { -1 }
        $PytestExit = if ($MetaContent -match 'pytest_exit:\s*(\d+)') { [int]$Matches[1] } else { -1 }
        $ExitCode = if ($MetaContent -match 'exit_code:\s*(\d+)') { [int]$Matches[1] } else { -1 }
        
        Write-Host "  Report:       $($LatestReport.Name)" -ForegroundColor Gray
        Write-Host "  VERIFY_EXIT:  $VerifyExit" -ForegroundColor Gray
        Write-Host "  PYTEST_EXIT:  $PytestExit" -ForegroundColor Gray
        Write-Host "  EXIT_CODE:    $ExitCode" -ForegroundColor Gray
        
        # Validar condições para promoção
        if ($VerifyExit -ne 0) {
            Write-Host "  SKIP: VERIFY_EXIT != 0 (tests have errors)" -ForegroundColor Red
            continue
        }
        
        if ($PytestExit -ne 0) {
            Write-Host "  SKIP: PYTEST_EXIT != 0 (pytest failed)" -ForegroundColor Red
            continue
        }
        
        if ($ExitCode -ne 3) {
            Write-Host "  SKIP: EXIT_CODE != 3 (not drift/outdated)" -ForegroundColor Red
            continue
        }
        
        # Determinar classe primária
        $PrimaryClass = if ($MetaContent -match 'primary_class:\s*(\w+)') { $Matches[1] } else { $null }
        
        if (-not $PrimaryClass) {
            Write-Host "  ERROR: PRIMARY_CLASS not found in meta.txt" -ForegroundColor Red
            continue
        }
        
        Write-Host "  PRIMARY_CLASS: $PrimaryClass" -ForegroundColor Gray
        
        # Paths de promoção
        $GoldenDir = Join-Path $InvDir "_golden_$PrimaryClass"
        
        # Comandos de promoção
        $RemoveCmd = "Remove-Item -Path '$GoldenDir' -Recurse -Force -ErrorAction SilentlyContinue"
        $CopyCmd = "Copy-Item -Path '$LatestReportPath' -Destination '$GoldenDir' -Recurse -Force"
        
        Write-Host ""
        Write-Host "  $RemoveCmd" -ForegroundColor Cyan
        Write-Host "  $CopyCmd" -ForegroundColor Cyan
        Write-Host ""
        
        if (-not $WhatIf) {
            # Executar promoção
            Remove-Item -Path $GoldenDir -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item -Path $LatestReportPath -Destination $GoldenDir -Recurse -Force
            Write-Host "  PROMOTED: _golden_$PrimaryClass" -ForegroundColor Green
            $PromotionCount++
        }
        
        Write-Host ""
    }
    
    if ($WhatIf) {
        Write-Host "Dry-run complete. Use -Promote to execute promotion." -ForegroundColor Yellow
        Write-Host ""
        exit $AggregatedExitCode
    }
    
    Write-Host "Promoted $PromotionCount golden baselines." -ForegroundColor Green
    Write-Host ""
    
    # (6) Re-run gate_all para validar EXIT_ALL=0
    if ($PromotionCount -gt 0) {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "RE-RUNNING GATE_ALL (POST-PROMOTION)" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        
        # Re-executar este script sem -Promote
        & $PSCommandPath -Verbose:$Verbose
        $FinalExitCode = $LASTEXITCODE
        
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FINAL RESULT" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        
        if ($FinalExitCode -eq 0) {
            Write-Host "EXIT_ALL:  $FinalExitCode" -ForegroundColor Green
            Write-Host "RESULT:    ALL PASS (promotion successful)" -ForegroundColor Green
        } else {
            Write-Host "EXIT_ALL:  $FinalExitCode" -ForegroundColor Red
            Write-Host "RESULT:    STILL HAS ISSUES (review promotion)" -ForegroundColor Red
        }
        
        Write-Host ""
        exit $FinalExitCode
    }
}

exit $AggregatedExitCode

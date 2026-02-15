#Requires -Version 5.1
# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=docs
# HB_SCRIPT_SIDE_EFFECTS=NONE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=scripts/checks/docs/check_policy_determinism.ps1
# HB_SCRIPT_OUTPUTS=stdout

<#
.SYNOPSIS
    Valida determinismo do gate de scripts policy (via stdout, sem FS_WRITE)
.DESCRIPTION
    Roda o gate 3x e compara outputs em memória (não cria arquivos).
    Imprime resultado em stdout.
    
    Exit codes:
      0 = DETERMINISMO PROVADO (3 runs idênticos)
      2 = FALHA (outputs divergem)
      3 = ERRO (gate não executou)
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = "C:\HB TRACK"
$Gate = Join-Path $RepoRoot "scripts\_policy\check_scripts_policy.ps1"

Write-Host "`n[check_policy_determinism] Validando determinismo do gate (memória)..." -ForegroundColor Cyan

# Executar gate 3x e capturar output em memória
$Outputs = @()
$ExitCodes = @()

for ($i = 1; $i -le 3; $i++) {
    Write-Host "[Run $i/3] Executando..." -ForegroundColor Cyan
    
    try {
        # Captura output + stderr em memória
        $Output = & $Gate 2>&1 | Out-String
        $ExitCode = $LASTEXITCODE
        
        $Outputs += $Output
        $ExitCodes += $ExitCode
        
        Write-Host "  Exit code: $ExitCode" -ForegroundColor Gray
    }
    catch {
        Write-Error "[ERRO] Falha ao executar gate: $_"
        exit 3
    }
}

Write-Host "`n[ANÁLISE] Comparando 3 runs em memória..." -ForegroundColor Cyan

# Normalizar line endings em memória
$Output1_Norm = $Outputs[0] -replace "`r`n", "`n"
$Output2_Norm = $Outputs[1] -replace "`r`n", "`n"
$Output3_Norm = $Outputs[2] -replace "`r`n", "`n"

# Comparar exit codes
$ExitCodesUnique = $ExitCodes | Sort-Object -Unique
$UniqueCount = @($ExitCodesUnique).Count
if ($UniqueCount -ne 1) {
    Write-Host "[FAIL] Exit codes divergem: $($ExitCodes -join ', ')" -ForegroundColor Red
    exit 2
}
Write-Host "[OK] Exit codes: $($ExitCodes[0])" -ForegroundColor Green

# Comparar outputs
if ($Output1_Norm -ne $Output2_Norm) {
    Write-Host "[FAIL] Outputs 1 vs 2 divergem" -ForegroundColor Red
    exit 2
}
Write-Host "[OK] Outputs 1 vs 2 idênticos" -ForegroundColor Green

if ($Output2_Norm -ne $Output3_Norm) {
    Write-Host "[FAIL] Outputs 2 vs 3 divergem" -ForegroundColor Red
    exit 2
}
Write-Host "[OK] Outputs 2 vs 3 idênticos" -ForegroundColor Green

# Sucesso
Write-Host "`n[DETERMINISMO PROVADO] ✓" -ForegroundColor Green
Write-Host "  3 runs com output byte-idêntico" -ForegroundColor Gray
Write-Host "  Exit codes consistentes ($($ExitCodes[0]))" -ForegroundColor Gray

exit 0


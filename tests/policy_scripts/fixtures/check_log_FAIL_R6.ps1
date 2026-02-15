#Requires -Version 5.1
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: diagnostics
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: tests/policy_scripts/fixtures/check_log_FAIL_R6.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    Sentinela 4: FAIL - Check com side-effect (FS_WRITE)
.DESCRIPTION
    Este script VIOLA R6: checks declararam NONE mas têm FS_WRITE.
    Esperado: FAIL (exit 2) com código CHECKS-E_SIDE_EFFECT_DETECTED
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "[check_log_FAIL] Executando check..." -ForegroundColor Cyan

# ❌ SIDE-EFFECT: checks não podem escrever arquivos
"Debug log entry" | Out-File -FilePath "debug.log"

Write-Host "[OK] Check complete" -ForegroundColor Green
exit 0

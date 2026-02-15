#Requires -Version 5.1
# HB_SCRIPT_KIND: RUNNER
# HB_SCRIPT_SCOPE: testing
# HB_SCRIPT_SIDE_EFFECTS: PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT: false
# HB_SCRIPT_ENTRYPOINT: tests/policy_scripts/fixtures/run_tests_PASS.ps1
# HB_SCRIPT_OUTPUTS: stdout

<#
.SYNOPSIS
    Sentinela 2: PASS - Wrapper que roda pytest
.DESCRIPTION
    Wrapper de testes (RUNNER pode ter PROC_EXEC).
    Esperado: PASS (exit 0)
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "[run_tests_PASS] Wrapper pode executar processos externos" -ForegroundColor Cyan

# Wrappers podem invocar pytest (categoria RUNNER)
# pytest tests/

Write-Host "[OK] Wrapper conforme" -ForegroundColor Green
exit 0

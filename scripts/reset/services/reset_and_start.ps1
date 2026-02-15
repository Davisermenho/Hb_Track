# HB_SCRIPT_KIND=RESET
# HB_SCRIPT_SCOPE=env
# HB_SCRIPT_SIDE_EFFECTS=PROC_START_STOP,DESTRUCTIVE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/reset/services/reset_and_start.ps1
# HB_SCRIPT_OUTPUTS=stdout
# =============================================================================
# SCRIPT COMPLETO: RESET + MIGRATIONS + SEED + START BACKEND + FRONTEND
# =============================================================================
#
# Executa pipeline completo para testes manuais:
# 1. Reset do banco 
# 2. Migrations via Alembic
# 3. Seed inicial
# 4. Inicia backend
# 5. Inicia frontend
#
# Uso: .\reset-and-start.ps1
#
# =============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PIPELINE COMPLETO - TESTE MANUAL" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$ErrorActionPreference = 'Stop'

# =============================================================================
# FASE 1: RESET + MIGRATIONS + SEED
# =============================================================================

Write-Host "[1/4] Executando reset do banco + migrations (alembic + sql) + seed..." -ForegroundColor Cyan

Push-Location "c:\HB TRACK\Hb Track - Backend"

try {
    # Executar reset completo
    .\reset-hb-track-dev.ps1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erro ao executar reset-hb-track-dev.ps1" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Banco resetado, migrations aplicadas e seed executado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao executar reset-hb-track-dev.ps1" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# Aguardar um pouco para garantir que o banco está pronto
Start-Sleep -Seconds 2

# =============================================================================
# PASSO 2: REINICIAR BACKEND
# =============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PASSO 2: Reiniciando Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Parar processo Python existente na porta 8000
Write-Host "Verificando processos na porta 8000..." -ForegroundColor Yellow
$process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($process) {
    Write-Host "Parando processo na porta 8000 (PID: $process)..." -ForegroundColor Yellow
    Stop-Process -Id $process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Iniciar backend
Write-Host "`n[INFO] Iniciando backend..." -ForegroundColor Cyan
Set-Location "c:\HB TRACK\Hb Track - Backend"

# Backend usa .env padrão (hb_track_dev)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\HB TRACK\Hb Track - Backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info --access-log"

Write-Host "Backend iniciando em segundo plano..." -ForegroundColor Green
Write-Host "   Banco: hb_track_dev (localhost:5433)" -ForegroundColor Yellow
Write-Host "   Super Admin: adm@handballtrack.app / Admin@123!" -ForegroundColor Yellow
Write-Host "   Schema: Canonico 100% completo" -ForegroundColor Yellow
Write-Host "Aguardando 8 segundos para backend inicializar..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# =============================================================================
# PASSO 3: INICIAR FRONTEND
# =============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PASSO 3: Iniciando Frontend" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Parar processo Node existente na porta 3000
Write-Host "Verificando processos na porta 3000..." -ForegroundColor Yellow
$nodeProcess = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($nodeProcess) {
    Write-Host "Parando processo na porta 3000 (PID: $nodeProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $nodeProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Verificar se existe package.json no frontend
$frontendPath = "c:\HB TRACK\Hb Track - Fronted"
if (-not (Test-Path "$frontendPath\package.json")) {
    Write-Host "[ERRO] package.json não encontrado em $frontendPath" -ForegroundColor Red
    exit 1
}

# Iniciar frontend
Write-Host "`n[INFO] Iniciando frontend Next.js..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"

Write-Host "Frontend iniciando em segundo plano..." -ForegroundColor Green
Write-Host "URL: http://localhost:3000" -ForegroundColor Yellow
Write-Host "Aguardando 5 segundos para frontend inicializar..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# =============================================================================
# RESULTADO FINAL
# =============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "[OK] PIPELINE COMPLETO EXECUTADO!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Servicos iniciados:" -ForegroundColor Cyan
Write-Host "   Backend: http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Banco de dados:" -ForegroundColor Cyan
Write-Host "   Host: localhost:5433" -ForegroundColor White
Write-Host "   Database: hb_track_dev" -ForegroundColor White
Write-Host "   User: hbtrack_dev" -ForegroundColor White
Write-Host ""
Write-Host "Acesso administrativo:" -ForegroundColor Cyan
Write-Host "   Email: adm@handballtrack.app" -ForegroundColor White
Write-Host "   Senha: Admin@123!" -ForegroundColor White
Write-Host ""
Write-Host "Acesso treinador (E2E):" -ForegroundColor Cyan
Write-Host "   Email: e2e.treinador@teste.com" -ForegroundColor White
Write-Host "   Senha: Admin@123" -ForegroundColor White
Write-Host ""
Write-Host "Status do sistema:" -ForegroundColor Cyan
Write-Host "   Schema canonico 100% completo" -ForegroundColor Green
Write-Host "   Migrations aplicadas (roles, permissions, positions)" -ForegroundColor Green
Write-Host "   Seeds de teste executados (organizacao + atletas)" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Yellow
Write-Host "   1. Acesse http://localhost:3000 para usar o sistema" -ForegroundColor White
Write-Host "   2. Faca login com as credenciais admin acima" -ForegroundColor White
Write-Host "   3. Execute testes: pytest tests/ -v" -ForegroundColor White
Write-Host ""
Write-Host "Para parar os servicos, feche as janelas do PowerShell abertas." -ForegroundColor Gray

# HB_SCRIPT_KIND=OPS
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=PROC_START_STOP
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/ops/infra/ops_start_flower.ps1
# HB_SCRIPT_OUTPUTS=stdout
# Flower - Step 18
# Executa monitoring UI do Celery

Write-Host "Starting Flower (Celery Monitoring UI)..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Navegar para o backend (se não estiver lá)
if (-not (Test-Path "app\core\celery_app.py")) {
    if (Test-Path "Hb Track - Backend") {
        Set-Location "Hb Track - Backend"
    }
}

# Ativar ambiente virtual (se existir)
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & .venv\Scripts\Activate.ps1
}

# Verificar se Redis esta rodando
Write-Host "Checking Redis connection..." -ForegroundColor Cyan
try {
    $redisTest = redis-cli ping 2>&1
    if ($redisTest -ne "PONG") {
        Write-Host "Redis not responding. Starting Redis via Docker..." -ForegroundColor Yellow
        Set-Location "..\infra"
        docker-compose up -d redis
        Start-Sleep -Seconds 3
        Set-Location "..\Hb Track - Backend"
    } else {
        Write-Host "Redis is running" -ForegroundColor Green
    }
} catch {
    Write-Host "redis-cli not found. Make sure Redis is running (docker-compose up -d redis)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting Flower UI..." -ForegroundColor Cyan
Write-Host "   URL: http://localhost:5555" -ForegroundColor Gray
Write-Host "   Auth: admin / hbtrack2026" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Executar flower
# --port=5555: Porta do servidor
# --basic_auth: Autenticacao basica
python -m celery -A app.core.celery_app flower --port=5555 --basic_auth=admin:hbtrack2026

# Mensagem ao encerrar
Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "Flower stopped" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red

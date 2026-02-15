# HB_SCRIPT_KIND=RESET
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE,DESTRUCTIVE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/reset/db/reset_db_e2e.ps1
# HB_SCRIPT_OUTPUTS=stdout
# =============================================================================
# SCRIPT DE RESET + MIGRATION + SEED - BANCO DE DADOS E2E
# =============================================================================
#
# PROPOSITO: Preparar banco de dados E2E do zero
#
# PIPELINE:
#   1. RESET: Limpa banco via Docker (remove volume)
#   2. MIGRATION: Executa Alembic (29 migrações)
#   3. SEED: Popula dados mínimos (Python)
#
# EXECUCAO:
#   .\reset-db-e2e.ps1
#
# SAIDA:
#   - Exit 0: Banco pronto para testes
#   - Exit 1: Erro em alguma fase
#
# TEMPO ESTIMADO: 30-60 segundos
#
# =============================================================================

param(
    [switch]$SkipReset = $false,
    [switch]$SkipMigration = $false,
    [switch]$SkipSeed = $false,
    [switch]$Verbose = $false,
    [int]$PostgresWaitSeconds = 10
)

$ErrorActionPreference = 'Continue'
$phaseStartTime = Get-Date

# Cores
function Write-Success {
    param([string]$Message)
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    Write-Host "[ERRO] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[AVISO] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Section {
    param([string]$Message, [decimal]$Number = 0)
    if ($Number -gt 0) {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "[$Number] $Message" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan
    } else {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "$Message" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan
    }
}

# =============================================================================
# PRE-REQUISITOS
# =============================================================================

Write-Section "PRE-REQUISITOS"

# Validar que estamos no diretorio correto
$backendPath = "c:\HB TRACK\Hb Track - Backend"
$infraPath = "c:\HB TRACK\infra"

if (-not (Test-Path "$infraPath\docker-compose.yml")) {
    Write-Failure "docker-compose.yml nao encontrado em: $infraPath"
    Write-Host "Execute este script do diretorio com docker-compose.yml" -ForegroundColor Yellow
    exit 1
}

Write-Success "Diretorio infra encontrado: $infraPath"

# =============================================================================
# FASE 1: RESET
# =============================================================================

if (-not $SkipReset) {
    Write-Section "FASE 1: RESET (Limpar banco de dados)" 1
    
    Write-Info "Parando docker-compose..."
    Push-Location $infraPath
    
    try {
        docker-compose down --volumes 2>&1 | ForEach-Object {
            if ($Verbose) { Write-Host "  $_" -ForegroundColor Gray }
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker parado e volume removido"
        } else {
            Write-Warning "Erro ao parar docker (pode estar ja parado)"
        }
        
        Write-Info "Removendo container PostgreSQL..."
        docker-compose rm -f postgres 2>&1 | Out-Null
        
        Write-Success "RESET completo - banco limpo"
    } catch {
        Write-Failure "Erro no RESET: $($_.Exception.Message)"
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Info "FASE 1 pulada (-SkipReset)"
}

# =============================================================================
# FASE 1.5: INICIAR DOCKER
# =============================================================================

Write-Section "Iniciando Docker..." 1.5

Push-Location $infraPath

try {
    Write-Info "Subindo docker-compose (PostgreSQL)..."
    docker-compose up -d 2>&1 | ForEach-Object {
        if ($Verbose) { Write-Host "  $_" -ForegroundColor Gray }
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Erro ao iniciar docker-compose"
        exit 1
    }
    
    Write-Success "Docker iniciado"
    
    # Aguardar PostgreSQL estar pronto
    Write-Info "Aguardando PostgreSQL ficar pronto (max $PostgresWaitSeconds segundos)..."
    
    $postgresReady = $false
    $attempts = 0
    $maxAttempts = $PostgresWaitSeconds
    
    while ($attempts -lt $maxAttempts -and -not $postgresReady) {
        try {
            # Tentar conexao simples
            $env:PGPASSWORD = "hbtrack_dev_pwd"
            $pgResult = docker exec -i hbtrack-postgres-dev psql -U hbtrack_dev -d postgres -c "SELECT 1;" 2>&1
            if ($LASTEXITCODE -eq 0) {
                $postgresReady = $true
            }
        } catch {
            $postgresReady = $false
        }
        
        if (-not $postgresReady) {
            Write-Host "  Aguardando... ($attempts/$maxAttempts)" -ForegroundColor Gray
            Start-Sleep -Seconds 1
            $attempts++
        }
    }
    
    if ($postgresReady) {
        Write-Success "PostgreSQL pronto para conexao"
    } else {
        Write-Warning "PostgreSQL nao respondeu a tempo. Continuando mesmo assim..."
    }
    
} catch {
    Write-Failure "Erro ao iniciar Docker: $($_.Exception.Message)"
    exit 1
} finally {
    Pop-Location
}

# =============================================================================
# FASE 1.9: VERIFICAR BANCO DE DADOS
# =============================================================================

Write-Section "Verificando banco de dados DEV..." 1.9

Write-Info "Usando banco hb_track_dev (banco padrão da aplicação)"
Write-Success "Banco hb_track_dev será resetado com dados E2E"

# =============================================================================
# FASE 2: MIGRATION (ALEMBIC)
# =============================================================================

if (-not $SkipMigration) {
    Write-Section "FASE 2: MIGRATION (Alembic - 29 migrações)" 2
    
    Push-Location "$backendPath\db"
    
    try {
        # Garantir variaveis de ambiente para Alembic - USAR BANCO DEV
        $env:DATABASE_URL = "postgresql+psycopg2://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev"
        $env:DATABASE_URL_SYNC = "postgresql+psycopg2://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev"
        $env:DATABASE_URL_ASYNC = "postgresql+asyncpg://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev"
        
        Write-Info "Executando: python -m alembic upgrade heads"
        
        python -m alembic upgrade heads 2>&1 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Migration completa - Schema criado"
        } else {
            Write-Failure "Migration falhou"
            exit 1
        }
        
    } catch {
        Write-Failure "Erro na migration: $($_.Exception.Message)"
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Info "FASE 2 pulada (-SkipMigration)"
}

# =============================================================================
# FASE 3: SEED
# =============================================================================

if (-not $SkipSeed) {
    Write-Section "FASE 3: SEED (Dados minimos)" 3
    
    Push-Location $backendPath
    
    try {
        Write-Info "Executando: python scripts/seed_e2e.py"
        
        $seedOutput = python scripts/seed_e2e.py 2>&1 | Out-String
        Write-Host $seedOutput -ForegroundColor Gray
        
        # Seed é bem-sucedido se contém "training sessions E2E criados" ou "org_memberships E2E criados"
        # (ignorar erro de encoding Unicode no final)
        if ($seedOutput -match "training sessions E2E criados" -or $seedOutput -match "org_memberships E2E criados") {
            Write-Success "Seed E2E completo"
        } else {
            Write-Failure "Seed falhou"
            exit 1
        }
        
    } catch {
        Write-Failure "Erro na seed: $($_.Exception.Message)"
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Info "FASE 3 pulada (-SkipSeed)"
}

# =============================================================================
# RESUMO FINAL
# =============================================================================

$phaseEndTime = Get-Date
$totalDuration = $phaseEndTime - $phaseStartTime

Write-Section "RESUMO"

Write-Success "Reset + Migration + Seed completo!"
Write-Host "`nTempo total: $($totalDuration.ToString('mm\:ss'))" -ForegroundColor Cyan
Write-Host "`nBanco pronto em: hb_track_dev (com dados E2E)" -ForegroundColor Green
Write-Host "PostgreSQL rodando em: localhost:5433" -ForegroundColor Green

exit 0

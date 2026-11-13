# CertVerify AI - Multi-Service Launcher (Docker & Non-Docker Compatible)
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "       Starting CertVerify AI Services...          " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Check & Start Redis
Write-Host "[1/4] Checking Redis on port 6379..." -ForegroundColor Yellow
$redisRunning = Get-NetTCPConnection -LocalPort 6379 -ErrorAction SilentlyContinue

if ($redisRunning) {
    Write-Host "Redis is already running on port 6379." -ForegroundColor Green
} else {
    $hasDocker = Get-Command docker -ErrorAction SilentlyContinue
    if ($hasDocker) {
        try {
            Write-Host "Starting Redis via Docker..." -ForegroundColor Yellow
            docker start certverify-redis | Out-Null
        } catch {
            docker run -d -p 6379:6379 --name certverify-redis redis:7-alpine | Out-Null
        }
    } else {
        # Check if local redis-server.exe exists in common locations or in PATH
        $localRedis = Get-Command redis-server -ErrorAction SilentlyContinue
        if ($localRedis) {
            Start-Process redis-server
            Write-Host "Started native Redis process." -ForegroundColor Green
        } else {
            Write-Host "WARNING: Redis not detected on port 6379." -ForegroundColor Red
            Write-Host "Please start 'redis-server.exe' (download from https://github.com/tporadowski/redis/releases) or Memurai." -ForegroundColor Yellow
        }
    }
}

# 2. FastAPI Backend
Write-Host "[2/4] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\venv\Scripts\activate; uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

# 3. Celery Worker (solo mode for Windows)
Write-Host "[3/4] Starting Celery Worker (solo mode)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\venv\Scripts\activate; celery -A app.core.celery_app worker --loglevel=info -P solo"

# 4. React Frontend
Write-Host "[4/4] Starting React Frontend on http://localhost:3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "===================================================" -ForegroundColor Green
Write-Host "All services initiated!" -ForegroundColor Green
Write-Host "  Frontend : http://localhost:3000" -ForegroundColor Green
Write-Host "  API Docs : http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

@echo off
title CertVerify AI - Launch All Services (Zero-Docker Compatible)
echo ===================================================
echo        Starting CertVerify AI Services...
echo ===================================================

echo [1/4] Checking Redis on port 6379...
netstat -ano | findstr ":6379" >nul
if %errorlevel% equ 0 (
    echo Redis is already running on port 6379.
) else (
    where docker >nul 2>nul
    if %errorlevel% equ 0 (
        echo Starting Redis via Docker...
        docker start certverify-redis 2>nul || docker run -d -p 6379:6379 --name certverify-redis redis:7-alpine
    ) else (
        where redis-server >nul 2>nul
        if %errorlevel% equ 0 (
            echo Starting native redis-server...
            start "Redis Server" redis-server
        ) else (
            echo WARNING: Redis is not running on port 6379!
            echo Please run redis-server.exe ^(download from https://github.com/tporadowski/redis/releases^).
        )
    )
)

echo [2/4] Starting FastAPI Backend on http://127.0.0.1:8000...
start "CertVerify - Backend (FastAPI)" cmd /k "cd /d %~dp0backend && .\venv\Scripts\activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [3/4] Starting Celery AI Verification Worker...
start "CertVerify - Worker (Celery)" cmd /k "cd /d %~dp0backend && .\venv\Scripts\activate && celery -A app.core.celery_app worker --loglevel=info -P solo"

echo [4/4] Starting React Frontend on http://localhost:3000...
start "CertVerify - Frontend (React/Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo ===================================================
echo All services launched!
echo   Frontend : http://localhost:3000
echo   API Docs : http://127.0.0.1:8000/docs
echo ===================================================
pause

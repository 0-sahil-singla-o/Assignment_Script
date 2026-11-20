@echo off
title Academic Assignment Studio Launcher
echo ========================================================
echo   Starting Academic Assignment Studio (v2.0 LPU)
echo ========================================================

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "Backend - FastAPI" cmd /k "python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Launching React + Vite Frontend on http://localhost:5173 ...
start "Frontend - Vite React" cmd /k "cd frontend && npm run dev"

echo.
echo Both services are spinning up!
echo Backend API Docs: http://localhost:8000/docs
echo Frontend Studio:  http://localhost:5173
echo.
pause

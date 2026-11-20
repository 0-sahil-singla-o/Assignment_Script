# Academic Assignment Studio Launcher (PowerShell)
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting Academic Assignment Studio (v2.0 LPU)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host "[1/2] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "[2/2] Starting React + Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`nBoth services launched!" -ForegroundColor Yellow
Write-Host "Frontend Studio: http://localhost:5173" -ForegroundColor Yellow
Write-Host "Backend API:    http://localhost:8000/docs" -ForegroundColor Yellow

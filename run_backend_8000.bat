@echo off
setlocal
cd /d "%~dp0"
REM Runs FastAPI backend on port 8000
REM Run from project root so `backend.*` and `src.*` imports resolve consistently
"%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
pause

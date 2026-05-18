@echo off
setlocal
cd /d "%~dp0"
REM Runs FastAPI backend (v1 API contract + auth) on port 8002
REM IMPORTANT: run from project root so `backend.*` and `src.*` imports resolve
"%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8002 --log-level info
pause

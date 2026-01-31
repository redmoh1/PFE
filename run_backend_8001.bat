@echo off
setlocal
cd /d "%~dp0backend"
REM Runs FastAPI backend (v1) on port 8001
"%~dp0..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8001 --log-level info
pause

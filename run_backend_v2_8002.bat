@echo off
setlocal
cd /d "%~dp0backend"
REM Runs FastAPI backend v2 (enhanced) on port 8002
"%~dp0..\.venv\Scripts\python.exe" -m uvicorn main_enhanced:app --host 127.0.0.1 --port 8002 --log-level info
pause

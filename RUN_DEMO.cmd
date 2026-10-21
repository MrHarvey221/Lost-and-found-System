@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Set up the virtual environment using README.md first.
  pause
  exit /b 1
)
set "DATABASE_URL=sqlite:///./findly-demo.db"
set "DATA_DIR=./data-demo"
set "DEMO_MODE=true"
.venv\Scripts\python.exe manage.py seed-demo
if errorlevel 1 exit /b 1
echo Open http://127.0.0.1:8001/
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001

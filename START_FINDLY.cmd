@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Set up the virtual environment using README.md first.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8002/
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002
